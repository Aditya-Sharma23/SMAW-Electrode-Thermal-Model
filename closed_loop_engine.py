import numpy as np
import sqlite3

class ClosedLoopEngine:
    def __init__(self, selected_id):
        # Fetch electrode properties from database
        conn = sqlite3.connect("database.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM electrodes WHERE id = ?", (selected_id,))
        db = cursor.fetchone()
        conn.close()

        if db is None:
            raise ValueError(f"Electrode '{selected_id}' not found in database!")

        # Physical Properties
        self.name = db['name']
        self.I0 = db['i0']
        self.V_arc = db['v_arc']
        self.eta_arc = db['eta_arc']
        self.eta_m = db['eta_m']
        self.L_initial = db['l_initial']
        self.current_L = db['l_initial']
        self.Diameter = db['diameter']
        self.Area = np.pi * (self.Diameter / 2)**2
        self.Perimeter = np.pi * self.Diameter

        self.Density = db['density']
        self.Cp0 = db['cp0']
        self.Cp_temp_coeff = db['cp_temp_coeff']
        self.Resistivity_0 = db['resistivity_0']
        self.Alpha = db['alpha']
        self.k0 = db['k0']
        self.Beta_k = db['beta_k']
        self.Lf = db['lf']
        self.flux_mass_factor = db['flux_mass_factor']

        self.h_conv = db['h_conv']
        self.emissivity_0 = db['emissivity_0']
        self.sigma = 5.67e-8

        self.T_ambient = db['t_ambient']
        self.T_melt = db['t_melt']
        self.delta_T_melt = db['delta_t_melt']

        # Controller Boundaries
        self.T_warning = db['t_warning']
        self.T_critical = db['t_critical']
        self.T_plastic = db['t_plastic']
        self.I_floor = db['i_floor']

        # Discretization
        self.num_segments = 150
        self.T_segments = np.full(self.num_segments, self.T_ambient)

    def step(self, I_commanded, dt_requested):
        """
        Sub-steps internally using FTCS stability logic so that shorter rod 
        lengths do not cause numerical blowups or negative temperatures.
        """
        t_accumulated = 0.0

        while t_accumulated < dt_requested:
            dx_safe = max(self.current_L / self.num_segments, 1e-5)

            # Re-calculate strict Von Neumann stability limit
            dt_stable = (self.Density * self.Cp0 * (dx_safe**2)) / (2.0 * self.k0)
            dt = min(0.2 * dt_stable, 0.01, dt_requested - t_accumulated)

            # Dynamic Melting Model
            melting_rate_L = (self.eta_arc * self.eta_m * self.V_arc * I_commanded) / (
                self.Density * self.Area * (self.Cp0 * (self.T_melt - self.T_ambient) + self.Lf)
            )
            self.current_L -= melting_rate_L * dt
            mass_segment = (self.Density * self.Area * dx_safe) * self.flux_mass_factor

            # Electrical State
            local_dR = np.zeros(self.num_segments)
            T_old = self.T_segments.copy()

            for i in range(self.num_segments):
                rho_local = self.Resistivity_0 * (1 + self.Alpha * (T_old[i] - self.T_ambient))
                local_dR[i] = (rho_local * dx_safe) / self.Area

            # Thermal Finite Difference Update
            for i in range(self.num_segments):
                Cp_local = min(self.Cp0 * (1 + self.Cp_temp_coeff * (T_old[i] - self.T_ambient)), 900)
                if abs(T_old[i] - self.T_melt) <= self.delta_T_melt:
                    Cp_local += self.Lf / (2.0 * self.delta_T_melt)

                k_local = max(self.k0 * (1 - self.Beta_k * (T_old[i] - self.T_ambient)), 15.0)
                emissivity = min(0.95, self.emissivity_0 + 0.00005 * (T_old[i] - self.T_ambient))

                # Heat Terms
                Q_joule = (I_commanded**2) * local_dR[i]

                n_arc = max(3, int(self.num_segments * 0.05))
                arc_weights = np.linspace(1, 5, n_arc, dtype=float)
                arc_weights /= np.sum(arc_weights)
                Q_arc = self.eta_arc * self.V_arc * I_commanded * arc_weights[i - (self.num_segments - n_arc)] if i >= self.num_segments - n_arc else 0.0

                Q_droplet = (self.Density * self.Area * melting_rate_L * (Cp_local * (T_old[i] - self.T_ambient) + self.Lf)) if i == self.num_segments - 1 else 0.0

                # Heat Conduction
                if i == 0:
                    Q_conduction = ((k_local * self.Area) / dx_safe) * (T_old[i+1] - 2*T_old[i] + 40.0)
                elif i == self.num_segments - 1:
                    Q_conduction = (k_local * self.Area * (T_old[i-1] - T_old[i])) / dx_safe
                else:
                    Q_conduction = (k_local * self.Area * (T_old[i+1] - 2*T_old[i] + T_old[i-1])) / dx_safe

                # Cooling
                Q_convection = self.h_conv * self.Perimeter * dx_safe * (T_old[i] - self.T_ambient)
                
                # Protect Kelvin values against scalar underflow
                T_k = max(0.0, T_old[i] + 273.15)
                T_amb_k = self.T_ambient + 273.15
                Q_radiation = emissivity * self.sigma * self.Perimeter * dx_safe * (T_k**4 - T_amb_k**4)

                Net_Heat = Q_joule + Q_arc - Q_droplet + Q_conduction - Q_convection - Q_radiation
                dT = (Net_Heat * dt) / (mass_segment * Cp_local)
                self.T_segments[i] += dT

                if i >= self.num_segments - 3 and self.T_segments[i] > (self.T_melt + self.delta_T_melt):
                    self.T_segments[i] = self.T_melt + self.delta_T_melt

            t_accumulated += dt

        return float(np.mean(self.T_segments)), self.current_L
