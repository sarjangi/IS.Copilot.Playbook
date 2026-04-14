import ast
import sys
import tempfile
import unittest
from pathlib import Path

INTEGRATION_PLATFORM_DIR = Path(__file__).resolve().parents[1]
if str(INTEGRATION_PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(INTEGRATION_PLATFORM_DIR))

from tools import test_generator


class TestPythonGeneratorAdvanced(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _write_source(self, name: str, content: str) -> Path:
        source_path = self.root / name
        source_path.write_text(content, encoding="utf-8")
        return source_path

    def test_list_frameworks_includes_python_frameworks(self):
        result = test_generator.generate_tests({"action": "list_frameworks", "ecosystem": "python"})

        self.assertTrue(result["success"])
        names = [item["name"] for item in result["frameworks"]]
        self.assertIn("pytest", names)
        self.assertIn("unittest", names)

    def test_analyze_source_detects_async_and_sync(self):
        source = self._write_source(
            "service.py",
            """
class Worker:
    def run(self):
        return 1

    async def run_async(self):
        return 2


def process():
    return 3


async def process_async():
    return 4
""".strip(),
        )

        result = test_generator.generate_tests(
            {
                "action": "analyze_source",
                "ecosystem": "python",
                "source_path": str(source),
            }
        )

        self.assertTrue(result["success"])
        self.assertEqual("service", result["module"])
        self.assertEqual(1, len(result["classes"]))
        methods = result["classes"][0]["methods"]
        self.assertEqual(2, len(methods))
        self.assertTrue(any(method["is_async"] for method in methods))
        self.assertEqual(2, len(result["module_functions"]))
        self.assertTrue(any(fn["is_async"] for fn in result["module_functions"]))

    def test_generate_pytest_stub_marks_async_tests(self):
        source = self._write_source(
            "service.py",
            """
class Worker:
    async def run_async(self):
        return 2


def process():
    return 3


async def process_async():
    return 4
""".strip(),
        )

        result = test_generator.generate_tests(
            {
                "action": "generate_test_stub",
                "ecosystem": "python",
                "framework": "pytest",
                "source_path": str(source),
            }
        )

        self.assertTrue(result["success"])
        content = result["content"]
        self.assertIn("import pytest", content)
        self.assertIn("@pytest.mark.asyncio", content)
        self.assertIn("async def test_worker_run_async_behavior", content)
        self.assertIn("await service.process_async()", content)
        self.assertIn("def test_process_behavior", content)
        # Ensure generated code is valid Python syntax.
        ast.parse(content)

    def test_generate_unittest_stub_uses_isolated_asyncio(self):
        source = self._write_source(
            "service.py",
            """
class Worker:
    def run(self):
        return 1

    async def run_async(self):
        return 2
""".strip(),
        )

        result = test_generator.generate_tests(
            {
                "action": "generate_test_stub",
                "ecosystem": "python",
                "framework": "unittest",
                "source_path": str(source),
            }
        )

        self.assertTrue(result["success"])
        content = result["content"]
        self.assertIn("class TestGenerated(unittest.TestCase):", content)
        self.assertIn("class TestGeneratedAsync(unittest.IsolatedAsyncioTestCase):", content)
        self.assertIn("async def test_worker_run_async_behavior", content)
        self.assertIn("await instance.run_async()", content)
        ast.parse(content)

    def test_generate_to_output_file_and_count(self):
        source = self._write_source(
            "service.py",
            """
def a():
    return 1


def b():
    return 2
""".strip(),
        )
        output_file = self.root / "test_service_generated.py"

        result = test_generator.generate_tests(
            {
                "action": "generate_test_stub",
                "ecosystem": "python",
                "framework": "pytest",
                "source_path": str(source),
                "output_file": str(output_file),
            }
        )

        self.assertTrue(result["success"])
        self.assertEqual(2, result["generated_test_count"])
        self.assertTrue(output_file.exists())


if __name__ == "__main__":
    unittest.main()
