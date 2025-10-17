# Hybrid PV+BESS Energy Storage Simulation

A comprehensive web application for simulating and analyzing hybrid photovoltaic (PV) and battery energy storage systems (BESS) in the Australian National Electricity Market (NEM).

## Features

- **Interactive Configuration**: Configure battery parameters, solar PV settings, and market conditions
- **Real-time Simulation**: Run simulations with live results and visualizations
- **Multiple Scenarios**: Compare BESS-only vs Hybrid PV+BESS systems
- **Market Analysis**: Analyze performance across NSW1, QLD1, VIC1, and SA1 regions
- **Financial Modeling**: Calculate revenue, costs, and profitability metrics
- **Time Series Analysis**: Visualize battery behavior, energy flows, and price patterns

## System Requirements

- Python 3.8+
- Streamlit
- Access to NEM price data (included in organized data folder)

## Quick Start

1. **Run the dashboard locally**:
   ```bash
   streamlit run scripts/hybrid_pv_bess_web.py
   ```

2. **Access the dashboard**: Open http://localhost:8501 in your browser

## Configuration Options

### Battery Parameters
- Power capacity (MW)
- Energy capacity (MWh)
- State of charge limits
- Charge/discharge efficiency
- Initial SOC

### Solar PV Configuration
- System capacity (MW)
- Production profile selection
- PV efficiency
- Export efficiency
- Bidirectional charging option

### Market Settings
- Region selection (NSW1, QLD1, VIC1, SA1)
- Simulation date range
- Time resolution
- Price floor/ceiling

### Dispatch Windows
- Charge window (default: 10:30 AM - 2:30 PM)
- Discharge window (default: 5:00 PM - 9:00 PM)

### Network Tariffs
- Fixed charges (yearly)
- Volumetric charges (import/export)
- Demand charges
- Network loss factors

## Data Sources

- **NEM Price Data**: 5-minute spot prices from AEMO (2020-2025)
- **Solar Profiles**: 5.2MW tracking solar generation data
- **Market Regions**: NSW1, QLD1, VIC1, SA1

## Output Metrics

### Key Performance Indicators
- Total charge/discharge volumes
- Round trip efficiency
- Energy revenue and costs
- Network costs
- Gross and net profit

### Price Analysis
- Time-weighted average prices
- BESS import/export prices
- Solar-weighted prices
- Spread prices captured

### Financial Performance
- Revenue breakdown
- Cost analysis
- Profitability metrics
- ROI calculations

## File Structure

```
├── scripts/
│   └── hybrid_pv_bess_web.py          # Main dashboard application
├── src/
│   ├── battery_sim/
│   │   ├── config.py                  # Configuration classes
│   │   └── sim_hybrid.py              # Hybrid simulation logic
│   └── organized_data_loader.py       # Data loading utilities
├── data/
│   └── organized/                     # NEM price and solar data
├── requirements.txt                   # Python dependencies
└── README.md                         # This file
```

## Deployment

This application is designed to run on Streamlit Cloud. Simply connect your GitHub repository to Streamlit Cloud for automatic deployment.

## License

This project is for educational and research purposes in energy storage analysis.

## Contact

For questions or support, please refer to the project documentation or create an issue in the repository.