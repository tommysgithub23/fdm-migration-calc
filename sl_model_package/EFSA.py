from sl_model_functions import *


def efsa_migration_criterion(M_r, scenario):
    """
    Gibt das EFSA-Migrationskriterium [µg/kg food] zurück
    abhängig von der Molmasse (M_r) und dem Expositionsszenario (A, B oder C).

    Quelle: EFSA (2024) – Table 2: Exposure scenarios with the related migration criteria.
    """
    scenario = scenario.upper()

    # Migration criteria (µg/kg food) gemäß EFSA Table 2
    migration_table = {
        "A": {"small": 0.0481, "large": 0.0962},
        "B": {"small": 0.156,  "large": 0.312},
        "C": {"small": 0.625,  "large": 1.250},
    }

    if scenario not in migration_table:
        raise ValueError("Ungültiges Szenario. Verwende 'A', 'B' oder 'C'.")

    # Grenze bei 150 Da
    if M_r <= 150:
        return migration_table[scenario]["small"]
    else:
        return migration_table[scenario]["large"]
    
    
def calculate_sum_term_at_t(D_P, rho_P, K_PF, t, d_P, d_F):

    alpha = (1 / K_PF) * (d_F / d_P)

    def calculate_q_n(n, alpha):
        if alpha < 0.1:
            return n * np.pi / (1 + alpha)
        else:
            return (n - ((alpha / 2) * (1 + alpha))) * np.pi

    sum_a = 0
    k = 1
    while True:
        q_n = calculate_q_n(k, alpha)

        sum_term_i = (2 * alpha * (1 + alpha)) / (1 + alpha + alpha**2 * q_n**2) * np.exp(-q_n**2 * (D_P / d_P**2) * t)

        sum_before = sum_a
        sum_a += sum_term_i

        # Terminierung der unendlichen Summe
        if abs(sum_a - sum_before) < 1e-3:
            break
        k += 1

    # Berechnet Summen term zu dem Zeitpunkt t
    sum_term = rho_P * d_P * (alpha / (1 + alpha)) * (1 - sum_a)

    return sum_term


# EFSA-spezifische Parameter für die Risikobewertung von Recyclingverfahren für Lebensmittelkontaktmaterialien
c_ref = 3                              # konservative Referenzkonzentration für PET-Inputstrom [mg/kg]
eta = 0.985                              # Dekontaminierungseffizienz des Verfahrens [-]

c_res = c_ref * (1 - eta)              # resultierende Konzentration im Polymer nach der Dekontaminierung [mg/kg] 

ttc = 0.0025                           # Threshold of Toxicological Concern [mg/kg bw/day]

scenario = "A"                         # Expositionsszenario nach EFSA (A, B, C)

# Modellparameter
M_r = 92.1                               # Molmasse [g/mol] bzw. [Da] (Toluene,Test)
T_C = 25                               # Temperatur nach EFSA [°C] 
K_PF = 1                               # Polymer-Food Verteilungskoeffizient nach EFSA [-]
t_max = 3600 * 24 * 365                # maximale Expositionsdauer nach EFSA [s] (1 Jahr)
dt = 10                                # Zeitintervall für die Simulation nach EFSA [s] 

Material = "PET"                       # Polymermaterial
D_P_known = None                       # Diffusionskoeffizient des Polymers (falls bekannt) [m²/s]

A_PF = 6                               # Kontaktfläche Polymer/Lebensmittel [dm²]
d_P = 300e-4                           # Dicke des Polymermaterials nach EFSA [cm] (300 µm)
d_F = 16666.7e-4                       # Dicke der Lebensmittelschicht nach EFSA bzw. Artikel 17.2 EU Nr. 10/2011 [cm] (1 kg Lebensmittel auf 6 dm² Fläche s. Hoekstra et al. 2015)
rho_P = 1.375                          # Dichte des Polymers nach EFSA [g/cm³] (PET)

rho_F = None                           # Dichte des Lebensmittels [g/cm³] (nicht benötigt)
V_P = None                             # Volumen des Polymers [cm³] (nicht benötigt)
V_F = None                             # Volumen des Lebensmittels [cm³] (nicht benötigt)

migration_limit = efsa_migration_criterion(M_r, scenario)  # [µg/kg food]
migration_limit_mg_per_kg = migration_limit / 1000  # Umrechnung in [mg/kg food]

t = t_max
material_params = get_material_data(Material, simulation_case="best")

D_P = diffusion_coefficient_Piringer(M_r, T_C, material_params)

sum_term = calculate_sum_term_at_t(D_P, rho_P, K_PF, t, d_P, d_F)

c_mod = migration_limit * (1/6) / sum_term # [mg/kg]

print(f"{c_mod} mg/kg")