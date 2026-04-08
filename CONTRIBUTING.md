# Contributing Guide [Dev Level]

Thank you for your interest in contributing to HedgeVision! We are a "local-first" Open Source ecosystem.

## Ways to Contribute

1.  **Report Bugs**: Open an issue describing the bug and steps to reproduce.
2.  **Suggest Features**: Have an idea? Open a discussion or issue.
3.  **Code Contributions**: Submit Pull Requests (PRs).
4.  **Documentation**: Help improve our docs, tutorials, and examples.
5.  **Testing**: Add test coverage or improve existing tests.

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
    - Backend: `black --line-length 100 .` and `flake8 .`
    - Frontend: `npm run lint` (in `frontend-v2/`).
8.  **Push** and Open a **Pull Request**.

## Coding Standards

### Python (Backend)
- Follow **PEP 8** style guide
- Use **Black** formatter with line length 100: `black --line-length 100 .`
- Use **isort** for imports: `isort --profile black --line-length 100 .`
- Run **flake8** for linting: `flake8 .`
- Use **mypy** for type checking (strict mode): `mypy hedgevision/`
- Add type hints to all function signatures
- Minimum test coverage: **90%** for core package (`hedgevision/`)
- Use pytest markers: `@pytest.mark.unit`, `@pytest.mark.integration`, etc.

### TypeScript/JavaScript (Frontend)
- Use **TypeScript strict mode**
- Follow **ESLint** rules: `npm run lint`
- Use **Prettier** for formatting
- Prefer **functional components** and **React hooks**
- Target ES2020+ syntax
- Add unit tests for complex logic using **Vitest**

### Commit Messages
Use **conventional commits** format:
- `feat: add new correlation metric`
- `fix: resolve database connection timeout`
- `docs: update setup instructions`
- `test: add unit tests for auth service`
- `refactor: simplify broker abstraction`
- `chore: update dependencies`

## Testing Requirements

### Backend Testing
```bash
# Run all tests with coverage
pytest --cov=hedgevision --cov-fail-under=90

# Run by marker
pytest -m unit
pytest -m integration
pytest -m real_api

# Run specific test file
pytest tests/test_analytics_service_unit.py
```

### Frontend Testing
```bash
cd frontend-v2

# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run specific test file
npx vitest run src/pages/__tests__/SomePage.test.tsx
```

## Security Guidelines

- **Never commit secrets**: Use `.env` files (excluded via `.gitignore`)
- **Use environment variables** for all sensitive data
- **Paper mode default**: Always default to `BROKER_BACKEND=paper`
- **Sanitize LLM payloads**: Keep `SANITIZE_LLM_PAYLOADS=true`
- **No hardcoded credentials**: Use `.env.example` as template
- **Report security issues** privately to ayushverma108108@gmail.com

## "Local First" Philosophy

When adding features, ensure they can run effectively on a local machine (e.g., Mac M1/M2/M3, Linux Desktop).

Key principles:
- **SQLite by default**: External databases (Supabase) are opt-in
- **Paper trading default**: Live trading requires explicit configuration
- **No mandatory cloud services**: All core features work offline
- **Graceful degradation**: Features degrade gracefully when optional services unavailable
- **Local LLM support**: Support CPU-based and Ollama models alongside cloud LLMs

## Pull Request Process

1. **Keep PRs focused**: One feature or fix per PR
2. **Write clear descriptions**: Explain what and why, not just how
3. **Add tests**: New features need test coverage
4. **Update documentation**: If you change APIs or behavior
5. **Run linters and tests**: Ensure all checks pass before submitting
6. **Link related issues**: Reference issue numbers in PR description
7. **Be responsive**: Address review feedback promptly

## Code Review Standards

We review PRs for:
- **Correctness**: Does it work as intended?
- **Testing**: Is there adequate test coverage?
- **Security**: Are there any vulnerabilities?
- **Performance**: Are there obvious bottlenecks?
- **Documentation**: Are changes documented?
- **Style**: Does it follow our coding standards?

## Getting Help

- **Questions**: Open a [GitHub Discussion](https://github.com/ayush108108/hedgevision/discussions)
- **Bugs**: Open an [issue](https://github.com/ayush108108/hedgevision/issues)
- **Security**: Email ayushverma108108@gmail.com privately
- **Documentation**: Check [docs/](docs/) directory

## Recognition

Contributors are recognized in:
- GitHub contributors list
- Release notes for significant contributions
- Special thanks in documentation for major features

Thank you for contributing to HedgeVision! 🙏
