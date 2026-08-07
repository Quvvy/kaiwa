from __future__ import annotations

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
    infer_learner_state,
)
from kaiwa.prefs import UserPrefs, load_prefs


def make_client(settings: Settings) -> OpenAI:
    return OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)


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


def chat(
    settings: Settings,
    messages: list[dict[str, str]],
    *,
    prefs: UserPrefs | None = None,
    profile: LearnerProfile | None = None,
    memory: LearnerMemory | None = None,
    learner_state: str | None = None,
    client: OpenAI | None = None,
) -> tuple[str, str]:
    """Return (reply_text, model_used)."""
    prefs = prefs or load_prefs()
    profile = profile or load_profile()
    memory = memory or load_memory()
    last_user = ""
    for message in reversed(messages):
        if message.get("role") == "user" and message.get("content"):
            last_user = message["content"]
            break
    state = learner_state or infer_learner_state(last_user)
    system = build_tutor_system_prompt(
        prefs,
        last_user_text=last_user,
        profile=profile,
        memory=memory,
    )
    use_pro = needs_pro_routing(prefs, profile, state)
    model = settings.deepseek_model_pro if use_pro else settings.deepseek_model
    reply = _completion(settings, system, messages, client=client, model=model)
    return reply, model


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
