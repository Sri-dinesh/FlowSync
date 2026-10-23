# FlowSync server

FastAPI service, traffic simulation, classical/learned controllers and training.
Use Python 3.11 for the pinned CPU Torch dependency set. The locally preserved
Python 3.14 research environment is a separate existing installation; a fresh
installation of these requirements should use 3.11.

| Path | Purpose |
| --- | --- |
| `app/main.py` | Application lifespan and route/WebSocket registration |
| `app/routers/`, `app/websockets/` | HTTP and live-session interfaces |
| `app/controllers/` | Controller proposals, supervision and signal guards |
| `app/simulation/` | Traffic dynamics, demand, observations and rewards |
| `app/rl/` | Networks, replay, agent and application trainer |
| `app/realworld/` | Experimental camera, replay and detector-training modules |
| `app/services/` | Supabase persistence and checkpoint storage |
| `tests/` | API, simulation, RL, perception and research regressions |
| `scripts/` | Application-model and database maintenance utilities |

From the repository root:

```bash
python3.11 -m venv server/.venv
server/.venv/bin/python -m pip install -r research/requirements.txt -r server/requirements-dev.txt
server/.venv/bin/python -m uvicorn app.main:app --app-dir server --reload --port 8000
```

See [setup](../docs/setup.md) for `server/.env`, database and Docker instructions.
`requirements.txt` covers the application, `requirements-vision.txt` adds model
training/inference/export, and `requirements-dev.txt` covers testing. Statistical
analysis/evidence-export dependencies live in `../research/requirements.txt`.

The application trainer and audited research trainer have distinct reward,
observation-version and replay integration. A research checkpoint is not
automatically compatible with website inference. See
[architecture](../docs/architecture.md) and [research](../research/README.md).
