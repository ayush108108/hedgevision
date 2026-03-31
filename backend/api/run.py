"""
Run the FastAPI application with uvicorn.

This module provides a convenient way to start the API server.
"""

import argparse
import os
import sys

import uvicorn

# Add parent directory to path to import from parent modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import configuration
from api.utils.config import config


def main():
    """Run the FastAPI application."""
    parser = argparse.ArgumentParser(description="Run the HedgeVision API server")
    parser.add_argument(
        "--host",
        type=str,
        default=config["API_HOST"],
        help=f"Host to bind the server to (default: {config['API_HOST']})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=config["API_PORT"],
        help=f"Port to bind the server to (default: {config['API_PORT']})",
    )
    parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=config["API_DEBUG"],
        help="Enable debug mode",
    )
    args = parser.parse_args()

    # Run the server
    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="debug" if args.debug else "info",
    )


if __name__ == "__main__":
    main()
