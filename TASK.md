# Sensor Data Processing Task

## Objective

Process 3 Excel files containing non-reciprocal sensor transmission data to generate plots showing the change in frequency difference (DeltaF) as a function of capacitance (Co).

## Input Data Format

Each Excel file contains transmission spectrum data:
- **X-axis**: Frequency (check units - likely GHz or MHz)
- **Y-axis**: Transmission (likely in dB, look for negative values indicating loss)
- **Parameter**: Capacitance Co sweeping from 0 to 1 pF

### Expected Excel Structure

The data may be organized as:
- **Option A**: Separate sheets for each Co value
- **Option B**: Multiple column pairs (Frequency, Transmission) for each Co value
- **Option C**: A single sheet with Co as an additional column

Inspect the Excel files first to determine the actual structure.

## Processing Algorithm

### Step 1: Load and Inspect Data

```python
# Read each Excel file
# Identify the structure (sheets vs columns)
# Extract frequency and transmission data for each Co value
```

### Step 2: Peak Detection for Each Spectrum

For each Co value's transmission spectrum:

1. **Find TWO peaks** in the transmission data
   - Use `scipy.signal.find_peaks()` with appropriate parameters
   - Peaks in transmission spectra are typically local maxima (less negative dB values)
   - May need to adjust `height`, `distance`, `prominence` parameters

2. **Handle challenging cases**:
   - Closely spaced peaks: reduce `distance` parameter
   - Odd shapes: adjust `prominence` to distinguish real peaks from noise
   - If automatic detection fails, consider smoothing the data first

```python
from scipy.signal import find_peaks

# Example peak detection
peaks, properties = find_peaks(transmission,
                                prominence=0.5,  # Adjust as needed
                                distance=10)     # Minimum samples between peaks
```

### Step 3: Calculate Baseline DeltaF

At **Co = 0 pF** (the baseline):
1. Identify the two peak frequencies: `f1_baseline`, `f2_baseline`
2. Calculate baseline frequency difference:
   ```
   deltaF_baseline = |f2_baseline - f1_baseline|
   ```

### Step 4: Calculate DeltaF for Each Co Value

For each Co value from 0 to 1 pF:
1. Find the two peaks: `f1`, `f2`
2. Calculate current frequency difference:
   ```
   deltaF_current = |f2 - f1|
   ```
3. Calculate the change from baseline:
   ```
   DeltaF = deltaF_baseline - deltaF_current
   ```

**Important**: The formula is `baseline - current`, not `current - baseline`.

### Step 5: Generate Plots

Create 3 separate plots (one per Excel file):
- **X-axis**: Co (pF) - capacitance values from 0 to 1
- **Y-axis**: DeltaF - the change in frequency difference
- **Title**: Include sensor/file identifier
- **Labels**: Include units (pF for Co, Hz/MHz/GHz for DeltaF)

```python
import matplotlib.pyplot as plt

plt.figure(figsize=(10, 6))
plt.plot(co_values, delta_f_values, 'o-', linewidth=2, markersize=8)
plt.xlabel('Co (pF)')
plt.ylabel('ΔF (GHz)')  # Adjust units as appropriate
plt.title('Sensor Response: ΔF vs Capacitance')
plt.grid(True)
plt.savefig('output/sensor1_deltaF_vs_Co.png', dpi=300, bbox_inches='tight')
```

## Output Requirements

### 1. Plots (Required)

Save in `output/` directory:
- `sensor1_deltaF_vs_Co.png`
- `sensor2_deltaF_vs_Co.png`
- `sensor3_deltaF_vs_Co.png`

### 2. Processed Data (Optional but Recommended)

Save CSV files with the extracted data:
```
output/
├── sensor1_results.csv
├── sensor2_results.csv
└── sensor3_results.csv
```

CSV format:
```csv
Co_pF,Peak1_freq,Peak2_freq,deltaF_current,DeltaF
0.0,2.45,2.55,0.10,0.00
0.1,2.46,2.54,0.08,0.02
...
```

### 3. Summary Report (Optional)

A markdown summary with:
- Baseline deltaF for each sensor
- Maximum DeltaF observed
- Any data quality issues encountered

## Troubleshooting Peak Detection

### Problem: Can't find exactly 2 peaks

**Solutions**:
1. Adjust `prominence` parameter (try values from 0.1 to 2.0)
2. Adjust `distance` parameter based on expected peak separation
3. Apply smoothing before peak detection:
   ```python
   from scipy.ndimage import gaussian_filter1d
   smoothed = gaussian_filter1d(transmission, sigma=2)
   ```
4. Use `scipy.signal.find_peaks` with `height` parameter to filter noise

### Problem: Peaks are too close together

**Solutions**:
1. Reduce `distance` parameter
2. Increase frequency resolution if possible
3. Use derivative-based peak detection for overlapping peaks

### Problem: Inconsistent peak identification across Co values

**Solutions**:
1. Track peaks across consecutive Co values
2. Use peak properties (height, width) to match corresponding peaks
3. Implement a peak tracking algorithm that follows peaks as Co changes

## Code Structure Recommendation

```
src/
├── process_sensor_data.py   # Main processing script
├── peak_detection.py        # Peak finding utilities
├── plotting.py              # Visualization functions
└── utils.py                 # Data loading helpers
```

## Example Usage

```bash
# Run the main processing script
python src/process_sensor_data.py

# Or with specific input files
python src/process_sensor_data.py --input data/sensor1.xlsx data/sensor2.xlsx data/sensor3.xlsx
```

## Validation Checklist

- [ ] All 3 Excel files processed successfully
- [ ] Two peaks identified for each Co value in each file
- [ ] Baseline calculated at Co = 0
- [ ] DeltaF calculated as (baseline - current)
- [ ] 3 plots generated with proper labels
- [ ] Results saved to output directory
- [ ] Code handles edge cases gracefully
