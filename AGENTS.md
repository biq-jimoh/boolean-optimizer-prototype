# Repository Guidelines

## Project Structure & Module Organization
- `bankruptcy_query_optimizer.py`: Core orchestrator (consultants + executive synthesis).
- `optimize_query.py`: CLI entry for local optimization.
- `lambda_handler.py`: AWS Lambda entry; see `README_LAMBDA.md`.
- `prompts/consultants/*.txt`: Consultant agent prompts (AC-*, SI-*, RI-*).
- `prompts/executive/executive-agent.txt`: Executive agent prompt.
- `prompts/shared/mandatory_formatting_requirements.txt`: Shared rules injected via placeholder.
- `schemas/*.json`: Request validation for the Lambda API.
- Tests: `test_*.py` at repo root; utility modules alongside core files.

## Build, Test, and Development Commands
- Create env and install deps:
  - `python -m venv venv && source venv/bin/activate`
  - `pip install -r requirements.txt`
- Run locally (CLI):
  - `python optimize_query.py "section 363 sale"`
  - `python optimize_query.py --json "Till v. SCS Credit"`
- Run tests:
  - `pytest -q` (unit-style; API-dependent parts skip without `OPENAI_API_KEY`)
  - Script-style: `python test_optimizer.py`, `python test_lambda_local.py optimize_simple`
- Lambda packaging/deploy:
  - `./build_lambda_package.sh` → builds `lambda-package/` and zip
  - `./deploy.sh --stage prod --region us-east-1`

## Coding Style & Naming Conventions
- Python 3.11, 4-space indentation, PEP 8.
- Use type hints and Pydantic models for structured data (see `ConsultantOutput`, `ExecutiveOutput`).
- Filenames: snake_case for Python, `AC-#/SI-#` for consultant prompt files.
- Prompt files should include `{{MANDATORY_FORMATTING_REQUIREMENTS}}` when applicable.
- Keep logging through `_log()`; avoid noisy prints in library code.

## Testing Guidelines
- Framework: `pytest` (see `requirements.txt`).
- Naming: files `test_*.py`, tests `def test_*`.
- API-key sensitive tests: set `OPENAI_API_KEY` to enable; otherwise, model/format tests still run.
- Aim to cover consultant/executive formatting and critical paths; no strict coverage threshold.

## Commit & Pull Request Guidelines
- Commits: prefer Conventional Commits (e.g., `feat:`, `fix:`, `docs:`) as seen in history.
- PRs must include: clear description, motivation, linked issue (if any), test results (`pytest -q`), and doc updates (README or docs where relevant).
- For prompt changes, note affected consultant IDs (e.g., SI-7, SI-8) and include before/after examples.

## Security & Configuration Tips
- Required env vars: `OPENAI_API_KEY`; optional: `BRAVE_SEARCH_API_KEY`.
- Use `.env` (see `env.example`) and never commit secrets.
- Large vendor artifacts in `lambda-package/` are build outputs—avoid manual edits.
