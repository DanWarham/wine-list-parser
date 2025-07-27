"""
Database Enhanced Rule System

This module provides local wine knowledge databases to reduce AI fallback costs
by performing early database lookups before AI/rule processing.
"""

from .database_manager import DatabaseManager
from .early_extractor import EarlyExtractor

__all__ = ['DatabaseManager', 'EarlyExtractor'] 