# FlowSync

Traffic-signal simulation, reinforcement-learning experiments and an interactive
research dashboard, built with Next.js, FastAPI and PyTorch.

FlowSync is a simulation research prototype. The audited learned controllers
have **not established a reliable advantage over Max-Pressure**. Camera and city
interfaces are experimental; their presence does not establish field accuracy,
hardware readiness or equivalence with the audited headless experiments.
See the [current research status](research/RESEARCH_STATUS.md).

## What is included

- A Next.js dashboard for simulation, training, model history, comparisons and replay.
- A FastAPI service with REST and WebSocket interfaces.
- Classical controllers, DQN/D3QN policies, uncertainty fallback and signal guards.
- Headless research tools with explicit checkpoints, paired traffic seeds,
  synthetic sensing faults, source provenance and executed-signal audits.
- Experimental camera replay, vehicle-detection and multi-intersection modules.

## Getting started

Use Python **3.11**, Node.js **24** and npm. Frontend dependencies are locked in
`client/package-lock.json`; npm is the supported JavaScript package manager.
Supabase/PostgreSQL configuration is needed for the full application. Headless
research experiments and mocked unit tests do not require cloud credentials.

```bash
python3.11 -m venv server/.venv
server/.venv/bin/python -m pip install -r research/requirements.txt -r server/requirements-dev.txt
cp server/.env.example server/.env
cp client/.env.example client/.env.local
npm --prefix client ci
```

Fill in the private environment files using the [setup guide](docs/setup.md),
then start the services in separate terminals:

```bash
server/.venv/bin/python -m uvicorn app.main:app --app-dir server --reload --port 8000
npm --prefix client run dev
```

Open [the dashboard](http://localhost:3000) and
[the API documentation](http://localhost:8000/docs).
Camera training/export dependencies are optional; see the setup guide.

## Repository map

| Path | Purpose |
| --- | --- |
| [client/](client/README.md) | Next.js application and Prisma schema |
| [server/](server/README.md) | API, controllers, simulation, RL and backend tests |
| [research/](research/README.md) | Audited tools and grouped research documentation |
| [docs/](docs/README.md) | Setup and architecture guides |
| [scripts/](scripts/README.md) | Development, dataset and model utilities |
| [colab/](colab/README.md) | Optional detector-training notebook |
| [results/](results/README.md) | Artifact policy and historical-result interpretation |

Local checkpoints, datasets, recordings, credentials and raw experiment runs
are excluded from version control. Existing artifacts must be preserved when
reproducing or extending research.

## Development checks

From the repository root, with the Python environment installed:

```bash
make check-repository
make lint
make typecheck
make test
make build
```

The Makefile accepts `PYTHON=/path/to/python` and detects an existing
`server/.venv` or `server/venv`. Equivalent commands and testing scope are in
[CONTRIBUTING.md](CONTRIBUTING.md). Tests do not establish research superiority
or deployment readiness. CI is configured in [.github/workflows/ci.yml](.github/workflows/ci.yml).

## Research

Start with the [research index](research/README.md),
[evaluation audit](research/EVALUATION_AUDIT.md) and
[current status](research/RESEARCH_STATUS.md). Dated protocols, findings and
manuscripts are grouped under `research/docs/`. Python tools use purpose-based
packages and the `python -m research` command; saved source snapshots retain
their original command paths.

Learned-controller evaluation requires an explicit compatible checkpoint.
Preserve training replicates, distinguish development from final evaluation,
and record source/configuration/checkpoint hashes. Older files under
`results/final` and `results/tables` are historical, unaudited outputs; their
directory names do not make their performance claims valid.

## Contributing and license

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request and
[SECURITY.md](SECURITY.md) before sharing a security report or credentials.
FlowSync's code is available under the [MIT license](LICENSE).
Third-party datasets, model weights and dependencies retain their own licenses.
