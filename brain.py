import numpy as np
import matplotlib.pyplot as plt
import sqlite3
import numpy as np
import matplotlib.pyplot as plt

# =====================================================================
# 1. SELECT ELECTRODE & FETCH PROPERTIES DIRECTLY FROM SQL DATABASE
# =====================================================================
import sys

if len(sys.argv) > 1:
    selected_id = sys.argv[1]
else:
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM electrodes")
    records = cursor.fetchall()
    print("\n==================================================")
    print(" SELECT SMAW ELECTRODE FROM DATABASE ")
    print("==================================================")
    for idx, row in enumerate(records, 1):
        print(f" [{idx}] {row['name']} ({row['id']})")
    print("==================================================")
    try:
        choice = int(input("Enter Selection (1-5): ")) - 1
        selected_id = records[choice]['id']
    except (ValueError, IndexError):
        selected_id = "E6013_3.2mm"
    conn.close()

conn = sqlite3.connect("database.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("SELECT * FROM electrodes WHERE id = ?", (selected_id,))
db = cursor.fetchone()
conn.close()

# DIRECT ASSIGNMENT FROM DATABASE COLUMNS (NO Python-level hardcoding!)
I0              = db['i0']
delta_I         = db['delta_i']
frequency       = db['frequency']
V_arc           = db['v_arc']
eta_arc         = db['eta_arc']
eta_m           = db['eta_m']

L_initial       = db['l_initial']
Diameter        = db['diameter']
Area            = np.pi * (Diameter / 2)**2
Perimeter       = np.pi * Diameter

Density         = db['density']
Cp0             = db['cp0']
Cp_temp_coeff   = db['cp_temp_coeff']
Resistivity_0   = db['resistivity_0']
Alpha           = db['alpha']
k0              = db['k0']
Beta_k          = db['beta_k']
Lf              = db['lf']
flux_mass_factor= db['flux_mass_factor']

h_conv          = db['h_conv']
emissivity_0    = db['emissivity_0']
sigma           = 5.67e-8

T_ambient       = db['t_ambient']
T_melt          = db['t_melt']
delta_T_melt    = db['delta_t_melt']

# METALLURGICAL LIMITS FOR CONTROLLER
T_warning       = db['t_warning']
T_critical      = db['t_critical']
T_plastic      = db['t_plastic']
I_floor         = db['i_floor']

print(f"\n[BRAIN] Loaded '{db['name']}' successfully from database.db!")

# =====================================================================
# 6. NUMERICAL PARAMETERS
# =====================================================================

t_max = 60.0

num_segments = 150

# =====================================================================
# 7. INITIALIZATION
# =====================================================================

T_segments = np.full(
    num_segments,
    T_ambient
)

current_L = L_initial

t = 0.0

# =====================================================================
# 8. STORAGE ARRAYS
# =====================================================================

time_axis = []

voltage_total_axis = []
voltage_hot_axis = []
voltage_cold_axis = []

resistance_axis = []
temperature_axis = []

power_axis = []

length_axis = []
melting_rate_axis = []

# =====================================================================
# 9. TRANSIENT SIMULATION LOOP
# =====================================================================

while t <= t_max and current_L > 0.04:

    # -----------------------------------------------------------------
    # SPATIAL DISCRETIZATION
    # -----------------------------------------------------------------

    dx = current_L / num_segments

    dx_safe = max(dx, 1e-5)

    # -----------------------------------------------------------------
    # STABILITY CRITERION
    # -----------------------------------------------------------------

    dt_stable = (
        Density *
        Cp0 *
        (dx_safe**2)
    ) / (
        2.0 * k0
    )

    dt = min(
        0.2 * dt_stable,
        0.01
    )

    # -----------------------------------------------------------------
    # PULSED CURRENT
    # -----------------------------------------------------------------

    I = I0 + delta_I * np.sin(
        2 * np.pi * frequency * t
    )

    # -----------------------------------------------------------------
    # DYNAMIC MELTING MODEL
    # -----------------------------------------------------------------

    melting_rate_L = (
        eta_arc *
        eta_m *
        V_arc *
        I
    ) / (
        Density *
        Area *
        (
            Cp0 *
            (T_melt - T_ambient)
            + Lf
        )
    )

    dL = melting_rate_L * dt

    current_L -= dL

    # -----------------------------------------------------------------
    # SEGMENT MASS
    # -----------------------------------------------------------------

    mass_segment = (
        Density *
        Area *
        dx_safe
    ) * flux_mass_factor

    # -----------------------------------------------------------------
    # RESISTANCE INITIALIZATION
    # -----------------------------------------------------------------

    local_dR = np.zeros(
        num_segments
    )

    R_hot = 0.0
    R_cold = 0.0

    T_old = T_segments.copy()

    # =================================================================
    # PASS 1 : ELECTRICAL STATE EVALUATION
    # =================================================================

    for i in range(num_segments):

        # -------------------------------------------------------------
        # TEMPERATURE-DEPENDENT RESISTIVITY
        # -------------------------------------------------------------

        rho_local = (
            Resistivity_0 *
            (
                1 +
                Alpha *
                (
                    T_old[i]
                    - T_ambient
                )
            )
        )

        local_dR[i] = (
            rho_local *
            dx_safe
        ) / Area

        # -------------------------------------------------------------
        # IMPROVED HOT/COLD CLASSIFICATION
        # -------------------------------------------------------------

        hot_fraction = (
            T_old[i] - 200.0
        ) / (
            T_melt - 200.0
        )

        hot_fraction = np.clip(
            hot_fraction,
            0.0,
            1.0
        )

        cold_fraction = 1.0 - hot_fraction

        R_hot += (
            local_dR[i] *
            hot_fraction
        )

        R_cold += (
            local_dR[i] *
            cold_fraction
        )

    # =================================================================
    # PASS 2 : THERMAL FINITE DIFFERENCE UPDATE
    # =================================================================

    for i in range(num_segments):

        # -------------------------------------------------------------
        # TEMPERATURE-DEPENDENT SPECIFIC HEAT
        # -------------------------------------------------------------

        Cp_local = (
            Cp0 *
            (
                1 +
                Cp_temp_coeff *
                (
                    T_old[i]
                    - T_ambient
                )
            )
        )

        Cp_local = min(
            Cp_local,
            900
        )

        # -------------------------------------------------------------
        # EFFECTIVE HEAT CAPACITY METHOD
        # -------------------------------------------------------------

        if abs(
            T_old[i] - T_melt
        ) <= delta_T_melt:

            Cp_local += (
                Lf /
                (
                    2.0 *
                    delta_T_melt
                )
            )

        # -------------------------------------------------------------
        # TEMPERATURE-DEPENDENT CONDUCTIVITY
        # -------------------------------------------------------------

        k_local = (
            k0 *
            (
                1 -
                Beta_k *
                (
                    T_old[i]
                    - T_ambient
                )
            )
        )

        k_local = max(
            k_local,
            15.0
        )

        # -------------------------------------------------------------
        # TEMPERATURE-DEPENDENT EMISSIVITY
        # -------------------------------------------------------------

        emissivity = min(
            0.95,
            emissivity_0 +
            0.00005 *
            (
                T_old[i]
                - T_ambient
            )
        )

        # -------------------------------------------------------------
        # JOULE HEATING
        # -------------------------------------------------------------

        Q_joule = (
            I**2
        ) * local_dR[i]

        # -------------------------------------------------------------
        # DISTRIBUTED ARC HEATING
        # -------------------------------------------------------------

        Q_arc = 0.0

        n_arc = max(3, int(num_segments * 0.05))
        arc_weights = np.linspace(1, 5, n_arc, dtype=float)
        arc_weights = arc_weights / np.sum(arc_weights)

        if i >= num_segments - n_arc:
            local_index = i - (num_segments - n_arc)

            Q_arc = (
                eta_arc *
                V_arc *
                I *
                arc_weights[local_index]
            )

        # Enthalpy carried away by detached molten droplets at the tip
        Q_droplet = 0.0
        if i == num_segments - 1:
            mass_loss_rate = Density * Area * melting_rate_L
            Q_droplet = mass_loss_rate * (Cp_local * (T_old[i] - T_ambient) + Lf)

        # -------------------------------------------------------------
        # HEAT CONDUCTION
        # -------------------------------------------------------------

        if i == 0:

            holder_temperature = 40.0

            Q_conduction = (
                (
                    k_local *
                    Area
                ) / dx_safe
            ) * (
                T_old[i+1]
                - 2*T_old[i]
                + holder_temperature
            )

        elif i == num_segments - 1:

            Q_conduction = (
                k_local *
                Area *
                (
                    T_old[i-1]
                    - T_old[i]
                )
            ) / dx_safe

        else:

            Q_conduction = (
                k_local *
                Area *
                (
                    T_old[i+1]
                    - 2*T_old[i]
                    + T_old[i-1]
                )
            ) / dx_safe

        # -------------------------------------------------------------
        # CONVECTIVE COOLING
        # -------------------------------------------------------------

        Q_convection = (
            h_conv *
            Perimeter *
            dx_safe *
            (
                T_old[i]
                - T_ambient
            )
        )

        # -------------------------------------------------------------
        # RADIATIVE COOLING
        # -------------------------------------------------------------

        T_kelvin = (
            T_old[i]
            + 273.15
        )

        T_ambient_kelvin = (
            T_ambient
            + 273.15
        )

        Q_radiation = (
            emissivity *
            sigma *
            Perimeter *
            dx_safe *
            (
                T_kelvin**4
                - T_ambient_kelvin**4
            )
        )

        # -------------------------------------------------------------
        # TOTAL ENERGY BALANCE
        # -------------------------------------------------------------

        Net_Heat = (
            Q_joule
            + Q_arc
            - Q_droplet
            + Q_conduction
            - Q_convection
            - Q_radiation
        )

        # -------------------------------------------------------------
        # TEMPERATURE UPDATE
        # -------------------------------------------------------------

        dT = (
            Net_Heat *
            dt
        ) / (
            mass_segment *
            Cp_local
        )

        T_segments[i] += dT

        # -------------------------------------------------------------
        # TEMPERATURE LIMIT
        # -------------------------------------------------------------

        if i >= num_segments - 3:

            if T_segments[i] > (
                T_melt +
                delta_T_melt
            ):

                T_segments[i] = (
                    T_melt +
                    delta_T_melt
                )

    # =================================================================
    # GLOBAL ELECTRICAL VALUES
    # =================================================================

    R_total = R_hot + R_cold

    V_total = I * R_total

    V_hot = I * R_hot
    V_cold = I * R_cold

    P_total = I * (
        V_arc + V_total
    )

    # =================================================================
    # SAVE ARRAYS
    # =================================================================

    time_axis.append(t)

    voltage_total_axis.append(V_total)

    voltage_hot_axis.append(V_hot)

    voltage_cold_axis.append(V_cold)

    resistance_axis.append(R_total)

    temperature_axis.append(
        np.mean(T_segments)
    )

    power_axis.append(P_total)

    length_axis.append(current_L)

    melting_rate_axis.append(
        melting_rate_L
    )

    # -----------------------------------------------------------------
    # TIME UPDATE
    # -----------------------------------------------------------------

    t = round(t + dt, 6)

# =====================================================================
# 10. VISUALIZATION
# =====================================================================

# ---------------------------------------------------------------------
# VOLTAGE BREAKDOWN
# ---------------------------------------------------------------------

plt.figure(figsize=(10,6))

plt.plot(
    time_axis,
    voltage_total_axis,
    linewidth=3,
    color='black',
    label='Total Voltage'
)

plt.plot(
    time_axis,
    voltage_cold_axis,
    linewidth=2.5,
    linestyle=':',
    color='blue',
    label='Cold Region Voltage'
)

plt.plot(
    time_axis,
    voltage_hot_axis,
    linewidth=2.5,
    linestyle='--',
    color='red',
    label='Hot Region Voltage'
)

plt.xlabel('Welding Time (s)')
plt.ylabel('Voltage Drop (V)')

plt.title(
    'Voltage Contribution of Hot and Cold Regions'
)

plt.grid(True)

plt.legend()

# ---------------------------------------------------------------------
# RESISTANCE EVOLUTION
# ---------------------------------------------------------------------

plt.figure(figsize=(10,6))

plt.plot(
    time_axis,
    resistance_axis,
    linewidth=2.5,
    color='teal'
)

plt.xlabel('Time (s)')
plt.ylabel('Resistance (Ohm)')

plt.title(
    'Total Resistance Evolution'
)

plt.grid(True)

# ---------------------------------------------------------------------
# TEMPERATURE EVOLUTION
# ---------------------------------------------------------------------

plt.figure(figsize=(10,6))

plt.plot(
    time_axis,
    temperature_axis,
    linewidth=2.5,
    color='darkorange'
)

plt.xlabel('Time (s)')
plt.ylabel('Average Temperature (°C)')

plt.title(
    'Average Electrode Temperature'
)

plt.grid(True)

# ---------------------------------------------------------------------
# POWER EVOLUTION
# ---------------------------------------------------------------------

plt.figure(figsize=(10,6))

plt.plot(
    time_axis,
    power_axis,
    linewidth=2.5,
    color='purple'
)

plt.xlabel('Time (s)')
plt.ylabel('Power (W)')

plt.title(
    'Transient Welding Power'
)

plt.grid(True)

# ---------------------------------------------------------------------
# ELECTRODE LENGTH EVOLUTION
# ---------------------------------------------------------------------

plt.figure(figsize=(10,6))

plt.plot(
    time_axis,
    length_axis,
    linewidth=2.5,
    color='green'
)

plt.xlabel('Time (s)')
plt.ylabel('Electrode Length (m)')

plt.title(
    'Dynamic Electrode Consumption'
)

plt.grid(True)

# ---------------------------------------------------------------------
# MELTING RATE EVOLUTION
# ---------------------------------------------------------------------

plt.figure(figsize=(10,6))

plt.plot(
    time_axis,
    melting_rate_axis,
    linewidth=2.5,
    color='red'
)

plt.xlabel('Time (s)')
plt.ylabel('Melting Rate (m/s)')

plt.title(
    'Dynamic Melting Rate'
)

plt.grid(True)

# =====================================================================
# AVERAGE MELTING / BURN-OFF / DEPOSITION INFORMATION
# =====================================================================

average_melting_rate = np.mean(
    melting_rate_axis
)

# -------------------------------------------------------------
# MASS LOSS RATE
# -------------------------------------------------------------

average_mass_loss_rate = (
    Density *
    Area *
    average_melting_rate
) * 1000.0

# -------------------------------------------------------------
# DEPOSITION RATE
# -------------------------------------------------------------

deposition_efficiency = 0.75

deposition_rate = (
    average_mass_loss_rate *
    deposition_efficiency
)

# -------------------------------------------------------------
# PRINT RESULTS
# -------------------------------------------------------------

print("\n======================================")
print("AVERAGE WELDING PARAMETERS")
print("======================================")

print(
    f"Average Melting Rate      : "
    f"{average_melting_rate:.8e} m/s"
)

print(
    f"Average Mass Loss Rate    : "
    f"{average_mass_loss_rate:.6f} g/s"
)

print(
    f"Average Deposition Rate   : "
    f"{deposition_rate:.6f} g/s"
)

print("======================================")

plt.show()
print("======================================")
# =====================================================================
# SAVE DYNAMIC SQL PROFILE FOR CONTROLLER
# =====================================================================
import json

brain_profile = {
    "electrode_type": db['name'],
    "base_current": I0,
    "min_allowable_current": I_floor,
    "T_warning": T_warning,
    "T_critical": T_critical,
    "T_plastic": T_plastic,
    "total_burn_time": float(time_axis[-1]),
    "temperature_profile": [float(t) for t in temperature_axis]
}

with open("current_profile.json", "w") as f:
    json.dump(brain_profile, f, indent=4)

print(f"\n[BRAIN] Thermal profile for '{db['name']}' exported to current_profile.json")

plt.show(block=False)
plt.pause(1)
# =====================================================================
# FUNCTION TO RENDER ALL PREDICTION PLOTS
# =====================================================================
def plot_predictions():
    # 1. Voltage Breakdown
    plt.figure(figsize=(10, 6))
    plt.plot(time_axis, voltage_total_axis, linewidth=3, color='black', label='Total Voltage')
    plt.plot(time_axis, voltage_cold_axis, linewidth=2.5, linestyle=':', color='blue', label='Cold Region Voltage')
    plt.plot(time_axis, voltage_hot_axis, linewidth=2.5, linestyle='--', color='red', label='Hot Region Voltage')
    plt.xlabel('Welding Time (s)')
    plt.ylabel('Voltage Drop (V)')
    plt.title('Voltage Contribution of Hot and Cold Regions')
    plt.grid(True)
    plt.legend()

    # 2. Resistance Evolution
    plt.figure(figsize=(10, 6))
    plt.plot(time_axis, resistance_axis, linewidth=2.5, color='teal')
    plt.xlabel('Time (s)')
    plt.ylabel('Resistance (Ohm)')
    plt.title('Total Resistance Evolution')
    plt.grid(True)

    # 3. Temperature Evolution
    plt.figure(figsize=(10, 6))
    plt.plot(time_axis, temperature_axis, linewidth=2.5, color='darkorange')
    plt.xlabel('Time (s)')
    plt.ylabel('Average Temperature (°C)')
    plt.title('Average Electrode Temperature')
    plt.grid(True)

    # 4. Power Evolution
    plt.figure(figsize=(10, 6))
    plt.plot(time_axis, power_axis, linewidth=2.5, color='purple')
    plt.xlabel('Time (s)')
    plt.ylabel('Power (W)')
    plt.title('Transient Welding Power')
    plt.grid(True)

    # 5. Length Evolution
    plt.figure(figsize=(10, 6))
    plt.plot(time_axis, length_axis, linewidth=2.5, color='green')
    plt.xlabel('Time (s)')
    plt.ylabel('Electrode Length (m)')
    plt.title('Dynamic Electrode Consumption')
    plt.grid(True)

    # 6. Melting Rate Evolution
    plt.figure(figsize=(10, 6))
    plt.plot(time_axis, melting_rate_axis, linewidth=2.5, color='red')
    plt.xlabel('Time (s)')
    plt.ylabel('Melting Rate (m/s)')
    plt.title('Dynamic Melting Rate')
    plt.grid(True)

    plt.show()
