"""
Portfolio Analysis Library

A library for parsing and analyzing ETrade portfolio data.
"""

from .parsing import ETradeParser, parse_etrade_csv

__all__ = ["ETradeParser", "parse_etrade_csv"]
