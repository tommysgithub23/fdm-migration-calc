# Beispiel zum Test der 3D-Plot-Funktion
from gui.sl_model_functions import plot_migration_surface_over_parameter

# Parameter
M_r = 300  # g/mol
c_P0 = 10  # mg/kg
Material = "LDPE"
P_density = 0.92  # g/cm³
F_density = 1.0   # g/cm³
K_PF = 1
t_max = 10 * 24 * 3600  # 10 Tage in Sekunden
V_P = 1.0   # cm³
V_F = 10.0  # cm³
d_P = 0.01  # cm
d_F = 1.0   # cm
A_PF = 1.0  # dm²
dt = 3600   # 1 Stunde
D_P_known = None  # automatisch berechnen lassen
simulation_case = "worst"

# Parameter, den du variieren willst (hier Temperatur von 5 °C bis 60 °C)
param_name = "c_P0"
param_values = list(range(5, 61, 5))  # 5, 10, 15, ..., 60

# Aufruf der Funktion
plot_migration_surface_over_parameter(
    param_name=param_name,
    param_values=param_values,
    M_r=M_r,
    T_C=20,  # Platzhalter, wird überschrieben
    c_P0=c_P0,
    Material=Material,
    P_density=P_density,
    F_density=F_density,
    K_PF=K_PF,
    t_max=t_max,
    V_P=V_P,
    V_F=V_F,
    d_P=d_P,
    d_F=d_F,
    A_PF=A_PF,
    dt=dt,
    D_P_known=D_P_known,
    simulation_case=simulation_case
)