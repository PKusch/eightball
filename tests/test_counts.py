import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class ReadmeQuotesTheRealTestCount(unittest.TestCase):
    """The README says how many automated tests there are; it was edited by
    hand after new tests and fell behind (71 when there were 75)."""

    def test_the_quoted_count_matches_the_suite(self):
        # a fresh loader, so counting does not disturb the run that is counting
        n = unittest.TestLoader().discover(str(ROOT / "tests"), top_level_dir=str(ROOT / "tests")).countTestCases()
        quoted = [int(x) for x in re.findall(r"\b(\d+) automated tests\b", (ROOT / "README.md").read_text(encoding="utf-8"))]
        self.assertTrue(quoted, "README.md quotes no test count")
        self.assertEqual(set(quoted), {n}, f"README.md quotes {quoted}; the suite has {n}")



class OneVersion(unittest.TestCase):
    """The version is written in pyproject.toml and in the package; the
    changelog must have a section for it."""

    def test_the_package_pyproject_and_changelog_agree(self):
        import sys
        sys.path.insert(0, str(ROOT / "src"))
        from eightball import __version__
        project = re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(encoding="utf-8"), re.M).group(1)
        self.assertEqual(__version__, project)
        self.assertRegex((ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), rf"(?m)^## {re.escape(project)}\b")


if __name__ == "__main__":
    unittest.main()
