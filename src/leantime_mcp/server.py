# SPDX-FileCopyrightText: 2025 Daniel Eder
#
# SPDX-License-Identifier: MIT

"""Leantime MCP Server - Main server implementation."""

import os
import sys
import json
import logging
import uvicorn
from typing import Any
from dotenv import load_dotenv

from fastmcp import FastMCP

from leantime_mcp.client import LeantimeClient, LeantimeAPIError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize the FastMCP server
app = FastMCP("leantime-mcp")

# Global Leantime client instance
leantime_client: LeantimeClient = None


def get_client() -> LeantimeClient:
    """Get or create the Leantime client instance."""
    global leantime_client
    
    if leantime_client is None:
        # Get configuration from environment
        leantime_url = os.getenv("LEANTIME_URL")
        leantime_api_key = os.getenv("LEANTIME_API_KEY")
        leantime_user_email = os.getenv("LEANTIME_USER_EMAIL")
        
        if not leantime_url:
            raise ValueError(
                "LEANTIME_URL environment variable is required. "
                "Please set it in your .env file or environment."
            )
        
        if not leantime_api_key:
            raise ValueError(
                "LEANTIME_API_KEY environment variable is required. "
                "Please set it in your .env file or environment."
            )
        
        if not leantime_user_email:
            raise ValueError(
                "LEANTIME_USER_EMAIL environment variable is required. "
                "Please set it in your .env file or environment."
            )
        
        leantime_client = LeantimeClient(leantime_url, leantime_api_key)
        logger.info(f"Initialized Leantime client for {leantime_url}")
    
    return leantime_client


# Tool functions will be defined below


@app.tool()
async def get_project(project_id: int) -> str:
    """Get details of a specific project by ID."""
    client = get_client()
    result = await client.get_project(project_id)
    return json.dumps(result, indent=2)


@app.tool()
async def list_projects() -> str:
    """List all projects accessible to the user."""
    client = get_client()
    result = await client.list_projects()
    return json.dumps(result, indent=2)


@app.tool()
async def create_project(name: str, details: str = None, clientId: int = None, owner: int = None) -> str:
    """Create a new project.

    owner: Leantime user id of the project owner (e.g. the owning agent's
    Leantime account id). Optional; Leantime defaults it to the API user.
    """
    client = get_client()
    kwargs = {"owner": owner} if owner is not None else {}
    result = await client.create_project(name=name, details=details, clientId=clientId, **kwargs)
    return json.dumps(result, indent=2)


@app.tool()
async def get_ticket(ticket_id: int) -> str:
    """Get details of a specific ticket by ID."""
    client = get_client()
    result = await client.get_ticket(ticket_id)
    return json.dumps(result, indent=2)


@app.tool()
async def list_tickets(project_id: int = None) -> str:
    """List tickets, optionally filtered by project ID."""
    client = get_client()
    result = await client.list_tickets(project_id)
    return json.dumps(result, indent=2)


@app.tool()
async def create_ticket(headline: str, project_id: int, user_id: int, date: str = None, 
                       description: str = None, status: str = None, priority: str = None,
                       assignedTo: str = None, tags: str = None) -> str:
    """Create a new ticket."""
    client = get_client()
    result = await client.create_ticket(
        headline=headline, project_id=project_id, user_id=user_id, date=date,
        description=description, status=status, priority=priority,
        assignedTo=assignedTo, tags=tags
    )
    return json.dumps(result, indent=2)


@app.tool()
async def update_ticket(ticket_id: int, project_id: int, headline: str = None, description: str = None, 
                       status: int = None, priority: str = None, assignedTo: int = None) -> str:
    """Update an existing ticket."""
    client = get_client()
    # Build kwargs from non-None parameters
    kwargs = {}
    if headline is not None:
        kwargs['headline'] = headline
    if description is not None:
        kwargs['description'] = description
    if status is not None:
        kwargs['status'] = status
    if priority is not None:
        kwargs['priority'] = priority
    if assignedTo is not None:
        kwargs['assignedTo'] = assignedTo
    
    result = await client.update_ticket(ticket_id, project_id, **kwargs)
    return json.dumps(result, indent=2)


@app.tool()
async def get_status_labels() -> str:
    """Get available status labels."""
    client = get_client()
    result = await client.get_status_labels()
    return json.dumps(result, indent=2)


@app.tool()
async def get_user(user_id: int) -> str:
    """Get details of a specific user by ID."""
    client = get_client()
    result = await client.get_user(user_id)
    return json.dumps(result, indent=2)


@app.tool()
async def list_users() -> str:
    """List all users."""
    client = get_client()
    result = await client.list_users()
    return json.dumps(result, indent=2)


@app.tool()
async def add_comment(module: str, module_id: int, comment: str) -> str:
    """Add a comment to a module (ticket, project, etc.)."""
    client = get_client()
    result = await client.add_comment(module=module, module_id=module_id, comment=comment)
    return json.dumps(result, indent=2)


@app.tool()
async def get_comments(module: str, module_id: int) -> str:
    """Get comments for a module (ticket, project, etc.)."""
    client = get_client()
    result = await client.get_comments(module=module, module_id=module_id)
    return json.dumps(result, indent=2)


@app.tool()
async def add_timesheet(user_id: int, ticket_id: int, hours: float, date: str, description: str = None) -> str:
    """Add a timesheet entry."""
    client = get_client()
    result = await client.add_timesheet(
        user_id=user_id, ticket_id=ticket_id, hours=hours, date=date, description=description
    )
    return json.dumps(result, indent=2)


@app.tool()
async def get_timesheets(project_id: int = None, user_id: int = None) -> str:
    """Get timesheets, optionally filtered by project or user."""
    client = get_client()
    result = await client.get_timesheets(project_id=project_id, user_id=user_id)
    return json.dumps(result, indent=2)


@app.tool()
async def get_all_subtasks(ticket_id: int) -> str:
    """Get all subtasks for a ticket."""
    client = get_client()
    result = await client.get_all_subtasks(ticket_id)
    return json.dumps(result, indent=2)


@app.tool()
async def upsert_subtask(parent_ticket: int, headline: str,
                        date: str = None, description: str = None, status: str = None,
                        priority: str = None, assignedTo: str = None, tags: str = None) -> str:
    """Create or update a subtask."""
    client = get_client()
    result = await client.upsert_subtask(
        parent_ticket_id=parent_ticket, headline=headline,
        date=date, description=description, status=status, priority=priority,
        assignedTo=assignedTo, tags=tags
    )
    return json.dumps(result, indent=2)


def main():
    """Main entry point for the MCP server.

    Transport selection via LEANTIME_MCP_TRANSPORT (default: stdio):
      stdio            — for process-spawning clients (VS Code, Claude Desktop)
      streamable-http  — Streamable HTTP on LEANTIME_MCP_HOST/LEANTIME_MCP_PORT
    """
    transport = os.getenv("LEANTIME_MCP_TRANSPORT", "stdio").lower()
    logger.info("Starting Leantime MCP server with transport %s", transport)

    if transport == "streamable-http":
        _run_streamable_http()
    else:
        app.run(transport="stdio")


def _run_streamable_http():
    """Run the server over Streamable HTTP with DNS-rebinding protection.

    FastMCP 2.12.4 does not forward TransportSecuritySettings into the
    StreamableHTTP session manager, so the /mcp Route endpoint is wrapped
    with the MCP SDK's TransportSecurityMiddleware here.
    """
    import starlette.routing
    from starlette.requests import Request
    from mcp.server.transport_security import (
        TransportSecurityMiddleware,
        TransportSecuritySettings,
    )

    host = os.getenv("LEANTIME_MCP_HOST", "127.0.0.1")
    port = int(os.getenv("LEANTIME_MCP_PORT", "8000"))
    path = os.getenv("LEANTIME_MCP_PATH", "/mcp")
    allowed_hosts = [
        h for h in os.getenv("LEANTIME_MCP_ALLOWED_HOSTS", "").split(",") if h.strip()
    ]
    # Default allow-list covers the bind address itself; anything else is refused.
    if not allowed_hosts:
        allowed_hosts = [f"{host}:{port}", f"localhost:{port}"]

    settings = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        # Origins carry a scheme; allow both raw host:port and http(s) scheme forms.
        allowed_origins=list(
            {h for h in allowed_hosts} | {f"http://{h}" for h in allowed_hosts}
        ),
    )
    middleware = TransportSecurityMiddleware(settings)

    asgi_app = app.http_app(path=path)
    wrapped_route_index = next(
        (i for i, r in enumerate(asgi_app.router.routes)
         if isinstance(r, starlette.routing.Route) and r.path == path),
        None,
    )
    if wrapped_route_index is not None:
        inner = asgi_app.router.routes[wrapped_route_index].app

        class _SecurityGuard:
            """Pure-ASGI guard so Starlette keeps the route method-agnostic."""

            def __init__(self, app):
                self.app = app

            async def __call__(self, scope, receive, send):
                request = Request(scope, receive=receive)
                error_response = await middleware.validate_request(
                    request, is_post=(scope["method"] == "POST")
                )
                if error_response is not None:
                    await error_response(scope, receive, send)
                    return
                await self.app(scope, receive, send)

        asgi_app.router.routes[wrapped_route_index] = starlette.routing.Route(
            path, endpoint=_SecurityGuard(inner), name="mcp"
        )
    else:
        logger.warning(
            "Could not locate %s route; running without DNS-rebinding protection", path
        )

    logging.getLogger("uvicorn.error").info(
        "Leantime MCP Streamable HTTP on http://%s:%s%s (allowed hosts: %s)",
        host, port, path, ", ".join(allowed_hosts),
    )

    uvicorn.run(
        asgi_app,
        host=host,
        port=port,
        log_level="info",
        timeout_graceful_shutdown=0,
    )


if __name__ == "__main__":
    main()
