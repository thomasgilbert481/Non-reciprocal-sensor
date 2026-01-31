# Data Directory

Place your Excel sensor data files here:

- `sensor1.xlsx` (or your actual filename)
- `sensor2.xlsx` (or your actual filename)
- `sensor3.xlsx` (or your actual filename)

## Expected Data Format

Each Excel file should contain transmission spectrum data with:

1. **Frequency column**: The x-axis data (GHz or MHz)
2. **Transmission column**: The y-axis data (typically in dB)
3. **Co parameter**: Capacitance values from 0 to 1 pF

### Common Data Organizations

**Format A: Multiple Sheets**
- Each sheet represents a different Co value
- Sheet names could be: "Co=0", "Co=0.1", etc.

**Format B: Column Pairs**
- Single sheet with multiple column pairs
- Example: `Freq_0pF`, `Trans_0pF`, `Freq_0.1pF`, `Trans_0.1pF`, ...

**Format C: Stacked Data**
- Single sheet with Frequency, Transmission, and Co columns
- Each row includes the Co value for that measurement

The processing script will inspect and adapt to your specific format.
