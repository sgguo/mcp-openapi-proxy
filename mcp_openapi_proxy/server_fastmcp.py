"""
Provides the FastMCP server logic for mcp-openapi-proxy.

This server exposes a pre-defined set of functions based on an OpenAPI specification.
Configuration is controlled via environment variables:
- OPENAPI_SPEC_URL: URL to fetch the OpenAPI specification.
- OPENAPI_ENDPOINT: Optional override for the base URL from the OpenAPI spec.
- OPENAPI_PORT: Port to run the FastMCP server on (default is 8000).
- IGNORE_SSL_TOOLS: If true, skips SSL verification for tools that require it.
- API_KEY: Generic token for Bearer header.
"""

import os
import httpx
from fastmcp import FastMCP
from fastmcp.server.openapi import RouteMap, MCPType
from mcp_openapi_proxy.logging_setup import logger
from mcp_openapi_proxy.openapi import fetch_openapi_spec
import sys

# Logger is now configured in logging_setup.py, just use it
# logger = setup_logging(debug=os.getenv("DEBUG", "").lower() in ("true", "1", "yes"))

logger.debug(f"Server CWD: {os.getcwd()}")
spec = None  # Global spec for resources

def run_simple_server():
    """Runs the FastMCP server."""
    logger.debug("Starting run_simple_server")
    spec_url = os.environ.get("OPENAPI_SPEC_URL")
    if not spec_url:
        logger.error("OPENAPI_SPEC_URL environment variable is required for FastMCP mode.")
        sys.exit(1)
    assert isinstance(spec_url, str)

    logger.debug("Preloading functions from OpenAPI JSON spec...")
    global spec
    spec = httpx.get(spec_url).json()
    if spec is None:
        logger.error("Failed to fetch OpenAPI spec, no functions to preload.")
        sys.exit(1)

    # Create an HTTP client for your API
    openapi_endpoint = os.environ.get("OPENAPI_ENDPOINT")
    openapi_port = os.environ.get("OPENAPI_PORT", "8000")
    ignore_ssl_tools = os.getenv("IGNORE_SSL_TOOLS", "false").lower() in ("true", "1", "yes")
    api_key = os.environ.get("API_KEY")
    headers = {"Authorization": f"Bearer {api_key}"}
    client = httpx.AsyncClient(base_url=openapi_endpoint, verify=not ignore_ssl_tools, headers=headers)
    logger.debug(f"Using OpenAPI endpoint: {openapi_endpoint}")
    try:
        logger.debug("Starting eCloudTech MCP server (FastMCP version)...")
        # Restore pre-2.8.0 semantic mapping
        semantic_maps = [
            # Exclude all routes tagged "internal"
            RouteMap(tags={"Data Object Volume"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"Data Object Disk"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"Storage Resource View"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"User"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"Role"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"Privilege"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"Permission"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"Log"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"Tenant"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"Workspace"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"User Group"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"Template"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"Image"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"Metadata Backup Policy"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"Tape"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"Topology"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"Monitored Resource"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"Monitor"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"Director"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"Application Delegation"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"Export"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"Vault Policy"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"Log Sync Policy"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"CDP Policy"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"Data Engine"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"Commvault Bridge Client"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"Commvault Client"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"Commvault Image"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"Commvault Transform Policy"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"Client Resource"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(tags={"Client Package"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(pattern=r"^/nbu.*", mcp_type=MCPType.EXCLUDE),
            # GET requests with path parameters become ResourceTemplates
            RouteMap(methods=["GET"], pattern=r".*\{.*\}.*", mcp_type=MCPType.RESOURCE),
            # All other GET requests become Resources
            RouteMap(methods=["GET"], pattern=r".*", mcp_type=MCPType.RESOURCE),
        ]

        mcp = FastMCP.from_openapi(
            openapi_spec=spec,
            client=client,
            route_maps=semantic_maps,
            name="eCloudTech MCP Gateway"
        )
        mcp.run(transport="sse", host="0.0.0.0", port=int(openapi_port))
        # mcp.run(transport="stdio")
    except Exception as e:
        logger.error(f"Unhandled exception in MCP server (FastMCP): {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    run_simple_server()
