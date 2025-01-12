# utils/logger.py
from loguru import logger
import sys
import os

# This logger can be imported and used throughout the project.

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Remove the default handler to configure from scratch
logger.remove()

# Add a console logger at DEBUG
logger.add(sys.stdout, level="DEBUG", format="<green>{time}</green> <level>{message}</level>")

# Add a file logger at DEBUG (change path/level as you need)
logger.add(
    "logs/applog",       # Could also do "logs/applog.log" if you prefer a .log extension
    level="DEBUG",       # Capture DEBUG and above
    format="{time} {level} {message}",
    rotation="10 MB",    # optional: rotate file
    retention="10 days", # optional: keep logs for 10 days
    compression="zip"    # optional: compress rotated logs
)

logger.debug("This is a DEBUG log, will be captured in the file and console.")
logger.info("This is an INFO log, also captured.")
logger.warning("This is a WARNING log.")