import compileall
import sys
import unittest
from pathlib import Path


def run_compile_check(root: Path) -> bool:
    # Force compile to catch syntax/runtime import-side parser issues.
    return compileall.compile_dir(str(root), force=True, quiet=1)


def run_unittest_suite(root: Path) -> bool:
    suite = unittest.defaultTestLoader.discover(
        start_dir=str(root / "tests"),
        pattern="test_*.py",
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return result.wasSuccessful()


def main() -> int:
    root = Path(__file__).resolve().parent
    compiled = run_compile_check(root)
    tested = run_unittest_suite(root)

    if compiled and tested:
        print("QA PASSED")
        return 0

    print("QA FAILED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
