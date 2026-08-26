# MCP Interface Spec — a reusable pattern for workbench MCP servers

> How to give any workbench a **Model Context Protocol** server the same way the Pricing Workbench does: one tool surface that backs the app, the notebooks *and* external agents; governed and gated server-side; and a manifest-driven UI tab so the surface is visible and never drifts from what's actually served.
>
> Reference implementation (copy from here): `src/app/server/routes/mcp.py` (transport + manifest), `src/app/server/optimisation_mcp.py` (a tool module), `src/app/frontend/src/pages/Supervisor.tsx` (the MCP tab), `src/app/frontend/src/pages/Addons.tsx` (the Toolkit tile). Verified live: server `bricksurance-motor-distribution` v1.0.0, MCP protocol `2025-06-18`, 21 tools.

---

## 1. The principle (why this shape)

**MCP-first: build the capability once, expose it as a callable tool, and let the app, a notebook and an external agent all be clients of the same surface.** Nothing is built twice. A workbench "stage" (run the solver) and every "read" (read the factor table) becomes a tool; the app calls the same Python the MCP calls; an outside agent gets the identical behaviour over JSON-RPC.

Three non-negotiables, carried from the demo standard:
- **Deterministic core, agents at the edge.** Tools do the real work against real Unity Catalog objects / jobs / agent endpoints. The LLM decides *which* tool to call; it never invents the result.
- **Server-side gates.** Any tool that *writes/deploys* re-checks authorization and policy **inside the tool**, so no prompt or agent can bypass what the app UI enforces.
- **Everything auditable.** Every tool call can be logged; every action tool writes an audit row (and, where relevant, an immutable decision record).

---

## 2. Architecture — five building blocks

```
external agent ─┐
app UI ─────────┼──▶  POST /api/mcp   (JSON-RPC 2.0: initialize · tools/list · tools/call)
notebook ───────┘            │
                             ├── TOOL_SCHEMAS  (list of {name, description, inputSchema})
                             ├── TOOL_IMPLS    (dict  name → async impl)
                             │        │
                             │        ├── read tools   → SELECT from governed UC tables
                             │        ├── stage tools   → trigger a job / run a stage
                             │        └── action tools  → GATED write/deploy (RBAC + policy re-check + audit)
                             │
                    GET /api/mcp/manifest  (plain {server, protocol_version, tools} — what the UI reads)
```

The whole server is one FastAPI router. Multiple **tool modules** (one per domain area) each export a `SCHEMAS` list + an `IMPLS` dict; the transport file merges them into a single surface.

---

## 3. The tool contract

### 3.1 Implementation signature
Every tool is an async function with a fixed signature and a `{"ok": bool, ...}` return:

```python
async def _t_read_something(args: dict, session_id: str, agent_id: str) -> dict:
    rows = await _q(f"SELECT ... FROM {fqn('my_table')} ORDER BY ...")
    return {"ok": True, "something": rows}
```

- `args` — the caller's `arguments` object (validated against the tool's `inputSchema` by the client; validate the load-bearing ones yourself too).
- `session_id` — a stable id for the conversation (the transport supplies one if the caller didn't).
- `agent_id` — the caller's user-agent, for audit attribution.
- **Return shape:** always a dict with `ok`. On failure return `{"ok": False, "error": "..."}` (add `"gated": True` when a policy/RBAC gate blocked it). Never raise for expected failures — raising becomes a JSON-RPC `-32603`.

### 3.2 Schema helper + registry
Keep a one-line schema helper and two module-level exports:

```python
def _schema(name, desc, props=None, required=None):
    return {"name": name, "description": desc,
            "inputSchema": {"type": "object", "properties": props or {}, "required": required or []}}

XYZ_TOOL_SCHEMAS: list[dict] = [
    _schema("xyz_read_factors", "Read the solved per-segment factor table."),
    _schema("xyz_run_solver", "Solve the optimal factors for a given objective. Returns a run_id.",
            {"objective": {"type": "string", "enum": ["profit", "volume"]}}, ["objective"]),
    _schema("xyz_deploy", "Approve & deploy the solved set. Server-side gate: RBAC + policy re-check; cannot be bypassed."),
]

XYZ_TOOL_IMPLS: dict[str, callable] = {
    "xyz_read_factors": _t_read_factors,
    "xyz_run_solver":   _t_run_solver,
    "xyz_deploy":       _t_deploy,
}
```

**The `description` is the API.** It's the only thing the agent sees when choosing a tool — write it as an instruction, name the ordering ("Call this FIRST…"), and state honestly what a tool *can't* do (see the real `get_quote_requirements` / `price_motor_risk` descriptions).

### 3.3 Three kinds of tool
- **read** — `SELECT` from a governed table / view / UC function. Idempotent, ungated. The bulk of the surface.
- **stage** — kick off a job or run a stage; return a `run_id` the caller can poll. Idempotent-ish; ungated if it only computes into scratch tables.
- **action** — writes/deploys/promotes. **Always gated** (§4).

Prefix every tool with the workbench's short slug (`opt_`, `uw_`, `resv_`, `claims_`) so a merged multi-module server stays legible and the UI can group by prefix.

---

## 4. The governance gate (the load-bearing rule)

An action tool must enforce the **same gate as the app route**, inside the tool, so an MCP client cannot bypass the UI. The pattern (from `_t_deploy_factors`):

```python
async def _t_deploy(args, session_id, agent_id):
    # (1) RBAC — identical to the app route
    try:
        _require_admin("xyz-deploy")
    except HTTPException as e:
        return {"ok": False, "gated": True, "error": f"admin-only: {e.detail}"}

    # (2) policy re-check, server-side (re-validate the thing being deployed)
    rows = await _q(f"SELECT ... FROM {fqn('xyz_candidate')}")
    breaches = [... for r in rows if not within_policy(r)]
    if breaches:
        return {"ok": False, "gated": True, "error": f"blocked: {len(breaches)} outside policy"}

    # (3) write + audit + immutable decision record (parity with the app /deploy path)
    who = get_current_user() or agent_id or "mcp-agent"
    await execute_query("INSERT INTO ...deployment... ", {...})
    await execute_query("INSERT INTO ...audit_log...  ", {...})   # source='xyz_mcp'
    return {"ok": True, "deployed_by": who}
```

Rules:
- **Never** grant an action tool a path the app route doesn't have. If the app gates it, the tool gates it *the same way*.
- Use **bound `:named` params** for every write (never f-string user input into SQL) — same as the app.
- **Audit every action** with `source` naming the MCP, and write the decision record if the app does.
- Read tools inherit the app service principal's least-privilege grants — no extra grants for the MCP.

---

## 5. The transport (copy verbatim, rename the server)

One JSON-RPC entry point + a manifest. This is generic — only `SERVER_INFO`, `PROTOCOL_VERSION` and the imported tool modules change per workbench.

```python
router = APIRouter(prefix="/api/mcp", tags=["mcp"])
PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {"name": "<workbench>-<surface>", "version": "1.0.0"}

# merge every tool module into one surface
TOOL_SCHEMAS = XYZ_TOOL_SCHEMAS + ABC_TOOL_SCHEMAS
TOOL_IMPLS   = {**XYZ_TOOL_IMPLS, **ABC_TOOL_IMPLS}

def _ok(i, r):  return {"jsonrpc": "2.0", "id": i, "result": r}
def _err(i, c, m): return {"jsonrpc": "2.0", "id": i, "error": {"code": c, "message": m}}

@router.post("")
async def jsonrpc(request: Request) -> dict:
    body = await request.json()
    rpc_id, method, params = body.get("id"), body.get("method"), body.get("params") or {}
    agent_id = request.headers.get("user-agent", "unknown-agent")[:120]

    if method == "initialize":
        return _ok(rpc_id, {"protocolVersion": PROTOCOL_VERSION, "serverInfo": SERVER_INFO,
                            "capabilities": {"tools": {}}, "instructions": "<one-line how-to-drive-me>"})
    if method in ("notifications/initialized", "notifications/cancelled"):
        return _ok(rpc_id, {})
    if method == "tools/list":
        return _ok(rpc_id, {"tools": TOOL_SCHEMAS})
    if method == "tools/call":
        name, args = params.get("name"), params.get("arguments") or {}
        impl = TOOL_IMPLS.get(name)
        if impl is None:
            return _err(rpc_id, -32601, f"Unknown tool: {name}")
        session_id = str(args.get("session_id") or "").strip() or new_session_id()
        try:
            payload = await impl(args, session_id, agent_id)
        except Exception as e:
            return _err(rpc_id, -32603, f"Tool execution failed: {str(e)[:200]}")
        import json as _json
        return _ok(rpc_id, {"content": [{"type": "text", "text": _json.dumps(payload, default=str)}],
                            "structuredContent": payload, "isError": payload.get("ok") is False})
    return _err(rpc_id, -32601, f"Method not found: {method}")

@router.get("/manifest")
async def manifest():
    return {"server": SERVER_INFO, "protocol_version": PROTOCOL_VERSION, "tools": TOOL_SCHEMAS}
```

The `tools/call` envelope returns **both** `content` (text — what a generic MCP client reads) and `structuredContent` (the raw dict — what a typed client or the app uses), and sets `isError` from `ok`. Keep that shape; agent frameworks expect it.

Mount the router in the app's router registry alongside the others (`include_router(mcp.router)`).

---

## 6. The UI — a manifest-driven tab + a launcher tile

**Do not hand-list the tools in the UI.** Read the live manifest so the page can never drift from what's served.

### 6.1 The MCP tab (add to the workbench's AI / supervisor page)
- Fetch `GET /api/mcp/manifest` on mount.
- Header card: a **running** badge, and `server / version / MCP protocol / tool-count` tiles.
- The two **endpoints** (`POST /api/mcp` JSON-RPC + `GET /api/mcp/manifest`), URLs built from `window.location.origin`.
- Tools **grouped by prefix** into labelled cards (e.g. one card per domain module), each row `code(name) + description`.
- Call out any gated tool ("`xyz_deploy` is gated server-side — an agent can't bypass it").
- A "How does this work?" panel listing the endpoints + the shared-surface + server-side-gate points.

The reference component is `McpTab` in `Supervisor.tsx` (plus `PaneTab`, `McpMeta`, `McpToolList`) — copy it and change the two group prefixes. Make the tab deep-linkable: `?tab=mcp` read into the initial tab state.

### 6.2 The launcher tile
Add a tile to the workbench's Toolkit / launcher page that deep-links to the MCP tab (`/…-ai?tab=mcp`), tagged with the endpoint, tool count, and "server-side deploy gate". Reference: the "MCP Server" `AddonCard` in `Addons.tsx`.

---

## 7. Step-by-step: add MCP to a new workbench

1. **Pick the tools.** For each stage in the workbench's value chain, one *stage* tool; for each governed output, one *read* tool; for each promote/deploy, one *action* tool. Prefix them all (`<slug>_`).
2. **Write the tool module** `src/app/server/<workbench>_mcp.py`: the `_t_*` impls (thin wrappers over the same helpers the app routes already use — reuse `execute_query`, the agent client, `resolve_job_by_name`), the `_schema` helper, and the two exports (`*_TOOL_SCHEMAS`, `*_TOOL_IMPLS`).
3. **Gate the action tools** (§4) — RBAC + policy re-check + audit, identical to the app route. Add the writeback table(s) to the app SP's MODIFY grants if new.
4. **Add the transport** `src/app/server/routes/mcp.py` (copy §5), set `SERVER_INFO.name`, import + merge your module(s), mount the router.
5. **Add the UI** — the `McpTab` on the AI/supervisor page (copy §6.1), and the launcher tile (§6.2).
6. **Verify** (§8), deploy, and eyeball the tab against the live manifest.
7. **Document** — one line in the workbench's `DECISIONS.md`, and list the tools in `DEMO_QA.md` (a "what can an external agent do?" question).

Keep it MCP-first: if a capability exists in the app but not as a tool, add the tool and have the app call it — don't build the logic twice.

---

## 8. Verification (run before you trust it)

Confirm the server is up and enumerate the surface — from an authenticated browser console on the app origin, or any client with the app's OAuth:

```js
const base = location.origin;
await fetch(base + '/api/mcp/manifest').then(r => r.json());        // {server, protocol_version, tools[]}
await fetch(base + '/api/mcp', {method:'POST',
  headers:{'Content-Type':'application/json'},
  body: JSON.stringify({jsonrpc:'2.0', id:1, method:'tools/list'})}).then(r => r.json());  // {result:{tools[]}}
```

Both should return the same tool count. Then, in the app: open the MCP tab and confirm it shows `running` + the tool count + every tool with a description; click the Toolkit tile and confirm it deep-links there. Test one **gated** action tool as a non-admin — it must return `{ok:false, gated:true}`, not perform the action.

---

## 9. External callability & the managed-MCP path

- **Today (in-app MCP):** the server lives inside the Databricks App at `POST /api/mcp`. An external agent connects with the app's OAuth (the same SSO the UI uses) and speaks JSON-RPC. This is enough to demo "an outside agent operates the workbench."
- **Forward path (managed MCP):** the *tool contract* (§3) is transport-agnostic. When you move to a Databricks **managed MCP server** (UC functions / Genie / a served agent as tools), the same `_t_*` impls and schemas port over — you're swapping the transport, not rebuilding the tools. Treat the in-app server as the reference surface and the managed server as the same surface, hosted.

---

## 10. Checklist (definition of done)

- [ ] Tools cover every stage + every governed read + every action; all prefixed with the workbench slug.
- [ ] Every tool returns `{"ok": ...}`; read tools idempotent; action tools **gated server-side** (RBAC + policy re-check + audit), identical to the app route.
- [ ] Writes use bound params; new writeback tables added to the app-SP MODIFY grants.
- [ ] One JSON-RPC `POST /api/mcp` + `GET /api/mcp/manifest`; `SERVER_INFO` named `<workbench>-<surface>`; modules merged.
- [ ] MCP tab reads the **live manifest** (no hand-listed tools), grouped by prefix, gated tools flagged; deep-linkable `?tab=mcp`.
- [ ] Toolkit/launcher tile deep-links to the tab.
- [ ] Verified live (manifest + tools/list agree; gated tool blocks a non-admin); documented in DECISIONS + DEMO_QA.

*This spec is derived from the Pricing Workbench gen2 MCP server; it's workbench-agnostic — copy the templates, rename the slug, keep the gates.*
