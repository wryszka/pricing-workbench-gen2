import asyncio
import logging
import time
from typing import Any

from databricks.sdk.service.sql import StatementParameterListItem, StatementState

from server.config import get_workspace_client, get_warehouse_id

logger = logging.getLogger(__name__)

# States the statement can still leave: keep polling. Everything else is
# terminal (SUCCEEDED, or an error we raise on).
_PENDING_STATES = (StatementState.PENDING, StatementState.RUNNING)
# Max total time to wait for a statement, incl. a warehouse resuming from
# auto-stop (serverless resume is usually <60s but can spike). 50s of that is
# the initial synchronous wait_timeout; the rest is polling.
_MAX_WAIT_SECONDS = 180.0


def _execute_sync(sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    client = get_workspace_client()
    warehouse_id = get_warehouse_id()
    if not warehouse_id:
        raise RuntimeError(
            "No SQL warehouse available (WAREHOUSE_ID unset and none could be "
            "resolved) — cannot run queries.")
    logger.debug("SQL: %s", sql[:200])

    # Named parameters (`:name` markers) — the injection-proof path for any
    # user-supplied value. The server binds them; they can never alter the
    # statement structure. Values are passed as strings (Spark casts in-query).
    param_items = None
    if params:
        param_items = [StatementParameterListItem(name=k, value=(None if v is None else str(v)))
                       for k, v in params.items()]

    # INLINE disposition only — Databricks Apps' egress is firewalled away
    # from the cloud-storage hosts that EXTERNAL_LINKS would point to, so
    # large results have to be aggregated server-side before they come back
    # rather than streamed through pre-signed URLs.
    #
    # wait_timeout caps at 50s; if the warehouse is resuming from auto-stop the
    # statement comes back still PENDING/RUNNING (on_wait_timeout defaults to
    # CONTINUE — it keeps running async). Poll until it reaches a terminal state
    # so a cold warehouse produces correct results instead of an empty set.
    response = client.statement_execution.execute_statement(
        statement=sql,
        warehouse_id=warehouse_id,
        wait_timeout="50s",
        parameters=param_items,
    )

    deadline = time.monotonic() + _MAX_WAIT_SECONDS
    while response.status and response.status.state in _PENDING_STATES:
        if time.monotonic() > deadline:
            raise RuntimeError(
                f"SQL timed out after {_MAX_WAIT_SECONDS:.0f}s waiting for the "
                f"warehouse/statement to finish (warehouse may be resuming).")
        time.sleep(2)
        response = client.statement_execution.get_statement(response.statement_id)

    state = response.status.state if response.status else None
    if state != StatementState.SUCCEEDED:
        error_msg = (response.status.error.message
                     if response.status and response.status.error else str(state))
        raise RuntimeError(f"SQL {state}: {error_msg}")

    if not response.manifest or not response.manifest.schema or not response.manifest.schema.columns:
        # A SUCCEEDED statement with no schema is normal for DML/DDL (INSERT,
        # CREATE, DELETE). Only warn when a SELECT unexpectedly returns no schema
        # (a sign of a malformed query), so genuine empty result sets stay quiet.
        if sql.lstrip()[:6].upper() == "SELECT":
            logger.warning("SELECT returned no schema (possible malformed query): %s", sql[:160])
        return []

    columns = [col.name for col in response.manifest.schema.columns]
    rows: list[dict[str, Any]] = []

    # Inline data — first chunk is on response.result.data_array.
    if response.result and response.result.data_array:
        for row_data in response.result.data_array:
            rows.append(dict(zip(columns, row_data)))

    # Inline data, additional chunks — when the result spans more than one
    # chunk (the default 16 MiB inline cap), only chunk 0 lands on
    # response.result.data_array. Chunks 1..N are listed in manifest.chunks
    # and must be fetched explicitly. Without this loop, large result sets
    # silently truncate to the first chunk's row count (sometimes a single
    # row when wide rows compress to one chunk).
    manifest = response.manifest
    if manifest and getattr(manifest, "chunks", None):
        first_chunk = response.result.chunk_index if response.result else 0
        for chunk_info in manifest.chunks:
            idx = chunk_info.chunk_index
            if idx is None or idx == first_chunk:
                continue
            chunk = client.statement_execution.get_statement_result_chunk_n(
                statement_id=response.statement_id,
                chunk_index=idx,
            )
            if chunk.data_array:
                for row_data in chunk.data_array:
                    rows.append(dict(zip(columns, row_data)))

    return rows


async def execute_query(sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return await asyncio.to_thread(_execute_sync, sql, params)
