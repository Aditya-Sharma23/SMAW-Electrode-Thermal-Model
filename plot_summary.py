"""Run brain.py for one electrode without opening windows and save a 2x2 summary figure.

Usage: python plot_summary.py [ELECTRODE_ID] [OUTPUT_PNG]
"""
import os
import runpy
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

electrode_id = sys.argv[1] if len(sys.argv) > 1 else "E6013_3.2mm"
out_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join("docs", "summary_E6013.png")

here = os.path.dirname(os.path.abspath(__file__))
os.chdir(here)
sys.argv = ["brain.py", electrode_id]
r = runpy.run_path("brain.py", run_name="__main__")
plt.close("all")

t = r["time_axis"]
fig, ax = plt.subplots(2, 2, figsize=(11, 7.5))
fig.suptitle(f"Open-loop simulation: {r['db']['name']}, I = {r['I0']:.0f} ± {r['delta_I']:.0f} A", fontsize=13)

ax[0, 0].plot(t, r["temperature_axis"], color="darkorange", lw=2)
ax[0, 0].set(title="Mean electrode temperature", xlabel="Time (s)", ylabel="Temperature (°C)")

ax[0, 1].plot(t, [x * 1000 for x in r["resistance_axis"]], color="teal", lw=2)
ax[0, 1].set(title="Total electrode resistance", xlabel="Time (s)", ylabel="Resistance (mΩ)")

ax[1, 0].plot(t, r["voltage_total_axis"], color="black", lw=2, label="Total")
ax[1, 0].plot(t, r["voltage_hot_axis"], color="red", lw=1.8, ls="--", label="Hot region")
ax[1, 0].plot(t, r["voltage_cold_axis"], color="blue", lw=1.8, ls=":", label="Cold region")
ax[1, 0].set(title="Voltage drop along the electrode", xlabel="Time (s)", ylabel="Voltage (V)")
ax[1, 0].legend()

ax[1, 1].plot(t, [x * 1000 for x in r["length_axis"]], color="green", lw=2)
ax[1, 1].set(title="Remaining electrode length", xlabel="Time (s)", ylabel="Length (mm)")

for a in ax.flat:
    a.grid(True, alpha=0.4)
fig.tight_layout()
os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
fig.savefig(out_path, dpi=130)
print(f"Saved {out_path}")
