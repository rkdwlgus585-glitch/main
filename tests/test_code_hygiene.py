import ast
import unittest
from pathlib import Path


class CodeHygieneTest(unittest.TestCase):
    def test_no_bare_except_in_project_modules(self):
        root = Path(__file__).resolve().parent.parent
        candidates = [
            p for p in root.glob('*.py')
            if not p.name.startswith('test_') and p.name != 'run_qa.py'
        ]

        findings = []
        for path in sorted(candidates):
            src = path.read_text(encoding='utf-8-sig')
            mod = ast.parse(src)
            for node in ast.walk(mod):
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    findings.append(f'{path.name}:{node.lineno}')

        self.assertFalse(
            findings,
            msg='bare except violation: ' + ', '.join(findings),
        )


if __name__ == '__main__':
    unittest.main()
