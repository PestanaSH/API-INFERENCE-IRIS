"""
API Iris - Global configurations 

Centralizes environment variables, API Version, and logger.
Import from here to maintain a single source of configuration across the entire project.
"""
import os

from app.logging_config import setup_logging

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
API_VERSION = "2.0.0"

logger = setup_logging(os.getenv("LOG_LEVEL", "INFO"))