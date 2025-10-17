#!/usr/bin/env python3
"""
Organized Data Loader - Loads data directly from the organized data folder
"""

import pandas as pd
from pathlib import Path
from typing import Optional, Union
from datetime import datetime
import logging


class OrganizedDataLoader:
    """Loads data directly from the organized data folder."""
    
    def __init__(self, organized_data_path: str = "data/organized"):
        self.organized_data_path = Path(organized_data_path)
        self.logger = logging.getLogger(__name__)
        
        # Ensure organized data path exists
        if not self.organized_data_path.exists():
            raise FileNotFoundError(f"Organized data path not found: {self.organized_data_path}")
    
    def get_data(self, region: str, start_date: Union[str, datetime], 
                end_date: Union[str, datetime]) -> pd.DataFrame:
        """
        Get organized data for a specific region and date range.
        
        Args:
            region: NEM region code (NSW1, QLD1, VIC1, SA1)
            start_date: Start date (string or datetime)
            end_date: End date (string or datetime)
            
        Returns:
            DataFrame with organized data
        """
        # Convert string dates to datetime
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)
        if isinstance(end_date, str):
            end_date = pd.to_datetime(end_date)
        
        # Construct file path
        file_path = self.organized_data_path / f"{region}_rrp_2020_2025.parquet"
        
        if not file_path.exists():
            raise FileNotFoundError(f"Organized data file not found: {file_path}")
        
        # Load data
        self.logger.info(f"Loading organized data from {file_path}")
        df = pd.read_parquet(file_path)
        
        # Filter by date range
        df = df[(df.index >= start_date) & (df.index <= end_date)]
        
        if df.empty:
            self.logger.warning(f"No data found for {region} in date range {start_date} to {end_date}")
            return pd.DataFrame()
        
        self.logger.info(f"Loaded {len(df):,} rows for {region} from {start_date} to {end_date}")
        return df
    
    def get_available_regions(self) -> list:
        """Get list of available regions in organized data."""
        parquet_files = list(self.organized_data_path.glob("*_rrp_2020_2025.parquet"))
        regions = [f.stem.replace("_rrp_2020_2025", "") for f in parquet_files]
        return sorted(regions)
    
    def get_data_summary(self) -> dict:
        """Get summary of available organized data."""
        summary = {}
        
        for region in self.get_available_regions():
            file_path = self.organized_data_path / f"{region}_rrp_2020_2025.parquet"
            
            if file_path.exists():
                df = pd.read_parquet(file_path)
                summary[region] = {
                    "rows": len(df),
                    "size_mb": file_path.stat().st_size / (1024 * 1024),
                    "date_range": f"{df.index.min()} to {df.index.max()}",
                    "years": sorted(df.index.year.unique()),
                    "avg_price": df["price_aud_per_mwh"].mean(),
                    "price_range": f"${df['price_aud_per_mwh'].min():.2f} to ${df['price_aud_per_mwh'].max():.2f}"
                }
        
        return summary


def load_organized_data(region: str, start_date: Union[str, datetime], 
                       end_date: Union[str, datetime]) -> pd.DataFrame:
    """
    Convenience function to load organized data.
    
    Args:
        region: NEM region code (NSW1, QLD1, VIC1, SA1)
        start_date: Start date (string or datetime)
        end_date: End date (string or datetime)
        
    Returns:
        DataFrame with organized data
    """
    loader = OrganizedDataLoader()
    return loader.get_data(region, start_date, end_date)
