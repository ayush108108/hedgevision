# Security Policy

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in HedgeVision, please **do not** open a public issue. Instead, please report it responsibly.

### How to Report

1. **Email**: Send a detailed description of the vulnerability to [security contact] with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if you have one)

2. **Timeline**: We will:
   - Acknowledge receipt within 48 hours
   - Provide an initial assessment within 7 days
   - Work toward a fix and coordinate a responsible disclosure

### What We Consider a Vulnerability

- Authentication/authorization flaws
- Secrets or credentials exposed in code or logs
- Injection vulnerabilities (SQL, command, etc.)
- Cryptographic weaknesses
- Data exposure or privacy issues
- Denial of service vulnerabilities

### What We Don't Consider Vulnerabilities

- Typos or documentation errors
- Missing security best practices that don't expose actual vulnerabilities
- Performance issues
- Social engineering concerns

## Security Best Practices

When using HedgeVision:

1. **Keep Dependencies Updated**: Run `pip install -e ".[all]" --upgrade` regularly
2. **Protect Your `.env` Files**: Never commit credentials to version control
3. **Use Strong Secrets**: Generated secrets for `JWT_SECRET_KEY` and `SECRET_KEY` should be 32+ characters
4. **Paper Mode Default**: Always use `BROKER_BACKEND=paper` (default) unless explicitly enabling live trading
5. **LLM Sanitization**: The platform sanitizes LLM payloads by default — do not disable this
6. **Database Permissions**: If using Supabase, follow principle of least privilege for service roles

## Security Features

- LLM payload sanitization to prevent credential leakage
- Default local-first mode (no external dependencies required)
- Paper broker preventing accidental live trades
- Support for multiple authentication strategies
- Rate limiting and CORS middleware

## Version Support

We recommend always using the latest version. Security fixes may be backported to previous versions in critical cases.

| Version | Status |
|---------|--------|
| Latest | ✅ Actively Supported |
| 1.x | ⚠️ Limited Support |
| < 1.0 | ❌ No Support |

## Responsible Disclosure

We appreciate responsible disclosure and will:
- Credit you for the discovery if desired
- Work with you to ensure a thorough fix
- Coordinate public announcement timing
- Prioritize security patches above feature releases

---

Thank you for helping keep HedgeVision secure! 🙏
