# src/connectors/__init__.py
"""
Target connectors for different backup destinations
"""

from .local_target import LocalTargetConnector
from .gdrive_connector import GoogleDriveConnector

__all__ = ['LocalTargetConnector', 'GoogleDriveConnector']
