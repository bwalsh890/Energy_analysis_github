#!/usr/bin/env python3
"""
Run hybrid PV+BESS simulation for NSW 2024/2025.
"""

import sys
import pandas as pd
from pathlib import Path
sys.path.append(str(Path('src').resolve()))

from battery_sim.config import (
    BatteryConfig,
    SimulationConfig,
    MarketConfig,
    DispatchWindowsConfig,
    NetworkTariffsConfig,
    SolarPVConfig,
    FixedCharge,
    VolumeCharge,
    DemandCharge,
)
from battery_sim.sim_hybrid import run_simulation_hybrid
from src.utils.file_naming import create_timestamped_file


def create_hybrid_config():
    """Create configuration for hybrid PV+BESS simulation."""
    
    # Battery configuration (5MW, 20MWh)
    battery = BatteryConfig(
        name="Hybrid_PV_BESS",
        power_mw=5.0,
        energy_mwh=20.0,
        soc_init_mwh=2.0,  # Start at minimum SOC
        soc_min_mwh=2.0,
        soc_max_mwh=18.0,
        eta_charge=1.0,  # No efficiency loss during charging
        eta_discharge=1.0,  # No efficiency loss during discharging
    )
    
    # Simulation configuration
    sim = SimulationConfig(
        start="2024-01-01",
        end="2024-12-31",
        resolution_min=60,  # 1-hour resolution
    )
    
    # Market configuration
    market = MarketConfig(
        region="NSW1",
        price_column="price_aud_per_mwh",
        price_floor=-1000.0,
        price_ceiling=15000.0,
    )
    
    # Dispatch windows
    windows = DispatchWindowsConfig(
        charge_window=("10:30", "14:30"),  # 4-hour charge window
        discharge_window=("17:00", "21:00"),  # 4-hour discharge window
    )
    
    # Network tariffs
    tariffs = NetworkTariffsConfig(
        fixed=FixedCharge(cadence="daily", amount_aud=5000.0),
        volume=VolumeCharge(
            import_aud_per_mwh=0.0,
            export_aud_per_mwh=0.0,
        ),
        demand=DemandCharge(
            window=("17:00", "21:00"),
            cadence="monthly",
            metric="kW_import",
            rate_aud_per_kw=0.0,
        ),
        network_loss_factor=1.00,
        transmission_charges_aud_per_mwh=0.0,
        distribution_charges_aud_per_mwh=0.0,
    )
    
    # Solar PV configuration
    solar = SolarPVConfig(
        enabled=True,
        capacity_mw=5.0,  # 5MW solar system
        production_profile="5.2MW_tracking_solar_Hay2",
        efficiency=0.95,  # PV to battery efficiency
        export_efficiency=0.98,  # PV to grid export efficiency
        bidirectional_charging=False,  # Non-bidirectional (PV-only charging)
    )
    
    return battery, sim, market, windows, tariffs, solar


def main():
    """Run hybrid PV+BESS simulation."""
    print("Starting hybrid PV+BESS simulation...")
    
    # Create configuration
    battery, sim, market, windows, tariffs, solar = create_hybrid_config()
    
    print(f"Configuration:")
    print(f"  Battery: {battery.power_mw}MW / {battery.energy_mwh}MWh")
    print(f"  Solar: {solar.capacity_mw}MW ({'enabled' if solar.enabled else 'disabled'})")
    print(f"  Charging: {'Bidirectional' if solar.bidirectional_charging else 'PV-only'}")
    print(f"  Period: {sim.start} to {sim.end}")
    print(f"  Region: {market.region}")
    print()
    
    try:
        # Run simulation
        results = run_simulation_hybrid(
            battery=battery,
            sim=sim,
            market=market,
            windows=windows,
            tariffs=tariffs,
            solar=solar,
        )
        
        # Print summary
        summary = results["summary"]
        print("Simulation Results:")
        print(f"  Total Charge: {summary['total_charge_mwh']:.2f} MWh")
        print(f"  Total Discharge: {summary['total_discharge_mwh']:.2f} MWh")
        print(f"  Total Solar Export: {summary['total_solar_export_mwh']:.2f} MWh")
        print(f"  Round Trip Efficiency: {summary['round_trip_efficiency']:.1%}")
        print(f"  Avg Import Price: ${summary['avg_import_price']:.2f}/MWh")
        print(f"  Avg Export Price: ${summary['avg_export_price']:.2f}/MWh")
        print(f"  Avg Solar Export Price: ${summary['avg_solar_export_price']:.2f}/MWh")
        print(f"  Total Revenue: ${summary['energy_revenue_aud']:,.2f}")
        print(f"  Total Cost: ${summary['energy_cost_aud']:,.2f}")
        print(f"  Network Cost: ${summary['network_cost_aud']:,.2f}")
        print(f"  Gross Profit: ${summary['gross_profit_aud']:,.2f}")
        print(f"  Net Profit: ${summary['net_profit_aud']:,.2f}")
        print(f"  Initial SOC: {summary['initial_soc_mwh']:.2f} MWh")
        print(f"  Final SOC: {summary['final_soc_mwh']:.2f} MWh")
        print()
        
        # Save results
        output_dir = Path("outputs/hybrid_pv_bess")
        output_file = create_timestamped_file(
            "NSW1_Hybrid_PV_BESS_2024",
            "parquet",
            output_dir
        )
        
        # Save intervals data
        results["intervals"].to_parquet(output_file)
        print(f"Results saved to: {output_file}")
        
        # Save summary as CSV
        summary_file = create_timestamped_file(
            "NSW1_Hybrid_PV_BESS_2024_Summary",
            "csv",
            output_dir
        )
        
        summary_df = pd.DataFrame([summary])
        summary_df.to_csv(summary_file, index=False)
        print(f"Summary saved to: {summary_file}")
        
    except Exception as e:
        print(f"Error running simulation: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
