"""MCP (Model Context Protocol) server.

Exposes the skills registry via 8 tools over stdio JSON-RPC. Spawned as a
subprocess by MCP clients (Claude Code, OpenClaw, Cursor, etc.).

See docs/superpowers/specs/2026-05-12-mcp-and-search-design.md § 5.
"""

PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "iknowkungfu"
SERVER_VERSION = "0.1.6"
