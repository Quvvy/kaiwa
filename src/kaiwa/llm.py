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
    SHAPE_RETRY_BLOCK,
    build_practice_tip_system_prompt,
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
) -> str:
    client = client or make_client(settings)
    payload: list[dict[str, str]] = [{"role": "system", "content": system}, *messages]
    kwargs: dict = {
        "model": model or settings.deepseek_model,
        "messages": payload,
    }
    if settings.deepseek_thinking in {"disabled", "enabled"}:
        kwargs["extra_body"] = {"thinking": {"type": settings.deepseek_thinking}}

    response = client.chat.completions.create(**kwargs)
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("DeepSeek returned an empty reply")
    return content.strip()


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
) -> tuple[UserPrefs, LearnerProfile, LearnerMemory, str, str, str, bool]:
    """Return prefs, profile, memory, learner_state, system, model, shape_lock."""
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
    state = learner_state or infer_learner_state(last_user)
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
    system = build_tutor_system_prompt(
        prefs,
        last_user_text=last_user,
        last_assistant_text=last_assistant or None,
        profile=profile,
        memory=memory,
        learner_state=state,
        replay_questions=replay_questions,
    )
    use_pro = needs_pro_routing(prefs, profile, state, help_type=ht)
    model = settings.deepseek_model_pro if use_pro else settings.deepseek_model
    return prefs, profile, memory, state, system, model, locked


def _complete_with_retry(
    settings: Settings,
    system: str,
    messages: list[dict[str, str]],
    *,
    locked: bool,
    client: OpenAI | None = None,
    model: str | None = None,
) -> tuple[str, bool]:
    reply = _completion(settings, system, messages, client=client, model=model)
    if not locked or not reply_too_dense(reply):
        return reply, False
    retry_system = system.rstrip() + "\n\n" + SHAPE_RETRY_BLOCK.strip()
    try:
        reply = _completion(
            settings, retry_system, messages, client=client, model=model
        )
        return reply, True
    except Exception:
        return reply, False


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
    _prefs, _profile, _memory, _state, system, model, locked = _prepare_chat(
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
        settings, system, messages, locked=locked, client=client, model=model
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
    use_pro = needs_pro_routing(prefs, profile, state, help_type=ht)
    model = settings.deepseek_model_pro if use_pro else settings.deepseek_model
    prior = messages[:-1] if messages else []
    reply, retry = _complete_with_retry(
        settings, system, prior, locked=locked, client=client, model=model
    )
    return ChatGeneration(reply=reply, model=model, retry=retry, locked=locked)


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
    """Stream deltas. When shape-locked, finish (+ retry) before yielding so TTS waits."""
    _prefs, _profile, _memory, _state, system, model, locked = _prepare_chat(
        settings,
        messages,
        prefs=prefs,
        profile=profile,
        memory=memory,
        learner_state=learner_state,
        help_type=help_type,
        replay_questions=replay_questions,
    )
    client = client or make_client(settings)

    if locked:
        reply, retry = _complete_with_retry(
            settings, system, messages, locked=True, client=client, model=model
        )

        def _one() -> Iterator[str]:
            yield reply

        return ChatStreamStart(
            model=model, deltas=_one(), retry=retry, locked=True
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


def practice_tip(
    settings: Settings,
    *,
    target: str,
    heard: str,
    score: int,
    band: str,
    prefs: UserPrefs | None = None,
    client: OpenAI | None = None,
) -> str:
    prefs = prefs or load_prefs()
    user = (
        f"目標文: {target}\n"
        f"聞こえた文: {heard}\n"
        f"明瞭さスコア: {score}/100（{band}）\n"
        "短いヒントをください。"
    )
    return _completion(
        settings,
        build_practice_tip_system_prompt(prefs),
        [{"role": "user", "content": user}],
        client=client,
        model=settings.deepseek_model,
    )
