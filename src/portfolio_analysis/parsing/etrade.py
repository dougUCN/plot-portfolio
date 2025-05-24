"""
ETrade CSV Parser Module

This module provides functionality to parse ETrade portfolio download CSV files
and extract position data using pandas. Uses flexible column mapping to handle
varying CSV formats while ensuring required columns are present.
"""

import io
import re
from typing import Dict, Optional, Tuple

import pandas as pd

from portfolio_analysis.utils.logging import get_logger

logger = get_logger(__name__)


class ETradeParser:
    """Parser for ETrade CSV portfolio downloads with flexible column mapping.

    .. note::
        This parser requires the following columns to be present in the CSV:
        - symbol
        - last_price
        - quantity
        - price_paid

    Main public methods:
        - parse: Parses the CSV file and extracts position data.
        - get_positions: Returns a DataFrame of aggregated positions.
        - get_position_lots: Returns a DataFrame of individual position lots.
        - get_cash_position: Returns the cash position value.
        - get_portfolio_summary: Returns a summary of the entire portfolio.

    """

    # Required columns that must be present in the CSV
    REQUIRED_COLUMNS = ["symbol", "last_price", "quantity", "price_paid"]

    # Column mapping for flexible parsing
    COLUMN_MAPPINGS = {
        "symbol": ["Symbol", "symbol"],
        "last_price": ["Last Price $", "Last Price", "Price", "last_price"],
        "quantity": ["Quantity", "Shares", "quantity"],
        "price_paid": ["Price Paid $", "Price Paid", "Cost Basis", "price_paid"],
        "change_dollar": ["Change $", "Change", "change_dollar"],
        "change_percent": ["Change %", "Change Percent", "change_percent"],
        "days_gain": ["Day's Gain $", "Days Gain", "Daily Gain", "days_gain"],
        "total_gain_dollar": ["Total Gain $", "Total Gain", "total_gain_dollar"],
        "total_gain_percent": ["Total Gain %", "Total Gain Percent", "total_gain_percent"],
        "value": ["Value $", "Value", "value"],
        "purchase_date": ["Purchase Date", "Date", "purchase_date"],
    }

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
        self._column_map = None

    def parse(self) -> None:  # noqa: C901
        """Parse the CSV file and extract position data."""
        logger.info(f"Parsing ETrade CSV: {self.csv_path}")

        # Read the entire file to find the positions section
        with open(self.csv_path, "r") as file:
            content = file.read()

        # Find the correct position data header (contains both Symbol and Last Price)
        lines = content.split("\n")

        position_start_line = -1
        for i, line in enumerate(lines):
            if "Symbol" in line and "Last Price" in line and "Quantity" in line:
                position_start_line = i
                break

        if position_start_line == -1:
            logger.error("Could not find position data header in CSV")
            raise ValueError("Could not find position data header in CSV")

        # Extract position content from the header line onwards
        position_lines_content = lines[position_start_line:]

        # Find where the position data ends (TOTAL line or end of file)
        total_line_idx = -1
        for i, line in enumerate(position_lines_content):
            if line.startswith("TOTAL,"):
                total_line_idx = i
                break

        if total_line_idx != -1:
            position_lines_content = position_lines_content[:total_line_idx]

        # Get header and data lines
        header = position_lines_content[0]
        data_lines = [line.strip() for line in position_lines_content[1:] if line.strip()]

        # Create column mapping from header
        self._create_column_mapping(header)

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
            # Create header for lots (symbol + original header columns except symbol)
            header_cols = header.split(",")
            lot_header = "symbol,purchase_date," + ",".join(header_cols[1:])
            lot_csv = f"{lot_header}\n" + "\n".join(lot_lines)
            self._lots_df = self._parse_lots_csv(lot_csv)

        logger.info(
            f"Parsed {len(position_lines)} positions, {len(lot_lines)} lots, "
            f"cash: ${self._cash_position or 0:.2f}"
        )

    def _create_column_mapping(self, header: str) -> None:
        """Create a mapping from CSV column names to standardized names."""
        header_cols = [col.strip() for col in header.split(",")]

        self._column_map = {}

        for standard_name, possible_names in self.COLUMN_MAPPINGS.items():
            for col in header_cols:
                if col in possible_names:
                    self._column_map[col] = standard_name
                    break

        # Verify required columns are present
        mapped_standard_names = set(self._column_map.values())

        missing_cols = set(self.REQUIRED_COLUMNS) - mapped_standard_names
        if missing_cols:
            logger.error(f"Required columns not found: {missing_cols}")
            raise ValueError(f"Required columns not found: {missing_cols}")

    def _parse_positions_csv(self, csv_content: str) -> pd.DataFrame:
        """Parse positions using pandas CSV parser with flexible column mapping."""
        df = pd.read_csv(io.StringIO(csv_content), na_values=["", " "])

        # Rename columns using mapping
        df = df.rename(columns=self._column_map)

        # Remove any rows where symbol is NaN
        df = df.dropna(subset=["symbol"])

        # Convert required columns to appropriate types
        numeric_cols = ["last_price", "quantity", "price_paid"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Calculate derived columns
        df = self._calculate_derived_columns(df)

        return df

    def _parse_lots_csv(self, csv_content: str) -> pd.DataFrame:
        """Parse position lots using pandas CSV parser with flexible column mapping."""
        df = pd.read_csv(io.StringIO(csv_content), na_values=["", " "])

        # Rename columns using mapping (lots have symbol and purchase_date as first columns)
        # Create a copy of column mapping for lots
        lots_column_map = self._column_map.copy()
        lots_column_map["purchase_date"] = "purchase_date"  # Ensure purchase_date is mapped

        df = df.rename(columns=lots_column_map)

        # Remove any rows where symbol is NaN
        df = df.dropna(subset=["symbol"])

        # Convert required columns to appropriate types
        numeric_cols = ["last_price", "quantity", "price_paid"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Parse purchase dates
        if "purchase_date" in df.columns:
            df["purchase_date"] = pd.to_datetime(
                df["purchase_date"], format="%m/%d/%Y", errors="coerce"
            )

        # Calculate derived columns
        df = self._calculate_derived_columns(df)

        return df

    def _calculate_derived_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate derived columns: value, total_gain_dollar, total_gain_percent."""
        # Calculate value (quantity * last_price) - always recalculate for consistency
        df["value"] = df["quantity"] * df["last_price"]

        # Calculate total cost basis
        df["total_cost"] = df["quantity"] * df["price_paid"]

        # Calculate total_gain_dollar (value - total_cost)
        # - always recalculate for consistency
        df["total_gain_dollar"] = df["value"] - df["total_cost"]

        # Calculate total_gain_percent ((value - total_cost) / total_cost * 100)
        # - always recalculate for consistency
        with pd.option_context("mode.chained_assignment", None):
            df["total_gain_percent"] = (df["total_gain_dollar"] / df["total_cost"]) * 100
            # Handle division by zero
            df["total_gain_percent"] = df["total_gain_percent"].fillna(0)

        # Calculate days_gain if change_dollar is available
        if "change_dollar" in df.columns:
            df["days_gain"] = df["quantity"] * df["change_dollar"]
        elif "days_gain" not in df.columns:
            df["days_gain"] = 0.0

        # Ensure all columns have proper dtypes
        numeric_cols = ["value", "total_gain_dollar", "total_gain_percent", "days_gain"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

        # Also ensure other numeric columns from the CSV are properly typed
        optional_numeric_cols = ["change_dollar", "change_percent"]
        for col in optional_numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    def _parse_cash_position(self, line: str) -> None:
        """Parse the cash position line."""
        fields = line.split(",")
        # Look for the last non-empty field as the cash value
        for i in range(len(fields) - 1, -1, -1):
            field = fields[i].strip()
            if field and field != "CASH":
                try:
                    cash_value = float(field)
                    self._cash_position = cash_value
                    return
                except ValueError:
                    continue
        self._cash_position = 0.0
        logger.warning("Could not parse cash position, defaulting to $0.00")

    def _is_date(self, value: str) -> bool:
        """Check if a string looks like a date."""
        if not value:
            return False
        # ETrade format appears to be MM/DD/YYYY
        date_pattern = r"^\d{2}/\d{2}/\d{4}$"
        return bool(re.match(date_pattern, value))

    def get_positions(self) -> Optional[pd.DataFrame]:
        """
        Get aggregated positions DataFrame.

        Returns:
            DataFrame with columns: symbol, last_price, quantity, price_paid, value,
            total_gain_dollar, total_gain_percent, and any additional columns from the CSV.
            The value, total_gain_dollar, and total_gain_percent columns are calculated
            from the base columns.
        """
        if self._positions_df is None:
            self.parse()
        return self._positions_df

    def get_position_lots(self) -> Optional[pd.DataFrame]:
        """
        Get individual position lots DataFrame.

        Returns:
            DataFrame with columns: symbol, purchase_date, last_price, quantity,
            price_paid, value, total_gain_dollar, total_gain_percent, and any additional
            columns from the CSV. The value, total_gain_dollar, and total_gain_percent
            columns are calculated from the base columns.
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
            logger.warning("No positions found in portfolio")
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

        summary = {
            "total_value": total_value,
            "total_position_value": total_position_value,
            "cash_position": cash,
            "number_of_positions": len(positions_df),
            "total_gain_dollar": total_gain_dollar,
            "average_gain_percent": positions_df["total_gain_percent"].mean(),
        }

        return summary


def parse_etrade_csv(csv_path: str) -> Tuple[pd.DataFrame, pd.DataFrame, float, Dict]:
    """
    Convenience function to parse an ETrade CSV and return the main data structures.

    Uses flexible column mapping to handle varying CSV formats while ensuring
    required columns (symbol, last_price, quantity, price_paid) are present.
    Automatically calculates derived columns (value, total_gain_dollar, total_gain_percent).

    Args:
        csv_path: Path to the ETrade CSV file

    Returns:
        Tuple containing:
        - positions_df: DataFrame of aggregated positions with calculated columns
        - lots_df: DataFrame of individual lots with calculated columns
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
