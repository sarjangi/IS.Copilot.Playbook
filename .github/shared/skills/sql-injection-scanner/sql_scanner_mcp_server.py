#!/usr/bin/env python3
"""
SQL Injection Scanner - MCP Server
Model Context Protocol server for integrating with GitHub Copilot
"""
import json
import sys
import asyncio
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from tools.securityTool import scan_file_handler, scan_directory_handler
except ImportError:
    # Fallback if imports fail
    async def scan_file_handler(file_path):
        return {"success": False, "error": "Scanner not available"}
    async def scan_directory_handler(directory, recursive=True):
        return {"success": False, "error": "Scanner not available"}


class SQLScannerMCPServer:
    """MCP Server for SQL Injection Scanner"""
    
    def __init__(self):
        self.tools = {
            "scan_file": {
                "description": "Scan a single file for SQL injection vulnerabilities",
                "parameters": {
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
                "parameters": {
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
                    "name": "sql-injection-scanner",
                    "version": "1.0.0",
                    "capabilities": {"tools": True}
                }
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
                result = {"error": f"Unknown tool: {tool_name}"}
            
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
        """Read LSP-style framed message from stdin"""
        # Read headers
        headers = {}
        while True:
            line = sys.stdin.buffer.readline()
            if line == b'\r\n' or line == b'\n':
                break
            if b':' in line:
                key, value = line.decode('utf-8').strip().split(':', 1)
                headers[key.strip()] = value.strip()
        
        # Read content
        content_length = int(headers.get('Content-Length', 0))
        if content_length > 0:
            content = sys.stdin.buffer.read(content_length)
            return json.loads(content.decode('utf-8'))
        return None
    
    def write_message(self, response):
        """Write LSP-style framed message to stdout"""
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

