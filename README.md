# Solar Charging Scheduler

The **Solar Charging Scheduler** is a Python-based simulation framework designed to optimize the charging of Battery Electric Vehicles (BEVs) using photovoltaic (PV) energy. This project provides tools to develop, test, and compare scheduling algorithms, aiming to reduce charging costs and increase the utilization of PV-generated energy.

## Features

- **Dynamic Scheduling Algorithm**: Efficiently schedules charging to maximize PV energy usage.
- **Simulation Modes**:
  - **Consecutive**: Automatically schedules multiple vehicles as they arrive. Used for performance evaluation.
  - **Iterative**: Allows step-by-step simulation for detailed analysis.
- **Data Visualization**: Clear graphical representations of schedules, PV energy usage, and grid power consumption.
- **Test Data Generation**: Generate realistic BEV datasets for simulations.
- **API Integration**: Uses the `energy-charts.info` API for PV energy forecasts.

## Installation

### System Requirements

- Python 3.x
- Required Python packages:
  - `numpy`, `matplotlib`, `requests`, `pytz`, `scipy`
- Docker (optional for containerized execution)

```bash
git clone https://github.com/benkne/solar-charging-scheduler.git
```
Run the framework either locally or by using Docker.

### Local installation

1. Insall dependencies:
    ```bash
    cd solar-charging-scheduler

    pip install -r requirements.txt
    ```

### Docker

1. Build the Docker image
    ```bash
    docker build -t solar-charging-scheduler .
    ```

2. Run the framework in a Docker container
    ```
    docker run --name scheduler -ti -v $(pwd)/results:/app/results solar-charging-scheduler
    ```

3. Restart after stopping the container
    ```
    docker start -ai scheduling_framework
    ```

## Simulation

### Consecutive
```
python run.py
```

### Iterative
```
python simulation.py create --storepath simulation.json

python simulation.py add

python simulation.py schedule

python simulation.py visualize
```

## Future Enhancements

- Grid power constraints integration.
- Detailed modeling of charging power curves.
- Support for other renewable energy sources and storage systems.
- Improved user interfaces and reporting tools.