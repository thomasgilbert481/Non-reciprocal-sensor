# 3-Minute Thesis Presentation Outline

## Non-Reciprocal RF Sensor for Classical and Quantum Sensing Applications

---

## SLIDE 1 — The Problem & Motivation (~40 seconds)

**"Why do we need better sensors?"**

- Many sensing applications (temperature, humidity, pressure, chemical detection) rely on detecting tiny changes in capacitance — a material's electrical property that shifts with environmental conditions.
- Traditional reciprocal RF sensors couple two resonators together and measure how their resonant frequencies split apart as capacitance changes. This works, but the signal travels equally in both directions, which introduces noise, reflections, and limits sensitivity.
- **Key question**: Can we break this symmetry — make the signal travel in only one direction — to build a more sensitive capacitive sensor?
- This matters for **classical sensing** (agriculture: soil moisture/humidity monitoring, environmental temperature tracking) and lays groundwork for **quantum sensing** (where non-reciprocity is essential for protecting fragile quantum states from backaction noise).

---

## SLIDE 2 — What We Did (~50 seconds)

**"Three circuit designs, one experiment"**

- We designed and simulated three coupled-resonator sensor circuits operating in the GHz range (~4-5 GHz), each with two LC tanks and a variable coupling capacitor Co swept from 0 to 1 pF:

  1. **Reciprocal sensor with initial coupling (IC)** — baseline design with a fixed coupling capacitor (Cc = 0.1 pF) always connecting the two resonators.
  2. **Reciprocal sensor without IC** — same topology but no baseline coupling; resonators are fully decoupled at Co = 0.
  3. **Non-reciprocal sensor** — replaces the direct coupling path with a **circulator**, a 3-port device that forces the RF signal to travel in only one direction between resonators.

- For each design, we measured the transmission spectrum (S21) and tracked the two resonant peaks as coupling capacitance increased.
- We computed **|ΔF|** — the change in frequency splitting between the two peaks relative to baseline — as our sensitivity metric.

---

## SLIDE 3 — What We Observed (~50 seconds)

**"The non-reciprocal sensor shows enhanced sensitivity"**

Key results from the summary comparison plot:

- **All three sensors** show a monotonically increasing |ΔF| with capacitance, confirming that coupled-resonator frequency splitting is a viable sensing mechanism. The response spans 0 to ~1.7 GHz over the 0–1 pF range.

- **Reciprocal with IC** (blue curve): Smoothest response, starts responding immediately at Co = 0 due to baseline coupling. Reaches ~1.65 GHz at Co = 1 pF. Very linear and predictable.

- **Reciprocal without IC** (green curve): No response at Co = 0 (resonators decoupled). Closely tracks the "with IC" curve once coupling is established, reaching ~1.73 GHz. Slightly noisier at intermediate values.

- **Non-reciprocal sensor** (orange curve): Delayed onset (peaks not resolvable until Co ≈ 0.08 pF due to merged/shoulder peaks), but then shows a **steeper slope** through the mid-range and achieves the **highest |ΔF| ≈ 1.78 GHz** at Co = 1 pF. The steeper response in the 0.1–0.5 pF region suggests **higher sensitivity** to small capacitance changes in that operating range.

- The non-reciprocal design also exhibited more complex peak behavior (merged/shoulder peaks at low coupling), requiring advanced second-derivative peak detection — a signature of the richer mode structure introduced by the circulator.

---

## SLIDE 4 — What's Next & Implications (~40 seconds)

**"From simulation to real-world impact"**

### Immediate Next Steps
- **Hardware fabrication and measurement**: Validate simulation results with physical prototypes on PCB or integrated circuits.
- **Sensitivity analysis**: Quantify the exact sensitivity advantage (dF/dCo) of non-reciprocal vs. reciprocal designs, especially in the high-slope region.
- **Noise characterization**: Measure whether non-reciprocity reduces backaction noise and improves signal-to-noise ratio as theory predicts.

### Classical Sensing Implications
- A capacitance-to-frequency transduction mechanism with GHz-scale sensitivity opens applications in:
  - **Agriculture**: Soil moisture and humidity sensors (capacitance changes with water content)
  - **Environmental monitoring**: Temperature sensors (dielectric properties shift with temperature)
  - **Industrial**: Pressure and chemical sensors where sub-pF capacitance changes matter
- The non-reciprocal design's enhanced mid-range sensitivity is particularly relevant for these applications, where the capacitance changes of interest are often small.

### Quantum Sensing Implications
- Non-reciprocal devices are critical building blocks in quantum circuits — they protect qubits from measurement backaction and enable directional signal routing.
- This work demonstrates that non-reciprocity can **enhance classical sensor performance**, motivating its use in quantum-limited sensing where the same principles apply at single-photon energy scales.
- A non-reciprocal quantum sensor could achieve sensitivity beyond the standard quantum limit by isolating the sensing element from amplifier noise.

---

## Suggested One-Slide Visual Layout (if limited to 1 slide)

```
+--------------------------------------------------+
|  Title: Non-Reciprocal RF Sensor                  |
|                                                    |
|  [Circuit diagrams]     [Summary plot: ΔF vs Co]  |
|   3 small thumbnails     overlaid comparison       |
|                                                    |
|  Key takeaway:                                     |
|  "Breaking signal symmetry with a circulator       |
|   enhances capacitive sensing sensitivity —        |
|   with applications from agriculture to            |
|   quantum computing."                              |
+--------------------------------------------------+
```

---

## Speaking Notes / Key Phrases

- "Coupled resonators act like tuning forks — when you change the coupling, the frequencies split apart, and we measure that splitting."
- "The circulator acts as a one-way valve for microwave signals."
- "Non-reciprocity isn't just a quantum trick — it measurably improves classical sensor performance."
- "A farmer checking soil moisture and a physicist reading out a qubit are both, fundamentally, measuring a tiny change in capacitance."
