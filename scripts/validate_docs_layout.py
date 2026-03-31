"""
Simple docs layout validator. Ensures critical documentation follows the repo rules:
- No 'Moved to docs' placeholder strings in markdown files
- Component docs are colocated (frontend, backend, operations)
- Each key directory has a README
- Some canonical docs exist (docs/REPO_AUDIT.md, backend/YFINANCE_ARCHITECTURE.md)

Usage: python scripts/validate_docs_layout.py
"""
import os
import sys
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

CHECKS = []


def find_files(root, pattern):
    matches = []
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith(pattern):
                matches.append(os.path.join(dirpath, fn))
    return matches


def check_no_placeholder():
    placeholders = []
    for md in find_files(ROOT, '.md'):
        try:
            with open(md, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            continue
        # Allow a single policy mention in `docs/README.md`
        if (('Moved to docs/' in content or 'Moved to docs' in content) and
            not md.endswith(os.path.join('docs', 'README.md'))):
            placeholders.append(md)
    if placeholders:
        print('Found "Moved to docs" placeholders in the following files:')
        for p in placeholders:
            print(' -', os.path.relpath(p, ROOT))
        return False
    print('No "Moved to docs" placeholders found.')
    return True


def check_key_docs():
    required = [
        os.path.join(ROOT, 'docs', 'REPO_AUDIT.md'),
        os.path.join(ROOT, 'docs', 'PREREQUISITES.md'),
        os.path.join(ROOT, 'backend', 'YFINANCE_ARCHITECTURE.md'),
        os.path.join(ROOT, 'frontend-v2', 'docs', 'README.md'),
        os.path.join(ROOT, 'operations', 'README.md'),
    ]
    missing = [r for r in required if not os.path.exists(r)]
    if missing:
        print('Missing key documentation files:')
        for m in missing:
            print(' -', os.path.relpath(m, ROOT))
        return False
    print('All key docs are present.')
    return True


def check_readmes():
    # Check each top-level dir has a README
    top_dirs = ['backend', 'frontend-v2', 'scripts', 'tests', 'operations']
    missing = []
    for d in top_dirs:
        path = os.path.join(ROOT, d)
        readme = os.path.join(path, 'README.md')
        if not os.path.exists(readme):
            missing.append(readme)
    if missing:
        print('Missing READMEs in the following directories:')
        for m in missing:
            print(' -', os.path.relpath(m, ROOT))
        return False
    print('All required READMEs exist for top-level directories.')
    return True


def check_frontend_docs():
    front_docs = os.path.join(ROOT, 'frontend-v2', 'docs')
    if not os.path.isdir(front_docs):
        print('frontend-v2/docs is missing')
        return False
    # ensure TESTING.md exists
    testing = os.path.join(front_docs, 'TESTING.md')
    if not os.path.exists(testing):
        print('frontend-v2/docs/TESTING.md missing')
        return False
    print('Frontend docs are present (TESTING.md found).')
    return True


if __name__ == '__main__':
    ok = True
    ok = check_no_placeholder() and ok
    ok = check_key_docs() and ok
    ok = check_readmes() and ok
    ok = check_frontend_docs() and ok

    if not ok:
        print('\nOne or more documentation checks failed. See messages above.')
        sys.exit(2)
    print('\nDoc validations passed. Good job!')
    sys.exit(0)
