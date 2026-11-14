# Thermo-Electrical Model of SMAW Electrodes

A transient 1D thermo-electrical simulation of a shielded metal arc welding (SMAW) electrode. It predicts how the core wire heats up, how its electrical resistance rises during a weld, how fast the electrode burns off, and when the rod risks overheating ("red electrode"). A simulated closed-loop controller uses the model to lower the welding current before the rod overheats.

This code accompanies the paper:

> **Thermo-Electrical Modelling of Net Resistance Change in SMAW Electrodes: A Pathway to Current Optimization and Elimination of Red Electrode**
> Aditya Sharma, Sunil Pandey, Manoj Kumar, Department of Mechanical-Mechatronics Engineering, LNMIIT Jaipur
> Accepted at the ISME Conference 2026, IIT Guwahati (27–31 December 2026)

## The problem

During manual arc welding, a high current flows through the electrode's core wire for tens of seconds. Joule heating (I²R) raises the wire temperature, and resistivity rises with temperature, so the heating feeds itself. The rod can glow red, the flux coating degrades, and the gas shield protecting the weld weakens. This model tracks that feedback over time and tests whether actively lowering the current can stop it.

## What the model includes

The electrode is divided into **150 segments** along its length. Each time step updates the temperature of every segment with an explicit (FTCS) finite-difference energy balance:

| Term | How it is modelled |
|---|---|
| Joule heating | I² · R of each segment, with resistivity ρ(T) = ρ₀[1 + α(T − T₀)] |
| Arc heating | η_arc · V_arc · I, spread over the last 5% of segments at the tip with increasing weights |
| Conduction | Axial conduction with k(T) = k₀[1 − β(T − T₀)]. The holder end is held at 40 °C |
| Convection | h · perimeter · Δx · (T − T_ambient) |
| Radiation | ε(T) · σ · perimeter · Δx · (T⁴ − T_ambient⁴), with emissivity rising with temperature |
| Droplet enthalpy loss | Energy carried away by molten droplets leaving the tip |
| Melting / phase change | Effective heat-capacity method around the melting point |
| Burn-off | Electrode length shrinks at a melting rate set by arc power and the energy needed to melt the metal |
| Flux coating | Represented through a flux mass factor on each segment's heat capacity |

Other details:
- Specific heat, conductivity and emissivity all depend on temperature.
- The time step is chosen from the explicit stability limit, dt ≤ ρ·c_p·Δx² / (2k), using 20% of that limit and never more than 10 ms. It is recalculated every step because Δx shrinks as the rod burns.
- The open-loop run uses a pulsed current I(t) = I₀ + ΔI · sin(2πft).
- The resistance is split into a "hot" and a "cold" part, so the voltage drop across each region can be tracked separately.

## Electrode database

Material and process parameters are stored in `database.db` (SQLite), not hard-coded. Five electrodes are included, all 3.2 mm:

| ID | Electrode | Coating |
|---|---|---|
| `E6013_3.2mm` | E6013 carbon steel | Rutile |
| `E7018_3.2mm` | E7018 low-hydrogen structural | Basic / iron powder |
| `E6010_3.2mm` | E6010 pipe grade | Cellulosic |
| `E308L_3.2mm` | E308L stainless steel | Rutile-titanium |
| `ENi-CI_3.2mm` | ENi-CI nickel, cast-iron repair | Graphite basic |

Each entry holds the geometry, the nominal current and the minimum allowed current, the arc voltage and efficiencies, the thermal and electrical properties with their temperature coefficients, the melting data, and three controller thresholds (warning, critical and plastic temperature). To add an electrode, add a row in `setup_database.py` and run it again.

## Files

| File | Purpose |
|---|---|
| `brain.py` | Open-loop simulation. Runs one electrode, prints average melting, mass-loss and deposition rates, plots the results, and exports `current_profile.json` |
| `closed_loop_engine.py` | The same physics wrapped as a class (`ClosedLoopEngine`) that can be stepped with any commanded current. It sub-steps internally to stay stable |
| `controller.py` | Closed-loop current controller. Steps the engine every 0.1 s and lowers the current as the mean rod temperature crosses each threshold |
| `setup_database.py` | Creates or refreshes `database.db` with the five electrodes |
| `current_profile.json` | Example output from `brain.py` (temperature history for E6013) |

## Closed-loop control logic

Every 0.1 s of simulated time, `controller.py` reads the mean electrode temperature and adjusts the current. The current never goes below the electrode's minimum allowed value (`i_floor`):

| Mean temperature | Status | Current change per step |
|---|---|---|
| below T_warning | OPTIMAL | none |
| ≥ T_warning | WARNING | −0.2 A |
| ≥ T_critical | BENDING RISK | −1.0 A |
| ≥ T_plastic | EMERGENCY | −2.0 A |

## Running it

Requires Python 3.10 or newer.

```bash
pip install -r requirements.txt
```

Open-loop simulation (asks you to pick an electrode, or pass its ID):

```bash
python brain.py E6013_3.2mm
```

Closed-loop controller (runs the controlled weld, then opens the open-loop plots for comparison):

```bash
python controller.py
```

Rebuild the electrode database:

```bash
python setup_database.py
```

`brain.py` produces six plots: hot/cold voltage breakdown, total resistance, mean electrode temperature, welding power, remaining electrode length and melting rate.

## Validation status and limitations

- The model's burn-off output was calibrated against and compared with manufacturer datasheet burn-off data.
- **It has not yet been validated against laboratory measurements.** Physical welding trials with temperature and voltage measurement are planned.
- It is a 1D model: temperature varies along the rod only, not across its radius, and the core wire and flux coating are not modelled as separate layers.
- The holder-end temperature (40 °C), the arc heat distribution at the tip and several property coefficients are assumptions taken from typical values, listed in `setup_database.py`.
- The controller is a simple threshold rule acting on the mean rod temperature. It is a proof of concept, not a tuned controller.

## Author

Aditya Sharma, B.Tech. Mechanical Engineering, LNMIIT Jaipur. GitHub: [Aditya-Sharma23](https://github.com/Aditya-Sharma23)
