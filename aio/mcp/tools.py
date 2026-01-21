"""MCP tool definitions for AIorgianization.

This module contains the tool schema definitions. The actual handlers
are in server.py.
"""

# Tool schemas are defined inline in server.py using the @server.list_tools decorator.
# This file is kept for organizational purposes and potential future expansion.

TOOL_SCHEMAS = {
    "aio_add_task": {
        "description": "Create a new task in the vault",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Task title"},
                "due": {
                    "type": "string",
                    "description": "Due date (e.g., 'tomorrow', 'friday', '2024-01-20')",
                },
                "project": {"type": "string", "description": "Project name"},
                "status": {
                    "type": "string",
                    "enum": ["inbox", "next", "scheduled", "someday"],
                    "description": "Initial status (default: inbox)",
                },
            },
            "required": ["title"],
        },
    },
    "aio_list_tasks": {
        "description": "List tasks from the vault",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["inbox", "next", "waiting", "scheduled", "someday", "today", "overdue"],
                    "description": "Filter by status",
                },
                "project": {"type": "string", "description": "Filter by project name"},
            },
        },
    },
    "aio_complete_task": {
        "description": "Mark a task as completed",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Task ID or title substring",
                },
            },
            "required": ["query"],
        },
    },
    "aio_start_task": {
        "description": "Move a task to Next status",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Task ID or title substring",
                },
            },
            "required": ["query"],
        },
    },
    "aio_defer_task": {
        "description": "Move a task to Someday status",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Task ID or title substring",
                },
            },
            "required": ["query"],
        },
    },
    "aio_get_dashboard": {
        "description": "Get the daily dashboard",
        "inputSchema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date for dashboard (default: today)",
                },
            },
        },
    },
    "aio_get_context": {
        "description": "Get context pack content",
        "inputSchema": {
            "type": "object",
            "properties": {
                "packs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of context pack names",
                },
            },
            "required": ["packs"],
        },
    },
    "aio_sync_jira": {
        "description": "Sync tasks from Jira. Imports issues assigned to you from configured projects.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, show what would be synced without making changes",
                    "default": False,
                },
            },
        },
    },
    "aio_jira_status": {
        "description": "Get Jira sync status and configuration",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    "aio_list_context_packs": {
        "description": "List available context packs for AI assistance",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["domain", "system", "operating"],
                    "description": "Filter by category (optional)",
                },
            },
        },
    },
    "aio_add_to_context_pack": {
        "description": "Add content to an existing context pack",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pack": {
                    "type": "string",
                    "description": "Context pack name or ID (e.g., 'payments', 'auth-service')",
                },
                "content": {
                    "type": "string",
                    "description": "Markdown content to add to the pack",
                },
                "section": {
                    "type": "string",
                    "description": "Section heading to append under (e.g., 'Key Concepts'). If not specified, appends to end.",
                },
            },
            "required": ["pack", "content"],
        },
    },
    "aio_add_file_to_context_pack": {
        "description": "Copy a file's content into an existing context pack",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pack": {
                    "type": "string",
                    "description": "Context pack name or ID",
                },
                "file": {
                    "type": "string",
                    "description": "Path to the file in the vault (e.g., 'ADRs/2024-01-payment-provider.md')",
                },
                "section": {
                    "type": "string",
                    "description": "Section heading to append under (optional)",
                },
            },
            "required": ["pack", "file"],
        },
    },
    "aio_create_context_pack": {
        "description": "Create a new context pack file",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Display title for the pack",
                },
                "category": {
                    "type": "string",
                    "enum": ["domain", "system", "operating"],
                    "description": "Pack category: 'domain' for business domains, 'system' for technical systems, 'operating' for processes",
                },
                "content": {
                    "type": "string",
                    "description": "Initial markdown content (optional)",
                },
                "description": {
                    "type": "string",
                    "description": "Brief description for the pack (optional)",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for categorization (optional)",
                },
            },
            "required": ["title", "category"],
        },
    },
    "aio_delegate_task": {
        "description": (
            "Delegate a task to a person "
            "(moves to Waiting status with person set as waitingOn)"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Task ID or title substring",
                },
                "person": {
                    "type": "string",
                    "description": "Person name or ID to delegate to",
                },
            },
            "required": ["query", "person"],
        },
    },
}
