# Documentation Index

This folder contains detailed documentation for the Bankruptcy Query Optimizer.

Key documents:

- AGENTS.md: Repository guidelines and development conventions
- README_LAMBDA.md: AWS Lambda API quick start and operations
- API_DOCUMENTATION.md: Public API reference and examples
- DEPLOYMENT_GUIDE.md: Deployment walkthroughs and options
- AWS_LAMBDA_API_PLAN.md: Architecture and planning notes
- IMPLEMENTATION_SUMMARY.md: System overview and capabilities
- WEB_SEARCH_IMPLEMENTATION.md: SI-7/SI-8 web search architecture
- MULTIPLE_CITATIONS_GUIDE.md: Multiple citation handling and token budgets
- RATE_LIMIT_HANDLING.md: Exponential backoff and rate limit strategy

Run common tasks from repo root:

- Package Lambda: bash scripts/build_lambda_package.sh (outputs to build/)
- Deploy Lambda: bash scripts/deploy.sh --stage prod --region us-east-1
- Local Lambda test: python scripts/lambda_local_test.py optimize_simple
- Pytest suite: pytest -q
