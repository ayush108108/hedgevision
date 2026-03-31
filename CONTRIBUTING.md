# Contributing Guide [Dev Level]

Thank you for your interest in contributing to HedgeVision! We are a "local-first" Open Source ecosystem.

## Ways to Contribute

1.  **Report Bugs**: Open an issue describing the bug and steps to reproduce.
2.  **Suggest Features**: Have an idea? Open a discussion or issue.
3.  **Code Contributions**: Submit Pull Requests (PRs).

## Development Workflow

1.  **Fork** the repository.
2.  **Clone** your fork locally.
3.  **Create a Branch** for your feature (`git checkout -b feature/amazing-feature`).
4.  **Set up Environment**: Follow [docs/SETUP.md](docs/SETUP.md).
5.  **Make Changes**:
    - Backend changes: `backend/`
    - Frontend changes: `frontend-v2/`
    - Scripts: `scripts/`
6.  **Test**:
    - Backend: `pytest` (run from root or `backend/`).
    - Frontend: `npm test` (in `frontend-v2/`).
7.  **Lint**:
    - Backend: `black`, `flake8`.
    - Frontend: `npm run lint`.
8.  **Push** and Open a **Pull Request**.

## Coding Standards

- **Python**: Follow PEP 8. Use explicit type hints.
- **TypeScript**: Use strict mode. Prefer functional components and hooks.
- **Commits**: Use conventional commits (e.g., `feat: add new correlation metric`, `fix: resolve db connection timeout`).

## "Local First" Philosophy

When adding features, ensure they can run effectively on a local machine (e.g., Mac M1/M2/M3, Linux Desktop). Avoid heavy dependencies on cloud-only services unless absolutely necessary, or provide local fallbacks/mocks.
