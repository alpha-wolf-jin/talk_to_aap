#!/usr/bin/env python3
"""
MCP (Model Context Protocol) connection utilities.
Handles connections to MCP servers and tool registration.
"""

import os
from typing import Dict, Any, TYPE_CHECKING

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

if TYPE_CHECKING:
    from aap_MaaS import AAPAssistantAgent

# Import from config instead of direct environment access
try:
    from config import Config
    MCP_HOST = Config.MCP_HOST
    MCP_PORT = Config.MCP_PORT
except ImportError:
    # Fallback if config not available
    MCP_HOST = os.environ.get('MCP_HOST', 'localhost')
    MCP_PORT = os.environ.get('MCP_PORT', '8000')


async def connect_to_server(
    self: 'AAPAssistantAgent',
    server_name: str,
    server_config: Dict[str, Any]
) -> None:
    """
    Connect to a specific MCP server and register its tools.
    
    Args:
        self: AAPAssistantAgent instance
        server_name: Name of the server to connect to
        server_config: Configuration dict with server details
    """
    try:
        if server_config.get("type") == "sse":
            url = server_config["url"]
            print(f"\nConnecting to SSE MCP server: {url}")
            sse_transport = await self.exit_stack.enter_async_context(
                sse_client(url=url)
            )
            read, write = sse_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            await session.send_ping()
        else:
            # Stdio connection
            server_params = StdioServerParameters(**server_config)
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()

        try:
            response = await session.list_tools()
            tool_count = 0
            for tool in response.tools:
                self.sessions[tool.name] = session
                self.available_tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                })
                self.all_tools.append(tool.name)
                self.service_description += "\n<Tool Description>\n"
                self.service_description += f"Tool Name: {tool.name}\n"
                self.service_description += f"Tool Input Schema:\n{tool.inputSchema}\n\n"
                self.service_description += f"Tool Description:\n{tool.description}"
                self.service_description += "\n</Tool Description>\n"
                tool_count += 1

            self.service_description += self.separator
            print(f"Successfully registered {tool_count} tools from {server_name}")

        except Exception as e:
            print(f"Error listing tools from {server_name}: {e}")
            
    except Exception as e:
        print(f"Error connecting to {server_name}: {e}")


async def connect_to_servers(self: 'AAPAssistantAgent') -> None:
    """
    Connect to all configured MCP servers.
    
    Args:
        self: AAPAssistantAgent instance
    """
    try:
        servers = {
            'aap_01': {
                'url': f"http://{MCP_HOST}:{MCP_PORT}/sse",
                'type': 'sse'
            }
        }
        print(f"Connecting to MCP servers: {servers}")
        
        for server_name, server_config in servers.items():
            await self.connect_to_server(server_name, server_config)

        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.available_tools)
        # Note: mistral_with_tools was unused - removed

    except Exception as e:
        print(f"Error loading server config: {e}")
        raise

