"""Generic test generation module.

The Integration Platform exposes one action-routed test generator module tool.
This implementation starts with the C# ecosystem and can be expanded to other
ecosystems without changing the top-level MCP surface.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Dict, List


_SUPPORTED_ECOSYSTEMS = {"csharp", "python"}

_FRAMEWORKS: Dict[str, Dict[str, Dict[str, str]]] = {
    "csharp": {
        "xunit": {
            "description": "xUnit.net test stubs using [Fact].",
            "class_attribute": "",
            "method_attribute": "[Fact]",
            "using": "using Xunit;",
        },
        "nunit": {
            "description": "NUnit test stubs using [TestFixture] and [Test].",
            "class_attribute": "[TestFixture]",
            "method_attribute": "[Test]",
            "using": "using NUnit.Framework;",
        },
        "mstest": {
            "description": "MSTest stubs using [TestClass] and [TestMethod].",
            "class_attribute": "[TestClass]",
            "method_attribute": "[TestMethod]",
            "using": "using Microsoft.VisualStudio.TestTools.UnitTesting;",
        },
    }
    ,
    "python": {
        "pytest": {
            "description": "pytest test stubs with plain assert statements.",
        },
        "unittest": {
            "description": "unittest stubs using unittest.TestCase methods.",
        },
    },
}

_NAMESPACE_RE = re.compile(r"\bnamespace\s+([A-Za-z_][\w.]*)")
_CLASS_RE = re.compile(r"\bpublic\s+(?:sealed\s+|abstract\s+)?class\s+([A-Za-z_][\w]*)")
_METHOD_RE = re.compile(
    r"\bpublic\s+"
    r"(?:(static)\s+)?"
    r"(?:(async)\s+)?"
    r"([A-Za-z_][\w<>,?.\[\]\s]*)\s+"
    r"([A-Za-z_][\w]*)\s*"
    r"\(([^)]*)\)",
)


def _validate_ecosystem(ecosystem: str) -> Dict[str, Any] | None:
    if ecosystem not in _SUPPORTED_ECOSYSTEMS:
        return {
            "success": False,
            "error": f"Unsupported ecosystem: {ecosystem}",
            "supported_ecosystems": sorted(_SUPPORTED_ECOSYSTEMS),
        }
    return None


def _parse_csharp_source(source_path: Path) -> Dict[str, Any]:
    content = source_path.read_text(encoding="utf-8", errors="ignore")
    namespace_match = _NAMESPACE_RE.search(content)
    namespace = namespace_match.group(1) if namespace_match else None

    classes: List[Dict[str, Any]] = []
    class_names = _CLASS_RE.findall(content)
    method_matches = list(_METHOD_RE.finditer(content))

    if not class_names:
        class_names = [source_path.stem]

    for class_name in class_names:
        methods: List[Dict[str, Any]] = []
        for match in method_matches:
            is_static = bool(match.group(1))
            is_async = bool(match.group(2))
            return_type = " ".join(match.group(3).split())
            method_name = match.group(4)
            parameters = match.group(5).strip()

            if method_name == class_name:
                continue
            if method_name.startswith("get_") or method_name.startswith("set_"):
                continue

            methods.append(
                {
                    "name": method_name,
                    "return_type": return_type,
                    "parameters": parameters,
                    "is_static": is_static,
                    "is_async": is_async or return_type.startswith("Task") or " Task<" in return_type,
                }
            )

        classes.append({"name": class_name, "methods": methods})

    return {
        "namespace": namespace,
        "classes": classes,
        "source_text": content,
    }


def _parse_python_source(source_path: Path) -> Dict[str, Any]:
    content = source_path.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(content, filename=str(source_path))

    classes: List[Dict[str, Any]] = []
    module_functions: List[Dict[str, Any]] = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            methods: List[Dict[str, Any]] = []
            for class_node in node.body:
                if isinstance(class_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if class_node.name.startswith("_"):
                        continue
                    method_args = [arg.arg for arg in class_node.args.args]
                    if method_args and method_args[0] == "self":
                        method_args = method_args[1:]
                    methods.append(
                        {
                            "name": class_node.name,
                            "parameters": method_args,
                            "is_async": isinstance(class_node, ast.AsyncFunctionDef),
                        }
                    )
            classes.append({"name": node.name, "methods": methods})

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            module_functions.append(
                {
                    "name": node.name,
                    "parameters": [arg.arg for arg in node.args.args],
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                }
            )

    return {
        "module": source_path.stem,
        "classes": classes,
        "module_functions": module_functions,
        "source_text": content,
    }


def _list_frameworks(args: Dict[str, Any]) -> Dict[str, Any]:
    ecosystem = str(args.get("ecosystem", "csharp")).lower()
    validation = _validate_ecosystem(ecosystem)
    if validation:
        return validation

    return {
        "success": True,
        "action": "list_frameworks",
        "ecosystem": ecosystem,
        "frameworks": [
            {"name": name, "description": config["description"]}
            for name, config in sorted(_FRAMEWORKS[ecosystem].items())
        ],
    }


def _analyze_source(args: Dict[str, Any]) -> Dict[str, Any]:
    ecosystem = str(args.get("ecosystem", "csharp")).lower()
    validation = _validate_ecosystem(ecosystem)
    if validation:
        return validation

    source_path = args.get("source_path")
    if not source_path:
        return {"success": False, "error": "source_path is required"}

    path = Path(source_path)
    if not path.exists():
        return {"success": False, "error": f"Source path does not exist: {source_path}"}

    if ecosystem == "csharp":
        analysis = _parse_csharp_source(path)
        return {
            "success": True,
            "action": "analyze_source",
            "ecosystem": ecosystem,
            "source_path": str(path),
            "namespace": analysis["namespace"],
            "classes": analysis["classes"],
        }

    if ecosystem == "python":
        analysis = _parse_python_source(path)
        return {
            "success": True,
            "action": "analyze_source",
            "ecosystem": ecosystem,
            "source_path": str(path),
            "module": analysis["module"],
            "classes": analysis["classes"],
            "module_functions": analysis["module_functions"],
        }

    return {"success": False, "error": f"No analyzer implemented for ecosystem: {ecosystem}"}


def _build_csharp_test_content(analysis: Dict[str, Any], framework: str) -> str:
    framework_config = _FRAMEWORKS["csharp"][framework]
    namespace = analysis.get("namespace")
    classes = analysis.get("classes", [])
    target_class = classes[0] if classes else {"name": "TargetClass", "methods": []}
    class_name = target_class["name"]
    methods = target_class.get("methods", [])

    using_lines = [
        "using System;",
        "using System.Threading.Tasks;",
        framework_config["using"],
    ]
    if namespace:
        using_lines.append(f"using {namespace};")

    lines: List[str] = []
    lines.extend(using_lines)
    lines.append("")

    test_namespace = f"{namespace}.Tests" if namespace else "Generated.Tests"
    lines.append(f"namespace {test_namespace};")
    lines.append("")
    if framework_config["class_attribute"]:
        lines.append(framework_config["class_attribute"])
    lines.append(f"public class {class_name}Tests")
    lines.append("{")
    lines.append(f"    private static {class_name} CreateSut()")
    lines.append("    {")
    lines.append("        throw new NotImplementedException(\"Provide constructor dependencies for the system under test.\");")
    lines.append("    }")
    lines.append("")

    if not methods:
        lines.append("    // No public methods were detected. Add test cases manually.")
    else:
        for method in methods:
            if framework_config["method_attribute"]:
                lines.append(f"    {framework_config['method_attribute']}")
            signature = "public async Task" if method["is_async"] else "public void"
            test_name = f"{method['name']}_Should_BeTested"
            lines.append(f"    {signature} {test_name}()")
            lines.append("    {")
            lines.append("        // Arrange")
            if method["is_static"]:
                lines.append(f"        // TODO: configure inputs for static method {class_name}.{method['name']}")
            else:
                lines.append("        var sut = CreateSut();")
                lines.append("        // TODO: configure method inputs")
            lines.append("")
            lines.append("        // Act")
            if method["is_async"]:
                invocation = f"await sut.{method['name']}(/* TODO */);" if not method["is_static"] else f"await {class_name}.{method['name']}(/* TODO */);"
            else:
                invocation = f"sut.{method['name']}(/* TODO */);" if not method["is_static"] else f"{class_name}.{method['name']}(/* TODO */);"
            lines.append(f"        {invocation}")
            lines.append("")
            lines.append("        // Assert")
            if framework == "xunit":
                lines.append("        Assert.True(false, \"Add assertions for the expected behavior.\");")
            elif framework == "nunit":
                lines.append("        Assert.Fail(\"Add assertions for the expected behavior.\");")
            else:
                lines.append("        Assert.Fail(\"Add assertions for the expected behavior.\");")
            lines.append("    }")
            lines.append("")

    lines.append("}")
    return "\n".join(lines).rstrip() + "\n"


def _build_python_test_content(analysis: Dict[str, Any], framework: str) -> str:
    module = analysis.get("module", "target_module")
    classes = analysis.get("classes", [])
    module_functions = analysis.get("module_functions", [])

    has_async = any(method.get("is_async") for cls in classes for method in cls.get("methods", [])) or any(
        fn.get("is_async") for fn in module_functions
    )

    lines: List[str] = []
    if framework == "unittest":
        lines.append("import unittest")
    if framework == "pytest" and has_async:
        lines.append("import pytest")
    lines.append(f"import {module}")
    lines.append("")

    if framework == "pytest":
        emitted = False
        for cls in classes:
            class_name = cls.get("name", "TargetClass")
            for method in cls.get("methods", []):
                method_name = method.get("name", "method")
                if method.get("is_async"):
                    lines.append("@pytest.mark.asyncio")
                    lines.append(f"async def test_{class_name.lower()}_{method_name}_behavior():")
                else:
                    lines.append(f"def test_{class_name.lower()}_{method_name}_behavior():")
                lines.append("    # Arrange")
                lines.append(f"    instance = {module}.{class_name}()")
                lines.append("    # TODO: prepare method arguments")
                lines.append("")
                lines.append("    # Act")
                if method.get("is_async"):
                    lines.append(f"    result = await instance.{method_name}()")
                else:
                    lines.append(f"    result = instance.{method_name}()")
                lines.append("")
                lines.append("    # Assert")
                lines.append("    assert result is not None")
                lines.append("")
                emitted = True

        for fn in module_functions:
            function_name = fn.get("name", "function")
            if fn.get("is_async"):
                lines.append("@pytest.mark.asyncio")
                lines.append(f"async def test_{function_name}_behavior():")
            else:
                lines.append(f"def test_{function_name}_behavior():")
            lines.append("    # Arrange")
            lines.append("    # TODO: prepare function arguments")
            lines.append("")
            lines.append("    # Act")
            if fn.get("is_async"):
                lines.append(f"    result = await {module}.{function_name}()")
            else:
                lines.append(f"    result = {module}.{function_name}()")
            lines.append("")
            lines.append("    # Assert")
            lines.append("    assert result is not None")
            lines.append("")
            emitted = True

        if not emitted:
            lines.append("def test_placeholder():")
            lines.append("    assert True")

    else:
        emitted_sync = False
        emitted_async = False

        lines.append("class TestGenerated(unittest.TestCase):")
        for cls in classes:
            class_name = cls.get("name", "TargetClass")
            for method in cls.get("methods", []):
                if method.get("is_async"):
                    continue
                method_name = method.get("name", "method")
                lines.append(f"    def test_{class_name.lower()}_{method_name}_behavior(self):")
                lines.append("        # Arrange")
                lines.append(f"        instance = {module}.{class_name}()")
                lines.append("        # TODO: prepare method arguments")
                lines.append("")
                lines.append("        # Act")
                lines.append(f"        result = instance.{method_name}()")
                lines.append("")
                lines.append("        # Assert")
                lines.append("        self.assertIsNotNone(result)")
                lines.append("")
                emitted_sync = True

        for fn in module_functions:
            if fn.get("is_async"):
                continue
            function_name = fn.get("name", "function")
            lines.append(f"    def test_{function_name}_behavior(self):")
            lines.append("        # Arrange")
            lines.append("        # TODO: prepare function arguments")
            lines.append("")
            lines.append("        # Act")
            lines.append(f"        result = {module}.{function_name}()")
            lines.append("")
            lines.append("        # Assert")
            lines.append("        self.assertIsNotNone(result)")
            lines.append("")
            emitted_sync = True

        if not emitted_sync:
            lines.append("    def test_placeholder(self):")
            lines.append("        self.assertTrue(True)")

        if has_async:
            lines.append("")
            lines.append("class TestGeneratedAsync(unittest.IsolatedAsyncioTestCase):")
            for cls in classes:
                class_name = cls.get("name", "TargetClass")
                for method in cls.get("methods", []):
                    if not method.get("is_async"):
                        continue
                    method_name = method.get("name", "method")
                    lines.append(f"    async def test_{class_name.lower()}_{method_name}_behavior(self):")
                    lines.append("        # Arrange")
                    lines.append(f"        instance = {module}.{class_name}()")
                    lines.append("        # TODO: prepare method arguments")
                    lines.append("")
                    lines.append("        # Act")
                    lines.append(f"        result = await instance.{method_name}()")
                    lines.append("")
                    lines.append("        # Assert")
                    lines.append("        self.assertIsNotNone(result)")
                    lines.append("")
                    emitted_async = True

            for fn in module_functions:
                if not fn.get("is_async"):
                    continue
                function_name = fn.get("name", "function")
                lines.append(f"    async def test_{function_name}_behavior(self):")
                lines.append("        # Arrange")
                lines.append("        # TODO: prepare function arguments")
                lines.append("")
                lines.append("        # Act")
                lines.append(f"        result = await {module}.{function_name}()")
                lines.append("")
                lines.append("        # Assert")
                lines.append("        self.assertIsNotNone(result)")
                lines.append("")
                emitted_async = True

            if not emitted_async:
                lines.append("    async def test_placeholder_async(self):")
                lines.append("        self.assertTrue(True)")

        lines.append("")
        lines.append("if __name__ == '__main__':")
        lines.append("    unittest.main()")

    return "\n".join(lines).rstrip() + "\n"


def _generate_test_stub(args: Dict[str, Any]) -> Dict[str, Any]:
    ecosystem = str(args.get("ecosystem", "csharp")).lower()
    validation = _validate_ecosystem(ecosystem)
    if validation:
        return validation

    framework = str(args.get("framework", "xunit")).lower()
    if framework not in _FRAMEWORKS[ecosystem]:
        return {
            "success": False,
            "error": f"Unsupported framework '{framework}' for ecosystem '{ecosystem}'",
            "supported_frameworks": sorted(_FRAMEWORKS[ecosystem].keys()),
        }

    analysis_result = _analyze_source(args)
    if not analysis_result.get("success"):
        return analysis_result

    if ecosystem == "csharp":
        content = _build_csharp_test_content(analysis_result, framework)
    elif ecosystem == "python":
        content = _build_python_test_content(analysis_result, framework)
    else:
        return {"success": False, "error": f"No generator implemented for ecosystem: {ecosystem}"}

    output_file = args.get("output_file")
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")

    class_entries = analysis_result.get("classes", [])
    generated_class = class_entries[0].get("name", "TargetClass") if class_entries else "TargetClass"
    class_method_count = sum(len(entry.get("methods", [])) for entry in class_entries)
    module_function_count = len(analysis_result.get("module_functions", []))
    method_count = class_method_count + module_function_count
    return {
        "success": True,
        "action": "generate_test_stub",
        "ecosystem": ecosystem,
        "framework": framework,
        "source_path": analysis_result.get("source_path"),
        "generated_class": generated_class,
        "generated_test_count": method_count,
        "content": content,
        "output_file": str(output_file) if output_file else None,
    }


def generate_tests(args: Dict[str, Any]) -> Dict[str, Any]:
    """Route actions for the generic test generator module tool."""
    action = args.get("action")

    if action == "list_frameworks":
        return _list_frameworks(args)
    if action == "analyze_source":
        return _analyze_source(args)
    if action == "generate_test_stub":
        return _generate_test_stub(args)

    return {
        "success": False,
        "error": f"Unsupported test_generator action: {action}",
        "supported_actions": ["list_frameworks", "analyze_source", "generate_test_stub"],
    }