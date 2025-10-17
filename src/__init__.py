"""
NEM Data Analysis Infrastructure

A high-performance data science infrastructure for Australian NEM electricity market analysis
with intelligent data caching, automatic NEMOSIS integration, and optimized storage.
"""

from .config import data_config, nemosis_config, AEMO_TABLES, NEM_REGIONS, DataFormat, NEMRegion
from .data_manager import DataManager, DataInventory, DataQuery, get_nem_data, get_data_summary
from .nemosis_client import NEMOSISClient, SmartDataRetriever, get_nemosis_data, get_smart_data

__version__ = "1.0.0"
__author__ = "NEM Data Analysis Team"

# Main classes for easy import
__all__ = [
    # Configuration
    'data_config',
    'nemosis_config', 
    'AEMO_TABLES',
    'NEM_REGIONS',
    'DataFormat',
    'NEMRegion',
    
    # Data Management
    'DataManager',
    'DataInventory',
    'DataQuery',
    'get_nem_data',
    'get_data_summary',
    
    # NEMOSIS Integration
    'NEMOSISClient',
    'SmartDataRetriever',
    'get_nemosis_data',
    'get_smart_data',
]

# Convenience function for quick start
def quick_start():
    """Quick start function to initialize the data infrastructure."""
    from .data_manager import DataManager
    from .nemosis_client import SmartDataRetriever
    
    # Initialize data manager
    data_manager = DataManager()
    
    # Get inventory summary
    summary = data_manager.get_inventory_summary()
    print("NEM Data Infrastructure Initialized!")
    print(f"Found {summary.get('total_files', 0)} data files")
    print(f"Total size: {summary.get('total_size_mb', 0):.2f} MB")
    
    # Initialize smart retriever
    retriever = SmartDataRetriever(data_manager)
    
    return data_manager, retriever


# Example usage
if __name__ == "__main__":
    # Quick start example
    data_manager, retriever = quick_start()
    
    # Example: Get NSW price data for last 30 days
    from datetime import datetime, timedelta
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    print(f"\nExample: Getting NSW price data from {start_date.date()} to {end_date.date()}")
    
    try:
        price_data = retriever.get_price_data('NSW1', start_date, end_date)
        if not price_data.empty:
            print(f"Retrieved {len(price_data)} price records")
            print(f"Columns: {list(price_data.columns)}")
        else:
            print("No price data available for this period")
    except Exception as e:
        print(f"Error retrieving data: {e}")
