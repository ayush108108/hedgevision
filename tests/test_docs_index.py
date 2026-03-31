import os


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def test_docs_index_exists():
    required = [
        os.path.join(ROOT, 'docs', 'ARCHITECTURE.md'),
        os.path.join(ROOT, 'docs', 'SETUP.md'),
        os.path.join(ROOT, 'docs', 'DEPLOYMENT.md'),
    ]
    missing = [r for r in required if not os.path.exists(r)]
    assert not missing, f"Missing docs files: {missing}"


def test_architecture_doc_has_header():
    path = os.path.join(ROOT, 'docs', 'ARCHITECTURE.md')
    assert os.path.exists(path), "ARCHITECTURE.md missing"
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    assert 'Architecture' in content, 'Architecture header not found in ARCHITECTURE.md'
