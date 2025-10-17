from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Any
import pandas as pd
import numpy as np
from pathlib import Path

from .config import (
    BatteryConfig,
    SimulationConfig,
    MarketConfig,
    DispatchWindowsConfig,
    NetworkTariffsConfig,
    SolarPVConfig,
)
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from organized_data_loader import OrganizedDataLoader


def _is_in_window(ts: pd.Timestamp, start_hm: str, end_hm: str) -> bool:
    """Check if timestamp is within the specified time window."""
    hm = ts.strftime("%H:%M")
    if start_hm <= end_hm:
        return start_hm <= hm < end_hm
    # window crosses midnight
    return hm >= start_hm or hm < end_hm


def load_solar_profile(profile_name: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Load solar production profile from organized data."""
    data_loader = OrganizedDataLoader()
    
    # Try to load the solar profile
    try:
        solar_file = f"data/organized/{profile_name}_1990.parquet"
        if Path(solar_file).exists():
            solar_df = pd.read_parquet(solar_file)
            solar_df.index = pd.to_datetime(solar_df.index)
            
            # Create profile for the simulation period
            sim_start = pd.Timestamp(start_date)
            sim_end = pd.Timestamp(end_date)
            sim_dates = pd.date_range(start=sim_start, end=sim_end, freq='h')  # Changed from 'H' to 'h'
            
            # Map solar data using day of year and hour
            solar_df['day_of_year'] = solar_df.index.dayofyear
            solar_df['hour'] = solar_df.index.hour
            
            sim_profile = pd.DataFrame({'datetime': sim_dates})
            sim_profile['day_of_year'] = sim_profile['datetime'].dt.dayofyear
            sim_profile['hour'] = sim_profile['datetime'].dt.hour
            
            # Merge with solar data
            sim_profile = sim_profile.merge(
                solar_df[['day_of_year', 'hour', 'power_mw']], 
                on=['day_of_year', 'hour'], 
                how='left'
            )
            
            # Fill missing values with 0 (night time)
            sim_profile['solar_power_mw'] = sim_profile['power_mw'].fillna(0)
            sim_profile.set_index('datetime', inplace=True)
            
            return sim_profile[['solar_power_mw']]
        else:
            print(f"Warning: Solar profile {solar_file} not found. Using zero generation.")
            return pd.DataFrame(index=pd.date_range(start=start_date, end=end_date, freq='h'), 
                              columns=['solar_power_mw'], data=0)
    except Exception as e:
        print(f"Error loading solar profile: {e}. Using zero generation.")
        return pd.DataFrame(index=pd.date_range(start=start_date, end=end_date, freq='h'), 
                          columns=['solar_power_mw'], data=0)


def run_simulation_hybrid(
    battery: BatteryConfig,
    sim: SimulationConfig,
    market: MarketConfig,
    windows: DispatchWindowsConfig,
    tariffs: NetworkTariffsConfig,
    solar: SolarPVConfig,
) -> Dict[str, Any]:
    """
    Run hybrid PV+BESS simulation using organized data.
    
    Logic:
    1. If solar enabled: Use solar to charge battery first, export excess
    2. If bidirectional: Allow grid charging during charge windows
    3. If non-bidirectional: Only charge from solar, no grid charging
    4. Discharge during discharge windows
    """
    # Initialize organized data loader
    data_loader = OrganizedDataLoader()

    # Load market data
    df = data_loader.get_data(
        region=market.region,
        start_date=sim.start,
        end_date=sim.end,
    )

    if df.empty:
        raise ValueError(f"No organized data available for {market.region} in the specified period")

    # Ensure we have the price column
    if market.price_column not in df.columns:
        raise ValueError(f"Price column '{market.price_column}' not found in organized data")

    # Use the price column as specified
    df["price"] = df[market.price_column]

    # Apply price floor and ceiling
    df["price"] = df["price"].clip(lower=market.price_floor, upper=market.price_ceiling)

    # Resample to simulation resolution
    if sim.resolution_min != 5:
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df_numeric = df[numeric_cols].resample(f"{sim.resolution_min}min").mean()
        df = df_numeric

    # Load solar profile if enabled
    if solar.enabled:
        solar_profile = load_solar_profile(solar.production_profile, sim.start, sim.end)
        # Scale solar profile to the configured capacity
        solar_profile['solar_power_mw'] = solar_profile['solar_power_mw'] * (solar.capacity_mw / 5.2)
        
        # Align solar profile with market data - ensure both have datetime index
        if not isinstance(solar_profile.index, pd.DatetimeIndex):
            solar_profile.index = pd.to_datetime(solar_profile.index)
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
            
        # Reindex solar profile to match market data frequency
        solar_profile = solar_profile.reindex(df.index, method='ffill')
        df['solar_power_mw'] = solar_profile['solar_power_mw'].fillna(0)
    else:
        df['solar_power_mw'] = 0

    # Initialize simulation variables
    soc = battery.soc_init_mwh
    intervals = []

    # Hybrid dispatch logic
    for timestamp, row in df.iterrows():
        price = row["price"]
        solar_power = row["solar_power_mw"]
        
        # Determine if we should charge or discharge based on time windows
        should_charge = _is_in_window(timestamp, windows.charge_window[0], windows.charge_window[1])
        should_discharge = _is_in_window(timestamp, windows.discharge_window[0], windows.discharge_window[1])
        
        # Calculate power dispatch
        p_charge = 0.0
        p_discharge = 0.0
        p_solar_charge = 0.0
        p_solar_export = 0.0
        p_grid_charge = 0.0
        
        # Solar generation logic
        if solar.enabled and solar_power > 0:
            # First priority: Use solar to charge battery if in charge window and battery not full
            if should_charge and soc < battery.soc_max_mwh:
                # Calculate how much solar power can be used for charging
                available_charge_capacity = min(
                    battery.power_mw,  # Battery power limit
                    (battery.soc_max_mwh - soc) / (sim.resolution_min / 60),  # SOC limit
                    solar_power  # Available solar power
                )
                p_solar_charge = available_charge_capacity
                # Apply solar efficiency to SOC update (energy stored in battery)
                soc += p_solar_charge * (sim.resolution_min / 60) * solar.efficiency
            
            # Second priority: Export excess solar to grid
            remaining_solar = solar_power - p_solar_charge
            if remaining_solar > 0:
                p_solar_export = remaining_solar * solar.export_efficiency
        
        # Grid charging logic (only if bidirectional enabled)
        if should_charge and soc < battery.soc_max_mwh and (not solar.enabled or solar.bidirectional_charging):
            # Calculate remaining charge capacity
            available_charge_capacity = min(
                battery.power_mw,
                (battery.soc_max_mwh - soc) / (sim.resolution_min / 60)
            )
            p_grid_charge = available_charge_capacity
            # Apply battery efficiency to SOC update (energy stored in battery)
            soc += p_grid_charge * (sim.resolution_min / 60) * battery.eta_charge
        
        # Discharge logic
        if should_discharge and soc > battery.soc_min_mwh:
            # Calculate discharge capacity - account for efficiency losses
            available_energy_mwh = soc - battery.soc_min_mwh
            # Energy delivered to grid = available energy * discharge efficiency
            max_discharge_energy = available_energy_mwh * battery.eta_discharge
            max_discharge_power = max_discharge_energy / (sim.resolution_min / 60)
            p_discharge = min(battery.power_mw, max_discharge_power)
            # SOC decreases by the energy removed from battery (before efficiency)
            soc -= p_discharge * (sim.resolution_min / 60) / battery.eta_discharge
        
        # Ensure SOC stays within bounds
        soc = max(battery.soc_min_mwh, min(battery.soc_max_mwh, soc))
        
        # Calculate total charging power
        p_charge = p_solar_charge + p_grid_charge
        
        # Calculate energy flows - account for efficiency properly
        # Energy consumed from grid (for grid charging only)
        energy_grid_charge = p_grid_charge * (sim.resolution_min / 60)
        # Energy consumed from solar (for solar charging)
        energy_solar_charge = p_solar_charge * (sim.resolution_min / 60)
        # Total energy consumed (for revenue calculations)
        energy_charge = energy_grid_charge + energy_solar_charge
        # Energy delivered to grid from battery (after discharge efficiency)
        energy_discharge = p_discharge * (sim.resolution_min / 60)
        # Energy delivered to grid from solar export
        energy_solar_export = p_solar_export * (sim.resolution_min / 60)
        
        # Store actual energy flows for proper efficiency calculation
        # Energy stored in battery (after charging efficiency losses)
        energy_stored = (p_solar_charge * solar.efficiency + p_grid_charge * battery.eta_charge) * (sim.resolution_min / 60)
        # Energy removed from battery (before discharge efficiency losses)
        energy_removed = p_discharge * (sim.resolution_min / 60) / battery.eta_discharge
        
        # Calculate revenue and costs
        energy_revenue = (energy_discharge + energy_solar_export) * price
        energy_cost = p_grid_charge * (sim.resolution_min / 60) * price
        
        # Network charges (simplified)
        interval_duration_hours = sim.resolution_min / 60
        
        # Volumetric charges
        cogs_network_volumetric = (p_grid_charge * (sim.resolution_min / 60) * tariffs.volume.import_aud_per_mwh) + \
                                ((energy_discharge + energy_solar_export) * tariffs.volume.export_aud_per_mwh)
        
        # Demand charges (simplified)
        cogs_network_demand = 0.0
        if tariffs.demand and _is_in_window(timestamp, tariffs.demand.window[0], tariffs.demand.window[1]):
            cogs_network_demand = max(p_charge, p_discharge) * tariffs.demand.rate_aud_per_kw * interval_duration_hours

        intervals.append({
            "timestamp": timestamp,
            "price": price,
            "solar_power_mw": solar_power,
            "p_charge_mw": p_charge,
            "p_discharge_mw": p_discharge,
            "p_solar_charge_mw": p_solar_charge,
            "p_solar_export_mw": p_solar_export,
            "p_grid_charge_mw": p_grid_charge,
            "soc_mwh": soc,
            "energy_charge_mwh": energy_charge,
            "energy_discharge_mwh": energy_discharge,
            "energy_solar_export_mwh": energy_solar_export,
            "energy_revenue_aud": energy_revenue,
            "energy_cost_aud": energy_cost,
            "network_cost_aud": cogs_network_volumetric + cogs_network_demand,
        })

    intervals_df = pd.DataFrame(intervals).set_index("timestamp")

    # Calculate summary metrics
    total_charge = intervals_df["energy_charge_mwh"].sum()
    total_discharge = intervals_df["energy_discharge_mwh"].sum()
    total_solar_export = intervals_df["energy_solar_export_mwh"].sum()
    total_revenue = intervals_df["energy_revenue_aud"].sum()
    total_cost = intervals_df["energy_cost_aud"].sum()
    total_network_cost = intervals_df["network_cost_aud"].sum()
    
    # Calculate actual round trip efficiency based on energy flows
    # Total energy consumed from sources (grid + solar)
    total_energy_consumed = total_charge
    # Total energy delivered to grid from battery discharge only (excludes solar export)
    total_energy_delivered = total_discharge
    # Round trip efficiency = battery energy delivered / battery energy consumed
    if total_energy_consumed > 0:
        round_trip_efficiency = total_energy_delivered / total_energy_consumed
    else:
        round_trip_efficiency = 0.0
    
    # Price metrics
    charge_prices = intervals_df[intervals_df["p_charge_mw"] > 0]["price"]
    discharge_prices = intervals_df[intervals_df["p_discharge_mw"] > 0]["price"]
    solar_export_prices = intervals_df[intervals_df["p_solar_export_mw"] > 0]["price"]
    
    avg_import_price = charge_prices.mean() if not charge_prices.empty else 0.0
    avg_export_price = discharge_prices.mean() if not discharge_prices.empty else 0.0
    avg_solar_export_price = solar_export_prices.mean() if not solar_export_prices.empty else 0.0
    avg_price = intervals_df["price"].mean()

    # Fixed charges
    if tariffs.fixed.cadence == 'yearly':
        # Calculate the fraction of the year covered by the simulation
        sim_start = pd.to_datetime(sim.start)
        sim_end = pd.to_datetime(sim.end)
        year_start = pd.Timestamp(sim_start.year, 1, 1)
        year_end = pd.Timestamp(sim_start.year, 12, 31)
        
        # Calculate fraction of year
        total_year_days = (year_end - year_start).days + 1
        sim_days = (sim_end - sim_start).days + 1
        year_fraction = sim_days / total_year_days
        
        total_fixed_charges = tariffs.fixed.amount_aud * year_fraction
    else:  # daily
        num_days = (pd.to_datetime(sim.end) - pd.to_datetime(sim.start)).days + 1
        total_fixed_charges = tariffs.fixed.amount_aud * num_days
    
    total_network_cost += total_fixed_charges

    gross_profit = total_revenue - total_cost
    net_profit = gross_profit - total_network_cost

    summary = {
        "total_charge_mwh": total_charge,
        "total_discharge_mwh": total_discharge,
        "total_solar_export_mwh": total_solar_export,
        "round_trip_efficiency": round_trip_efficiency,
        "avg_import_price": avg_import_price,
        "avg_export_price": avg_export_price,
        "avg_solar_export_price": avg_solar_export_price,
        "avg_price": avg_price,
        "energy_revenue_aud": total_revenue,
        "energy_cost_aud": total_cost,
        "network_cost_aud": total_network_cost,
        "gross_profit_aud": gross_profit,
        "net_profit_aud": net_profit,
        "initial_soc_mwh": battery.soc_init_mwh,
        "final_soc_mwh": soc,
        "total_intervals": len(intervals_df),
        "solar_enabled": solar.enabled,
        "solar_capacity_mw": solar.capacity_mw if solar.enabled else 0,
        "bidirectional_charging": solar.bidirectional_charging if solar.enabled else False,
    }

    return {"intervals": intervals_df, "summary": summary}
