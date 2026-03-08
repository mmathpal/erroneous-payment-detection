#!/usr/bin/env python3
"""
SQL Server MCP Tool

Provides tools for querying the EM database tables for anomaly detection
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from typing import Any, Dict, List
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from src.database.connection import DatabaseConnection


# Initialize MCP server
app = Server("sql-server-tool")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available SQL Server tools"""
    return [
        Tool(
            name="query_collateral_movement",
            description="Query ci_collateral_movement table for split booking duplicates",
            inputSchema={
                "type": "object",
                "properties": {
                    "collateral_balance_id": {
                        "type": "integer",
                        "description": "Filter by collateral_balance_id (optional)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of records to return",
                        "default": 100
                    }
                }
            }
        ),
        Tool(
            name="query_arrangement_dra",
            description="Query arrangement_clearing_dra table for duplicate DRAs",
            inputSchema={
                "type": "object",
                "properties": {
                    "arrangement_id": {
                        "type": "integer",
                        "description": "Filter by arrangement_id (optional)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of records to return",
                        "default": 100
                    }
                }
            }
        ),
        Tool(
            name="query_trade",
            description="Query trade table for trade anomalies",
            inputSchema={
                "type": "object",
                "properties": {
                    "src_trade_ref": {
                        "type": "string",
                        "description": "Filter by trade reference (optional)"
                    },
                    "status": {
                        "type": "integer",
                        "description": "Filter by status (optional)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of records to return",
                        "default": 100
                    }
                }
            }
        ),
        Tool(
            name="detect_split_booking_duplicates",
            description="Detect split booking duplicate pattern (R + D = D) in collateral_movement",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="detect_dra_duplicates",
            description="Detect duplicate DRA records by arrangement_id + generation_id + calculation_date",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="detect_trade_anomalies",
            description="Detect various trade anomalies (duplicates, date errors, exposure mismatches, etc.)",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="execute_custom_query",
            description="Execute a custom SQL query on the EM database",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL SELECT query to execute"
                    }
                },
                "required": ["query"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls"""
    try:
        if name == "query_collateral_movement":
            result = await query_collateral_movement(
                arguments.get("collateral_balance_id"),
                arguments.get("limit", 100)
            )
        elif name == "query_arrangement_dra":
            result = await query_arrangement_dra(
                arguments.get("arrangement_id"),
                arguments.get("limit", 100)
            )
        elif name == "query_trade":
            result = await query_trade(
                arguments.get("src_trade_ref"),
                arguments.get("status"),
                arguments.get("limit", 100)
            )
        elif name == "detect_split_booking_duplicates":
            result = await detect_split_booking_duplicates()
        elif name == "detect_dra_duplicates":
            result = await detect_dra_duplicates()
        elif name == "detect_trade_anomalies":
            result = await detect_trade_anomalies()
        elif name == "execute_custom_query":
            result = await execute_custom_query(arguments["query"])
        else:
            raise ValueError(f"Unknown tool: {name}")

        return [TextContent(type="text", text=str(result))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def query_collateral_movement(
    collateral_balance_id: int = None,
    limit: int = 100
) -> Dict[str, Any]:
    """Query collateral movement table"""
    db = DatabaseConnection(database="EM")

    where_clause = ""
    params = ()

    if collateral_balance_id:
        where_clause = "WHERE collateral_balance_id = ?"
        params = (collateral_balance_id,)

    query = f"""
        SELECT TOP {limit}
            collateral_movement_id,
            collateral_balance_id,
            delivery_or_return,
            nominal,
            transaction_date,
            input_date
        FROM ci_collateral_movement
        {where_clause}
        ORDER BY collateral_balance_id, collateral_movement_id
    """

    results = db.execute_query(query, params if params else None)

    return {
        "table": "ci_collateral_movement",
        "record_count": len(results),
        "records": results
    }


async def query_arrangement_dra(
    arrangement_id: int = None,
    limit: int = 100
) -> Dict[str, Any]:
    """Query arrangement DRA table"""
    db = DatabaseConnection(database="EM")

    where_clause = ""
    params = ()

    if arrangement_id:
        where_clause = "WHERE arrangement_id = ?"
        params = (arrangement_id,)

    query = f"""
        SELECT TOP {limit} *
        FROM arrangement_clearing_dra
        {where_clause}
        ORDER BY arrangement_id, generation_id, id
    """

    results = db.execute_query(query, params if params else None)

    return {
        "table": "arrangement_clearing_dra",
        "record_count": len(results),
        "records": results
    }


async def query_trade(
    src_trade_ref: str = None,
    status: int = None,
    limit: int = 100
) -> Dict[str, Any]:
    """Query trade table"""
    db = DatabaseConnection(database="EM")

    where_clauses = []
    params = []

    if src_trade_ref:
        where_clauses.append("src_trade_ref = ?")
        params.append(src_trade_ref)

    if status is not None:
        where_clauses.append("status = ?")
        params.append(status)

    where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    query = f"""
        SELECT TOP {limit}
            generation_id,
            arrangement_id,
            src_trade_ref,
            buy_sell,
            exposure,
            exposure_in_usd,
            notional_1,
            notional_2,
            currency_1,
            currency_2,
            trade_date,
            maturity_date,
            effective_date,
            status
        FROM trade
        {where_clause}
        ORDER BY generation_id, arrangement_id
    """

    results = db.execute_query(query, tuple(params) if params else None)

    return {
        "table": "trade",
        "record_count": len(results),
        "records": results
    }


async def detect_split_booking_duplicates() -> Dict[str, Any]:
    """Detect split booking duplicate pattern"""
    db = DatabaseConnection(database="EM")

    # Find potential duplicates grouped by balance_id
    query = """
        WITH balance_groups AS (
            SELECT
                collateral_balance_id,
                collateral_movement_id,
                delivery_or_return,
                nominal,
                transaction_date,
                input_date
            FROM ci_collateral_movement
        ),
        r_records AS (
            SELECT * FROM balance_groups WHERE delivery_or_return = 'R'
        ),
        d_records AS (
            SELECT * FROM balance_groups WHERE delivery_or_return = 'D'
        )
        SELECT
            r.collateral_balance_id,
            r.collateral_movement_id as r_movement_id,
            r.nominal as r_nominal,
            d1.collateral_movement_id as d1_movement_id,
            d1.nominal as d1_nominal,
            d2.collateral_movement_id as d2_movement_id,
            d2.nominal as d2_nominal,
            (r.nominal + d1.nominal) as calculated_total,
            d2.nominal as duplicate_nominal,
            ABS((r.nominal + d1.nominal) - d2.nominal) as difference
        FROM r_records r
        JOIN d_records d1 ON r.collateral_balance_id = d1.collateral_balance_id
        JOIN d_records d2 ON r.collateral_balance_id = d2.collateral_balance_id
        WHERE d1.collateral_movement_id != d2.collateral_movement_id
          AND ABS((r.nominal + d1.nominal) - d2.nominal) < 0.01
    """

    results = db.execute_query(query)

    return {
        "anomaly_type": "split_booking_duplicate",
        "duplicates_found": len(results),
        "duplicates": results
    }


async def detect_dra_duplicates() -> Dict[str, Any]:
    """Detect duplicate DRA records"""
    db = DatabaseConnection(database="EM")

    query = """
        SELECT
            arrangement_id,
            generation_id,
            calculation_date,
            COUNT(*) as duplicate_count,
            STRING_AGG(CAST(id AS VARCHAR), ', ') as duplicate_ids
        FROM arrangement_clearing_dra
        GROUP BY arrangement_id, generation_id, calculation_date
        HAVING COUNT(*) > 1
    """

    results = db.execute_query(query)

    return {
        "anomaly_type": "dra_duplicate",
        "duplicate_groups_found": len(results),
        "duplicates": results
    }


async def detect_trade_anomalies() -> Dict[str, Any]:
    """Detect various trade anomalies"""
    db = DatabaseConnection(database="EM")

    anomalies = {}

    # 1. Duplicate trade references
    anomalies["duplicate_trade_refs"] = db.execute_query("""
        SELECT src_trade_ref, COUNT(*) as count,
               STRING_AGG(CAST(arrangement_id AS VARCHAR), ', ') as arrangement_ids
        FROM trade
        GROUP BY src_trade_ref
        HAVING COUNT(*) > 1
    """)

    # 2. Exposure anomalies (> 5x notional)
    anomalies["exposure_anomalies"] = db.execute_query("""
        SELECT src_trade_ref, notional_1, exposure,
               exposure/notional_1 as ratio
        FROM trade
        WHERE notional_1 > 0 AND exposure > notional_1 * 5
    """)

    # 3. Date anomalies
    anomalies["date_anomalies"] = db.execute_query("""
        SELECT src_trade_ref, effective_date, maturity_date
        FROM trade
        WHERE effective_date > maturity_date
    """)

    # 4. Active trades past maturity
    anomalies["expired_active_trades"] = db.execute_query("""
        SELECT src_trade_ref, maturity_date, status
        FROM trade
        WHERE status = 1 AND maturity_date < GETDATE()
    """)

    # 5. Negative exposure
    anomalies["negative_exposure"] = db.execute_query("""
        SELECT src_trade_ref, exposure, exposure_in_usd
        FROM trade
        WHERE exposure < 0 OR exposure_in_usd < 0
    """)

    # 6. PV discrepancies
    anomalies["pv_discrepancies"] = db.execute_query("""
        SELECT src_trade_ref, component_use_pv, used_pv,
               ABS(component_use_pv - used_pv) / component_use_pv * 100 as pct_diff
        FROM trade
        WHERE component_use_pv > 0
          AND ABS(component_use_pv - used_pv) / component_use_pv > 0.1
    """)

    total_anomalies = sum(len(v) for v in anomalies.values())

    return {
        "anomaly_type": "trade_anomalies",
        "total_anomalies_found": total_anomalies,
        "anomalies": anomalies
    }


async def execute_custom_query(query: str) -> Dict[str, Any]:
    """Execute custom SQL query"""
    # Basic SQL injection prevention
    query_upper = query.upper().strip()
    if not query_upper.startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed")

    forbidden_keywords = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "TRUNCATE"]
    for keyword in forbidden_keywords:
        if keyword in query_upper:
            raise ValueError(f"Keyword '{keyword}' is not allowed")

    db = DatabaseConnection(database="EM")
    results = db.execute_query(query)

    return {
        "query": query,
        "record_count": len(results),
        "results": results
    }


async def main():
    """Run the SQL Server MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
