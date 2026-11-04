# HAM LOG

Everything built on the `study-lab` branch during the 8-hour push, one entry per change.
Newest entries go at the bottom of each section's list; the numbers are stable IDs.

**How to read an entry:** what you'd notice, why it should work, how sure I am, and the commit.

**Status tags**
- ✅ tested = automated test and/or driven in the running app
- 🎤 needs a human = I can't test real speech from here; logic tested, voice path not
- 🧪 judgment call = sound reasoning, but you may disagree with the taste or the tradeoff

---

## For the agent reviewing this after the reset

- **Base:** `study-lab` branches from `phase-9-10-wip` at `2e6269f` (Kaiwa 2.1.0). Local `master` is 55 commits *behind* that, so `phase-9-10-wip` is the real trunk. Check with the owner which branch "main" means before applying anything.
- **Not pushed.** The branch is local only.
- **Each entry is its own commit** (the ID is in the commit subject, e.g. `[H12]`), so changes can be cherry-picked. Later entries may depend on earlier ones; dependencies are listed in the entry.
- **Tests:** `scripts/smoke_lab.py` covers this branch's logic with no network. Existing `scripts/smoke_course.py`, `smoke_learn.py` and `smoke_state_files.py` must keep passing. `scripts/sim_pacing.py` simulates a learner through the real scheduler.
- **Review for:** whether it fits Kaiwa's rule ("does this help them understand or speak?"), migration of existing `course_state.json`, and anything marked 🎤 or 🧪.

---

## Changes

