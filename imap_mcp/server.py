"""Main server implementation for IMAP MCP."""

import argparse
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Optional

from mcp.server.fastmcp import FastMCP

from imap_mcp.config import ServerConfig, load_config
from imap_mcp.imap_client import ImapClient
from imap_mcp.resources import register_resources
from imap_mcp.tools import register_tools
from imap_mcp.mcp_protocol import extend_server

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("imap_mcp")


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict]:
    """Server lifespan manager to handle IMAP client lifecycle.
    
    Args:
        server: MCP server instance
        
    Yields:
        Context dictionary containing IMAP client
    """
    # Access the config that was set in create_server
    # The config is stored in the server's state
    config = getattr(server, "_config", None)
    if not config:
        config = load_config()

    if not isinstance(config, ServerConfig):
        raise TypeError("Invalid server configuration")

    clients = {}
    try:
        for name, acct in config.accounts.items():
            logger.info(f"Connecting to IMAP server for account '{name}'...")
            client = ImapClient(acct.imap, acct.allowed_folders)
            # Register the client even if the initial connect fails, so the
            # account stays addressable and reconnects lazily (via
            # ensure_connected) once the host is reachable again. A single
            # unreachable account must not block startup / the MCP handshake.
            try:
                client.connect()
            except Exception as e:
                logger.warning(
                    f"Could not connect to account '{name}' at startup: {e}. "
                    f"It will be retried on first use."
                )
            clients[name] = client

        yield {
            "imap_clients": clients,
            "default_account": config.default_account,
        }
    finally:
        for name, client in clients.items():
            logger.info(f"Disconnecting IMAP account '{name}'...")
            client.disconnect()


def create_server(config_path: Optional[str] = None, debug: bool = False) -> FastMCP:
    """Create and configure the MCP server.

    Args:
        config_path: Path to configuration file
        debug: Enable debug mode

    Returns:
        Configured MCP server instance
    """
    # Set up logging level
    if debug:
        logger.setLevel(logging.DEBUG)
        
    # Load configuration
    config = load_config(config_path)
    
    # Create MCP server with all the necessary capabilities
    server = FastMCP(
        "IMAP",
        instructions="IMAP Model Context Protocol server for email processing",
        lifespan=server_lifespan,
    )
    
    # Store config for access in the lifespan
    server._config = config

    # Create IMAP client for setup (will be recreated in lifespan)
    default_acct = config.accounts[config.default_account]
    imap_client = ImapClient(default_acct.imap, default_acct.allowed_folders)

    # Register resources and tools
    register_resources(server, imap_client)
    register_tools(server, imap_client)

    # Add server status tool
    @server.tool()
    def server_status() -> str:
        """Get server status and configuration info."""
        lines = [f"server: IMAP MCP", f"version: 0.1.0", f"default_account: {config.default_account}"]
        for name, acct in config.accounts.items():
            lines.append(f"account '{name}': {acct.imap.username} @ {acct.imap.host}")
        return "\n".join(lines)

    @server.tool()
    def list_accounts() -> list[dict]:
        """List available IMAP accounts.

        Returns:
            A list of dicts with account name and username.
        """
        return [
            {"account": name, "username": acct.imap.username, "host": acct.imap.host}
            for name, acct in config.accounts.items()
        ]
    
    # Apply MCP protocol extension for Claude Desktop compatibility
    server = extend_server(server)
    
    return server


def main() -> None:
    """Run the IMAP MCP server."""
    parser = argparse.ArgumentParser(description="IMAP MCP Server")
    parser.add_argument(
        "--config", 
        help="Path to configuration file",
        default=os.environ.get("IMAP_MCP_CONFIG"),
    )
    parser.add_argument(
        "--dev", 
        action="store_true", 
        help="Enable development mode",
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug logging",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version information and exit",
    )
    args = parser.parse_args()
    
    if args.version:
        print("IMAP MCP Server version 0.1.0")
        return
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    server = create_server(args.config, args.debug)
    
    # Start the server
    logger.info("Starting server{}...".format(" in development mode" if args.dev else ""))
    server.run()
    
    
if __name__ == "__main__":
    main()
