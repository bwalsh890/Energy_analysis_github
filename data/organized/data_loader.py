#!/usr/bin/env python3
"""
NEM Data Loader - Easy access to organized RRP data
"""

import pandas as pd
from pathlib import Path


def load_rrp_data(region, start_date=None, end_date=None):
    """
    Load RRP data for a specific region and optional date range.
    
    Args:
        region (str): Region code (NSW1, VIC1, QLD1, SA1)
        start_date (str, optional): Start date in YYYY-MM-DD format
        end_date (str, optional): End date in YYYY-MM-DD format
    
    Returns:
        pd.DataFrame: RRP data with datetime index
    """
    data_file = Path(f'data/organized/{region}_rrp_2020_2025.parquet')
    
    if not data_file.exists():
        raise FileNotFoundError(f"Data file not found: {data_file}")
    
    df = pd.read_parquet(data_file)
    
    if start_date or end_date:
        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]
    
    return df


def get_available_regions():
    """Get list of available regions."""
    return ['NSW1', 'VIC1', 'QLD1', 'SA1']


def get_data_info():
    """Get information about available data."""
    info = {
        'regions': get_available_regions(),
        'period': '2020-01-01 to 2025-06-30',
        'resolution': '5-minute',
        'location': 'data/organized/'
    }
    return info


# Example usage
if __name__ == "__main__":
    # Load NSW data for 2024
    nsw_2024 = load_rrp_data('NSW1', '2024-01-01', '2024-12-31')
    print(f"NSW 2024 data: {len(nsw_2024)} rows")
    print(f"Date range: {nsw_2024.index.min()} to {nsw_2024.index.max()}")
    print(f"Price range: ${nsw_2024['price_aud_per_mwh'].min():.2f} to ${nsw_2024['price_aud_per_mwh'].max():.2f}")
