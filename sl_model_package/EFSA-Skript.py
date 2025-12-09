"""
EFSA-C_mod- und eta_min-Berechnung mit Plot
-------------------------------------------
Eingaben im Abschnitt "USER-EINGABEN" anpassen und Skript ausführen.
"""

import numpy as np
import matplotlib.pyplot as plt

# ============================================================
# USER-EINGABEN
# ============================================================

# EFSA-Defaultparameter
T_C   = 25.0           # Temperatur [°C]
K_PF  = 1.0            # Verteilungskoeffizient Polymer/Food [-]
t_max = 365 * 24 * 3600  # Kontaktzeit [s]
rho_P = 1.375          # Dichte Polymer [g/cm^3]
d_P   = 300e-4         # Polymerdicke [cm]
d_F   = 16666.7e-4     # Food-Äquivalentdicke [cm] (1 kg food auf 6 dm²)
DEFAULT_MATERIAL = "PET"

# EFSA-Referenzkonzentration im Inputstrom [mg/kg]
c_ref_default = 3.0

# Szenario ("A", "B" oder "C")
scenario = "A"

# Mr-Bereich für die Kurven
M_r_min = 80.0
M_r_max = 500.0
points  = 400

# Materialwahl für die Diffusionskoeffizienten
material = DEFAULT_MATERIAL

# Plot-Optionen
show_surrogates = False       # Surrogatpunkte aus der EFSA-Tabelle einzeichnen
save_figure     = False      # Plots als PNG speichern?
fig_filename_cmod = f"EFSA_Cmod_vs_Mr_scenario_{scenario}.pdf"
fig_filename_eta  = f"EFSA_eta_vs_Mr_scenario_{scenario}.pdf"

# ============================================================
# DATENBASEN (Literaturwerte & Surrogate)
# ============================================================

# Literaturwerte Cmod nach EFSA 2024, Table D.1 (mg/kg PET)
cmod_literature = {
    "Toluene":          {"A": 0.04, "B": 0.13, "C": 0.51},
    "Chlorobenzene":    {"A": 0.05, "B": 0.15, "C": 0.60},
    "Chloroform":       {"A": 0.05, "B": 0.16, "C": 0.63},
    "Methyl salicylate":{"A": 0.12, "B": 0.40, "C": 1.60},
    "Phenylcyclohexane":{"A": 0.13, "B": 0.42, "C": 1.69},
    "Benzophenone":     {"A": 0.15, "B": 0.49, "C": 1.96},
    "Lindane":          {"A": 0.28, "B": 0.92, "C": 3.67},
    "Methyl stearate":  {"A": 0.29, "B": 0.95, "C": 3.82},
}

# Surrogat-Molenmassen (Da)
surrogates = {
    "Toluene":          92.1,
    "Chlorobenzene":    112.6,
    "Chloroform":       119.4,
    "Methyl salicylate":152.2,
    "Phenylcyclohexane":160.3,
    "Benzophenone":     182.2,
    "Lindane":          290.8,
    "Methyl stearate":  298.5,
}

# ============================================================
# KERNFUNKTIONEN
# ============================================================

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


def calculate_sum_term_at_t(D_P, rho_P, K_PF, t, d_P, d_F):
    """
    Berechnet den Summenausdruck im Nenner der EFSA-Gleichung.
    Ergebnis in g/cm².
    """
    alpha = (1 / K_PF) * (d_F / d_P)
    upper_alpha = 10.0

    def calculate_q_n(n, alpha):
        if alpha < 0.1:
            return n * np.pi / (1 + alpha)
        elif alpha > upper_alpha:
            return (2 * n - 1) * np.pi / 2
        else:
            return (n - (alpha / (2 * (1 + alpha)))) * np.pi

    sum_a = 0.0
    k = 1
    while True:
        q_n = calculate_q_n(k, alpha)

        if alpha > upper_alpha:
            sum_term_i = (2 / q_n**2) * np.exp(-q_n**2 * (D_P / d_P**2) * t)
        else:
            sum_term_i = (2 * alpha * (1 + alpha)) / (1 + alpha + alpha**2 * q_n**2) \
                         * np.exp(-q_n**2 * (D_P / d_P**2) * t)

        sum_before = sum_a
        sum_a += sum_term_i

        # Terminierung der unendlichen Summe
        if abs(sum_a - sum_before) < 1e-6:
            break
        k += 1

    if alpha > upper_alpha:
        sum_term = rho_P * d_P * (1 - sum_a)
    else:
        sum_term = rho_P * d_P * (alpha / (1 + alpha)) * (1 - sum_a)

    return sum_term  # [g/cm²]


def migration_criterion_efsa(M_r, scenario):
    """
    EFSA-Table 2 (OF-korrigiert), Rückgabe in µg/kg food.
    """
    table = {
        "A": (0.0481, 0.0962),
        "B": (0.156, 0.312),
        "C": (0.625, 1.250),
    }
    small, large = table[scenario.upper()]
    return small if M_r <= 150 else large


def compute_cmod_efsa(M_r, scenario, material=DEFAULT_MATERIAL):
    """
    Berechnet C_mod [mg/kg] für gegebenes M_r und Szenario.
    """
    # 1) D_P (cm²/s)
    material_params = get_material_data(material, simulation_case="best")
    D_P = diffusion_coefficient_Piringer(M_r, T_C, material_params)

    # 2) Summenausdruck im Nenner (liefert g/cm²)
    sum_term_g_per_cm2 = calculate_sum_term_at_t(D_P, rho_P, K_PF, t_max, d_P, d_F)

    # 3) EFSA-Migrationskriterium (µg/kg food) -> mg/kg food
    Mcrit_mg_per_kg = migration_criterion_efsa(M_r, scenario) / 1000.0

    # 4) V_F/A = 1 kg / 6 dm² = 1 / 600 kg/cm²   → mg/cm²
    numerator_mg_per_cm2 = Mcrit_mg_per_kg * (1.0 / 600.0)

    # 5) g/cm² → kg/cm²
    sum_term_kg_per_cm2 = sum_term_g_per_cm2 / 1000.0

    # 6) C_mod = (mg/cm²) / (kg/cm²) = mg/kg
    C_mod_mg_per_kg = numerator_mg_per_cm2 / sum_term_kg_per_cm2
    return C_mod_mg_per_kg


def compute_eta_min_efsa(M_r, scenario, c_ref_value=3.0):
    """
    Berechnet die minimale notwendige Dekontaminierungseffizienz η_min [%]
    aus dem EFSA-Kriterium: η_min = 1 - C_mod / c_ref.
    Rückgabe in Prozent.
    """
    C_mod = compute_cmod_efsa(M_r, scenario, material=DEFAULT_MATERIAL)   # [mg/kg]
    eta_min = 1.0 - (C_mod / c_ref_value)
    return max(0.0, min(1.0, eta_min)) * 100.0  # Begrenzung auf [0, 100] %


def generate_curves(M_r_min=80.0, M_r_max=500.0, points=400,
                    scenario="A", material=DEFAULT_MATERIAL, c_ref_value=3.0):
    """
    Berechnet die Kurven für C_mod und eta_min über einen M_r-Bereich.
    Rückgabe: (M_r_values, C_mod_values, eta_min_values)
    """
    if points < 2:
        points = 2

    M_r_values = np.linspace(M_r_min, M_r_max, points)
    C_mod_values = [compute_cmod_efsa(M_r, scenario, material=material)
                    for M_r in M_r_values]
    eta_min_values = [compute_eta_min_efsa(M_r, scenario, c_ref_value)
                      for M_r in M_r_values]
    return M_r_values, np.array(C_mod_values), np.array(eta_min_values)


def compare_to_literature():
    """
    Textausgabe der Abweichungen zwischen berechnetem C_mod und Literaturwerten.
    """
    rows = []
    for name, Mr in surrogates.items():
        for scen in ("A", "B", "C"):
            calc = compute_cmod_efsa(Mr, scen)
            ref  = cmod_literature[name][scen]
            rel_err = (calc - ref) / ref * 100.0
            rows.append([name, Mr, scen, calc, ref, rel_err])

    print(f"{'Surrogate':20s} {'Mr [Da]':>8s} {'Scen':>4s} "
          f"{'C_mod calc [mg/kg]':>18s} {'C_mod lit [mg/kg]':>18s} {'rel. Abw. [%]':>12s}")
    for r in rows:
        print(f"{r[0]:20s} {r[1]:8.1f} {r[2]:>4s} "
              f"{r[3]:18.3f} {r[4]:18.2f} {r[5]:12.1f}")


# ============================================================
# HAUPTPROGRAMM: BERECHNUNG & PLOT
# ============================================================

if __name__ == "__main__":

    # Kurven berechnen
    M_r_vals, C_mod_vals, eta_min_vals = generate_curves(
        M_r_min=M_r_min,
        M_r_max=M_r_max,
        points=points,
        scenario=scenario,
        material=material,
        c_ref_value=c_ref_default,
    )

    # Plot 1: C_mod über M_r
    fig1, ax1 = plt.subplots()

    ax1.set_xlabel("Molare Masse $M_r$ [g/mol]")
    ax1.set_ylabel(r"$C_{mod}$ [mg/kg]", fontsize=11)
    ax1.plot(M_r_vals, C_mod_vals, color="#F06D1D")
    ax1.grid(True, which="both", linestyle=":")

    # Optionale Surrogatpunkte für C_mod einzeichnen
    if show_surrogates:
        for name, Mr in surrogates.items():
            if scenario.upper() in cmod_literature[name]:
                C_lit = cmod_literature[name][scenario.upper()]
                ax1.scatter(Mr, C_lit, marker="o", label="_nolegend_")
                ax1.annotate(name, (Mr, C_lit),
                             xytext=(3, 3), textcoords="offset points", fontsize=8)

    ax1.legend(loc="best")
    ax1.set_title(f"EFSA-Szenario {scenario}: $C_{{mod}}$ in Abhängigkeit von $M_r$", fontsize=12)
    fig1.tight_layout()

    # Plot 2: eta_min über M_r
    fig2, ax2 = plt.subplots()

    ax2.set_xlabel("Molare Masse $M_r$ [g/mol]")
    ax2.set_ylabel(r"$\eta_{\min}$ [%]", fontsize=11)
    ax2.plot(M_r_vals, eta_min_vals, color="#F06D1D")
    ax2.grid(True, which="both", linestyle=":")

    ax2.legend(loc="best")
    ax2.set_title(f"EFSA-Szenario {scenario}: $\eta_{{\min}}$ in Abhängigkeit von $M_r$", fontsize=12)
    fig2.tight_layout()

    if save_figure:
        fig1.savefig(fig_filename_cmod, dpi=300)
        fig2.savefig(fig_filename_eta, dpi=300)
        print(f"Abbildung gespeichert als: {fig_filename_cmod}")
        print(f"Abbildung gespeichert als: {fig_filename_eta}")

    # Beide Plots anzeigen
    plt.show()