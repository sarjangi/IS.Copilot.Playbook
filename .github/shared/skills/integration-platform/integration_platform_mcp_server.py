#!/usr/bin/env python3
"""
Integration Platform MCP Server

A unified MCP server providing five file-level tools:
- sql_scanner
- repo_analyzer
- scan_security
- test_generator
- pipeline

Usage:
    python integration_platform_mcp_server.py
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, Optional

from tools.repo_analyzer import (
    check_repository_access,
    list_repository_branches,
    scan_repository,
)
from tools.sql_scanner import (
    check_parameterized_query,
    generate_html_report,
    generate_scan_report,
    scan_sql_injection_directory,
    scan_sql_injection_file,
)
from tools.security_scanner import scan_security_vulnerabilities
from tools.test_generator import generate_tests
from tools.pipeline import run_pipeline

# Configure optional debug logging.
DEBUG_MODE = os.getenv("MCP_DEBUG") == "1"
VERBOSE_STDERR = os.getenv("MCP_VERBOSE") == "1"


def debug_log(message: str) -> None:
    """Log debug message to stderr only if verbose mode is enabled."""
    if VERBOSE_STDERR:
        print(message, file=sys.stderr, flush=True)


if DEBUG_MODE:
    log_file = os.path.expanduser("~/integration_platform_mcp_debug.log")
    logging.basicConfig(
        filename=log_file,
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
else:
    # MCP uses stdio; disable logging noise on stdout/stderr.
    logging.disable(logging.CRITICAL)


class IntegrationPlatformMCPServer:
    """Main MCP server for Integration Platform."""

    def __init__(self) -> None:
        self.name = "Integration Platform"
        self.version = "1.0.0"
        self.message_mode = "framed"

        # Exactly four top-level tools, aligned to tool modules/files.
        self.tools = {
            "sql_scanner": {
                "description": "SQL scanner module tool: scan files/directories, validate parameterization, and generate reports.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "scan_sql_injection_file",
                                "scan_sql_injection_directory",
                                "check_parameterized_query",
                                "generate_scan_report",
                                "generate_html_report",
                            ],
                            "description": "SQL scanner action to execute.",
                        },
                        "file_path": {"type": "string"},
                        "directory_path": {"type": "string"},
                        "recursive": {"type": "boolean"},
                        "code_snippet": {"type": "string"},
                        "findings": {
                            "type": "array",
                            "items": {"type": "object"},
                        },
                        "output_format": {
                            "type": "string",
                            "enum": ["text", "json", "summary"],
                        },
                        "output_file": {"type": "string"},
                        "scan_path": {"type": "string"},
                    },
                    "required": ["action"],
                },
                "handler": self._handle_sql_scanner_tool,
            },
            "repo_analyzer": {
                "description": "Repository analyzer module tool: scan repositories, list branches, and validate access.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "scan_repository",
                                "list_repository_branches",
                                "check_repository_access",
                            ],
                            "description": "Repository analyzer action to execute.",
                        },
                        "repo_url": {"type": "string"},
                        "branch": {"type": "string"},
                        "auth_token": {"type": "string"},
                        "scan_type": {
                            "type": "string",
                            "enum": ["security", "full"],
                        },
                        "file_patterns": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "exclude_patterns": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["action"],
                },
                "handler": self._handle_repo_analyzer_tool,
            },
            "scan_security": {
                "description": "Security scanner module tool with action routing for path scans and profile discovery.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["scan_path", "list_profiles", "generate_report", "generate_html_report"],
                            "description": "Security scanner action to execute.",
                        },
                        "target_path": {
                            "type": "string",
                            "description": "Path to scan for security vulnerabilities",
                        },
                        "recursive": {
                            "type": "boolean",
                            "description": "Recursively scan subdirectories (default: true)",
                        },
                        "profile": {
                            "type": "string",
                            "enum": ["quick", "full", "secrets"],
                            "description": "Named scan profile to use for scan_path.",
                        },
                        "findings": {
                            "type": "array",
                            "items": {"type": "object"},
                        },
                        "output_format": {
                            "type": "string",
                            "enum": ["text", "json", "summary"],
                            "description": "Report format to use for generate_report.",
                        },
                        "output_file": {
                            "type": "string",
                            "description": "Output HTML file path for generate_html_report.",
                        },
                        "scan_path": {
                            "type": "string",
                            "description": "Display label/path for the generated HTML report.",
                        },
                    },
                    "required": ["action"],
                },
                "handler": self._handle_scan_security_tool,
            },
            "test_generator": {
                "description": "Generic test generator module tool with ecosystem-aware action routing.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["list_frameworks", "analyze_source", "generate_test_stub"],
                            "description": "Test generator action to execute.",
                        },
                        "ecosystem": {
                            "type": "string",
                            "enum": ["csharp", "python"],
                            "description": "Target ecosystem for generation.",
                        },
                        "framework": {
                            "type": "string",
                            "enum": ["xunit", "nunit", "mstest", "pytest", "unittest"],
                            "description": "Test framework to use for generate_test_stub.",
                        },
                        "source_path": {
                            "type": "string",
                            "description": "Path to the source file to analyze or generate tests for.",
                        },
                        "output_file": {
                            "type": "string",
                            "description": "Optional output path for the generated test file.",
                        },
                    },
                    "required": ["action"],
                },
                "handler": self._handle_test_generator_tool,
            },
            "pipeline": {
                "description": (
                    "End-to-end security pipeline: clone repository, run SQL + security scans, "
                    "generate fix suggestions (unified diffs), produce an HTML report, and "
                    "(optionally) push a fix branch and create a pull request (GitHub or Azure DevOps)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["dry_run", "run"],
                            "description": (
                                "dry_run: scan + report only, no git push or PR. "
                                "run: scan + fix + push branch + create PR."
                            ),
                        },
                        "repo_url": {
                            "type": "string",
                            "description": "HTTPS URL of the repository to scan.",
                        },
                        "branch": {
                            "type": "string",
                            "description": "Branch to clone and scan (defaults to repository default branch).",
                        },
                        "auth_token": {
                            "type": "string",
                            "description": "Personal Access Token for private repos and PR creation (required for action=run).",
                        },
                        "base_branch": {
                            "type": "string",
                            "description": "Target branch for the pull request (default: main).",
                        },
                        "scan_profile": {
                            "type": "string",
                            "enum": ["quick", "full", "secrets"],
                            "description": "Security scan profile (default: quick).",
                        },
                        "pr_title": {
                            "type": "string",
                            "description": "Override the auto-generated pull request title.",
                        },
                        "pr_body": {
                            "type": "string",
                            "description": "Additional text appended to the auto-generated PR description.",
                        },
                        "output_file": {
                            "type": "string",
                            "description": "Full path to save the HTML report to disk (e.g. C:/Users/you/Desktop/report.html). If omitted the report is returned inline only.",
                        },
                        "pbi_number": {
                            "type": "string",
                            "description": "Azure DevOps Product Backlog Item (PBI) number to link to the PR (e.g. '12345'). Only used in run mode.",
                        },
                    },
                    "required": ["action", "repo_url"],
                },
                "handler": self._handle_pipeline_tool,
            },
        }

    def _handle_sql_scanner_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
        action = args.get("action")
        if action == "scan_sql_injection_file":
            return scan_sql_injection_file(args)
        if action == "scan_sql_injection_directory":
            return scan_sql_injection_directory(args)
        if action == "check_parameterized_query":
            return check_parameterized_query(args)
        if action == "generate_scan_report":
            return generate_scan_report(args)
        if action == "generate_html_report":
            return generate_html_report(args)
        return {
            "success": False,
            "error": f"Unsupported sql_scanner action: {action}",
            "supported_actions": [
                "scan_sql_injection_file",
                "scan_sql_injection_directory",
                "check_parameterized_query",
                "generate_scan_report",
                "generate_html_report",
            ],
        }

    def _handle_repo_analyzer_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
        action = args.get("action")
        if action == "scan_repository":
            return scan_repository(args)
        if action == "list_repository_branches":
            return list_repository_branches(args)
        if action == "check_repository_access":
            return check_repository_access(args)
        return {
            "success": False,
            "error": f"Unsupported repo_analyzer action: {action}",
            "supported_actions": [
                "scan_repository",
                "list_repository_branches",
                "check_repository_access",
            ],
        }

    def _handle_scan_security_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return scan_security_vulnerabilities(args)

    def _handle_test_generator_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return generate_tests(args)

    def _handle_pipeline_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return run_pipeline(args)

    def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": self.name, "version": self.version},
                "capabilities": {"tools": {}, "resources": {}},
            }
        }

    def handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "result": {
                "tools": [
                    {
                        "name": tool_name,
                        "description": tool_info["description"],
                        "inputSchema": tool_info["inputSchema"],
                    }
                    for tool_name, tool_info in self.tools.items()
                ]
            }
        }

    def handle_tool_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name not in self.tools:
            return {
                "result": {
                    "content": [{"type": "text", "text": f"Error: Unknown tool '{tool_name}'"}],
                    "isError": True,
                }
            }

        try:
            handler = self.tools[tool_name]["handler"]
            result = handler(arguments)
            return {
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                }
            }
        except Exception as e:
            return {
                "result": {
                    "content": [{"type": "text", "text": f"Error executing {tool_name}: {str(e)}"}],
                    "isError": True,
                }
            }

    async def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        if method in {"notifications/initialized", "initialized"}:
            return None

        if method == "ping":
            result = {"result": {}}
        elif method == "initialize":
            result = self.handle_initialize(params)
        elif method == "tools/list":
            result = self.handle_tools_list(params)
        elif method == "tools/call":
            result = self.handle_tool_call(params)
        else:
            result = {"error": {"code": -32601, "message": f"Method not found: {method}"}}

        result["jsonrpc"] = "2.0"
        result["id"] = request_id
        return result

    def read_message(self) -> Optional[Dict[str, Any]]:
        try:
            first_line = sys.stdin.buffer.readline()
            if not first_line:
                return None

            stripped = first_line.strip()
            if stripped.startswith(b"{") or stripped.startswith(b"["):
                self.message_mode = "line"
                return json.loads(stripped.decode("utf-8"))

            headers = {}
            line = first_line
            while True:
                if line == b"\r\n" or line == b"\n":
                    break
                if b":" in line:
                    key, value = line.decode("utf-8").strip().split(":", 1)
                    headers[key.strip().lower()] = value.strip()
                line = sys.stdin.buffer.readline()
                if not line:
                    return None

            content_length = int(headers.get("content-length", 0))
            if content_length > 0:
                self.message_mode = "framed"
                content = sys.stdin.buffer.read(content_length)
                return json.loads(content.decode("utf-8"))
            return None
        except Exception as e:
            debug_log(f"[ERROR] read_message exception: {type(e).__name__}: {str(e)}")
            return None

    def write_message(self, response: Dict[str, Any]) -> None:
        if self.message_mode == "line":
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
            return

        content = json.dumps(response).encode("utf-8")
        message = f"Content-Length: {len(content)}\r\n\r\n".encode("utf-8") + content
        sys.stdout.buffer.write(message)
        sys.stdout.buffer.flush()

    async def run(self) -> None:
        while True:
            request = await asyncio.get_event_loop().run_in_executor(None, self.read_message)
            if request is None:
                break

            response = await self.handle_request(request)
            if response is not None:
                await asyncio.get_event_loop().run_in_executor(None, self.write_message, response)


async def main() -> None:
    server = IntegrationPlatformMCPServer()
    await server.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
