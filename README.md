# Non-Reciprocal Sensor Data Analysis

This project processes transmission spectrum data (S21 parameter) from RF sensors to analyze frequency shifts as a function of capacitance (Co).

## Overview

The sensors generate transmission spectra (frequency vs. |S21|) at various capacitor values (Co: 0-1 pF). Each spectrum contains characteristic peaks. By tracking how the difference between peaks changes with capacitance, we can characterize the sensor's response.

## Data Files

Three sensor datasets in `data/`:

| File | Sensor Type |
|------|-------------|
| `Reciprocal Sensor with IC Co sweep (o-1pf).xlsx` | Reciprocal sensor with integrated circuit |
| `non reciprocal sensor (0-1) co sweep.xlsx` | Non-reciprocal sensor |
| `reciprocal sensor without IC (0-1pf_.xlsx` | Reciprocal sensor without integrated circuit |

### Data Format

- **Frequency range**: 0.10 - 20.00 GHz (1991 points)
- **Capacitance range**: 0 - 1 pF (101 values, 0.01 pF steps)
- **Transmission**: Linear magnitude of S21 parameter

## Output

The analysis produces:
1. **DeltaF vs Co plots** - 3 PNG files showing frequency shift vs capacitance
2. **CSV data** - Processed peak frequencies and DeltaF values

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the analysis
python src/process_sensor_data.py
```

## Algorithm

1. For each Co value, identify two transmission peaks
2. Calculate frequency difference between peaks (deltaF)
3. At Co=0 (baseline): record deltaF_baseline
4. For each Co: DeltaF = deltaF_baseline - deltaF_current
5. Plot Co vs DeltaF for each sensor

## Dependencies

- Python 3.8+
- pandas, numpy, scipy, matplotlib, openpyxl

See `requirements.txt` for details.

## Task Instructions

See [TASK.md](TASK.md) for detailed processing algorithm and implementation guidance.
