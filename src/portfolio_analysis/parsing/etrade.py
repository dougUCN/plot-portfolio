"""
ETrade CSV Parser Module

This module provides functionality to parse ETrade portfolio download CSV files
and extract position data using pandas. Uses Pydantic for data validation and
pandas built-in CSV parsing capabilities.
"""

import io
import re
from datetime import datetime
from typing import Dict, Optional, Tuple

import pandas as pd
from pydantic import BaseModel


class Position(BaseModel):
    """Container for a single position (aggregated)."""

    symbol: str
    last_price: float
    change_dollar: float
    change_percent: float
    quantity: float
    price_paid: float
    days_gain: float
    total_gain_dollar: float
    total_gain_percent: float
    value: float


class PositionLot(BaseModel):
    """Container for a single position lot (specific purchase)."""

    symbol: str
    purchase_date: Optional[datetime] = None
    last_price: float
    change_dollar: float
    change_percent: float
    quantity: float
    price_paid: float
    days_gain: float
    total_gain_dollar: float
    total_gain_percent: float
    value: float


class ETradeParser:
    """Parser for ETrade CSV portfolio downloads."""

    def __init__(self, csv_path: str):
        """
        Initialize the parser with a CSV file path.

        Args:
            csv_path: Path to the ETrade CSV file
        """
        self.csv_path = csv_path
        self._positions_df = None
        self._lots_df = None
        self._cash_position = None

    def parse(self) -> None:
        """Parse the CSV file and extract position data."""
        # Read the entire file to find the positions section
        with open(self.csv_path, "r") as file:
            content = file.read()

        # Find the start and end of the position data
        position_start = content.find("Symbol,Last Price $")
        if position_start == -1:
            raise ValueError("Could not find position data in CSV")

        # Extract just the position section
        position_content = content[position_start:]

        # Find where the position data ends (TOTAL line or end of file)
        total_pos = position_content.find("\nTOTAL,")
        if total_pos != -1:
            position_content = position_content[:total_pos]

        # Split into lines and separate main positions from lots
        lines = position_content.split("\n")
        header = lines[0]
        data_lines = [line.strip() for line in lines[1:] if line.strip()]

        # Separate positions and lots
        position_lines = []
        lot_lines = []
        current_symbol = None

        for line in data_lines:
            if line.startswith("CASH"):
                self._parse_cash_position(line)
                continue
            elif line.startswith("TOTAL") or not line:
                break

            # Check if line starts with a date (lot) or symbol (position)
            first_field = line.split(",")[0].strip()
            if self._is_date(first_field):
                # This is a lot - add symbol as first column
                if current_symbol:
                    lot_lines.append(f"{current_symbol},{line}")
            else:
                # This is a main position
                current_symbol = first_field
                position_lines.append(line)

        # Parse positions using pandas
        if position_lines:
            position_csv = f"{header}\n" + "\n".join(position_lines)
            self._positions_df = self._parse_positions_csv(position_csv)

        # Parse lots using pandas
        if lot_lines:
            lot_header = (
                "symbol,purchase_date,last_price,change_dollar,change_percent,quantity,"
                "price_paid,days_gain,total_gain_dollar,total_gain_percent,value"
            )
            lot_csv = f"{lot_header}\n" + "\n".join(lot_lines)
            self._lots_df = self._parse_lots_csv(lot_csv)

    def _parse_positions_csv(self, csv_content: str) -> pd.DataFrame:
        """Parse positions using pandas CSV parser."""
        # Clean up column names
        csv_content = csv_content.replace(
            "Symbol,Last Price $,Change $,Change %,Quantity,"
            "Price Paid $,Day's Gain $,Total Gain $,Total Gain %,Value $",
            "symbol,last_price,change_dollar,change_percent,quantity,"
            "price_paid,days_gain,total_gain_dollar,total_gain_percent,value",
        )

        df = pd.read_csv(
            io.StringIO(csv_content),
            dtype={
                "symbol": str,
                "last_price": float,
                "change_dollar": float,
                "change_percent": float,
                "quantity": float,
                "price_paid": float,
                "days_gain": float,
                "total_gain_dollar": float,
                "total_gain_percent": float,
                "value": float,
            },
            na_values=["", " "],
        )

        # Remove any rows where symbol is NaN
        df = df.dropna(subset=["symbol"])

        return df

    def _parse_lots_csv(self, csv_content: str) -> pd.DataFrame:
        """Parse position lots using pandas CSV parser."""
        df = pd.read_csv(
            io.StringIO(csv_content),
            dtype={
                "symbol": str,
                "last_price": float,
                "change_dollar": float,
                "change_percent": float,
                "quantity": float,
                "price_paid": float,
                "days_gain": float,
                "total_gain_dollar": float,
                "total_gain_percent": float,
                "value": float,
            },
            na_values=["", " "],
        )

        # Parse purchase dates
        df["purchase_date"] = pd.to_datetime(
            df["purchase_date"], format="%m/%d/%Y", errors="coerce"
        )

        # Remove any rows where symbol is NaN
        df = df.dropna(subset=["symbol"])

        return df

    def _parse_cash_position(self, line: str) -> None:
        """Parse the cash position line."""
        fields = line.split(",")
        if len(fields) >= 10:
            try:
                cash_value = float(fields[9]) if fields[9].strip() else 0.0
                self._cash_position = cash_value
            except (ValueError, IndexError):
                self._cash_position = 0.0

    def _is_date(self, value: str) -> bool:
        """Check if a string looks like a date."""
        if not value:
            return False
        # ETrade format appears to be MM/DD/YYYY
        date_pattern = r"^\d{2}/\d{2}/\d{4}$"
        return bool(re.match(date_pattern, value))

    # Public methods for accessing parsed data

    def get_positions(self) -> Optional[pd.DataFrame]:
        """
        Get aggregated positions DataFrame.

        Returns:
            DataFrame with columns: symbol, last_price, change_dollar, change_percent,
            quantity, price_paid, days_gain, total_gain_dollar, total_gain_percent, value
        """
        if self._positions_df is None:
            self.parse()
        return self._positions_df

    def get_position_lots(self) -> Optional[pd.DataFrame]:
        """
        Get individual position lots DataFrame.

        Returns:
            DataFrame with columns: symbol, purchase_date, last_price, change_dollar,
            change_percent, quantity, price_paid, days_gain, total_gain_dollar,
            total_gain_percent, value
        """
        if self._lots_df is None:
            self.parse()
        return self._lots_df

    def get_cash_position(self) -> float:
        """Get the cash position value."""
        if self._cash_position is None:
            self.parse()
        return self._cash_position or 0.0

    def get_portfolio_summary(self) -> Dict:
        """
        Get a summary of the entire portfolio.

        Returns:
            Dictionary containing portfolio summary statistics
        """
        positions_df = self.get_positions()
        cash = self.get_cash_position()

        if positions_df is None or positions_df.empty:
            return {
                "total_value": cash,
                "cash_position": cash,
                "number_of_positions": 0,
                "total_gain_dollar": 0.0,
                "total_gain_percent": 0.0,
            }

        total_position_value = positions_df["value"].sum()
        total_value = total_position_value + cash
        total_gain_dollar = positions_df["total_gain_dollar"].sum()

        return {
            "total_value": total_value,
            "total_position_value": total_position_value,
            "cash_position": cash,
            "number_of_positions": len(positions_df),
            "total_gain_dollar": total_gain_dollar,
            "average_gain_percent": positions_df["total_gain_percent"].mean(),
        }


def parse_etrade_csv(csv_path: str) -> Tuple[pd.DataFrame, pd.DataFrame, float, Dict]:
    """
    Convenience function to parse an ETrade CSV and return the main data structures.

    Args:
        csv_path: Path to the ETrade CSV file

    Returns:
        Tuple containing:
        - positions_df: DataFrame of aggregated positions
        - lots_df: DataFrame of individual lots
        - cash_position: Cash position value
        - portfolio_summary: Dictionary with portfolio summary
    """
    parser = ETradeParser(csv_path)
    parser.parse()

    return (
        parser.get_positions(),
        parser.get_position_lots(),
        parser.get_cash_position(),
        parser.get_portfolio_summary(),
    )
