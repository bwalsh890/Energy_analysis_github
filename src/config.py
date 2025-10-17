"""
Configuration module for NEM Data Analysis Infrastructure.

This module contains all configuration settings, constants, and path management
for the NEM data analysis system.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class DataFormat(Enum):
    """Supported data formats for storage and retrieval."""
    PARQUET = "parquet"
    FEATHER = "feather"
    CSV = "csv"
    EXCEL = "excel"
    SQLITE = "sqlite"


class NEMRegion(Enum):
    """NEM region codes."""
    NSW1 = "NSW1"
    VIC1 = "VIC1"
    QLD1 = "QLD1"
    SA1 = "SA1"
    TAS1 = "TAS1"


@dataclass
class DataConfig:
    """Configuration for data storage and retrieval."""
    
    # Paths
    project_root: Path = Path(__file__).parent.parent
    data_dir: Path = project_root / "data"
    raw_data_dir: Path = data_dir / "raw"
    processed_data_dir: Path = data_dir / "processed"
    cache_dir: Path = data_dir / "cache"
    
    # Storage settings
    default_format: DataFormat = DataFormat.PARQUET
    compression: str = "snappy"  # snappy, gzip, brotli
    chunk_size: int = 100000  # Rows per chunk for large files
    
    # Performance settings
    max_memory_usage: str = "2GB"
    parallel_workers: int = 4
    cache_size_mb: int = 1000
    
    # Data validation
    validate_schemas: bool = True
    strict_mode: bool = False
    
    def __post_init__(self):
        """Ensure directories exist after initialization."""
        for directory in [self.data_dir, self.raw_data_dir, 
                         self.processed_data_dir, self.cache_dir]:
            directory.mkdir(parents=True, exist_ok=True)


@dataclass
class NEMOSISConfig:
    """Configuration for NEMOSIS integration."""
    
    # NEMOSIS settings
    cache_format: str = "feather"  # feather, parquet, csv
    retry_attempts: int = 3
    retry_delay: float = 1.0
    timeout: int = 300  # seconds
    
    # Rate limiting
    max_requests_per_minute: int = 60
    request_delay: float = 1.0
    
    # Data filtering
    default_regions: List[str] = None
    default_tables: List[str] = None
    
    def __post_init__(self):
        """Set default values after initialization."""
        if self.default_regions is None:
            self.default_regions = [region.value for region in NEMRegion]
        
        if self.default_tables is None:
            self.default_tables = [
                "DISPATCHPRICE",
                "DISPATCHLOAD", 
                "TRADINGPRICE",
                "TRADINGLOAD",
                "BIDPEROFFER",
                "DISPATCH_UNIT_SCADA",
                "DUDETAILSUMMARY"
            ]


# AEMO Table Mappings
AEMO_TABLES = {
    "DISPATCHPRICE": {
        "description": "5-minute dispatch prices by region",
        "key_columns": ["SETTLEMENTDATE", "REGIONID", "RRP"],
        "time_column": "SETTLEMENTDATE",
        "region_column": "REGIONID"
    },
    "DISPATCHLOAD": {
        "description": "5-minute generator dispatch targets",
        "key_columns": ["SETTLEMENTDATE", "DUID", "INITIALMW"],
        "time_column": "SETTLEMENTDATE",
        "generator_column": "DUID"
    },
    "TRADINGPRICE": {
        "description": "30-minute trading prices",
        "key_columns": ["SETTLEMENTDATE", "REGIONID", "RRP"],
        "time_column": "SETTLEMENTDATE",
        "region_column": "REGIONID"
    },
    "BIDPEROFFER": {
        "description": "Market participant bids and offers",
        "key_columns": ["SETTLEMENTDATE", "DUID", "BIDTYPE", "PRICE", "VOLUME"],
        "time_column": "SETTLEMENTDATE",
        "generator_column": "DUID"
    },
    "DISPATCH_UNIT_SCADA": {
        "description": "5-minute SCADA values for generators",
        "key_columns": ["SETTLEMENTDATE", "DUID", "SCADAVALUE"],
        "time_column": "SETTLEMENTDATE",
        "generator_column": "DUID"
    },
    "DUDETAILSUMMARY": {
        "description": "Generator details and specifications",
        "key_columns": ["DUID", "STATIONNAME", "REGIONID", "FUELTECH"],
        "time_column": None,
        "generator_column": "DUID"
    }
}

# NEM Region Information
NEM_REGIONS = {
    "NSW1": {"name": "New South Wales", "timezone": "Australia/Sydney"},
    "VIC1": {"name": "Victoria", "timezone": "Australia/Melbourne"},
    "QLD1": {"name": "Queensland", "timezone": "Australia/Brisbane"},
    "SA1": {"name": "South Australia", "timezone": "Australia/Adelaide"},
    "TAS1": {"name": "Tasmania", "timezone": "Australia/Hobart"}
}

# File Pattern Mappings for Auto-Detection
FILE_PATTERNS = {
    "DISPATCHPRICE": [
        r".*dispatch.*price.*\.(csv|parquet|feather)$",
        r".*price.*dispatch.*\.(csv|parquet|feather)$"
    ],
    "DISPATCHLOAD": [
        r".*dispatch.*load.*\.(csv|parquet|feather)$",
        r".*dispatch.*NSW.*\.(csv|parquet|feather)$",
        r".*dispatch.*Vic.*\.(csv|parquet|feather)$"
    ],
    "DISPATCH_UNIT_SCADA": [
        r".*SCADA.*\.(csv|parquet|feather)$",
        r".*DISPATCH_UNIT_SCADA.*\.(csv|parquet|feather)$"
    ],
    "TRADINGPRICE": [
        r".*trading.*price.*\.(csv|parquet|feather)$",
        r".*30min.*\.(csv|parquet|feather)$"
    ]
}

# Performance Settings
PERFORMANCE_CONFIG = {
    "parquet_engine": "pyarrow",  # pyarrow or fastparquet
    "csv_engine": "c",  # c or python
    "chunk_size": 100000,
    "memory_map": True,
    "use_threads": True
}

# Logging Configuration
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "data_analysis.log",
    "max_size": "10MB",
    "backup_count": 5
}

# Create global configuration instances
data_config = DataConfig()
nemosis_config = NEMOSISConfig()

# Environment-specific overrides
if os.getenv("NEM_DATA_STRICT_MODE", "false").lower() == "true":
    data_config.strict_mode = True

if os.getenv("NEM_DATA_CACHE_SIZE"):
    data_config.cache_size_mb = int(os.getenv("NEM_DATA_CACHE_SIZE"))

if os.getenv("NEM_DATA_WORKERS"):
    data_config.parallel_workers = int(os.getenv("NEM_DATA_WORKERS"))


def get_data_path(table_name: str, region: Optional[str] = None, 
                 format_type: Optional[DataFormat] = None) -> Path:
    """
    Generate standardized file path for data storage.
    
    Args:
        table_name: AEMO table name
        region: NEM region code (optional)
        format_type: Data format (optional, uses default if not specified)
    
    Returns:
        Path object for the data file
    """
    if format_type is None:
        format_type = data_config.default_format
    
    # Create filename
    filename_parts = [table_name.lower()]
    if region:
        filename_parts.append(region.lower())
    filename_parts.append(format_type.value)
    
    filename = "_".join(filename_parts) + f".{format_type.value}"
    
    # Determine directory
    if table_name in ["DUDETAILSUMMARY"]:
        # Static tables go in processed directory
        return data_config.processed_data_dir / filename
    else:
        # Dynamic tables go in raw directory
        return data_config.raw_data_dir / filename


def validate_config() -> bool:
    """
    Validate configuration settings.
    
    Returns:
        True if configuration is valid, False otherwise
    """
    try:
        # Check if directories exist
        for directory in [data_config.data_dir, data_config.raw_data_dir,
                         data_config.processed_data_dir, data_config.cache_dir]:
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
        
        # Validate data format
        if data_config.default_format not in DataFormat:
            raise ValueError(f"Invalid default format: {data_config.default_format}")
        
        # Validate compression
        valid_compressions = ["snappy", "gzip", "brotli", "lz4"]
        if data_config.compression not in valid_compressions:
            raise ValueError(f"Invalid compression: {data_config.compression}")
        
        return True
    
    except Exception as e:
        print(f"Configuration validation failed: {e}")
        return False


if __name__ == "__main__":
    # Validate configuration on import
    if validate_config():
        print("Configuration validated successfully")
    else:
        print("Configuration validation failed")
