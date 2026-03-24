"""MCP server for Boudicaa. SDS 8.1."""
import asyncio

from mcp.server import Server
from mcp.types import TextContent, Tool

from .tools import GTDTools

server = Server("boudicaa")
tools = GTDTools()


@server.list_tools()
async def list_tools():
    return tools.get_tool_definitions()


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    return await tools.execute(name, arguments)
