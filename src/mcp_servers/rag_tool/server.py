#!/usr/bin/env python3
"""
RAG Retriever MCP Server

Provides tools for semantic search of historical incidents using RAG.
Uses in-memory FAISS index with sentence-transformers.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from typing import List, Dict, Any
from mcp.server import Server
from mcp.types import Tool, TextContent
import json

from src.rag.indexer import get_rag_indexer, IncidentMatch
from src.rag.sample_incidents import load_incidents_to_rag


# Initialize MCP server
app = Server("rag-retriever")

# Initialize RAG indexer (global singleton)
indexer = get_rag_indexer()

# Load sample incidents on startup
try:
    num_loaded = load_incidents_to_rag(indexer)
    print(f"[RAG] Loaded {num_loaded} sample incidents into RAG index", file=sys.stderr)
except Exception as e:
    print(f"[RAG] Warning: Failed to load sample incidents: {e}", file=sys.stderr)


def incident_match_to_dict(match: IncidentMatch) -> Dict[str, Any]:
    """Convert IncidentMatch to dictionary"""
    return {
        "incident_id": match.incident.incident_id,
        "title": match.incident.title,
        "description": match.incident.description,
        "client_id": match.incident.client_id,
        "incident_type": match.incident.incident_type,
        "value_date": match.incident.value_date,
        "resolution_steps": match.incident.resolution_steps,
        "outcome": match.incident.outcome,
        "metadata": match.incident.metadata,
        "similarity_score": match.similarity_score,
        "rank": match.rank
    }


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available RAG tools"""
    return [
        Tool(
            name="semantic_search",
            description=(
                "Semantic search for similar historical incidents. "
                "Returns top-k most similar incidents based on query description. "
                "Uses sentence embeddings for similarity matching."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query describing the incident or issue"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (default: 5)",
                        "default": 5
                    },
                    "min_similarity": {
                        "type": "number",
                        "description": "Minimum similarity threshold 0-1 (default: 0.0)",
                        "default": 0.0
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="search_by_incident_type",
            description=(
                "Search for similar incidents filtered by specific incident type. "
                "Types: split_booking_duplicate, dra_duplicate, exposure_anomaly, "
                "date_anomaly, negative_value, expired_active_trade"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "incident_type": {
                        "type": "string",
                        "description": "Filter by incident type",
                        "enum": [
                            "split_booking_duplicate",
                            "dra_duplicate",
                            "exposure_anomaly",
                            "date_anomaly",
                            "negative_value",
                            "expired_active_trade"
                        ]
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results (default: 3)",
                        "default": 3
                    }
                },
                "required": ["query", "incident_type"]
            }
        ),
        Tool(
            name="get_resolution_steps",
            description="Get detailed resolution steps for a specific incident by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "incident_id": {
                        "type": "string",
                        "description": "Incident ID (e.g., INC-2024-001)"
                    }
                },
                "required": ["incident_id"]
            }
        ),
        Tool(
            name="get_similar_incidents",
            description=(
                "Get similar incidents based on anomaly findings. "
                "Automatically constructs search query from findings object."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "error_type": {
                        "type": "string",
                        "description": "Error type from finding"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of the anomaly"
                    },
                    "client_id": {
                        "type": "string",
                        "description": "Client identifier (optional)"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results (default: 3)",
                        "default": 3
                    }
                },
                "required": ["error_type", "description"]
            }
        ),
        Tool(
            name="get_rag_stats",
            description="Get statistics about the RAG index (number of incidents, types, etc.)",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""

    if name == "semantic_search":
        query = arguments["query"]
        top_k = arguments.get("top_k", 5)
        min_similarity = arguments.get("min_similarity", 0.0)

        try:
            matches = indexer.search(query, top_k=top_k, min_similarity=min_similarity)
            results = [incident_match_to_dict(match) for match in matches]

            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "query": query,
                        "results_count": len(results),
                        "matches": results
                    }, indent=2)
                )
            ]
        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": str(e),
                        "error_type": type(e).__name__
                    }, indent=2)
                )
            ]

    elif name == "search_by_incident_type":
        query = arguments["query"]
        incident_type = arguments["incident_type"]
        top_k = arguments.get("top_k", 3)

        try:
            matches = indexer.search_by_type(query, incident_type=incident_type, top_k=top_k)
            results = [incident_match_to_dict(match) for match in matches]

            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "query": query,
                        "incident_type": incident_type,
                        "results_count": len(results),
                        "matches": results
                    }, indent=2)
                )
            ]
        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": str(e)
                    }, indent=2)
                )
            ]

    elif name == "get_resolution_steps":
        incident_id = arguments["incident_id"]

        try:
            incident = indexer.get_incident_by_id(incident_id)

            if incident is None:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": f"Incident {incident_id} not found"
                        }, indent=2)
                    )
                ]

            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "incident_id": incident_id,
                        "title": incident.title,
                        "resolution_steps": incident.resolution_steps,
                        "outcome": incident.outcome,
                        "metadata": incident.metadata
                    }, indent=2)
                )
            ]
        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": str(e)
                    }, indent=2)
                )
            ]

    elif name == "get_similar_incidents":
        error_type = arguments["error_type"]
        description = arguments["description"]
        client_id = arguments.get("client_id", "")
        top_k = arguments.get("top_k", 3)

        # Construct search query
        query = f"Error type: {error_type}. Description: {description}"
        if client_id:
            query += f" Client: {client_id}"

        try:
            matches = indexer.search(query, top_k=top_k)
            results = [incident_match_to_dict(match) for match in matches]

            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "error_type": error_type,
                        "results_count": len(results),
                        "similar_incidents": results
                    }, indent=2)
                )
            ]
        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": str(e)
                    }, indent=2)
                )
            ]

    elif name == "get_rag_stats":
        try:
            stats = indexer.get_stats()

            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "stats": stats
                    }, indent=2)
                )
            ]
        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": str(e)
                    }, indent=2)
                )
            ]

    else:
        return [
            TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"Unknown tool: {name}"
                }, indent=2)
            )
        ]


async def main():
    """Run MCP server"""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
