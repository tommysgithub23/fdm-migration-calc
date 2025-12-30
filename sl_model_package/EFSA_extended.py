try:
    from .sl_model_functions import *
except ImportError:
    from sl_model_functions import *


def calculate_sum_term_at_t(D_P, rho_P, K_PF, t, d_P, d_F):

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
            sum_term_i = (2 / q_n**2) * np.exp(-q_n**2 * (D_P / d_P**2) * t)
        else:
            sum_term_i = (2 * alpha * (1 + alpha)) / (1 + alpha + alpha**2 * q_n**2) * np.exp(-q_n**2 * (D_P / d_P**2) * t)


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

    return sum_term


# EFSA-spezifische Parameter für die Risikobewertung von Recyclingverfahren für Lebensmittelkontaktmaterialien
c_ref = 3                              # konservative Referenzkonzentration für PET-Inputstrom [mg/kg]
eta = 0.985                              # Dekontaminierungseffizienz des Verfahrens [-]
c_res = c_ref * (1 - eta)              # resultierende Konzentration im Polymer nach der Dekontaminierung [mg/kg] 
ttc = 0.0025                           # Threshold of Toxicological Concern [mg/kg bw/day]

# Vergleich mit Literaturwerten

# ---- Literaturwerte Cmod nach EFSA 2024, Table D.1 (mg/kg PET) ----
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

# ---- Surrogat-Molenmassen (Da) ----
surrogates = {
    "Toluene": 92.1,
    "Chlorobenzene": 112.6,
    "Chloroform": 119.4,
    "Methyl salicylate": 152.2,
    "Phenylcyclohexane": 160.3,
    "Benzophenone": 182.2,
    "Lindane": 290.8,
    "Methyl stearate": 298.5
}

# ---- EFSA-Defaultparameter (Appendix D) ----
T_C   = 25.0
K_PF  = 1.0
t_max = 365*24*3600
rho_P = 1.375           # g/cm^3
d_P   = 300e-4          # cm
d_F   = 16666.7e-4      # cm (entspricht 1 kg food auf 6 dm²)
DEFAULT_MATERIAL = "PET"
D_P_known = None
scenario = "A"

def migration_criterion_efsa(M_r, scenario):
    # Table 2 (OF-korrigiert), µg/kg food
    table = {"A": (0.0481, 0.0962), "B": (0.156, 0.312), "C": (0.625, 1.250)}
    small, large = table[scenario.upper()]
    return small if M_r <= 150 else large   # µg/kg food

def compute_cmod_efsa(M_r, scenario, material=DEFAULT_MATERIAL):
    # 1) D_P (cm^2/s)
    material_params = get_material_data(material, simulation_case="best")
    D_P = diffusion_coefficient_Piringer(M_r, T_C, material_params)

    # 2) Summenausdruck im Nenner (liefert g/cm²)
    sum_term_g_per_cm2 = calculate_sum_term_at_t(D_P, rho_P, K_PF, t_max, d_P, d_F)

    # 3) EFSA-Migrationskriterium (µg/kg food) -> mg/kg food
    Mcrit_mg_per_kg = migration_criterion_efsa(M_r, scenario) / 1000.0

    # 4) V_F/A = 1 kg / 6 dm² = 1 / 600 kg/cm²   → mg/cm²
    numerator_mg_per_cm2 = Mcrit_mg_per_kg * (1.0/600.0)

    # 5) g/cm² → erst nach kg/cm² normieren
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
    # in Prozent, begrenzt auf [0, 100]
    return max(0.0, min(1.0, eta_min)) * 100.0

def compare_to_literature():
    rows = []
    for name, Mr in surrogates.items():
        for scen in ("A","B","C"):
            calc = compute_cmod_efsa(Mr, scen)
            ref  = cmod_literature[name][scen]
            rel_err = (calc - ref) / ref * 100.0
            rows.append([name, Mr, scen, calc, ref, rel_err])
    # Schöne Ausgabe
    print(f"{'Surrogate':20s} {'Mr [Da]':>8s} {'Scen':>4s} {'C_mod calc [mg/kg]':>18s} {'C_mod lit [mg/kg]':>18s} {'rel. Abw. [%]':>12s}")
    for r in rows:
        print(f"{r[0]:20s} {r[1]:8.1f} {r[2]:>4s} {r[3]:18.3f} {r[4]:18.2f} {r[5]:12.1f}")

def generate_curves(M_r_min=80.0, M_r_max=500.0, points=400, scenario="A", material=DEFAULT_MATERIAL, c_ref_value=3.0):
    """
    Berechnet die Kurven für C_mod und eta_min über einen Mr-Bereich.
    Rückgabe: (M_r_values, C_mod_values, eta_min_values)
    """
    if points < 2:
        points = 2
    M_r_values = np.linspace(M_r_min, M_r_max, points)
    C_mod_values = [compute_cmod_efsa(M_r, scenario, material=material) for M_r in M_r_values]
    eta_min_values = [compute_eta_min_efsa(M_r, scenario, c_ref_value) for M_r in M_r_values]
    return M_r_values, C_mod_values, eta_min_values


__all__ = [
    "calculate_sum_term_at_t",
    "migration_criterion_efsa",
    "compute_cmod_efsa",
    "compute_eta_min_efsa",
    "generate_curves",
    "surrogates",
    "cmod_literature",
    "DEFAULT_MATERIAL",
]
