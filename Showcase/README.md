# Home Assistant Energy Monitoring System

A comprehensive home energy monitoring and automation system built on Home Assistant, InfluxDB, and Grafana.

## System Overview

This setup monitors whole-home energy consumption at the circuit level, HVAC efficiency, and various home systems using statistical process control (SPC) techniques.

### Core Components

| Component | Purpose |
|-----------|---------|
| **Home Assistant** | Central automation hub |
| **InfluxDB** | Time-series database for sensor data |
| **Grafana** | Visualization and dashboards |
| **Emporia Vue** | Circuit-level energy monitoring (16 circuits) |
| **Shelly Devices** | Temperature and humidity sensors |
| **Tailscale** | Secure remote access |

### Monitored Circuits

- HVAC (1F & 2F systems)
- Hot Water Heater + Recirculation Pump
- Dehumidifier
- Washer/Dryer
- Kitchen Appliances
- Office Equipment
- And more...

## Live Dashboards

> Snapshots update automatically every 6 hours

### Energy Overview
<!-- SNAPSHOT:energy_overview -->
[![Energy Overview](https://snapshots.raintank.io/dashboard/snapshot/6FJDrgIMfOIGpy1JLmuYeChPkIdPmIzR)](https://snapshots.raintank.io/dashboard/snapshot/6FJDrgIMfOIGpy1JLmuYeChPkIdPmIzR)
<!-- /SNAPSHOT:energy_overview -->

### Daily Energy by Circuit
<!-- SNAPSHOT:daily_energy -->
[![Daily Energy by Circuit](https://snapshots.raintank.io/dashboard/snapshot/mswWiIz6oZRst4ZXpadb7WNn9JK0BGrT)](https://snapshots.raintank.io/dashboard/snapshot/mswWiIz6oZRst4ZXpadb7WNn9JK0BGrT)
<!-- /SNAPSHOT:daily_energy -->

### HVAC Performance
<!-- SNAPSHOT:hvac_performance -->
[![HVAC Performance](https://snapshots.raintank.io/dashboard/snapshot/2knaOMUJWNpc4uviJZQI5pGH0NX9BqVs)](https://snapshots.raintank.io/dashboard/snapshot/2knaOMUJWNpc4uviJZQI5pGH0NX9BqVs)
<!-- /SNAPSHOT:hvac_performance -->

### SPC Monitoring
<!-- SNAPSHOT:spc_monitoring -->
[![SPC Monitoring](https://snapshots.raintank.io/dashboard/snapshot/sweA6YfOGw0Pnhzkp4rB61j8Bmn7xeJR)](https://snapshots.raintank.io/dashboard/snapshot/sweA6YfOGw0Pnhzkp4rB61j8Bmn7xeJR)
<!-- /SNAPSHOT:spc_monitoring -->

## Features

### Energy Monitoring
- Real-time power consumption by circuit
- Daily/weekly/monthly energy totals
- Cost calculations based on utility rates
- Circuit-level breakdown and trends

### HVAC Analytics
- Runtime tracking per cycle
- Efficiency monitoring (runtime vs outdoor temp)
- Short-cycling detection with alerts
- Seasonal performance comparison

### Statistical Process Control (SPC)
- Automated baseline calculation
- Control limits (mean +/- 2 sigma)
- Anomaly detection for appliance degradation
- 7-day rolling statistics

### Automations
- Climate control based on occupancy
- Energy usage alerts
- Efficiency degradation notifications
- Daily/weekly report generation

## Architecture

```
                    +------------------+
                    |   Emporia Vue    |
                    |  (16 circuits)   |
                    +--------+---------+
                             |
                             v
+-------------+      +-------+-------+      +------------+
|   Shelly    +----->+ Home Assistant+----->+  InfluxDB  |
|   Sensors   |      |     Core      |      | (30d data) |
+-------------+      +-------+-------+      +-----+------+
                             |                    |
                             v                    v
                    +--------+--------+    +------+------+
                    |  Automations &  |    |   Grafana   |
                    |  Notifications  |    | Dashboards  |
                    +-----------------+    +-------------+
```

## Repository Structure

```
homeassistant/
├── configuration.yaml     # Main HA config
├── automations.yaml       # All automations
├── packages/              # Modular config packages
│   ├── spc.yaml          # SPC monitoring
│   ├── watchdog.yaml     # System monitoring
│   └── ...
├── grafana/
│   ├── dashboards/       # Dashboard JSON files
│   └── provisioning/     # Grafana auto-provisioning
├── scripts/              # Utility scripts
└── showcase/             # This folder - live demos
```

## Snapshot Automation

Dashboards are automatically captured and published every 6 hours using Grafana's snapshot API. See [update_snapshots.py](./update_snapshots.py) for implementation details.

---

*Last updated: P26-07-22 17:36:49<!-- /LAST_UPDATED -->*
