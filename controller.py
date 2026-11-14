import time
import sqlite3
import subprocess
import sys
import setup_database
from closed_loop_engine import ClosedLoopEngine

# Ensure Database Exists
def ensure_database():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='electrodes'")
    if not cursor.fetchone():
        setup_database.build_welding_database()
    conn.close()

ensure_database()

# Select Electrode
conn = sqlite3.connect("database.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("SELECT id, name FROM electrodes")
records = cursor.fetchall()
conn.close()

print("\n==================================================")
print("=== CLOSED-LOOP SMART WELDING CONTROLLER ===")
print("==================================================")
for idx, row in enumerate(records, 1):
    print(f" [{idx}] {row['name']} ({row['id']})")
print("==================================================")

try:
    choice = int(input("Select Electrode (1-5): ")) - 1
    selected_id = records[choice]['id']
except (ValueError, IndexError):
    selected_id = "E6013_3.2mm"

# Initialize Physics Engine
engine = ClosedLoopEngine(selected_id)
current_I = engine.I0

print(f"\n=== CLOSED LOOP ENGINE ACTIVE [{engine.name}] ===")
print(f"Initial Amperage   : {current_I} A")
print(f"Safe Current Floor : {engine.I_floor} A\n")

sim_time = 0.0
dt = 0.1

try:
    while engine.current_L > 0.04:
        core_temp, remaining_length = engine.step(current_I, dt)
        sim_time += dt

        if core_temp >= engine.T_plastic:
            current_I = max(engine.I_floor, current_I - 2.0)
            status = "EMERGENCY"
        elif core_temp >= engine.T_critical:
            current_I = max(engine.I_floor, current_I - 1.0)
            status = "BENDING RISK"
        elif core_temp >= engine.T_warning:
            current_I = max(engine.I_floor, current_I - 0.2)
            status = "WARNING"
        else:
            status = "OPTIMAL"

        print(f"[{sim_time:.2f}s] Temp: {core_temp:.1f}°C | Status: {status} | Current: {current_I:.1f} A | Rod: {remaining_length:.3f}m")

    print(f"\n[{sim_time:.2f}s] ARC EXTINGUISHED: Electrode consumed.")

except KeyboardInterrupt:
    print("\n[CONTROLLER] Terminated by user.")

# CALL BRAIN PREDICTION PLOTS AT THE VERY END
print("\n[CONTROLLER] Generating Brain prediction plots...")
subprocess.run([sys.executable, "brain.py", selected_id])
