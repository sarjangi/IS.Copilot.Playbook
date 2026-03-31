#!/usr/bin/env python3
"""
SQL Injection Scanner - MCP Server
Model Context Protocol server for integrating with GitHub Copilot
"""
import json
import sys
import asyncio
import importlib.util
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from tools.securityTool import scan_file_handler, scan_directory_handler
except ImportError:
    # Load the local security tool directly so MCP file scans still work even
    # when optional repository-scan dependencies are not installed.
    try:
        security_tool_path = Path(__file__).parent / "tools" / "securityTool.py"
        spec = importlib.util.spec_from_file_location("sql_scanner_security_tool", security_tool_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load module spec for {security_tool_path}")
        security_tool_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(security_tool_module)
        scan_file_handler = security_tool_module.scan_file_handler
        scan_directory_handler = security_tool_module.scan_directory_handler
    except Exception:
        async def scan_file_handler(file_path):
            return {"success": False, "error": "Scanner not available"}

        async def scan_directory_handler(directory, recursive=True):
            return {"success": False, "error": "Scanner not available"}


class SQLScannerMCPServer:
    """MCP Server for SQL Injection Scanner"""
    
    def __init__(self):
        self.message_mode = "framed"
        self.tools = {
            "scan_file": {
                "description": "Scan a single file for SQL injection vulnerabilities",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file to scan"
                        }
                    },
                    "required": ["file_path"]
                }
            },
            "scan_directory": {
                "description": "Scan a directory recursively for SQL injection vulnerabilities",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "Path to the directory to scan"
                        }
                    },
                    "required": ["directory"]
                }
            }
        }
    
    async def handle_request(self, request):
        """Handle MCP protocol requests"""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "sql-injection-scanner",
                        "version": "1.0.0"
                    }
                }
            }
        
        elif method in {"notifications/initialized", "initialized"}:
            return None
        
        elif method == "ping":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {}
            }
        
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": [
                    {"name": name, **info} 
                    for name, info in self.tools.items()
                ]}
            }
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name == "scan_file":
                result = await scan_file_handler(arguments.get("file_path", ""))
            elif tool_name == "scan_directory":
                result = await scan_directory_handler(arguments.get("directory", "."))
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                        "isError": True
                    }
                }
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
            }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            }
    
    def read_message(self):
        """Read either framed (Content-Length) or line-delimited JSON-RPC messages."""
        first_line = sys.stdin.buffer.readline()
        if not first_line:
            return None

        stripped = first_line.strip()
        if stripped.startswith(b'{') or stripped.startswith(b'['):
            self.message_mode = "line"
            return json.loads(stripped.decode('utf-8'))

        # Parse framed transport headers (case-insensitive)
        headers = {}
        line = first_line
        while True:
            if line == b'\r\n' or line == b'\n':
                break
            if b':' in line:
                key, value = line.decode('utf-8').strip().split(':', 1)
                headers[key.strip().lower()] = value.strip()
            line = sys.stdin.buffer.readline()
            if not line:
                return None

        content_length = int(headers.get('content-length', 0))
        if content_length > 0:
            self.message_mode = "framed"
            content = sys.stdin.buffer.read(content_length)
            return json.loads(content.decode('utf-8'))
        return None
    
    def write_message(self, response):
        """Write response using the same mode as the incoming request."""
        if self.message_mode == "line":
            line = json.dumps(response) + "\n"
            sys.stdout.write(line)
            sys.stdout.flush()
            return

        content = json.dumps(response).encode('utf-8')
        message = f"Content-Length: {len(content)}\r\n\r\n".encode('utf-8') + content
        sys.stdout.buffer.write(message)
        sys.stdout.buffer.flush()
    
    async def run(self):
        """Main server loop - read from stdin, write to stdout using LSP framing"""
        while True:
            try:
                request = await asyncio.get_event_loop().run_in_executor(
                    None, self.read_message
                )
                if request is None:
                    break
                
                response = await self.handle_request(request)
                if response is not None:
                    await asyncio.get_event_loop().run_in_executor(
                        None, self.write_message, response
                    )
                
            except json.JSONDecodeError as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
                }
                await asyncio.get_event_loop().run_in_executor(
                    None, self.write_message, error_response
                )
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32000, "message": str(e)}
                }
                await asyncio.get_event_loop().run_in_executor(
                    None, self.write_message, error_response
                )


async def main():
    server = SQLScannerMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())

