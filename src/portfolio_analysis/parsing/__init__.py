"""
Parsing submodule for portfolio analysis.

This module contains parsers for different brokerage CSV formats.
"""

from .etrade import ETradeParser, parse_etrade_csv

__all__ = ["ETradeParser", "parse_etrade_csv"]
