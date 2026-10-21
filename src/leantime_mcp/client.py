# SPDX-FileCopyrightText: 2025 Daniel Eder
#
# SPDX-License-Identifier: MIT

"""Leantime JSON-RPC 2.0 client implementation."""

import httpx
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


class LeantimeAPIError(Exception):
    """Exception raised for Leantime API errors."""
    
    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"Leantime API Error {code}: {message}")


class LeantimeClient:
    """Client for interacting with Leantime's JSON-RPC 2.0 API."""
    
    def __init__(self, base_url: str, api_key: str):
        """Initialize the Leantime client.
        
        Args:
            base_url: Base URL of the Leantime instance (e.g., https://leantime.example.com)
            api_key: API key for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.endpoint = f"{self.base_url}/api/jsonrpc"
        self._request_id = 0
    
    def _get_next_id(self) -> int:
        """Get next JSON-RPC request ID."""
        self._request_id += 1
        return self._request_id
    
    async def call(self, method: str, params: Optional[dict] = None) -> Any:
        """Make a JSON-RPC 2.0 call to Leantime API.
        
        Args:
            method: RPC method name (e.g., "leantime.rpc.Projects.getProject")
            params: Method parameters as dictionary
            
        Returns:
            The result from the JSON-RPC response
            
        Raises:
            LeantimeAPIError: If the API returns an error
            httpx.HTTPError: If there's a network/HTTP error
        """
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": self._get_next_id()
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-API-KEY": self.api_key
        }
        
        logger.debug(f"Calling Leantime RPC: {method} with params: {params}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.endpoint,
                json=payload,
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Check for JSON-RPC error
            if "error" in data:
                error = data["error"]
                raise LeantimeAPIError(
                    code=error.get("code", -1),
                    message=error.get("message", "Unknown error"),
                    data=error.get("data")
                )
            
            # Return the result
            return data.get("result")
    
    # Convenience methods for common operations
    
    async def get_project(self, project_id: int) -> dict:
        """Get project details by ID."""
        return await self.call("leantime.rpc.Projects.getProject", {"id": project_id})
    
    async def list_projects(self) -> list:
        """List all projects."""
        return await self.call("leantime.rpc.Projects.getAll")
    
    async def create_project(self, name: str, details: Optional[str] = None, **kwargs) -> dict:
        """Create a new project.

        Note: Leantime's Projects.addProject RPC expects the project fields
        wrapped in a single 'values' object (same shape as addTicket/updateTicket).
        Passing them flat returns JSON-RPC error -32602 (Invalid params).
        """
        values = {"name": name, **kwargs}
        if details:
            values["details"] = details
        return await self.call("leantime.rpc.Projects.addProject", {"values": values})
    
    async def get_ticket(self, ticket_id: int) -> dict:
        """Get ticket details by ID."""
        return await self.call("leantime.rpc.Tickets.Tickets.getTicket", {"id": ticket_id})
    
    async def list_tickets(self, project_id: Optional[int] = None) -> list:
        """List tickets, optionally filtered by project."""
        searchCriteria = {}
        if project_id:
            searchCriteria["currentProject"] = project_id
        params = {"searchCriteria": searchCriteria}
        return await self.call("leantime.rpc.Tickets.Tickets.getAll", params)
    
    async def create_ticket(self, headline: str, project_id: int, user_id: int, date: Optional[str] = None, tags: Optional[str] = None, **kwargs) -> dict:
        """Create a new ticket.
        
        Args:
            headline: Title/headline of the ticket
            project_id: Project ID where the ticket will be created
            user_id: The ID of the user creating the ticket
            date: The date when the ticket is created (YYYY-MM-DD format). Defaults to current date if not provided.
            tags: Comma-separated list of tags to add to the ticket
            **kwargs: Additional parameters
        """
        from datetime import datetime
        
        # Use current date if none provided
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # The API expects a 'values' parameter containing the ticket data
        values = {
            "headline": headline, 
            "projectId": project_id,
            "userId": user_id,
            "date": date,
            **kwargs
        }
        
        # Add tags if provided
        if tags is not None:
            values["tags"] = tags

        # Assignee normalization (#80 quirk +3, fix 2026-10-09): Leantime's ticket
        # assignee column is 'editorId'; 'assignedTo' is silently ignored by
        # addTicket (verified live on #88).
        self._normalize_assignee(values)

        params = {"values": values}
        return await self.call("leantime.rpc.Tickets.Tickets.addTicket", params)

    async def update_ticket(self, ticket_id: int, project_id: int, **kwargs) -> dict:
        """Update an existing ticket.

        Args:
            ticket_id: The ID of the ticket to update
            project_id: The project ID where the ticket belongs
            **kwargs: Additional parameters to update
        """
        values = {"id": ticket_id, "projectId": project_id, **kwargs}
        # Assignee normalization (#80 quirk +3, fix 2026-10-09): Leantime ignores
        # 'assignedTo' on updateTicket (string AND int probes left editorId ''
        # on #88); the real column is 'editorId' (verified live: editorId: 13
        # landed and rendered as the assignee).
        self._normalize_assignee(values)
        params = {"values": values}
        return await self.call("leantime.rpc.Tickets.Tickets.updateTicket", params)
    
    async def get_status_labels(self) -> dict:
        """Get all available ticket status labels with their IDs.
        
        Returns:
            A dictionary mapping status IDs to their labels
        """
        return await self.call("leantime.rpc.Tickets.Tickets.getStatusLabels")
    
    async def get_user(self, user_id: int) -> dict:
        """Get user details by ID."""
        return await self.call("leantime.rpc.Users.getUser", {"id": user_id})
    
    async def list_users(self) -> list:
        """List all users."""
        return await self.call("leantime.rpc.Users.getAll")
    
    async def get_user_by_email(self, email: str) -> dict:
        """Get user details by email address."""
        return await self.call("leantime.rpc.Users.Users.getUserByEmail", {"email": email})
    
    async def add_comment(self, module: str, module_id: int, comment: str) -> bool:
        """Add a comment to a module (e.g., ticket, project).

        Leantime's Comments.addComment RPC signature is
        addComment($values, $module, $entityId, $entity = null): the text must
        ride in a 'values' object under 'text' ('father'/'parentId' selects the
        parent comment), and the entity id must be named 'entityId'. The old
        flat {module, moduleId, comment} shape is the ROOT CAUSE of ticket #71:
        the JSON-RPC layer answers -32602 Invalid params because required
        params 'values' and 'entityId' are missing. Verified against the live
        instance 2026-10-09: flat shape -> -32602; corrected shape -> result
        true + read-back via corrected getComments. Aliases ('tickets', 'task',
        'tasks') are normalized server-side; unknown modules raise -32602.
        """
        params = {
            "values": {"text": comment, "father": 0},
            "module": module,
            "entityId": module_id,
        }
        return await self.call("leantime.rpc.Comments.addComment", params)

    async def get_comments(self, module: str, module_id: int) -> list:
        """Get comments for a module.

        Leantime's Comments.getComments RPC signature is
        getComments($module, $entityId, $commentOrder = 0, $parent = 0,
        $strict = false): the entity id must be named 'entityId' - the old
        {module, moduleId} shape returns -32602 Invalid params (ticket #71).
        Verified live 2026-10-09: corrected shape returns the comment array.
        """
        params = {
            "module": module,
            "entityId": module_id,
        }
        return await self.call("leantime.rpc.Comments.getComments", params)
    
    async def add_timesheet(self, user_id: int, ticket_id: int, hours: float, date: str, **kwargs) -> dict:
        """Add a timesheet entry."""
        params = {
            "userId": user_id,
            "ticketId": ticket_id,
            "hours": hours,
            "date": date,
            **kwargs
        }
        return await self.call("leantime.rpc.Timesheets.addTime", params)
    
    async def get_timesheets(self, project_id: Optional[int] = None, user_id: Optional[int] = None) -> list:
        """Get timesheet entries.

        Backed by ``leantime.rpc.Timesheets.pollForNewTimesheets`` — Leantime
        has no ``Timesheets.getTimesheets`` RPC method (its API answers
        -32601 "Method doesn't exist: getTimesheets"; verified 2026-10-05).
        pollForNewTimesheets takes an optional projectId and has no server-side
        user filter, so a user_id filter is applied client-side on the rows.
        Re-verified live 2026-10-09 (#80): getTimesheets still answers -32601
        ("Method doesn't exist: getTimesheets") - the gap is upstream truth, not
        a wrapper bug. For server-side filters prefer get_timesheets_range()
        below (Timesheets.getAll; accepts plain date strings, probe-verified
        same day), or get_timesheet() for a single entry (Timesheets.getTimesheet,
        also probe-verified 2026-10-09).
        """
        params = {}
        if project_id:
            params["projectId"] = project_id
        entries = await self.call("leantime.rpc.Timesheets.pollForNewTimesheets", params) or []
        if user_id:
            entries = [row for row in entries if str(row.get("userId", "")) == str(user_id)]
        return entries
    
    async def get_all_subtasks(self, ticket_id: int) -> list:
        """Get all subtasks for a ticket.
        
        Args:
            ticket_id: The ID of the parent ticket
            
        Returns:
            A list of subtasks or false if an error occurred
        """
        params = {"ticketId": ticket_id}
        return await self.call("leantime.rpc.Tickets.Tickets.getAllSubtasks", params)
    
    async def upsert_subtask(self, parent_ticket_id: int, headline: str, date: Optional[str] = None, tags: Optional[str] = None, **kwargs) -> dict:
        """Create or update a subtask.
        
        Args:
            parent_ticket_id: The ID of the parent ticket
            headline: Title/headline of the subtask
            date: The date when the subtask is created (YYYY-MM-DD format). Defaults to current date if not provided.
            tags: Comma-separated list of tags to add to the subtask
            **kwargs: Additional parameters (description, status, priority, assignedTo, etc.)
            
        Returns:
            The created subtask data
        """
        from datetime import datetime
        
        # Use current date if none provided
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Fetch the parent ticket data to get project_id and milestone_id
        parent_ticket_data = await self.get_ticket(parent_ticket_id)
        
        if not parent_ticket_data:
            raise ValueError(f"Parent ticket with ID {parent_ticket_id} not found")
        
        # Extract required fields from parent ticket
        project_id = parent_ticket_data.get("projectId")
        if not project_id:
            raise ValueError(f"Could not determine projectId from parent ticket {parent_ticket_id}")
        
              # Extract required fields from parent ticket
        user_id = parent_ticket_data.get("userId")
        if not user_id:
            raise ValueError(f"Could not determine userId from parent ticket {parent_ticket_id}")

        milestone_id = parent_ticket_data.get("milestoneid")
        
        # The API expects a 'values' parameter containing the subtask data
        values = {
            "headline": headline,
            "type": "subtask",  # Mark this as a subtask
            "projectId": project_id,
            "userId": user_id,
            "date": date,
            "dependingTicketId": parent_ticket_id,  # Link to parent ticket
            "milestoneid": milestone_id if milestone_id else "",  # Use parent's milestone
            **kwargs
        }
        
        # Add tags if provided
        if tags is not None:
            values["tags"] = tags
        
        self._normalize_assignee(values)  # assignee fix: assignedTo -> editorId (#80 quirk +3)

        # Use addTicket to create the subtask
        params = {"values": values}
        
        # Debug logging
        logger.info(f"Creating subtask via addTicket: type=subtask, dependingTicketId={parent_ticket_id}, milestoneid={milestone_id}")
        
        return await self.call("leantime.rpc.Tickets.Tickets.addTicket", params)

    # ------------------------------------------------------------------
    # Helpers + methods added 2026-10-09 for the #80 quirk family
    # (ride the #71 redeploy window; fixes verified by live RPC probes)
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_assignee(values: dict) -> None:
        """Translate an 'assignedTo' value into Leantime's real assignee column.

        Leantime stores the ticket assignee in 'editorId' ("assigned to"); there
        is NO 'assignedTo' RPC key - addTicket/updateTicket silently ignore it
        (#80 quirk +3, verified live 2026-10-09 on #88: string '13' and int 13
        both left editorId '', while values {'editorId': 13} landed and rendered
        as assignee "Pike Agent"). Casts numeric values to int; junk values are
        dropped with a warning instead of being shipped to Leantime.
        """
        raw = values.pop("assignedTo", None)
        if raw is None or (isinstance(raw, str) and raw.strip() == ""):
            return
        try:
            values["editorId"] = int(raw)
        except (TypeError, ValueError):
            logger.warning("Dropping non-numeric assignedTo value: %r", raw)

    async def update_project(self, project_id: int, **fields) -> bool:
        """Patch a project with PARTIAL updates (only the fields passed change).

        RPC: leantime.rpc.Projects.patchProject($id, $values) - the @api JSON-RPC
        entry point that delegates to Projects::patch(); unlike editProject
        (full replace) it preserves every field not passed, including 'type', and
        explicitly strips control fields. Requires manager+ on the target project
        (projects.edit); verified live 2026-10-09 with an idempotent patch on
        project 21 (result true). Closes #80 quirk 2: the toolset had
        create_project but no project-update path, so details corrections needed
        manual UI edits or direct DB writes.

        Common fields: name, details, clientId, hourBudget, dollarBudget,
        start, end, menuType, state (-1 archives, fires ProjectArchived),
        parent (container nesting; cyclic parents rejected server-side).
        """
        params = {"id": project_id, "values": fields}
        return await self.call("leantime.rpc.Projects.patchProject", params)

    async def get_timesheet(self, entry_id: int) -> dict:
        """Read ONE timesheet entry by id.

        RPC: leantime.rpc.Timesheets.getTimesheet(int $id) - exists on the live
        instance (probe 2026-10-09: id 1 returned the row). Soft-denies to false
        for entries the seat may not view (other users' entries need manager+).
        """
        return await self.call("leantime.rpc.Timesheets.getTimesheet", {"id": entry_id})

    async def get_timesheets_range(self, date_from: str, date_to: str, project_id: Optional[int] = None, user_id: Optional[int] = None, kind: str = "all") -> list:
        """Read timesheets in a date bracket with SERVER-SIDE filters.

        RPC: leantime.rpc.Timesheets.getAll($dateFrom, $dateTo, $projectId = -1,
        $kind = 'all', $userId = null, ...). Verified live 2026-10-09: the JSON-RPC
        layer accepts plain date strings for the CarbonInterface args and applies
        the projectId/userId filters server-side (probe returned [] cleanly).

        Permission split (soft, per the Timesheets service): filtering on YOUR
        OWN userId -> timesheets.view (editor+); another user's data or an
        all-users pull (userId omitted) -> manager+ (timesheets.manage). This is
        the sharp alternative to get_timesheets()'s pollForNewTimesheets
        all-account pull.
        """
        params: dict = {"dateFrom": date_from, "dateTo": date_to, "kind": kind}
        if project_id is not None:
            params["projectId"] = project_id
        if user_id is not None:
            params["userId"] = user_id
        result = await self.call("leantime.rpc.Timesheets.getAll", params)
        return result or []

    # ------------------------------------------------------------------
    # Ideas methods added 2026-10-17 for ticket #333 (founder route word "B":
    # adopt Leantime's native Ideas module as the house idea board).
    # LIVE-PROBE RECEIPTS (Pike 027, 2026-10-17; scripts
    # logs/probe-leantime-ideas-v3-pike.py + logs/probe-leantime-ideas-v3b-boards.py;
    # keys read from .env in-memory, never echoed; zero deletes): every Ideas
    # RPC call must use the leantime.rpc FQN — a bare "Ideas.ping"-style
    # string answers -32602 "Method string doesn't start with leantime.rpc."
    # (that -32602 is the method-string wall, NOT an existence signal —
    # correcting the v2 probe receipt; all six v2 candidate names answer
    # -32601 "Method doesn't exist" under the correct FQN). Verified shapes:
    # Ideas.getAllBoards(projectId REQUIRED), Ideas.pollForNewIdeas(projectId?
    # and board? both optional), Ideas.createIdeaItem(input/projectId/authorId
    # -> int id), Ideas.getBoardLabels/getCanvasTypes (no params),
    # Ideas.getIdeaItem(id REQUIRED), Ideas.getBoardItems(boardId).
    # Read/create only: NO delete/patch Ideas methods ship this pass.
    # ------------------------------------------------------------------

    async def ideas_list_boards(self, project_id: int) -> list:
        """List the Ideas boards (canvases) of one project.

        RPC: leantime.rpc.Ideas.getAllBoards(int $projectId) - projectId is a
        REQUIRED param ({} answers -32602 "Required Parameter Missing:
        projectId", probe-verified live 2026-10-17). Returns board rows
        [{id, title, projectId, ...}]; the Ideas module auto-bootstraps a
        default "Board" per project, so an empty result means no boards for
        this key.
        """
        return await self.call("leantime.rpc.Ideas.getAllBoards", {"projectId": project_id})

    async def ideas_list(self, project_id: Optional[int] = None, board: Optional[int] = None) -> list:
        """List ideas, optionally filtered by project and/or board.

        RPC: leantime.rpc.Ideas.pollForNewIdeas(?int $projectId = null,
        ?int $board = null) - both params are optional ({} probed OK,
        returning every idea accessible to the key). Rows carry id,
        description, data, status, box, projectId, canvasId and ISO8601
        created/modified dates (dates normalized server-side).
        """
        params: dict = {}
        if project_id is not None:
            params["projectId"] = project_id
        if board is not None:
            params["board"] = board
        result = await self.call("leantime.rpc.Ideas.pollForNewIdeas", params)
        return result or []

    async def ideas_create(self, description: str, board_canvas_id: int, project_id: int, author_id: int, status: str = "idea", data: str = "", box: str = "idea") -> int:
        """Create one idea (canvas item) on an Ideas board.

        RPC: leantime.rpc.Ideas.createIdeaItem(array $input, int $projectId,
        int $authorId) - probe-verified live 2026-10-17 against project 19 /
        board 26: input keys box / description / status / data / canvasId;
        the result is the new idea id as an int (scratch idea id 3 read back
        verbatim through pollForNewIdeas + getIdeaItem). Read/create pass
        only - NO API delete exists in this toolset; native deletions stay
        founder-UI-side.
        """
        params = {
            "input": {
                "box": box,
                "description": description,
                "status": status,
                "data": data,
                "canvasId": int(board_canvas_id),
            },
            "projectId": int(project_id),
            "authorId": int(author_id),
        }
        result = await self.call("leantime.rpc.Ideas.createIdeaItem", params)
        try:
            return int(result)
        except (TypeError, ValueError):
            return result

    # ------------------------------------------------------------------
    # Wiki + Files methods added 2026-10-21 for ticket #373 (ag-dawa
    # wire-up; founder pick of record option (c): Files READ only, uploads
    # stay native-UI, binary-upload legs intentionally absent).
    # Surface of record = the #371 T-P0 two-plane verified table (source
    # GitHub v3.10.4 sha d437285a... + live read-only probes), named-param
    # shape mirrors the PHP signatures exactly like the Ideas methods do.
    # Deletes stay OUT of this toolset (deleteArticle/deleteWiki are
    # no-delete-law founder-GO class; updateWiki stays out - staged scope).
    # House rule for every write in this family: read-back verify with
    # wiki_get_article (C2) and carry the truth footer (canonical Trilium
    # noteId + mirror date + writer) inside the written content.
    # ------------------------------------------------------------------

    async def wiki_get_article(self, article_id: int, project_id: Optional[int] = None) -> Any:
        """Read one wiki article by id (leantime.rpc.Wiki.Wiki.getArticle)."""
        params: dict = {"id": int(article_id)}
        if project_id is not None:
            params["projectId"] = int(project_id)
        return await self.call("leantime.rpc.Wiki.Wiki.getArticle", params)

    async def wiki_get_all_project_wikis(self, project_id: int) -> Any:
        """List a project's wikis (leantime.rpc.Wiki.Wiki.getAllProjectWikis)."""
        return await self.call("leantime.rpc.Wiki.Wiki.getAllProjectWikis", {"projectId": int(project_id)})

    async def wiki_get_all_headlines(self, wiki_id: int, user_id: int) -> Any:
        """List a wiki's headlines (leantime.rpc.Wiki.Wiki.getAllWikiHeadlines)."""
        return await self.call(
            "leantime.rpc.Wiki.Wiki.getAllWikiHeadlines",
            {"wikiId": int(wiki_id), "userId": int(user_id)},
        )

    async def wiki_get_wiki(self, wiki_id: int) -> Any:
        """Read one wiki (leantime.rpc.Wiki.Wiki.getWiki)."""
        return await self.call("leantime.rpc.Wiki.Wiki.getWiki", {"id": int(wiki_id)})

    async def wiki_create_wiki(self, title: str, project_id: int, category: str = "", author: Optional[int] = None) -> Any:
        """Create a wiki (leantime.rpc.Wiki.Wiki.createWiki; CREATE checked
        server-side against the target project). Model-cast hydration: the
        fields ride inside the named 'wiki' param (probe receipt 2026-10-21)."""
        fields: dict = {"title": title, "projectId": int(project_id)}
        if category:
            fields["category"] = category
        if author is not None:
            fields["author"] = int(author)
        return await self.call("leantime.rpc.Wiki.Wiki.createWiki", {"wiki": fields})

    async def wiki_create_article(self, title: str, canvas_id: int, data: str, description: str = "", tags: str = "") -> Any:
        """Create a wiki article page (leantime.rpc.Wiki.Wiki.createArticle).
        canvas_id must be a real wiki id - the service fails closed on a
        foreign id (source-verified #371). Author attribution is the calling
        mount's Leantime account; the truth footer rides inside 'data'."""
        fields: dict = {
            "title": title,
            "description": description,
            "data": data,
            "canvasId": int(canvas_id),
        }
        if tags:
            fields["tags"] = tags
        return await self.call("leantime.rpc.Wiki.Wiki.createArticle", {"article": fields})

    async def wiki_update_article(self, article_id: int, title: str, canvas_id: int, data: str, description: str = "", tags: str = "", existing_article: Optional[dict] = None) -> Any:
        """Update a wiki article (leantime.rpc.Wiki.Wiki.updateArticle; fails
        closed on a non-article id). Passing existing_article (the article as
        read via wiki_get_article) records the audit diff server-side."""
        fields: dict = {
            "id": int(article_id),
            "title": title,
            "description": description,
            "data": data,
            "canvasId": int(canvas_id),
        }
        if tags:
            fields["tags"] = tags
        params: dict = {"article": fields}
        if existing_article is not None:
            params["existingArticle"] = existing_article
        return await self.call("leantime.rpc.Wiki.Wiki.updateArticle", params)

    async def wiki_get_article_activity(self, article_id: int, limit: int = 20) -> Any:
        """Read an article's audit + comment feed (leantime.rpc.Wiki.Wiki.getArticleActivity)."""
        return await self.call(
            "leantime.rpc.Wiki.Wiki.getArticleActivity",
            {"articleId": int(article_id), "limit": int(limit)},
        )

    async def files_get_by_module(self, module: str, entity_id: Optional[int] = None, user_id: Optional[int] = None) -> Any:
        """Read files attached to a module (leantime.rpc.Files.Files.getFilesByModule). READ only.
        Binary upload/fetch ships NO tool path here by founder pick of record
        (option (c), 2026-10-21: uploads stay native-UI)."""
        params: dict = {"module": module}
        if entity_id is not None:
            params["entityId"] = int(entity_id)
        if user_id is not None:
            params["userId"] = int(user_id)
        return await self.call("leantime.rpc.Files.Files.getFilesByModule", params)
