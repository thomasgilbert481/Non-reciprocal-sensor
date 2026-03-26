# Handoff: Amp Circuit Log-Log Plot

## Branch
`claude/recreate-figure-2b-K4adf` on repo `thomasgilbert481/Non-reciprocal-sensor`

## What Was Being Done
User added a new Excel file to `data/` named:
```
Amp circ Csensing sweep (0-1600pf).xlsx
```
The file did **not** sync to the environment. The user pasted the raw data in chat.
**Ask the user to re-upload the file OR paste the data again** — it is tab-separated and starts with:
```
Frequency (GHz)	|S(2,1)| : Linear Amp circ (Csensing = 100 )  ...  (Csensing = 1600 )
0.005   0.00643408  ...
...
0.04    0.0719211   ...
```
- 351 frequency rows: 0.005 → 0.04 GHz (step 0.0001 GHz = 0.1 MHz)
- 16 Csensing columns: 100, 200, 300, … 1600 pF

## Task
Create a **log-log plot** of frequency splitting Δf vs Csensing and **label the fitted slope**.

## Key Observations About the Data
- Each trace has **two peaks** in the 5–40 MHz range
- Near **Csensing ≈ 500 pF**, the peak amplitude is enormous (>4.7) — this is near the **exceptional point (EP)** where gain ≈ loss
- For Csensing=100: peaks near ~20 MHz and ~30 MHz → Δf ≈ 10 MHz
- For Csensing=1600: peaks near ~16.8 MHz and ~22.8 MHz → Δf ≈ 6 MHz
- Δf appears to **decrease** as Csensing increases → expect a **negative slope** on the log-log plot

## Existing Reference Script
`src/ep_circuit_analysis.py` — already does this exact analysis for `data/paper Csensing sweep (100-1600pf).xlsx`.
Use it as the template. Key differences for the new file:

| Parameter | paper file | Amp circ file |
|---|---|---|
| Column pattern | `Csensing = \d+` | `Csensing = \d+` (same) |
| Freq units | GHz × 1000 → MHz | GHz × 1000 → MHz (same) |
| Freq range for peaks | (10, 30) MHz | (5, 40) MHz |
| C1_PF (if using ε) | 3200.0 | Unknown — just use Csensing (pF) directly on x-axis |
| Theory curve | Δf = 2√(κε)·f₀ | Skip or TBD |

## Steps to Complete
1. Save the pasted data as `data/Amp circ Csensing sweep (0-1600pf).xlsx` (use pandas + openpyxl or write a TSV)
2. Write `src/amp_circ_analysis.py` modeled on `src/ep_circuit_analysis.py`
3. For each Csensing, find two peaks → compute Δf = f₊ − f₋
4. Log-log plot: x = Csensing (pF), y = Δf (MHz); fit line; annotate slope
5. Save output to `output/amp_circ_loglog.png`
6. Commit + push to `claude/recreate-figure-2b-K4adf`

## Invoke the Skill
Use `/perturbation-graph` to get step-by-step guidance on writing the script.
