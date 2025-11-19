import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime


def get_material_data(material, simulation_case="worst"):
    """
    Liefert die materialabhängigen Parameter nach Piringer basierend auf dem angegebenen Material und Simulationsfall (best/worst case).

    Parameter:
    material (str): Name des Materials (z.B. 'LDPE', 'HDPE').
    simulation_case (str): Simulationsfall, entweder 'worst' (Standard) oder 'best'.

    Rückgabe:
    dict: Materialparameter (A_Pt, tau) für das angegebene Material.

    Raises:
    ValueError: Wenn das Material oder der Simulationsfall unbekannt ist.
    """
    material_parameters_worst_case = {
        "LDPE": {"A_Pt": 11.7, "tau": 0},
        "HDPE": {"A_Pt": 13.2, "tau": 1577},
        "LLDPE": {"A_Pt": 11.5, "tau": 0},
        "PP": {"A_Pt": 12.4, "tau": 1577},
        # "PET": {"A_Pt": 6.35, "tau": 1577}, # auskommentiert für EFSA Skript
        "PET": {"A_Pt": 3.1, "tau": 1577},
        "PS": {"A_Pt": -0.7, "tau": 0},
        "PEN": {"A_Pt": 3.7, "tau": 1577},
        "HIPS": {"A_Pt": 0.1, "tau": 0}
    }

    material_parameters_best_case = {
        "LDPE": {"A_Pt": 10.0, "tau": 0},
        "HDPE": {"A_Pt": 10.0, "tau": 1577},
        "PP": {"A_Pt": 9.4, "tau": 1577},
        # "PET": {"A_Pt": 2.2, "tau": 1577}, # auskommentiert für EFSA Skript
        "PET": {"A_Pt": 3.1, "tau": 1577},
        "PS": {"A_Pt": -2.8, "tau": 0},
        "PEN": {"A_Pt": -0.34, "tau": 1577},
        "HIPS": {"A_Pt": -2.7, "tau": 0}
    }

    if simulation_case == "worst":
        if material in material_parameters_worst_case:
            return material_parameters_worst_case[material]
    elif simulation_case == "best":
        if material in material_parameters_best_case:
            return material_parameters_best_case[material]

    raise ValueError("Unbekanntes Material oder Simulation Case")

def diffusion_coefficient_Piringer(M_r, T_C, material_params):
    """
    Berechnet den Diffusionskoeffizienten nach dem Piringer-Modell.

    Parameter:
    M_r (float): relative Molekülmasse des Migranten [g/mol].
    T_C (float): Temperatur in Grad Celsius.
    material_params (dict): Materialparameter für das Modell (A_Pt, tau).

    Rückgabe:
    float: Berechneter Diffusionskoeffizient in [cm²/s].

    Raises:
    ValueError: Wenn die Molekülmasse größer als 4000 Dalton ist.
    """
    A_Pt, tau = material_params['A_Pt'], material_params['tau']
    T = 273.15 + T_C  # Temperatur in K
    R = 8.3145  # Gaskonstante (J/(mol*K))
    E_A = (10454 + tau) * R  # Diffusionsaktivierungsenergie
    A_P = A_Pt - (tau / T)
    D_0 = 1e4  # D_0 nach Piringer Modell

    if M_r <= 4000:
        D_P =  D_0 * np.exp(A_P - 0.1351 * M_r**(2 / 3) + 0.003 * M_r - (10454 * R / (R * T)))
    else:
        raise ValueError("M_r über 4000 Dalton, andere Berechnung von D_P nötig!")
    
    return D_P

def calculate_migration_timestep(D_P, c_t, P_density, F_density, K_PF, t_step, V_P, V_F, d_P, d_F, A_PF):
    """
    Berechnet die Migration für einen Zeitschritt basierend auf dem Piringer-Modell.

    Parameter:
    D_P (float): Diffusionskoeffizient des Polymers [cm²/s].
    c_t (float): Konzentration des Migranten im Polymer [mg/kg].
    P_density (float): Dichte des Polymers [g/cm³].
    F_density (float): Dichte des Fluids [g/cm³].
    K_PF (float): Verteilungskoeffizient zwischen Polymer und Fluid [-].
    t_step (float): Zeitschrittgröße [s].
    V_P (float): Volumen des Polymers [cm³].
    V_F (float): Volumen des Fluids [cm³].
    d_P (float): Dicke des Polymers [cm].
    d_F (float): Dicke des Fluids [cm].
    A_PF (float): Kontaktfläche zwischen Polymer und Fluid [dm²].

    Rückgabe:
    float: Migrationsmenge des Migranten nach einem Zeitschritt [mg/dm²].
    """
    
    alpha = (1 / K_PF) * (d_F / d_P)
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

def migrationsmodell_piringer(M_r, T_C, c_P0, Material, P_density, F_density, K_PF, t_max, V_P, V_F, d_P, d_F, A_PF, dt, D_P_known, simulation_case="worst"):
    """
    Führt die Migration des Migranten im Polymer nach dem Piringer-Modell durch und gibt die Migrationsmenge über die Zeit zurück.

    Parameter:
    M_r (float): Molekulargewicht des Migranten [g/mol].
    T_C (float): Temperatur in Grad Celsius.
    c_P0 (float): Anfangskonzentration im Polymer [mg/kg].
    Material (str): Material des Polymers (z.B. 'LDPE').
    P_density (float): Dichte des Polymers [g/cm³].
    F_density (float): Dichte des Fluids [g/cm³].
    K_PF (float): Verteilungskoeffizient zwischen Polymer und Fluid [-].
    t_max (float): Maximale Simulationszeit [s].
    V_P (float): Volumen des Polymers [cm³].
    V_F (float): Volumen des Fluids [cm³].
    d_P (float): Dicke des Polymers [cm].
    d_F (float): Dicke des Fluids [cm].
    A_PF (float): Kontaktfläche zwischen Polymer und Fluid [dm²].
    dt (float): Zeitschrittgröße [s].
    simulation_case (str): Simulationsfall, entweder 'worst' oder 'best' (Standard ist 'worst').
    D_P_known (float, optional): Optionaler bekannter Diffusionskoeffizient [cm²/s].

    Rückgabe:
    list: Liste der Migrationsmengen über die Zeit [mg/dm²].
    """
    
    if D_P_known is not None:
        D_P = D_P_known

    else:
        material_params = get_material_data(Material, simulation_case)
        D_P = diffusion_coefficient_Piringer(M_r, T_C, material_params)

    migration_data = []
    current_time = 0

    while current_time < t_max:
        migration_amount = calculate_migration_timestep(D_P, c_P0, P_density, F_density, K_PF, current_time, V_P, V_F, d_P, d_F, A_PF)
        migration_data.append(migration_amount)
        current_time += dt
        
    migration_data = np.array(migration_data) / 10 # Umrechnung in [mg/dm²]

    return migration_data

def migrationsmodell_piringer_with_temp_profile(M_r, c_P0, Material, P_density, F_density, K_PF, t_max, V_P, V_F, d_P, d_F, A_PF, dt, simulation_case="worst"):
    """
    Simuliert die Migration unter einem variablen Temperaturprofil nach dem Piringer-Modell.

    Parameter:
    M_r (float): relative Molekülmasse des Migranten [g/mol].
    c_P0 (float): Anfangskonzentration im Polymer [mg/kg].
    Material (str): Material des Polymers (z.B. 'LDPE').
    P_density (float): Dichte des Polymers [g/cm³].
    F_density (float): Dichte des Fluids [g/cm³].
    K_PF (float): Verteilungskoeffizient zwischen Polymer und Fluid [-].
    t_max (float): Maximale Simulationszeit [s].
    V_P (float): Volumen des Polymers [cm³].
    V_F (float): Volumen des Fluids [cm³].
    d_P (float): Dicke des Polymers [cm].
    d_F (float): Dicke des Fluids [cm].
    A_PF (float): Kontaktfläche zwischen Polymer und Fluid [dm²].
    dt (float): Zeitschrittgröße [s].
    simulation_case (str): Simulationsfall, entweder 'worst' oder 'best' (Standard ist 'worst').

    Rückgabe:
    list: Liste der Migrationsmengen über die Zeit [mg/dm²] bei variierendem Temperaturprofil.
    """
    material_params = get_material_data(Material, simulation_case)

    # Define the temperature profile sections (converted to seconds)
    temperature_profile = [
        (0, 864000, 40),     # Day 1-10, temperature = 10°C
        (864000, 1728000, 20),  # Day 10-20, temperature = 30°C
        (1728000, t_max, 40)  # Day 20+, temperature = 20°C
    ]

    migration_data = []
    current_time = 0

    for (start_time, end_time, temp) in temperature_profile:
        while current_time < min(end_time, t_max):
            D_P = diffusion_coefficient_Piringer(M_r, temp, material_params)

            migration_amount = calculate_migration_timestep(D_P, c_P0, P_density, F_density, K_PF, current_time, V_P, V_F, d_P, d_F, A_PF)
            migration_data.append(migration_amount)

            current_time += dt
            if current_time >= t_max:
                break
            
    migration_data = np.array(migration_data) / 10 # Umrechnung in [mg/dm²]

    return migration_data

def calculate_max_cp0(SML, M_r, T_C, Material, P_density, F_density, K_PF, t_max, V_P, V_F, d_P, d_F, A_PF, dt, D_P_known):
    # Initial guess für c_P0 und Toleranz
    c_P0_guess = 1 
    tolerance = 1e-6  
    max_iterations = 300  
    
    for _ in range(max_iterations):
        # Berechne die Migration für den aktuellen c_P0-Schätzwert
        migration_data = migrationsmodell_piringer(M_r, T_C, c_P0_guess, Material, P_density, F_density, K_PF, t_max, V_P, V_F, d_P, d_F, A_PF, dt, D_P_known)
        
        # Berechne die maximale Migration
        migration_max = max(migration_data)  # max migration 
        
        if abs(migration_max - SML) < tolerance:
            return c_P0_guess
        
        # Anpassung von c_P0 basierend auf dem Verhältnis zwischen aktueller Migration und Ziel-SML
        c_P0_guess *= (SML / migration_max)
    
    # Wenn keine Konvergenz erreicht wird
    raise ValueError("Maximale Iterationen erreicht, keine Lösung gefunden")

def plot_results_area(results_area, t_max, dt, save_path=None): 
    # Plot the area-specific migration results
    plt.figure(figsize=(10, 6))
    time_days = np.arange(0, t_max / (3600 * 24), dt / (3600 * 24))
    plt.plot(time_days, results_area, linewidth = 2, color = '#F06D1D')
    
    # Plot speichern, wenn ein Pfad angegeben wurde
    if save_path:
        plot_filename = os.path.join(save_path, 'migrated_mass_plot.pdf')
        plt.savefig(plot_filename, bbox_inches='tight')
        print(f"Migrationsplot gespeichert unter: {plot_filename}")
              
    # Achsenbeschriftungen und Titel
    plt.xlabel('Zeit $[Tage]$', fontsize=14)
    plt.ylabel('spez. Migrationsmenge $[mg/dm^2]$', fontsize=14)
    plt.xticks(fontsize=14)
    plt.yticks(fontsize=14)
    plt.show()