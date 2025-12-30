import numpy as np
import matplotlib.pyplot as plt
import pandas as pd 
import os

def calculate_migration_timestep(D_P, c_t, P_density, K_PF, t_step, V_P, V_F, d_P, d_F, A_PF):
    
    alpha = (1 / K_PF) * (V_F / V_P)
    upper_alpha = 10

    def calculate_q_n(n, alpha):
        if alpha < 0.1:
            return n * np.pi / (1 + alpha)
        elif alpha > upper_alpha:
            return (2 * n - 1) * np.pi / 2
        else:
            return (n - (alpha / (2 * (1 + alpha)))) * np.pi

    sum_a = 0
    k = 1
    while True:
        q_n = calculate_q_n(k, alpha)
        if alpha > upper_alpha:
            sum_term_i = (2 / q_n**2) * np.exp(-q_n**2 * (D_P / d_P**2) * t_step)
        else:
            sum_term_i = (2 * alpha * (1 + alpha)) / (1 + alpha + alpha**2 * q_n**2) * np.exp(-q_n**2 * (D_P / d_P**2) * t_step)

        sum_before = sum_a
        sum_a += sum_term_i

        # Terminierung der unendlichen Summe
        if abs(sum_a - sum_before) < 1e-6:
            break
        k += 1

    # Berechnet Migrationsmenge zu dem Zeitpunkt t_step und Fallunterscheidung abhängig von alpha
    if alpha > upper_alpha:
        migration_amount = c_t * P_density * d_P * (1 - sum_a)
    else:
        migration_amount = c_t * P_density * d_P * (alpha / (1 + alpha)) * (1 - sum_a)

    # Verhindert negative Konzentrationen
    if migration_amount < 0:
        migration_amount = 0

    return migration_amount

def migrationsmodell_piringer_for_curve_fitting(c_P0, P_density, K_PF, t_max, V_P, V_F, d_P, d_F, A_PF, dt, D_P_known):
    
    D_P = D_P_known

    migration_data = []
    current_time = 0

    while current_time <= t_max:
        migration_amount = calculate_migration_timestep(D_P, c_P0, P_density, K_PF, current_time, V_P, V_F, d_P, d_F, A_PF)
        migration_data.append(migration_amount)
        current_time += dt
        
    migration_data = (np.array(migration_data) - migration_data[0]) / 10  # Umrechnung in [mg/dm²] und Normierung auf 0

    return migration_data

def error_function(D_P_candidate, c_P0, P_density, K_PF, t_max, V_P, V_F, d_P, d_F, A_PF, dt, measured_values, measurement_seconds):
    simulation_result = migrationsmodell_piringer_for_curve_fitting(c_P0, P_density, K_PF, t_max, V_P, V_F, d_P, d_F, A_PF, dt, D_P_candidate)
    
    # Indizes: Hier Messzeit in Sekunden, um Indizes aus Array für vergleich zu finden
    indices = [int(indice_second / dt) for indice_second in measurement_seconds]
    sim_values = simulation_result[indices]
    
    error = np.sum((sim_values - measured_values)**2)
    return error

def find_optimized_D_P(D_P_candidates, c_P0, P_density, K_PF, t_max, V_P, V_F, d_P, d_F, A_PF, dt, measured_values, measurement_seconds):
    errors = []
    for D_P_candidate in D_P_candidates:
        err = error_function(D_P_candidate, c_P0, P_density, K_PF, t_max, V_P, V_F, d_P, d_F, A_PF, dt, measured_values, measurement_seconds)
        errors.append(err)

    errors = np.array(errors)
    optimal_index = np.argmin(errors)
    optimal_D_P = D_P_candidates[optimal_index]
    print("Optimierter Diffusionskoeffizient:", optimal_D_P, "cm²/s")
    return optimal_D_P
    
def save_results_to_excel(measurement_point, optimal_D_P, excel_path):
    """Speichert Messdaten & berechneten Diffusionskoeffizienten in Excel.
    Falls die Datei noch nicht existiert, wird sie initialisiert.
    Vermeidet doppelte Einträge basierend auf Surrogate & Temperatur.
    """

    # Basisdaten für den Messpunkt (ohne Messwerte und Zeitpunkte)
    base_data = {
        "Surrogate": measurement_point["surrogate"],
        "Temperatur [°C]": measurement_point["temperature_C"],
        "c_P0 [mg/kg]": measurement_point["c_P0"],
        "D_calc [cm²/s]": optimal_D_P
    }

    # In DataFrame umwandeln
    new_entry = pd.DataFrame([base_data])

    # Falls Datei existiert, lade sie und prüfe auf Duplikate
    if os.path.exists(excel_path):
        try:
            existing_df = pd.read_excel(excel_path)

            # Falls die Datei existiert, aber leer ist, initialisieren wir sie mit den richtigen Spalten
            if existing_df.empty:
                print("Excel-Datei existiert, aber ist leer. Sie wird neu initialisiert.")
                existing_df = pd.DataFrame(columns=new_entry.columns)

        except Exception as e:
            print(f"Fehler beim Laden der Datei: {e}. Datei wird neu erstellt.")
            existing_df = pd.DataFrame(columns=new_entry.columns)

    else:
        # Falls Datei nicht existiert, erzeuge leere Datei mit korrekten Überschriften
        existing_df = pd.DataFrame(columns=new_entry.columns)
        print("Neue Excel-Datei wird erstellt.")

    # Prüfe, ob der Messpunkt bereits existiert (Surrogate + Temperatur)
    duplicate_mask = (
        (existing_df["Surrogate"] == measurement_point["surrogate"]) &
        (existing_df["Temperatur [°C]"] == measurement_point["temperature_C"])
    )

    if duplicate_mask.any():
        print("Messpunkt existiert bereits. Kein doppelter Eintrag.")
        return

    # Falls kein Duplikat, neue Daten anhängen
    updated_df = pd.concat([existing_df, new_entry], ignore_index=True)

    # Speichern als Excel-Datei
    updated_df.to_excel(excel_path, index=False)
    print(f"Ergebnisse gespeichert unter: {excel_path}")

def plot_migration_results(
    t_max,
    dt,
    optimal_simulation,
    measurement_seconds,
    measured_values,
    optimal_D_P,
    measurement_point,
    P_density,
    F_density,
    K_PF,
    c_P0,
    plot_dir=None,
):
    save_path = None
    if plot_dir:
        os.makedirs(plot_dir, exist_ok=True)
        file_name = f"migration_plot_{measurement_point['surrogate']}_{measurement_point['temperature_C']}C.pdf"
        separators = [os.path.sep]
        if os.path.altsep:
            separators.append(os.path.altsep)
        for sep in separators:
            file_name = file_name.replace(sep, "_")
        save_path = os.path.join(plot_dir, file_name)

    time = np.arange(0, t_max + dt, dt) 
    plt.figure(figsize=(8, 6))
    seconds_per_day = 3600 * 24
    time_days = time / seconds_per_day
    measurement_days = np.asarray(measurement_seconds) / seconds_per_day
    plt.plot(time_days, optimal_simulation, label='Simulation', linewidth=2, color='#F06D1D')
    
    # Overlay der Messwerte
    plt.scatter(measurement_days, measured_values, label='Messwerte', color='blue', s=60, zorder=5, marker='^')
    
    # Berechnung der Residuen
    # Sicherstellen, dass die Indizes exakt auf den Messzeitpunkten liegen
    indices = [int(indice_second / dt) for indice_second in measurement_seconds]
    simulated_at_measurement = optimal_simulation[indices]  
    residuals = measured_values - simulated_at_measurement  # Residuen 
    
    # Residuen als vertikale Linien anzeigen
    for x_day, y_meas, y_sim in zip(measurement_days, measured_values, simulated_at_measurement):
        plt.vlines(x_day, y_sim, y_meas, color='red', linestyle='dashed', linewidth=1)
    
    # Achsenbeschriftungen und Titel
    plt.plot([], [], color='red', linestyle='dashed', linewidth=1, label='Residuen')  # Dummy für Residuen
    plt.text(0.32, 0.055, rf"$D_{{calc}}(T_{{C}}={measurement_point['temperature_C']}°C) = {optimal_D_P:.3e} \,\text{{cm²/s}}$",
             transform=plt.gca().transAxes, fontsize=11, bbox=dict(facecolor='white', alpha=0.8))
    plt.xlabel('Zeit [Tage]', fontsize=12)
    plt.ylabel('spez. Migrationsmenge [mg/dm²]', fontsize=12)
    plt.grid(True, which='both', linestyle='--', linewidth=0.7, alpha=0.7)
    plt.ylim(0)
    plt.legend(fontsize=11, loc='lower right')
    plt.xticks(fontsize=11)
    plt.yticks(fontsize=11)
    
    boundary_conditions = (
        rf"$\text{{Substanz}}$: {measurement_point['surrogate']}, "
        rf"$T = {measurement_point['temperature_C']}\,^{{\circ}}\text{{C}},$ "
        rf"$c_{{P0}} = {c_P0}\,\text{{mg/kg}},$ "
        rf"$K_{{PF}} = {K_PF}$"
        "\n"
        rf"$\rho_P = {P_density}\,\text{{g/cm³}},$ " 
        rf"$\rho_F = {F_density}\,\text{{g/cm³}}$"
    )
    
    ax = plt.gca()
    ax.text(
        0.5,
        -0.2,
        boundary_conditions,
        ha='center',
        va='top',
        transform=ax.transAxes,
        fontsize=11,
        bbox=dict(facecolor='white', alpha=0.8),
        clip_on=False,
    )
    plt.subplots_adjust(bottom=0.02)
    # Plot speichern
    if save_path:
        plt.savefig(save_path, bbox_inches='tight')
        print(f"Plot gespeichert unter: {save_path}")
    else:
        plt.tight_layout()
    return save_path
def load_measurement_data(file_path):
    df = pd.read_excel(file_path, sheet_name="Sheet1")
    grouped_data = {}
    
    for (substance, temp), group in df.groupby(["Substanz", "Temperatur [°C]"]):
        grouped_data[(substance, temp)] = {
            "time_days": group["Zeit [Tage]"].values,
            "c_F": group["Messwert [mg/kg]"].values,
            "c_P0": group["c_P0 [mg/kg]"].values[0]
        }
    
    return grouped_data

def process_all_measurements(file_path, excel_output_path, plots_dir):
    data = load_measurement_data(file_path)
    for (substance, temp), values in data.items():
        measurement_point = {
            "surrogate": substance,
            "temperature_C": temp,
            "c_P0": values["c_P0"],
            "time_days": values["time_days"],
            "c_F": values["c_F"]
        }
        
        # Parameter für die Berechnung
        P_density = 0.9045
        F_density = 0.9
        K_PF = 1
        dt = 3600
        
        # Geometrische Größen
        A_PF = 0.2827
        V_P = 10.6384
        V_F = 28.27
        d_P = V_P / (A_PF * 1e2)
        d_F = V_F / (A_PF * 1e2)
        
        # Messwerte umrechnen
        m_F = V_F * F_density * 1e-3
        measured_values = (measurement_point["c_F"] / A_PF) * m_F
        measurement_days = measurement_point["time_days"]
        measurement_seconds = measurement_days * 24 * 3600         # Messtage in Sekunden

        t_max = max(measurement_seconds)
        
        # Zeitachse
        time_days_full = np.arange(0, max(measurement_days) + 1, 1)
        
        # Diffusionskoeffizient suchen
        D_P_candidates = np.logspace(-12, -6, num=100)
        optimal_D_P = find_optimized_D_P(D_P_candidates, measurement_point["c_P0"], P_density, K_PF, t_max, V_P, V_F, d_P, d_F, A_PF, dt, measured_values, measurement_seconds)
        
        # Simulation durchführen
        optimal_simulation = migrationsmodell_piringer_for_curve_fitting(measurement_point["c_P0"], P_density, K_PF, t_max, V_P, V_F, d_P, d_F, A_PF, dt, optimal_D_P)
        
        # Plot speichern 
        plot_migration_results(t_max, dt, optimal_simulation, measurement_seconds, measured_values, optimal_D_P, measurement_point, P_density, F_density, K_PF, measurement_point["c_P0"], plots_dir)
        
        # Ergebnisse speichern
        save_results_to_excel(measurement_point, optimal_D_P, excel_output_path)

# Speicherpfad der Excel-Datei
if __name__ == "__main__":
    data_file = "/Users/tomhartmann/Documents/GitHub/fdm-migration-calc/data/Messwerte_Umstrukturiert.xlsx"
    results_file = "/Users/tomhartmann/Documents/GitHub/fdm-migration-calc/data/Ergebnisse_Diffcoeff_curve-fitting.xlsx"
    # plots_dir = "/Users/tomhartmann/Documents/GitHub/fdm-migration-calc/data/plots"
    plots_dir = "/Users/tomhartmann/Desktop/temp"
    process_all_measurements(data_file, results_file, plots_dir)
