# Sensor Data Processing Task

## Objective

Process 3 Excel files containing sensor transmission data (S21 parameter) to generate plots showing the change in frequency difference (DeltaF) as a function of capacitance (Co).

## Input Data Files

The following 3 Excel files are in the `data/` directory:

| File | Description | Notes |
|------|-------------|-------|
| `Reciprocal Sensor with IC Co sweep (o-1pf).xlsx` | Reciprocal sensor with IC | 2 clear peaks at ~4.42 GHz and ~4.80 GHz |
| `non reciprocal sensor (0-1) co sweep.xlsx` | Non-reciprocal sensor | May have closely spaced/merged peaks |
| `reciprocal sensor without IC (0-1pf_.xlsx` | Reciprocal sensor without IC | **C0=0 has no data** - use C0=0.01 pF as baseline |

## Data Format (Confirmed)

Each Excel file has:
- **Single sheet**: `Sheet1`
- **1991 rows**: Frequency points from 0.10 to 20.00 GHz
- **102 columns**: 1 frequency column + 101 transmission columns (Co = 0 to 1 pF in 0.01 pF steps)

### Column Structure

```
Column 1: "Frequency (GHz)"
Column 2: "|S(2,1)| : [Sensor Name] (C0 = 0 )"
Column 3: "|S(2,1)| : [Sensor Name] (C0 = 0.01 )"
...
Column 102: "|S(2,1)| : [Sensor Name] (C0 = 1 )"
```

### Data Values

- **Frequency**: 0.10 to 20.00 GHz (linear spacing)
- **Transmission**: Linear magnitude (NOT dB) - values range from ~1e-12 to ~1.0
- **Peaks**: Local maxima in transmission (values approaching 1.0)

## Processing Algorithm

### Step 1: Load Data

```python
import pandas as pd
import re

def load_sensor_data(filepath):
    df = pd.read_excel(filepath, sheet_name='Sheet1')
    freq = df['Frequency (GHz)'].values

    # Extract Co values and transmission data
    co_data = {}
    for col in df.columns:
        if 'C0 =' in col:
            # Extract Co value using regex
            match = re.search(r'C0 = ([\d.]+)', col)
            if match:
                co_val = float(match.group(1))
                co_data[co_val] = df[col].values

    return freq, co_data
```

### Step 2: Peak Detection

Use `scipy.signal.find_peaks()` with parameters tuned for this data:

```python
from scipy.signal import find_peaks

def find_two_peaks(freq, transmission):
    """Find the two main peaks in transmission spectrum."""

    # For reciprocal sensors with clear peaks
    peaks, props = find_peaks(transmission,
                               prominence=0.1,   # Works for clear peaks
                               distance=20)      # ~0.2 GHz separation

    if len(peaks) >= 2:
        # Sort by peak height and take top 2
        heights = transmission[peaks]
        top2_idx = peaks[heights.argsort()[-2:]]
        return sorted(top2_idx)

    # Fallback: try lower prominence for merged peaks
    peaks, _ = find_peaks(transmission, prominence=0.01, distance=30)
    if len(peaks) >= 2:
        heights = transmission[peaks]
        top2_idx = peaks[heights.argsort()[-2:]]
        return sorted(top2_idx)

    # If only 1 peak found, return None or handle specially
    return None
```

### Step 3: Calculate Baseline DeltaF

```python
def get_baseline(freq, co_data, baseline_co=0.0):
    """Calculate baseline frequency difference at Co=0 (or first available)."""

    # Handle special case: reciprocal without IC has no data at C0=0
    if baseline_co not in co_data or co_data[baseline_co].max() < 1e-10:
        baseline_co = min(co for co in co_data.keys() if co_data[co].max() > 1e-10)
        print(f"Warning: Using Co={baseline_co} pF as baseline (C0=0 has no data)")

    transmission = co_data[baseline_co]
    peak_indices = find_two_peaks(freq, transmission)

    if peak_indices is None:
        raise ValueError("Could not find 2 peaks for baseline")

    f1 = freq[peak_indices[0]]
    f2 = freq[peak_indices[1]]
    deltaF_baseline = abs(f2 - f1)

    return deltaF_baseline, baseline_co
```

### Step 4: Process All Co Values

```python
def process_sensor(freq, co_data):
    """Process all Co values and calculate DeltaF."""

    deltaF_baseline, baseline_co = get_baseline(freq, co_data)

    results = []
    for co_val in sorted(co_data.keys()):
        transmission = co_data[co_val]

        # Skip if no data
        if transmission.max() < 1e-10:
            continue

        peak_indices = find_two_peaks(freq, transmission)

        if peak_indices is not None:
            f1 = freq[peak_indices[0]]
            f2 = freq[peak_indices[1]]
            deltaF_current = abs(f2 - f1)
            DeltaF = deltaF_baseline - deltaF_current  # baseline - current

            results.append({
                'Co_pF': co_val,
                'Peak1_GHz': f1,
                'Peak2_GHz': f2,
                'deltaF_current_GHz': deltaF_current,
                'DeltaF_GHz': DeltaF
            })
        else:
            # Handle single peak case
            results.append({
                'Co_pF': co_val,
                'Peak1_GHz': None,
                'Peak2_GHz': None,
                'deltaF_current_GHz': None,
                'DeltaF_GHz': None
            })

    return pd.DataFrame(results), deltaF_baseline
```

### Step 5: Generate Plots

```python
import matplotlib.pyplot as plt

def plot_deltaF_vs_Co(results_df, sensor_name, output_path):
    """Create DeltaF vs Co plot."""

    # Filter out None values
    valid = results_df.dropna(subset=['DeltaF_GHz'])

    plt.figure(figsize=(10, 6))
    plt.plot(valid['Co_pF'], valid['DeltaF_GHz'], 'o-',
             linewidth=2, markersize=6, color='#1f77b4')

    plt.xlabel('Co (pF)', fontsize=12)
    plt.ylabel('ΔF (GHz)', fontsize=12)
    plt.title(f'{sensor_name}: ΔF vs Capacitance', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_path}")
```

## Output Requirements

### 1. Plots (Required)

Save in `output/` directory:
- `reciprocal_with_IC_deltaF_vs_Co.png`
- `non_reciprocal_deltaF_vs_Co.png`
- `reciprocal_without_IC_deltaF_vs_Co.png`

### 2. Processed Data (CSV)

Save CSV files with extracted data:
```
output/
├── reciprocal_with_IC_results.csv
├── non_reciprocal_results.csv
└── reciprocal_without_IC_results.csv
```

CSV columns:
```csv
Co_pF,Peak1_GHz,Peak2_GHz,deltaF_current_GHz,DeltaF_GHz
0.0,4.42,4.80,0.38,0.00
0.01,4.41,4.79,0.38,0.00
...
```

## Special Cases to Handle

### 1. Reciprocal Sensor WITHOUT IC: No data at C0=0

The file `reciprocal sensor without IC (0-1pf_.xlsx` has all zeros at C0=0.

**Solution**: Use C0=0.01 pF (or first available non-zero Co) as baseline.

### 2. Non-Reciprocal Sensor: Possibly only 1 peak visible

The `non reciprocal sensor (0-1) co sweep.xlsx` may show only one dominant peak.

**Possible solutions**:
1. Look for a secondary peak with lower prominence threshold
2. Use derivative-based peak detection
3. Document this as a limitation and skip this file if 2 peaks cannot be found
4. Check if peaks exist in a specific frequency range (e.g., 3-6 GHz)

### 3. Peak Tracking Across Co Values

As Co increases, peaks may shift in frequency. Ensure you're tracking the same physical peaks:
- Peaks should shift smoothly, not jump
- If a peak disappears, flag this in the output

## Expected Results (Approximate)

Based on initial analysis:

| Sensor | Baseline Peaks | Expected Baseline ΔF |
|--------|----------------|---------------------|
| Reciprocal with IC | 4.42 GHz, 4.80 GHz | ~0.38 GHz |
| Non-Reciprocal | ~3.97 GHz, ? | TBD |
| Reciprocal without IC | 4.42 GHz, 4.80 GHz (at C0=0.1) | ~0.38 GHz |

## Validation Checklist

- [ ] All 3 Excel files loaded successfully
- [ ] Handle C0=0 missing data in "without IC" file
- [ ] Two peaks identified (or documented if not possible)
- [ ] Baseline calculated correctly
- [ ] DeltaF = baseline - current (not current - baseline)
- [ ] 3 plots saved to output/
- [ ] CSV results saved to output/
- [ ] Edge cases handled gracefully with warnings
