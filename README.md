# Non-Reciprocal Sensor Data Analysis

This project processes transmission spectrum data from non-reciprocal sensors to analyze frequency shifts as a function of capacitance (Co).

## Overview

The sensor generates transmission spectra (frequency vs. transmission) at various capacitor values (Co: 0-1 pF). Each spectrum contains two characteristic peaks. By tracking how the difference between these peaks changes with capacitance, we can characterize the sensor's response.

## Data Structure

```
data/
├── sensor1.xlsx    # First sensor dataset
├── sensor2.xlsx    # Second sensor dataset
└── sensor3.xlsx    # Third sensor dataset
```

Each Excel file should contain:
- Multiple sheets or columns for different Co values (0 to 1 pF)
- Frequency data (typically in GHz or MHz)
- Transmission data (typically in dB)

## Output

The analysis produces:
1. **DeltaF vs Co plots** for each sensor
2. **Processed data** in CSV format
3. **Summary statistics** for peak identification

## Quick Start

1. Place your Excel files in the `data/` directory
2. Install dependencies: `pip install -r requirements.txt`
3. Run the analysis: `python src/process_sensor_data.py`

## Dependencies

- Python 3.8+
- pandas
- numpy
- scipy
- matplotlib
- openpyxl

See `requirements.txt` for exact versions.

## Task Instructions

See [TASK.md](TASK.md) for detailed instructions on the data processing algorithm and expected output format.
