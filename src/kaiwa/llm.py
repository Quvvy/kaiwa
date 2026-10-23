from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from openai import OpenAI

from kaiwa.config import Settings
from kaiwa.learner_memory import LearnerMemory, load_memory
from kaiwa.learner_profile import (
    LearnerProfile,
    load_profile,
    needs_pro_routing,
)
from kaiwa.persona import (
    RECAST_RETRY_BLOCK,
    SHAPE_RETRY_BLOCK,
    build_practice_sitting_system_prompt,
    build_tutor_system_prompt,
    compute_support_mode,
    governor_pitch,
    infer_help_type,
    infer_learner_state,
    rescue_rewrite_block,
    shape_lock_active,
)
from kaiwa.prefs import UserPrefs, load_prefs
from kaiwa.reply_shape import reply_too_dense
from kaiwa.wo_ga import (
    expects_recast,
    needs_any_recast,
    prefer_recast_reply,
)


@dataclass(frozen=True)
class ChatGeneration:
    """One Chat LLM result. `retry` / `locked` feed silent reply_shape logs."""

    reply: str
    model: str
    retry: bool
    locked: bool


@dataclass
class ChatStreamStart:
    model: str
    deltas: Iterator[str]
    retry: bool
    locked: bool


def make_client(settings: Settings) -> OpenAI:
    # Explicit timeout — default OpenAI client can hang forever on a bad network path.
    return OpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        timeout=90.0,
    )


def _completion(
    settings: Settings,
    system: str,
    messages: list[dict[str, str]],
    *,
    client: OpenAI | None = None,
    model: str | None = None,
    json_mode: bool = False,
) -> str:
    client = client or make_client(settings)
    payload: list[dict[str, str]] = [{"role": "system", "content": system}, *messages]
    kwargs: dict = {
        "model": model or settings.deepseek_model,
        "messages": payload,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    if settings.deepseek_thinking in {"disabled", "enabled"}:
        kwargs["extra_body"] = {"thinking": {"type": settings.deepseek_thinking}}

    response = client.chat.completions.create(**kwargs)
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("DeepSeek returned an empty reply")
    return content.strip()


def complete_json(
    settings: Settings,
    system: str,
    user: str,
    *,
    client: OpenAI | None = None,
    model: str | None = None,
) -> dict | None:
    """One JSON-mode call (Flash unless `model` says otherwise). None on any failure."""
    import json

    try:
        raw = _completion(
            settings, system, [{"role": "user", "content": user}], client=client, model=model, json_mode=True
        )
        data = json.loads(raw)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _prepare_chat(
    settings: Settings,
    messages: list[dict[str, str]],
    *,
    prefs: UserPrefs | None = None,
    profile: LearnerProfile | None = None,
    memory: LearnerMemory | None = None,
    learner_state: str | None = None,
    help_type: str | None = None,
    replay_questions: list[str] | None = None,
) -> tuple[UserPrefs, LearnerProfile, LearnerMemory, str, str, str, bool, str, str]:
    """Return prefs, profile, memory, learner_state, system, model, shape_lock, last_user, last_assistant."""
    prefs = prefs or load_prefs()
    profile = profile or load_profile()
    memory = memory or load_memory()
    last_user = ""
    last_assistant = ""
    for message in reversed(messages):
        role = message.get("role")
        content = (message.get("content") or "").strip()
        if not content:
            continue
        if not last_user and role == "user":
            last_user = content
        elif not last_assistant and role == "assistant":
            last_assistant = content
        if last_user and last_assistant:
            break
    state = learner_state or infer_learner_state(last_user, last_assistant)
    ht = help_type if help_type is not None else infer_help_type(last_user)
    support = compute_support_mode(
        learner_state=state,
        help_type=ht,
        struggle_streak=profile.stats.struggle_streak,
    )
    locked = shape_lock_active(
        governor_pitch(prefs, profile, state, support_mode=support),
        support,
        chat_pace=prefs.chat_pace,
    )
    from kaiwa.course.state import known_phrases_for_chat
    from kaiwa.practice.sitting import peek_pending_elicit

    try:
        known = known_phrases_for_chat()
    except Exception:
        known = None
    system = build_tutor_system_prompt(
        prefs,
        last_user_text=last_user,
        last_assistant_text=last_assistant or None,
        profile=profile,
        memory=memory,
        learner_state=state,
        help_type=ht,
        replay_questions=replay_questions,
        elicit_line=peek_pending_elicit(),
        known_phrases=known,
    )
    use_pro = needs_pro_routing(settings.model_routing, profile, state, help_type=ht)
    model = settings.deepseek_model_pro if use_pro else settings.deepseek_model
    return prefs, profile, memory, state, system, model, locked, last_user, last_assistant


def _complete_with_retry(
    settings: Settings,
    system: str,
    messages: list[dict[str, str]],
    *,
    locked: bool,
    last_user: str = "",
    last_assistant: str = "",
    allow_recast: bool = True,
    client: OpenAI | None = None,
    model: str | None = None,
) -> tuple[str, bool]:
    reply = _completion(settings, system, messages, client=client, model=model)
    need_shape = locked and reply_too_dense(reply)
    need_recast = bool(
        allow_recast and last_user and needs_any_recast(last_user, reply, last_assistant)
    )
    if not need_shape and not need_recast:
        return reply, False
    extra: list[str] = []
    if need_recast:
        extra.append(RECAST_RETRY_BLOCK.strip())
    if need_shape:
        extra.append(SHAPE_RETRY_BLOCK.strip())
    retry_system = system.rstrip() + "\n\n" + "\n\n".join(extra)
    try:
        retry_reply = _completion(
            settings, retry_system, messages, client=client, model=model
        )
    except Exception:
        if need_recast:
            chosen, landed = prefer_recast_reply(
                last_user, reply, "", last_assistant
            )
            return chosen, landed
        return reply, False
    if need_recast:
        chosen, landed = prefer_recast_reply(
            last_user, reply, retry_reply, last_assistant
        )
        return chosen, landed
    # Shape-only retry must not throw away a recast that already landed.
    if allow_recast and last_user and expects_recast(last_user, last_assistant):
        if needs_any_recast(
            last_user, retry_reply, last_assistant
        ) and not needs_any_recast(last_user, reply, last_assistant):
            return reply, True
    return retry_reply, True


def chat(
    settings: Settings,
    messages: list[dict[str, str]],
    *,
    prefs: UserPrefs | None = None,
    profile: LearnerProfile | None = None,
    memory: LearnerMemory | None = None,
    learner_state: str | None = None,
    help_type: str | None = None,
    replay_questions: list[str] | None = None,
    client: OpenAI | None = None,
) -> ChatGeneration:
    """Return reply text, model id, and shape-lock retry flags."""
    _prefs, _profile, _memory, _state, system, model, locked, last_user, last_assistant = _prepare_chat(
        settings,
        messages,
        prefs=prefs,
        profile=profile,
        memory=memory,
        learner_state=learner_state,
        help_type=help_type,
        replay_questions=replay_questions,
    )
    reply, retry = _complete_with_retry(
        settings,
        system,
        messages,
        locked=locked,
        last_user=last_user,
        last_assistant=last_assistant,
        client=client,
        model=model,
    )
    return ChatGeneration(reply=reply, model=model, retry=retry, locked=locked)


def rescue_rewrite(
    settings: Settings,
    messages: list[dict[str, str]],
    *,
    prefs: UserPrefs | None = None,
    profile: LearnerProfile | None = None,
    memory: LearnerMemory | None = None,
    last_user: str = "",
    last_assistant: str = "",
    step: str = "shorter",
    replay_questions: list[str] | None = None,
    client: OpenAI | None = None,
) -> ChatGeneration:
    """Rewrite the last Kaiwa line. `messages` should still include that assistant turn."""
    prefs = prefs or load_prefs()
    profile = profile or load_profile()
    memory = memory or load_memory()
    state = "help_request"
    ht = "comprehension"
    support = compute_support_mode(
        learner_state=state,
        help_type=ht,
        struggle_streak=profile.stats.struggle_streak,
    )
    locked = shape_lock_active(
        governor_pitch(prefs, profile, state, support_mode=support),
        support,
        chat_pace=prefs.chat_pace,
    )
    system = build_tutor_system_prompt(
        prefs,
        last_user_text=last_user,
        last_assistant_text=last_assistant or None,
        profile=profile,
        memory=memory,
        learner_state=state,
        help_type=ht,
        replay_questions=replay_questions,
    )
    system = system.rstrip() + "\n\n" + rescue_rewrite_block(last_assistant, step).strip()
    use_pro = needs_pro_routing(settings.model_routing, profile, state, help_type=ht)
    model = settings.deepseek_model_pro if use_pro else settings.deepseek_model
    prior = messages[:-1] if messages else []
    reply, retry = _complete_with_retry(
        settings,
        system,
        prior,
        locked=locked,
        allow_recast=False,
        client=client,
        model=model,
    )
    return ChatGeneration(reply=reply, model=model, retry=retry, locked=locked)


def practice_sitting(
    settings: Settings,
    messages: list[dict[str, str]],
    card: dict,
    *,
    remaining_turns: int,
    opening: bool = False,
    wrap: bool = False,
    prefs: UserPrefs | None = None,
    memory: LearnerMemory | None = None,
    client: OpenAI | None = None,
) -> ChatGeneration:
    """Easy-locked sitting turn. Always locked, even if Chat pace is Free."""
    prefs = prefs or load_prefs()
    memory = memory or load_memory()
    system = build_practice_sitting_system_prompt(
        prefs,
        card,
        remaining_turns=remaining_turns,
        opening=opening,
        wrap=wrap,
        memory=memory,
    )
    model = settings.deepseek_model
    reply, retry = _complete_with_retry(
        settings,
        system,
        messages,
        locked=True,
        allow_recast=False,
        client=client,
        model=model,
    )
    return ChatGeneration(reply=reply, model=model, retry=retry, locked=True)


def chat_stream(
    settings: Settings,
    messages: list[dict[str, str]],
    *,
    prefs: UserPrefs | None = None,
    profile: LearnerProfile | None = None,
    memory: LearnerMemory | None = None,
    learner_state: str | None = None,
    help_type: str | None = None,
    replay_questions: list[str] | None = None,
    client: OpenAI | None = None,
) -> ChatStreamStart:
    """Stream deltas. Buffer when shape-locked or a recast is expected."""
    _prefs, _profile, _memory, _state, system, model, locked, last_user, last_assistant = (
        _prepare_chat(
            settings,
            messages,
            prefs=prefs,
            profile=profile,
            memory=memory,
            learner_state=learner_state,
            help_type=help_type,
            replay_questions=replay_questions,
        )
    )
    client = client or make_client(settings)
    expect_recast = expects_recast(last_user, last_assistant)

    if locked or expect_recast:
        reply, retry = _complete_with_retry(
            settings,
            system,
            messages,
            locked=locked,
            last_user=last_user,
            last_assistant=last_assistant,
            client=client,
            model=model,
        )

        def _one() -> Iterator[str]:
            yield reply

        return ChatStreamStart(
            model=model, deltas=_one(), retry=retry, locked=locked
        )

    payload: list[dict[str, str]] = [{"role": "system", "content": system}, *messages]
    kwargs: dict = {
        "model": model,
        "messages": payload,
        "stream": True,
    }
    if settings.deepseek_thinking in {"disabled", "enabled"}:
        kwargs["extra_body"] = {"thinking": {"type": settings.deepseek_thinking}}

    stream = client.chat.completions.create(**kwargs)

    def _deltas() -> Iterator[str]:
        got = False
        for chunk in stream:
            choices = getattr(chunk, "choices", None) or []
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            content = getattr(delta, "content", None) if delta is not None else None
            if not content:
                continue
            got = True
            yield content
        if not got:
            raise RuntimeError("DeepSeek returned an empty reply")

    return ChatStreamStart(
        model=model, deltas=_deltas(), retry=False, locked=False
    )
