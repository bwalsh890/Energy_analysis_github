from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict, Any


@dataclass
class SolarPVConfig:
    """Configuration for solar PV system in hybrid PV+BESS setup."""
    enabled: bool = False
    capacity_mw: float = 5.0  # PV system capacity in MW
    production_profile: str = "5.2MW_tracking_solar_Hay2"  # Profile name in organized data
    efficiency: float = 0.95  # PV to battery charging efficiency
    export_efficiency: float = 0.98  # PV to grid export efficiency
    bidirectional_charging: bool = False  # Allow grid charging (True) or PV-only charging (False)


@dataclass
class BatteryConfig:
    name: str
    power_mw: float
    energy_mwh: float
    soc_init_mwh: float
    soc_min_mwh: float
    soc_max_mwh: float
    eta_charge: float = 0.95
    eta_discharge: float = 0.95
    simultaneous_charge_discharge: bool = False
    ramp_mw_per_min: Optional[float] = None
    
    # Additional battery parameters
    degradation_per_cycle: float = 0.0  # % capacity loss per full cycle
    degradation_per_year: float = 0.02  # % capacity loss per year (calendar aging)
    min_operating_temp_c: float = -20.0
    max_operating_temp_c: float = 60.0
    standby_power_kw: float = 0.0  # Continuous power consumption
    aux_power_kw: float = 0.0  # Additional power during operation
    
    # Cycling constraints
    max_cycles_per_day: Optional[float] = None
    max_cycles_per_week: Optional[float] = None
    max_cycles_per_month: Optional[float] = None
    
    # Reserve requirements
    reserve_requirement_mwh: float = 0.0  # Minimum SoC to maintain
    emergency_reserve_mwh: float = 0.0  # Additional reserve for emergencies


@dataclass
class SimulationConfig:
    start: str
    end: str
    resolution_min: int = 5
    timezone: Optional[str] = None  # e.g., 'Australia/Sydney'
    
    # Additional simulation parameters
    random_seed: Optional[int] = None
    enable_degradation: bool = True
    enable_temperature_effects: bool = False
    ambient_temperature_c: float = 25.0  # Constant ambient temperature
    temperature_profile_file: Optional[str] = None  # Path to temperature data


@dataclass
class MarketConfig:
    region: str  # one of NSW1/VIC1/QLD1/SA1
    price_source: str = "dispatchprice"
    price_column: str = "RRP"
    price_currency: str = "AUD/MWh"
    
    # Additional market parameters
    price_floor: Optional[float] = None  # Minimum price to consider
    price_ceiling: Optional[float] = None  # Maximum price to consider
    price_smoothing_window: int = 1  # Moving average window for price smoothing
    enable_price_forecasting: bool = False
    forecast_horizon_hours: int = 24
    forecast_accuracy: float = 0.85  # Forecast accuracy (0-1)
    
    # FCAS market participation
    enable_fcas: bool = False
    fcas_raise_6sec: bool = False
    fcas_raise_60sec: bool = False
    fcas_raise_5min: bool = False
    fcas_raise_reg: bool = False
    fcas_lower_6sec: bool = False
    fcas_lower_60sec: bool = False
    fcas_lower_5min: bool = False
    fcas_lower_reg: bool = False


@dataclass
class DispatchWindowsConfig:
    charge_window: Tuple[str, str]  # ("HH:MM", "HH:MM")
    discharge_window: Tuple[str, str]  # ("HH:MM", "HH:MM")
    weekends_same: bool = True
    
    # Additional dispatch parameters
    weekend_charge_window: Optional[Tuple[str, str]] = None
    weekend_discharge_window: Optional[Tuple[str, str]] = None
    holiday_charge_window: Optional[Tuple[str, str]] = None
    holiday_discharge_window: Optional[Tuple[str, str]] = None
    holiday_dates: List[str] = None  # List of holiday dates in YYYY-MM-DD format
    
    # Price-based dispatch triggers
    charge_price_threshold: Optional[float] = None  # Charge when price below this
    discharge_price_threshold: Optional[float] = None  # Discharge when price above this
    min_price_spread: float = 0.0  # Minimum price spread to trigger dispatch
    
    # Advanced dispatch options
    enable_dynamic_windows: bool = False  # Adjust windows based on price patterns
    enable_peak_shaving: bool = False  # Discharge during peak demand periods
    enable_load_following: bool = False  # Follow load patterns
    enable_frequency_regulation: bool = False  # Provide frequency regulation services


@dataclass
class FixedCharge:
    cadence: str  # 'daily' | 'monthly'
    amount_aud: float


@dataclass
class VolumeCharge:
    import_aud_per_mwh: float = 0.0
    export_aud_per_mwh: float = 0.0


@dataclass
class DemandCharge:
    window: Tuple[str, str]  # ("HH:MM", "HH:MM")
    cadence: str  # 'monthly'
    metric: str  # 'kW_import' | 'kW_site_net'
    rate_aud_per_kw: float


@dataclass
class NetworkTariffsConfig:
    fixed: FixedCharge
    volume: VolumeCharge
    demand: Optional[DemandCharge] = None
    
    # Additional tariff components
    connection_fee_aud: float = 0.0  # One-time connection fee
    metering_fee_aud_per_month: float = 0.0  # Monthly metering fee
    network_loss_factor: float = 1.0  # Network loss factor (1.0 = no losses)
    transmission_charges_aud_per_mwh: float = 0.0  # Transmission network charges
    distribution_charges_aud_per_mwh: float = 0.0  # Distribution network charges
    
    # Time-of-use tariffs
    enable_tou: bool = False
    tou_peak_rate_aud_per_mwh: float = 0.0
    tou_off_peak_rate_aud_per_mwh: float = 0.0
    tou_shoulder_rate_aud_per_mwh: float = 0.0
    tou_peak_hours: List[Tuple[str, str]] = None  # Peak time windows
    tou_off_peak_hours: List[Tuple[str, str]] = None  # Off-peak time windows
    tou_shoulder_hours: List[Tuple[str, str]] = None  # Shoulder time windows
    
    # Renewable energy certificates
    enable_lgc: bool = False  # Large-scale Generation Certificates
    lgc_price_aud_per_certificate: float = 0.0
    enable_stc: bool = False  # Small-scale Technology Certificates
    stc_price_aud_per_certificate: float = 0.0
    
    # Carbon pricing
    enable_carbon_pricing: bool = False
    carbon_price_aud_per_tonne: float = 0.0
    grid_emissions_factor_tonnes_per_mwh: float = 0.0


@dataclass
class OperationalConstraints:
    """Operational constraints and limits"""
    max_continuous_charge_hours: Optional[float] = None
    max_continuous_discharge_hours: Optional[float] = None
    min_rest_period_hours: float = 0.0  # Minimum rest between charge/discharge
    max_daily_energy_throughput_mwh: Optional[float] = None
    max_weekly_energy_throughput_mwh: Optional[float] = None
    max_monthly_energy_throughput_mwh: Optional[float] = None
    
    # Maintenance constraints
    maintenance_windows: List[Tuple[str, str]] = None  # Maintenance periods
    maintenance_energy_penalty: float = 0.0  # Energy penalty during maintenance
    
    # Environmental constraints
    max_ambient_temp_c: float = 60.0
    min_ambient_temp_c: float = -20.0
    temp_derating_factor: float = 0.0  # Power derating per degree above/below optimal


@dataclass
class FinancialConfig:
    """Financial parameters and costs"""
    # Capital costs
    battery_capex_aud_per_mwh: float = 0.0
    inverter_capex_aud_per_mw: float = 0.0
    balance_of_plant_capex_aud: float = 0.0
    installation_capex_aud: float = 0.0
    grid_connection_capex_aud: float = 0.0
    
    # Operating costs
    opex_fixed_aud_per_year: float = 0.0
    opex_variable_aud_per_mwh: float = 0.0
    maintenance_cost_aud_per_mwh: float = 0.0
    insurance_cost_aud_per_year: float = 0.0
    
    # Financial parameters
    discount_rate: float = 0.08  # Annual discount rate
    project_life_years: float = 20.0
    tax_rate: float = 0.30  # Corporate tax rate
    depreciation_years: float = 10.0  # Asset depreciation period
    
    # Revenue streams
    enable_energy_arbitrage: bool = True
    enable_fcas_revenue: bool = False
    enable_ancillary_services: bool = False
    enable_grid_services: bool = False


@dataclass
class ReportingConfig:
    """Reporting and output configuration"""
    # Output formats
    save_interval_data: bool = True
    save_daily_summaries: bool = True
    save_monthly_summaries: bool = True
    save_annual_summaries: bool = True
    
    # Plotting options
    generate_plots: bool = True
    plot_soc: bool = True
    plot_power: bool = True
    plot_prices: bool = True
    plot_revenue: bool = True
    plot_cycles: bool = True
    plot_heatmap: bool = False
    
    # KPI calculations
    calculate_round_trip_efficiency: bool = True
    calculate_utilization: bool = True
    calculate_cycles: bool = True
    calculate_degradation: bool = True
    calculate_financial_metrics: bool = True
    
    # Output directory
    output_directory: str = "outputs/battery_sim"
    create_subdirectories: bool = True


@dataclass
class ValidationConfig:
    """Data validation and quality checks"""
    enable_validation: bool = True
    check_price_data_quality: bool = True
    check_battery_constraints: bool = True
    check_energy_balance: bool = True
    check_soc_bounds: bool = True
    
    # Validation thresholds
    max_price_spike_factor: float = 10.0  # Max price spike relative to average
    min_price_threshold: float = -1000.0  # Minimum acceptable price
    max_price_threshold: float = 15000.0  # Maximum acceptable price
    soc_tolerance: float = 0.01  # SoC validation tolerance (MWh)
    
    # Warning thresholds
    warn_high_utilization: float = 0.95  # Warn if utilization > 95%
    warn_high_cycles: float = 2.0  # Warn if cycles per day > 2
    warn_low_efficiency: float = 0.80  # Warn if efficiency < 80%


