#!/usr/bin/env python3
"""
Streamlit web interface for hybrid PV+BESS simulation.
"""

import sys
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, time
from pathlib import Path

# Add src to path
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


def calculate_year_summary(intervals_df: pd.DataFrame, year: int) -> dict:
    """Calculate summary metrics for a specific year."""
    # Calculate summary metrics
    total_charge = intervals_df["energy_charge_mwh"].sum()
    total_discharge = intervals_df["energy_discharge_mwh"].sum()
    total_solar_export = intervals_df["energy_solar_export_mwh"].sum()
    total_revenue = intervals_df["energy_revenue_aud"].sum()
    total_cost = intervals_df["energy_cost_aud"].sum()
    total_network_cost = intervals_df["network_cost_aud"].sum()
    
    # Calculate actual round trip efficiency based on energy flows
    total_energy_consumed = total_charge
    total_energy_delivered = total_discharge + total_solar_export
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

    # Fixed charges (yearly)
    total_fixed_charges = 5000.0  # $5k per year
    total_network_cost += total_fixed_charges

    gross_profit = total_revenue - total_cost
    net_profit = gross_profit - total_network_cost

    return {
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
        "initial_soc_mwh": 0.5,
        "final_soc_mwh": intervals_df["soc_mwh"].iloc[-1] if not intervals_df.empty else 0.5,
        "total_intervals": len(intervals_df),
        "solar_enabled": True,
        "solar_capacity_mw": 5.0,
        "bidirectional_charging": False,
    }


def create_hybrid_config_from_ui():
    """Create configuration from Streamlit UI inputs."""
    
    # Battery configuration
    battery = BatteryConfig(
        name=st.session_state.get('battery_name', 'Hybrid_PV_BESS'),
        power_mw=st.session_state.get('battery_power_mw', 5.0),
        energy_mwh=st.session_state.get('battery_energy_mwh', 20.0),
        soc_init_mwh=st.session_state.get('battery_soc_init_mwh', 0.5),
        soc_min_mwh=st.session_state.get('battery_soc_min_mwh', 0.5),
        soc_max_mwh=st.session_state.get('battery_soc_max_mwh', 19.5),
        eta_charge=st.session_state.get('battery_eta_charge', 0.95),
        eta_discharge=st.session_state.get('battery_eta_discharge', 0.95),
    )
    
    # Simulation configuration
    sim = SimulationConfig(
        start=st.session_state.get('sim_start_str', '2024-01-01'),
        end=st.session_state.get('sim_end_str', '2024-12-31'),
        resolution_min=st.session_state.get('sim_resolution_min', 60),
    )
    
    # Market configuration
    market = MarketConfig(
        region=st.session_state.get('market_region', 'NSW1'),
        price_column='price_aud_per_mwh',
        price_floor=st.session_state.get('market_price_floor', -1000.0),
        price_ceiling=st.session_state.get('market_price_ceiling', 15000.0),
    )
    
    # Dispatch windows
    windows = DispatchWindowsConfig(
        charge_window=(
            st.session_state.get('charge_start_str', '10:30'),
            st.session_state.get('charge_end_str', '14:30')
        ),
        discharge_window=(
            st.session_state.get('discharge_start_str', '17:00'),
            st.session_state.get('discharge_end_str', '21:00')
        ),
    )
    
    # Network tariffs
    tariffs = NetworkTariffsConfig(
        fixed=FixedCharge(
            cadence=st.session_state.get('fixed_cadence', 'yearly'),
            amount_aud=st.session_state.get('fixed_amount', 5000.0)
        ),
        volume=VolumeCharge(
            import_aud_per_mwh=st.session_state.get('import_rate', 0.0),
            export_aud_per_mwh=st.session_state.get('export_rate', 0.0),
        ),
        demand=DemandCharge(
            window=(
                st.session_state.get('demand_window_start', '17:00'),
                st.session_state.get('demand_window_end', '21:00')
            ),
            cadence=st.session_state.get('demand_cadence', 'monthly'),
            metric=st.session_state.get('demand_metric', 'kW_import'),
            rate_aud_per_kw=st.session_state.get('demand_rate', 0.0),
        ),
        network_loss_factor=st.session_state.get('network_loss', 1.00),
        transmission_charges_aud_per_mwh=st.session_state.get('transmission_rate', 0.0),
        distribution_charges_aud_per_mwh=st.session_state.get('distribution_rate', 0.0),
    )
    
    # Solar PV configuration - check if system type is hybrid
    system_type = st.session_state.get('system_type', 'Hybrid PV+BESS')
    solar_enabled = (system_type == 'Hybrid PV+BESS')
    
    solar = SolarPVConfig(
        enabled=solar_enabled,
        capacity_mw=st.session_state.get('solar_capacity_mw', 5.0) if solar_enabled else 0.0,
        production_profile=st.session_state.get('solar_profile', '5.2MW_tracking_solar_Hay2'),
        efficiency=st.session_state.get('solar_efficiency', 0.95),
        export_efficiency=st.session_state.get('solar_export_efficiency', 0.98),
        bidirectional_charging=st.session_state.get('solar_bidirectional', False),
    )
    
    return battery, sim, market, windows, tariffs, solar


def main():
    """Main Streamlit app."""
    st.set_page_config(
        page_title="Hybrid PV+BESS Simulation",
        page_icon="🔋☀️",
        layout="wide"
    )
    
    st.title("🔋☀️ Hybrid PV+BESS Simulation")
    st.markdown("Simulate battery storage with solar PV generation")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        # System type selection
        st.subheader("System Type")
        system_type = st.radio(
            "Choose system type:",
            ["Hybrid PV+BESS", "Battery Only"],
            index=0,
            key='system_type'
        )
        
        # Solar configuration
        st.subheader("Solar PV Configuration")
        
        if system_type == "Hybrid PV+BESS":
            solar_enabled = True
            st.info("Solar PV is enabled for hybrid system")
        else:
            solar_enabled = False
            st.info("Solar PV is disabled for battery-only system")
        
        if solar_enabled:
            solar_capacity = st.number_input(
                "Solar Capacity (MW)",
                min_value=0.1,
                max_value=100.0,
                value=5.0,
                step=0.1,
                key='solar_capacity_mw'
            )
            
            solar_profile = st.selectbox(
                "Solar Profile",
                ["5.2MW_tracking_solar_Hay2"],
                key='solar_profile'
            )
            
            solar_efficiency = st.slider(
                "PV to Battery Efficiency",
                min_value=0.8,
                max_value=1.0,
                value=0.95,
                step=0.01,
                key='solar_efficiency'
            )
            
            solar_export_efficiency = st.slider(
                "PV to Grid Export Efficiency",
                min_value=0.8,
                max_value=1.0,
                value=0.98,
                step=0.01,
                key='solar_export_efficiency'
            )
            
            bidirectional = st.checkbox(
                "Bidirectional Charging (Allow grid charging)",
                value=False,
                help="If unchecked, battery can only charge from solar PV",
                key='solar_bidirectional'
            )
        
        # Battery configuration
        st.subheader("Battery Configuration")
        battery_power = st.number_input(
            "Battery Power (MW)",
            min_value=0.1,
            max_value=100.0,
            value=5.0,
            step=0.1,
            key='battery_power_mw'
        )
        
        battery_energy = st.number_input(
            "Battery Energy (MWh)",
            min_value=0.1,
            max_value=1000.0,
            value=20.0,
            step=0.1,
            key='battery_energy_mwh'
        )
        
        soc_min = st.number_input(
            "Minimum SOC (MWh)",
            min_value=0.0,
            max_value=battery_energy * 0.5,
            value=0.5,
            step=0.1,
            key='battery_soc_min_mwh'
        )
        
        soc_max = st.number_input(
            "Maximum SOC (MWh)",
            min_value=battery_energy * 0.5,
            max_value=battery_energy,
            value=19.5,
            step=0.1,
            key='battery_soc_max_mwh'
        )
        
        # Market configuration
        st.subheader("Market Configuration")
        region = st.selectbox(
            "NEM Region",
            ["NSW1", "QLD1", "VIC1", "SA1"],
            key='market_region'
        )
        
        start_date = st.date_input(
            "Start Date",
            value=datetime(2020, 1, 1).date(),
            key='sim_start'
        )
        
        end_date = st.date_input(
            "End Date",
            value=datetime(2024, 12, 31).date(),
            key='sim_end'
        )
        
        # Convert dates to strings for the simulation
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        resolution = st.selectbox(
            "Resolution",
            [5, 15, 30, 60],
            index=2,
            format_func=lambda x: f"{x} minutes",
            key='sim_resolution_min'
        )
        
        # Dispatch windows
        st.subheader("Dispatch Windows")
        charge_start = st.time_input(
            "Charge Start Time",
            value=time(10, 30),
            key='charge_start'
        )
        
        charge_end = st.time_input(
            "Charge End Time",
            value=time(14, 30),
            key='charge_end'
        )
        
        discharge_start = st.time_input(
            "Discharge Start Time",
            value=time(17, 0),
            key='discharge_start'
        )
        
        discharge_end = st.time_input(
            "Discharge End Time",
            value=time(21, 0),
            key='discharge_end'
        )
        
        # Convert time objects to strings for the simulation
        charge_start_str = charge_start.strftime('%H:%M')
        charge_end_str = charge_end.strftime('%H:%M')
        discharge_start_str = discharge_start.strftime('%H:%M')
        discharge_end_str = discharge_end.strftime('%H:%M')
        
        # Network tariffs
        st.subheader("Network Tariffs")
        fixed_charge = st.number_input(
            "Fixed Charge (AUD/year)",
            min_value=0.0,
            value=5000.0,
            step=100.0,
            key='fixed_amount'
        )
        
        import_rate = st.number_input(
            "Import Rate (AUD/MWh)",
            min_value=0.0,
            value=0.0,
            step=1.0,
            key='import_rate'
        )
        
        export_rate = st.number_input(
            "Export Rate (AUD/MWh)",
            min_value=0.0,
            value=0.0,
            step=1.0,
            key='export_rate'
        )
    
    # Store string dates and times in session state for simulation
    st.session_state['sim_start_str'] = start_date_str
    st.session_state['sim_end_str'] = end_date_str
    st.session_state['charge_start_str'] = charge_start_str
    st.session_state['charge_end_str'] = charge_end_str
    st.session_state['discharge_start_str'] = discharge_start_str
    st.session_state['discharge_end_str'] = discharge_end_str
    st.session_state['solar_enabled'] = solar_enabled
    
    # Run simulation button
    button_text = "🚀 Run Hybrid Simulation" if system_type == "Hybrid PV+BESS" else "🚀 Run Battery Simulation"
    if st.button(button_text, type="primary"):
        with st.spinner("Running simulation..."):
            try:
                # Create configuration
                battery, sim, market, windows, tariffs, solar = create_hybrid_config_from_ui()
                
                # Run simulation
                results = run_simulation_hybrid(
                    battery=battery,
                    sim=sim,
                    market=market,
                    windows=windows,
                    tariffs=tariffs,
                    solar=solar,
                )
                
                # Store results in session state
                st.session_state['simulation_results'] = results
                st.session_state['simulation_config'] = {
                    'battery': battery,
                    'sim': sim,
                    'market': market,
                    'windows': windows,
                    'tariffs': tariffs,
                    'solar': solar,
                }
                
                st.success("Simulation completed successfully!")
                
            except Exception as e:
                st.error(f"Simulation failed: {e}")
    
    # Display results
    if 'simulation_results' in st.session_state:
        results = st.session_state['simulation_results']
        all_intervals = results['intervals']
        
        # Get selected year from session state
        selected_year = st.session_state.get('selected_year', 2024)
        
        # Filter intervals to selected year
        year_intervals = all_intervals[all_intervals.index.year == selected_year]
        
        if year_intervals.empty:
            st.warning(f"No data available for year {selected_year}. Available years: {sorted(all_intervals.index.year.unique())}")
            year_intervals = all_intervals  # Fallback to all data
        
        # Recalculate summary for selected year
        summary = calculate_year_summary(year_intervals, selected_year)
        intervals = year_intervals
        
        # Year selector at the top of results
        st.header("📅 Year Analysis")
        col_year, col_info = st.columns([1, 3])
        with col_year:
            selected_year = st.selectbox(
                "Select Year:",
                options=[2020, 2021, 2022, 2023, 2024, 2025],
                index=4,  # Default to 2024
                key='year_selector'
            )
        with col_info:
            st.info(f"Showing data for {selected_year} ({len(intervals):,} intervals)")
        
        # Update session state
        if 'selected_year' not in st.session_state:
            st.session_state['selected_year'] = selected_year
        elif st.session_state['selected_year'] != selected_year:
            st.session_state['selected_year'] = selected_year
            st.rerun()
        
        # Key Performance Indicators
        st.header("📊 Key Performance Indicators")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Revenue",
                f"${summary['energy_revenue_aud']:,.0f}",
                delta=None
            )
            st.metric(
                "Net Profit",
                f"${summary['net_profit_aud']:,.0f}",
                delta=None
            )
        
        with col2:
            st.metric(
                "Battery Charge",
                f"{summary['total_charge_mwh']:,.0f} MWh",
                delta=None
            )
            st.metric(
                "Battery Discharge",
                f"{summary['total_discharge_mwh']:,.0f} MWh",
                delta=None
            )
        
        with col3:
            st.metric(
                "Solar Export",
                f"{summary['total_solar_export_mwh']:,.0f} MWh",
                delta=None
            )
            st.metric(
                "Round Trip Efficiency",
                f"{summary['round_trip_efficiency']:.1%}",
                delta=None
            )
        
        with col4:
            st.metric(
                "Avg Export Price",
                f"${summary['avg_export_price']:,.0f}/MWh",
                delta=None
            )
            st.metric(
                "Avg Solar Export Price",
                f"${summary['avg_solar_export_price']:,.0f}/MWh",
                delta=None
            )
        
        # Additional price metrics for selected year
        st.header("💰 Price Analysis")
        
        # Calculate price metrics for selected year
        time_weighted_avg_price = intervals['price'].mean()
        
        # BESS Import average price (when charging)
        bess_import_prices = intervals[intervals['p_charge_mw'] > 0]['price']
        bess_import_avg_price = bess_import_prices.mean() if not bess_import_prices.empty else 0
        
        # BESS Export average price (when discharging)
        bess_export_prices = intervals[intervals['p_discharge_mw'] > 0]['price']
        bess_export_avg_price = bess_export_prices.mean() if not bess_export_prices.empty else 0
        
        # Solar weighted price (total production)
        solar_generation = intervals['solar_power_mw'] * (intervals.index.to_series().diff().dt.total_seconds() / 3600)
        solar_weighted_price = (intervals['price'] * solar_generation).sum() / solar_generation.sum() if solar_generation.sum() > 0 else 0
        
        # Solar export weighted price (after BESS)
        solar_export_energy = intervals['p_solar_export_mw'] * (intervals.index.to_series().diff().dt.total_seconds() / 3600)
        solar_export_weighted_price = (intervals['price'] * solar_export_energy).sum() / solar_export_energy.sum() if solar_export_energy.sum() > 0 else 0
        
        # Spread price captured (export - import)
        spread_price_captured = bess_export_avg_price - bess_import_avg_price
        
        # Display price metrics in columns
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Time Weighted Avg Price",
                f"${time_weighted_avg_price:,.0f}/MWh"
            )
            st.metric(
                "BESS Import Avg Price",
                f"${bess_import_avg_price:,.0f}/MWh"
            )
        
        with col2:
            st.metric(
                "BESS Export Avg Price",
                f"${bess_export_avg_price:,.0f}/MWh"
            )
            st.metric(
                "Solar Weighted Price",
                f"${solar_weighted_price:,.0f}/MWh"
            )
        
        with col3:
            st.metric(
                "Solar Export Weighted Price",
                f"${solar_export_weighted_price:,.0f}/MWh"
            )
            st.metric(
                "Spread Price Captured",
                f"${spread_price_captured:,.0f}/MWh"
            )
        
        # Detailed metrics
        st.header("📈 Detailed Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Energy Flows")
            energy_data = {
                'Metric': ['Battery Charge', 'Battery Discharge', 'Solar Export', 'Total Generation'],
                'Value (MWh)': [
                    f"{summary['total_charge_mwh']:,.0f}",
                    f"{summary['total_discharge_mwh']:,.0f}",
                    f"{summary['total_solar_export_mwh']:,.0f}",
                    f"{summary['total_charge_mwh'] + summary['total_solar_export_mwh']:,.0f}"
                ]
            }
            st.dataframe(pd.DataFrame(energy_data), use_container_width=True)
        
        with col2:
            st.subheader("Financial Performance")
            financial_data = {
                'Metric': ['Energy Revenue', 'Energy Cost', 'Network Cost', 'Gross Profit', 'Net Profit'],
                'Value (AUD)': [
                    f"${summary['energy_revenue_aud']:,.0f}",
                    f"${summary['energy_cost_aud']:,.0f}",
                    f"${summary['network_cost_aud']:,.0f}",
                    f"${summary['gross_profit_aud']:,.0f}",
                    f"${summary['net_profit_aud']:,.0f}"
                ]
            }
            st.dataframe(pd.DataFrame(financial_data), use_container_width=True)
        
        # Time series plots
        st.header("📊 Time Series Analysis")
        
        # Select time period for plotting
        time_period = st.selectbox(
            "Select time period for plotting:",
            ["First Week", "First Month", "Full Period", "Custom Range"],
            index=0
        )
        
        if time_period == "First Week":
            plot_data = intervals.head(24 * 7)  # First week
        elif time_period == "First Month":
            plot_data = intervals.head(24 * 30)  # First month
        elif time_period == "Custom Range":
            start_idx = st.number_input("Start hour", min_value=0, max_value=len(intervals)-1, value=0)
            end_idx = st.number_input("End hour", min_value=start_idx+1, max_value=len(intervals), value=min(start_idx+168, len(intervals)))
            plot_data = intervals.iloc[start_idx:end_idx]
        else:
            plot_data = intervals
        
        # SOC and Power plot
        fig_soc = go.Figure()
        
        # Add SOC trace
        fig_soc.add_trace(go.Scatter(
            x=plot_data.index,
            y=plot_data['soc_mwh'],
            mode='lines',
            name='SOC (MWh)',
            line=dict(color='blue', width=2),
            fill='tonexty',
            fillcolor='rgba(0,100,200,0.2)'
        ))
        
        # Add power traces
        fig_soc.add_trace(go.Scatter(
            x=plot_data.index,
            y=plot_data['p_charge_mw'],
            mode='lines',
            name='Charge Power (MW)',
            line=dict(color='green', width=2)
        ))
        
        fig_soc.add_trace(go.Scatter(
            x=plot_data.index,
            y=-plot_data['p_discharge_mw'],
            mode='lines',
            name='Discharge Power (MW)',
            line=dict(color='red', width=2)
        ))
        
        if solar_enabled:
            fig_soc.add_trace(go.Scatter(
                x=plot_data.index,
                y=plot_data['p_solar_export_mw'],
                mode='lines',
                name='Solar Export (MW)',
                line=dict(color='orange', width=2)
            ))
        
        fig_soc.update_layout(
            title="Battery SOC and Power Flows",
            xaxis_title="Time",
            yaxis_title="Power (MW) / SOC (MWh)",
            hovermode='x unified',
            height=500
        )
        
        st.plotly_chart(fig_soc, use_container_width=True)
        
        # Price plot
        fig_price = go.Figure()
        
        fig_price.add_trace(go.Scatter(
            x=plot_data.index,
            y=plot_data['price'],
            mode='lines',
            name='Electricity Price',
            line=dict(color='purple', width=2)
        ))
        
        fig_price.update_layout(
            title="Electricity Price",
            xaxis_title="Time",
            yaxis_title="Price (AUD/MWh)",
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig_price, use_container_width=True)
        
        # Download results
        st.header("💾 Download Results")
        
        csv_data = intervals.to_csv()
        st.download_button(
            label="Download Simulation Data (CSV)",
            data=csv_data,
            file_name=f"hybrid_pv_bess_simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )


if __name__ == "__main__":
    main()
