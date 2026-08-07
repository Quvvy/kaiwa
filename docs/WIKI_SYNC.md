# Wiki sync

Vault: `C:\Users\elifs\Projects\llm-wiki`  
Cursor rule: `.cursor/rules/wiki-sync.mdc` (**always apply**)

## Policy

After **every** change in this repo, the agent must decide whether llm-wiki needs an update.

- **If the change updates durable project knowledge** (architecture, decisions, roadmap, stack, goals, status, README facts) → sync canonical docs to `raw/kaiwa/`, refresh related wiki pages, update `wiki/index.md`, append `wiki/log.md`.
- **If not** → **do not** touch the wiki (no empty log entries, no date-only bumps).

Follow the vault `AGENTS.md` for ingest conventions. Tag with `kaiwa`.

## Canonical → raw map

| This repo | Wiki raw |
|-----------|----------|
| `README.md` | `raw/kaiwa/README.md` |
| `docs/ARCHITECTURE.md` | `raw/kaiwa/ARCHITECTURE.md` |
| `docs/DECISIONS.md` | `raw/kaiwa/DECISIONS.md` |
| `docs/ROADMAP.md` | `raw/kaiwa/ROADMAP.md` |
| `docs/WIKI_SYNC.md` | `raw/kaiwa/WIKI_SYNC.md` |

## Related wiki pages

- Entity: `wiki/entities/kaiwa.md`
- Concepts: hybrid speech pipeline, local Japanese TTS, Japanese AI conversation partner
- Sources: `wiki/sources/kaiwa-*.md`
