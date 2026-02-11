#!/usr/bin/env python3
import asyncio
import logging
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server.stdio import stdio_server
from duckduckgo_search import DDGS

server = Server("web-search")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search",
            description="Search the web using DuckDuckGo (General search)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "max_results": {"type": "integer", "description": "Maximum number of results to return", "default": 5}
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="search_news",
            description="Search for recent news using DuckDuckGo",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The news search query"},
                    "max_results": {"type": "integer", "description": "Maximum number of results to return", "default": 5}
                },
                "required": ["query"],
            },
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name == "search":
        query = arguments.get("query")
        max_results = arguments.get("max_results", 5)
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            if not results:
                # Fallback to news search if general search returns nothing
                results = list(ddgs.news(query, max_results=max_results))
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error during general search: {str(e)}")]
        
        if not results:
            return [types.TextContent(type="text", text="No results found for this query.")]

        formatted_results = []
        for r in results:
            formatted_results.append(f"Title: {r.get('title')}\nURL: {r.get('href') or r.get('url')}\nBody: {r.get('body')}\n---")
        
        return [types.TextContent(type="text", text="\n".join(formatted_results))]

    elif name == "search_news":
        query = arguments.get("query")
        max_results = arguments.get("max_results", 5)
        try:
            with DDGS() as ddgs:
                results = list(ddgs.news(query, max_results=max_results))
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error during news search: {str(e)}")]
            
        if not results:
            return [types.TextContent(type="text", text="No news found for this query.")]

        formatted_results = []
        for r in results:
            formatted_results.append(f"Title: {r.get('title')}\nDate: {r.get('date')}\nURL: {r.get('url')}\nBody: {r.get('body')}\n---")
        
        return [types.TextContent(type="text", text="\n".join(formatted_results))]

    raise ValueError(f"Unknown tool: {name}")

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="web-search",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
