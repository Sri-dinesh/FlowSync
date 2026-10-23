# Contributing

Start with [setup](docs/setup.md), [architecture](docs/architecture.md) and the
[research index](research/README.md). Use Python 3.11 for a fresh CPU environment
and Node.js 24/npm for the client. Preserve existing local environments and data.

## Development workflow

Create a focused branch, keep changes scoped, and explain the problem, resulting
behavior and verification in the pull request. Report existing failures and
checks not run. Avoid broad formatting churn in simulation/training code and
do not reset someone else's dirty worktree. Be respectful in reviews and issues.
Follow the [community guidelines](CODE_OF_CONDUCT.md).

From the repository root:

```bash
python scripts/check_repository.py
npm --prefix client run lint
npm --prefix client run typecheck
PYTHONDONTWRITEBYTECODE=1 server/.venv/bin/python -m pytest server/tests --no-cov -p no:cacheprovider
npm --prefix client run build
```

The Makefile provides the same commands and accepts `PYTHON=/path/to/python`.
Run focused meaningful tests while editing, then the relevant broader checks.
Tests must use temporary checkpoints/directories and mocked external services;
they must not change real Supabase data, train long jobs or download models.

`client/package-lock.json` is the frontend lockfile. Use `npm ci` for installation;
commit the lockfile when dependencies change. Do not add npm/pnpm/yarn lockfiles
for the same application. Optional detector dependencies are separate from the
core installation; research analysis dependencies belong in `research/requirements.txt`.

## Research changes

- Read current status before launching an experiment; completed failed recipes
  are not next-step instructions.
- Freeze controls, budgets, endpoints, source/configuration and checkpoint hashes.
- Preserve all replicates, raw outputs and unfavorable cases; use new output directories.
- Keep training/development/final-test roles separate. Do not tune on inspected final panels.
- Preserve delivered-observation isolation, physical signal rules and existing checkpoint semantics.
- Document version/compatibility changes and test the actual behavior affected.
- Do not copy historical README/paper figures into new claims. Data-derived
  exports must verify their raw source and provenance.

Research docs belong in `research/docs/`; application guides belong in `docs/`.
Stable research Python/CLI paths are compatibility interfaces. Archived source
and result files must not be rewritten when reorganizing the live codebase.

## Before sharing

Exclude credentials, raw footage, datasets, generated dependencies, checkpoints
and local experiment outputs. Clear notebook outputs containing tokens or private
data and document third-party model/dataset licenses. Use [SECURITY.md](SECURITY.md)
for sensitive reports. Passing tests does not establish controller superiority,
paper readiness or a publicly hardened deployment.
