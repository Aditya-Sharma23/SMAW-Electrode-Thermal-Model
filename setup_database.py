import sqlite3

def build_welding_database():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Create master schema
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS electrodes (
        id TEXT PRIMARY KEY,
        name TEXT,
        type TEXT,
        diameter REAL,
        l_initial REAL,
        i0 REAL,
        i_floor REAL,
        delta_i REAL,
        frequency REAL,
        v_arc REAL,
        eta_arc REAL,
        eta_m REAL,
        density REAL,
        cp0 REAL,
        cp_temp_coeff REAL,
        resistivity_0 REAL,
        alpha REAL,
        k0 REAL,
        beta_k REAL,
        lf REAL,
        flux_mass_factor REAL,
        h_conv REAL,
        emissivity_0 REAL,
        t_ambient REAL,
        t_melt REAL,
        delta_t_melt REAL,
        t_warning REAL,
        t_critical REAL,
        t_plastic REAL
    )
    ''')

    # ALL 5 MAJOR ELECTRODE BENCHMARKS
    all_electrodes = [
        # 1. E6013 (Carbon Steel - Rutile Coating)
        ('E6013_3.2mm', 'E6013 Carbon Steel (3.2mm)', 'Rutile',
         0.0032, 0.32, 120.0, 95.0, 10.0, 2.0, 24.0, 0.76, 0.20,
         7850.0, 460.0, 0.00015, 1.6e-7, 0.0025, 54.0, 0.00015, 2.7e5, 1.30,
         22.0, 0.75, 25.0, 1450.0, 20.0, 500.0, 600.0, 700.0),

        # 2. E7018 (Carbon Steel - Heavy Iron Powder / Low Hydrogen)
        ('E7018_3.2mm', 'E7018 Low-Hydrogen Structural (3.2mm)', 'Basic/Iron Powder',
         0.0032, 0.35, 140.0, 105.0, 12.0, 2.0, 25.0, 0.78, 0.22,
         7850.0, 480.0, 0.00018, 1.8e-7, 0.0028, 50.0, 0.00012, 2.7e5, 1.45,
         25.0, 0.80, 25.0, 1480.0, 20.0, 520.0, 620.0, 720.0),

        # 3. E6010 (Carbon Steel - Deep Penetration Cellulosic)
        ('E6010_3.2mm', 'E6010 Fast-Freeze Pipe Grade (3.2mm)', 'Cellulosic',
         0.0032, 0.30, 110.0, 85.0, 8.0, 2.0, 27.0, 0.72, 0.18,
         7850.0, 450.0, 0.00012, 1.5e-7, 0.0022, 58.0, 0.00018, 2.7e5, 1.15,
         20.0, 0.70, 25.0, 1430.0, 20.0, 480.0, 580.0, 680.0),

        # 4. E308L-16 (Stainless Steel - High Electrical Resistivity Core)
        ('E308L_3.2mm', 'E308L Stainless Steel (3.2mm)', 'Rutile-Titanium',
         0.0032, 0.32, 100.0, 75.0, 8.0, 2.0, 23.0, 0.74, 0.19,
         7920.0, 500.0, 0.00020, 7.2e-7, 0.0012, 16.0, 0.00008, 2.9e5, 1.35,
         22.0, 0.82, 25.0, 1400.0, 25.0, 450.0, 550.0, 650.0),

        # 5. ENi-CI (Cast Iron Repair - Pure Nickel Core)
        ('ENi-CI_3.2mm', 'ENi-CI Pure Nickel Cast Iron (3.2mm)', 'Graphite Basic',
         0.0032, 0.30, 95.0, 70.0, 5.0, 2.0, 22.0, 0.70, 0.17,
         8900.0, 444.0, 0.00010, 7.0e-8, 0.0035, 38.0, 0.00010, 3.0e5, 1.25,
         18.0, 0.75, 25.0, 1320.0, 20.0, 420.0, 520.0, 620.0)
    ]

    cursor.executemany('''
    INSERT OR REPLACE INTO electrodes VALUES 
    (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', all_electrodes)

    conn.commit()
    conn.close()
    print(" Database database.db updated with ALL 5 major electrode profiles!")

if __name__ == "__main__":
    build_welding_database()
