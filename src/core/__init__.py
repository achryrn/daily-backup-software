# src/core/__init__.py
"""
Core application logic and engine
"""

from .backup_engine import backup_engine
from .database import db_manager
from .config import config_manager

__all__ = ['backup_engine', 'db_manager', 'config_manager']
