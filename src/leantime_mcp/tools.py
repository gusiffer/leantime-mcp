# SPDX-FileCopyrightText: 2025 Daniel Eder
#
# SPDX-License-Identifier: MIT

"""MCP tool definitions for Leantime API."""

from mcp.types import Tool
from typing import Any

# Define MCP tools that map to Leantime operations
TOOLS = [
    Tool(
        name="get_project",
        description="Get details of a specific project by ID",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "The ID of the project to retrieve"
                }
            },
            "required": ["project_id"]
        }
    ),
    Tool(
        name="list_projects",
        description="List all projects accessible to the user",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ),
    Tool(
        name="create_project",
        description="Create a new project",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the project"
                },
                "details": {
                    "type": "string",
                    "description": "Project description/details"
                },
                "clientId": {
                    "type": "integer",
                    "description": "Client ID associated with the project"
                }
            },
            "required": ["name"]
        }
    ),
    Tool(
        name="get_ticket",
        description="Get details of a specific ticket/task by ID",
        inputSchema={
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "integer",
                    "description": "The ID of the ticket to retrieve"
                }
            },
            "required": ["ticket_id"]
        }
    ),
    Tool(
        name="list_tickets",
        description="List tickets, optionally filtered by project",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "Optional project ID to filter tickets"
                }
            }
        }
    ),
    Tool(
        name="create_ticket",
        description="Create a new ticket/task",
        inputSchema={
            "type": "object",
            "properties": {
                "headline": {
                    "type": "string",
                    "description": "Title/headline of the ticket"
                },
                "project_id": {
                    "type": "integer",
                    "description": "Project ID where the ticket will be created"
                },
                "user_id": {
                    "type": "integer",
                    "description": "The ID of the user creating the ticket"
                },
                "date": {
                    "type": "string",
                    "description": "The date when the ticket is created (YYYY-MM-DD format)"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of the ticket"
                },
                "status": {
                    "type": "integer",
                    "description": "Status ID of the ticket"
                },
                "priority": {
                    "type": "string",
                    "description": "Priority level (e.g., 'high', 'medium', 'low')"
                },
                "assignedTo": {
                    "type": "integer",
                    "description": "User ID to assign the ticket to"
                },
                "tags": {
                    "type": "string",
                    "description": "Comma-separated list of tags to add to the ticket"
                }
            },
            "required": ["headline", "project_id", "user_id"]
        }
    ),
    Tool(
        name="update_ticket",
        description="Update an existing ticket",
        inputSchema={
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "integer",
                    "description": "ID of the ticket to update"
                },
                "project_id": {
                    "type": "integer",
                    "description": "Project ID where the ticket belongs"
                },
                "headline": {
                    "type": "string",
                    "description": "New title/headline"
                },
                "description": {
                    "type": "string",
                    "description": "New description"
                },
                "status": {
                    "type": "integer",
                    "description": "New status ID"
                },
                "priority": {
                    "type": "string",
                    "description": "New priority level"
                },
                "assignedTo": {
                    "type": "integer",
                    "description": "New assignee user ID"
                }
            },
            "required": ["ticket_id", "project_id"]
        }
    ),
    Tool(
        name="get_status_labels",
        description="Get all available ticket status labels with their IDs. Use this to find out what status ID corresponds to what status name (e.g., Open, In Progress, Done, etc.)",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ),
    Tool(
        name="get_user",
        description="Get details of a specific user by ID",
        inputSchema={
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "The ID of the user to retrieve"
                }
            },
            "required": ["user_id"]
        }
    ),
    Tool(
        name="list_users",
        description="List all users in the Leantime instance",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ),
    Tool(
        name="add_comment",
        description="Add a comment to a module (ticket, project, etc.)",
        inputSchema={
            "type": "object",
            "properties": {
                "module": {
                    "type": "string",
                    "description": "Module type (e.g., 'ticket', 'project')"
                },
                "module_id": {
                    "type": "integer",
                    "description": "ID of the module to comment on"
                },
                "comment": {
                    "type": "string",
                    "description": "Comment text"
                }
            },
            "required": ["module", "module_id", "comment"]
        }
    ),
    Tool(
        name="get_comments",
        description="Get all comments for a module",
        inputSchema={
            "type": "object",
            "properties": {
                "module": {
                    "type": "string",
                    "description": "Module type (e.g., 'ticket', 'project')"
                },
                "module_id": {
                    "type": "integer",
                    "description": "ID of the module"
                }
            },
            "required": ["module", "module_id"]
        }
    ),
    Tool(
        name="add_timesheet",
        description="Add a timesheet entry for time tracking",
        inputSchema={
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "ID of the user logging time"
                },
                "ticket_id": {
                    "type": "integer",
                    "description": "ID of the ticket"
                },
                "hours": {
                    "type": "number",
                    "description": "Number of hours worked"
                },
                "date": {
                    "type": "string",
                    "description": "Date of work (YYYY-MM-DD format)"
                },
                "description": {
                    "type": "string",
                    "description": "Description of work done"
                }
            },
            "required": ["user_id", "ticket_id", "hours", "date"]
        }
    ),
    Tool(
        name="get_timesheets",
        description="Get timesheet entries, optionally filtered by project or user (RPC Timesheets.pollForNewTimesheets)",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "Optional project ID to filter timesheets"
                },
                "user_id": {
                    "type": "integer",
                    "description": "Optional user ID to filter timesheets"
                }
            }
        }
    ),
    Tool(
        name="get_all_subtasks",
        description="Get all subtasks for a specific ticket",
        inputSchema={
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "integer",
                    "description": "The ID of the parent ticket"
                }
            },
            "required": ["ticket_id"]
        }
    ),
    Tool(
        name="upsert_subtask",
        description="Create or update a subtask for a ticket",
        inputSchema={
            "type": "object",
            "properties": {
                "parent_ticket": {
                    "type": "integer",
                    "description": "The ID of the parent ticket"
                },
                "headline": {
                    "type": "string",
                    "description": "Title/headline of the subtask"
                },
                "date": {
                    "type": "string",
                    "description": "The date when the subtask is created (YYYY-MM-DD format)"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of the subtask"
                },
                "status": {
                    "type": "integer",
                    "description": "Status ID of the subtask"
                },
                "priority": {
                    "type": "string",
                    "description": "Priority level (e.g., 'high', 'medium', 'low')"
                },
                "assignedTo": {
                    "type": "integer",
                    "description": "User ID to assign the subtask to"
                },
                "tags": {
                    "type": "string",
                    "description": "Comma-separated list of tags to add to the subtask"
                }
            },
            "required": ["parent_ticket", "headline"]
        }
    ),
    Tool(
        name="ideas_list_boards",
        description="List the Ideas boards of a project (Ideas.getAllBoards; projectId required). Read-only; read/create pass only - no delete/patch Ideas methods exist in this toolset.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "Project ID whose Ideas boards to list"
                }
            },
            "required": ["project_id"]
        }
    ),
    Tool(
        name="ideas_list",
        description="List ideas, optionally filtered by project and/or board (Ideas.pollForNewIdeas). Read-only; read/create pass only - no delete/patch Ideas methods exist in this toolset.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "Optional project ID to filter ideas"
                },
                "board": {
                    "type": "integer",
                    "description": "Optional board (canvas) ID to filter ideas"
                }
            }
        }
    ),
    Tool(
        name="ideas_create",
        description="Create a new idea on an Ideas board (Ideas.createIdeaItem), returning the new idea id. READ/CREATE ONLY - no delete/patch Ideas methods exist in this toolset; native deletions stay founder-UI-side this pass (ticket #333 scope-out).",
        inputSchema={
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Idea text/description"
                },
                "board_canvas_id": {
                    "type": "integer",
                    "description": "Board (canvas) ID to place the idea on, from ideas_list_boards"
                },
                "project_id": {
                    "type": "integer",
                    "description": "Project ID owning the board"
                },
                "author_id": {
                    "type": "integer",
                    "description": "Leantime user id authoring the idea (the calling mount's account id)"
                },
                "status": {
                    "type": "string",
                    "description": "Idea status key (default 'idea'; labels: idea/research/prototype/validation/implemented/deferred)"
                },
                "data": {
                    "type": "string",
                    "description": "Details/data for the idea (optional)"
                },
                "box": {
                    "type": "string",
                    "description": "Canvas box type (default 'idea')"
                }
            },
            "required": ["description", "board_canvas_id", "project_id", "author_id"]
        }
    ),
]


def get_tools() -> list[Tool]:
    """Return the list of available MCP tools."""
    return TOOLS
