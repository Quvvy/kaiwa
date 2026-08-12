from __future__ import annotations

from collections.abc import Iterator

from openai import OpenAI

from kaiwa.config import Settings
from kaiwa.learner_memory import LearnerMemory, load_memory
from kaiwa.learner_profile import (
    LearnerProfile,
    load_profile,
    needs_pro_routing,
)
from kaiwa.persona import (
    build_practice_tip_system_prompt,
    build_tutor_system_prompt,
    infer_help_type,
    infer_learner_state,
)
from kaiwa.prefs import UserPrefs, load_prefs


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
) -> tuple[UserPrefs, LearnerProfile, LearnerMemory, str, str, str]:
    """Return prefs, profile, memory, learner_state, system prompt, model id."""
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
    system = build_tutor_system_prompt(
        prefs,
        last_user_text=last_user,
        last_assistant_text=last_assistant or None,
        profile=profile,
        memory=memory,
        learner_state=state,
    )
    use_pro = needs_pro_routing(prefs, profile, state, help_type=ht)
    model = settings.deepseek_model_pro if use_pro else settings.deepseek_model
    return prefs, profile, memory, state, system, model


def chat(
    settings: Settings,
    messages: list[dict[str, str]],
    *,
    prefs: UserPrefs | None = None,
    profile: LearnerProfile | None = None,
    memory: LearnerMemory | None = None,
    learner_state: str | None = None,
    help_type: str | None = None,
    client: OpenAI | None = None,
) -> tuple[str, str]:
    """Return (reply_text, model_used)."""
    _prefs, _profile, _memory, _state, system, model = _prepare_chat(
        settings,
        messages,
        prefs=prefs,
        profile=profile,
        memory=memory,
        learner_state=learner_state,
        help_type=help_type,
    )
    reply = _completion(settings, system, messages, client=client, model=model)
    return reply, model


def chat_stream(
    settings: Settings,
    messages: list[dict[str, str]],
    *,
    prefs: UserPrefs | None = None,
    profile: LearnerProfile | None = None,
    memory: LearnerMemory | None = None,
    learner_state: str | None = None,
    help_type: str | None = None,
    client: OpenAI | None = None,
) -> tuple[str, Iterator[str]]:
    """Return (model_used, iterator of text deltas)."""
    _prefs, _profile, _memory, _state, system, model = _prepare_chat(
        settings,
        messages,
        prefs=prefs,
        profile=profile,
        memory=memory,
        learner_state=learner_state,
        help_type=help_type,
    )
    client = client or make_client(settings)
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

    return model, _deltas()


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
