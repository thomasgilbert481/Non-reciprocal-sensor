# Data Directory

## Files

| File | Description |
|------|-------------|
| `Reciprocal Sensor with IC Co sweep (o-1pf).xlsx` | Reciprocal sensor with IC - 2 clear peaks |
| `non reciprocal sensor (0-1) co sweep.xlsx` | Non-reciprocal sensor - may have merged peaks |
| `reciprocal sensor without IC (0-1pf_.xlsx` | Reciprocal without IC - **C0=0 has no data** |

## Data Format

Each Excel file contains a single sheet (`Sheet1`) with:

### Dimensions
- **Rows**: 1991 (frequency points)
- **Columns**: 102 (1 frequency + 101 transmission columns)

### Column Structure

```
Column 1: "Frequency (GHz)"
    - Range: 0.10 to 20.00 GHz
    - Linear spacing (~0.01 GHz steps)

Columns 2-102: "|S(2,1)| : [Sensor Name] (C0 = X )"
    - X ranges from 0 to 1 pF in 0.01 pF steps
    - Values are linear magnitude (NOT dB)
    - Peak values approach 1.0, low transmission ~1e-12
```

### Example Column Names

```
Frequency (GHz)
|S(2,1)| : Reciprocal Sensor (C0 = 0 )
|S(2,1)| : Reciprocal Sensor (C0 = 0.01 )
|S(2,1)| : Reciprocal Sensor (C0 = 0.02 )
...
|S(2,1)| : Reciprocal Sensor (C0 = 1 )
```

## Known Issues

1. **reciprocal sensor without IC**: C0=0 column contains all zeros
   - Use C0=0.01 pF as baseline instead

2. **non reciprocal sensor**: May only show 1 visible peak
   - Peaks might be closely spaced or merged
   - May require adjusted peak detection parameters
