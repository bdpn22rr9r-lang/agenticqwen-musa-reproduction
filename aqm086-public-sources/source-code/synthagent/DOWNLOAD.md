# SynthAgent — source code & data acquisition

## Code repository (frozen)
- URL: https://github.com/aiming-lab/SynthAgent
- Commit: `bae3603e9115cf9de4b317abac1d4a19369601e2`
- Paper: https://aclanthology.org/2026.acl-long.716/
- License: **NONE** in repository → UNCONFIRMED → see [../../licenses/SYNTHAGENT_LICENSE.txt](../../licenses/SYNTHAGENT_LICENSE.txt)
- Codeload zip sha256 (this commit): `6e639bc69539a2ff7d9c01e24022809c335b460465ec15a9fd38bc7e0b45f52d` (953830 B)

```bash
git clone https://github.com/aiming-lab/SynthAgent.git
cd SynthAgent && git checkout bae3603e9115cf9de4b317abac1d4a19369601e2
```

## Data
- Public **tasks + trajectories** are published **ONLY on Hugging Face** (`ChilleD/SynthAgent`).
- AQM086 rule 1 forbids HF as a source, and no non-HF public mirror was found → **data NOT obtained**.
- `data_status = CODE_ONLY` · `task_count = 0` · `trajectory_count = 0`
- `configs/webarena.jsonl` is a WebArena **evaluation config** → evaluation_only.

## What the code repo contains (method, not data)
Task synthesis, environment/tool definitions, trajectory collection + refinement
(`synthagent.py`, `multi_exeagent.py`, `scoreagent.py`, `convert_data.py`), and the
WebArena eval harness. It does **not** ship the synthesized task/trajectory data.

## Conclusion
No agentic training data is obtainable from an allowed channel. Code files
must **not** be counted as training samples. Whether tasks are executable,
whether trajectories are refined, and whether env state is present **cannot be
verified** because the data is absent (HF-only).
