# Instructions to Check MCP Status in VS Code

## Option 1: Developer Console Method

1. In VS Code, press: `Ctrl+Shift+P`
2. Type: `Developer: Toggle Developer Tools`
3. Go to `Console` tab
4. Filter for: `mcp` (use the filter box)
5. Try using Copilot Chat to scan a file
6. Look for MCP-related log messages

## Option 2: Settings UI Method

1. In VS Code, press: `Ctrl+,` (Settings)
2. Search for: `mcp`
3. You should see:
   - `Chat > Experimental > MCP: Enabled` (should be checked)
   - `Chat > MCP > Gallery: Enabled` (should be checked)
   - `Chat > MCP > Servers` (click "Edit in settings.json")

## Option 3: Direct Test Method

1. Open Copilot Chat: `Ctrl+Shift+I`
2. Open the test file: `test_sql_injection.py`
3. In Copilot Chat, type: "Scan this file for SQL vulnerabilities"
4. Expected behavior:
   - ✅ WITH MCP: Detailed scan results, identifies line 10 vulnerability
   - ❌ WITHOUT MCP: Generic advice about SQL injection, no specific line numbers

## Option 4: Command Palette Search

1. Press: `Ctrl+Shift+P`
2. Type: `mcp`
3. See what MCP-related commands appear
4. Common variations:
   - "MCP: Show Servers"
   - "Copilot: MCP Servers"
   - "Chat: MCP Servers"

## If Nothing Works:

The MCP feature might not be available in your VS Code/Copilot version yet.
Check your extension versions:
- GitHub Copilot: Should be v1.150+ (for MCP support)
- GitHub Copilot Chat: Should be latest version

Update extensions:
1. Extensions panel (`Ctrl+Shift+X`)
2. Search "GitHub Copilot"
3. Check for updates
