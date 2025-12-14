# Imports 
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os
from datetime import datetime
from matplotlib.patches import Patch

class Layer:
    def __init__(self, material, d, nx, K_value=1.0, C_init=0.0, density=1.0, D=None):
        """
        Initialisiert ein Layer-Objekt, das eine einzelne Schicht des Simulationsmodells repräsentiert.

        Parameter:
            material (str): Das Material der Schicht, z.B. 'LDPE', 'Kontaktphase'.
            d (float): Dicke der Schicht in cm.
            nx (int): Anzahl der Gitterpunkte in der Schicht.
            K_value (float): Verteilungskoeffizient zwischen den Schichten (Standardwert: 1.0).
            C_init (float): Anfangskonzentration in der Schicht in mg/kg (Standardwert: 0.0).
            density (float): Dichte des Materials in g/cm³ (Standardwert: 1.0).
            D (float, optional): Diffusionskoeffizient der Schicht in cm²/s, falls explizit angegeben. Ansonsten wird er über die Piringer Gleichung berechnet.

        Methoden:
            set_diffusion_coefficient(M_r, T_C): Berechnet und setzt den Diffusionskoeffizienten nach Piringer basierend auf der relativen Molekülmasse des Migranten und der Temperatur.
        """

        self.material = material
        self.d = d
        self.nx = nx
        self.K_value = K_value
        self.C_init = C_init
        self.density = density
        self.D = D  # Falls kein Diffusionskoeffizient übergeben wurde, wird er mit der Piringer Gleichung berechnet

    def set_diffusion_coefficient(self, M_r, T_C):
        """
        Berechnet und setzt den Diffusionskoeffizienten für die Schicht, falls nicht manuell angegeben.
        
        Parameter:
            M_r (float): rel. Molekülmasse des Migranten [g/mol].
            T_C (float): Temperatur [°C].
        """
        if self.D is None: 
            if self.material == 'Kontaktphase':
                self.D = 1e-2  # Nach EU-Verordnung für durchmischte Kontaktphase
            else:
                material_params = get_material_data(self.material)
                self.D = diffusion_coefficient_Piringer(M_r, T_C, material_params)

def get_material_data(material):
    """
    Gibt die materialbezogenen Parameter für die Berechnung des Diffusionskoeffizienten zurück.

    Parameter:
        material (str): Name des Materials.

    Rückgabe:
        dict: Ein Dictionary, das die Parameter 'A_Pt' und 'tau' für das angegebene Material enthält.

    Raises:
        ValueError: Wenn das angegebene Material nicht in der Liste der bekannten Materialien enthalten ist.
    """

    material_parameters = {
        "LDPE": {"A_Pt": 11.7, "tau": 0},
        "LLDPE": {"A_Pt": 9.8, "tau": 0}, # für Validierung
        "HDPE": {"A_Pt": 13.2, "tau": 1577},
        "PP": {"A_Pt": 12.4, "tau": 1577},
        "PET": {"A_Pt": 6.35, "tau": 1577},
        "PS": {"A_Pt": -0.7, "tau": 0},
        "PEN": {"A_Pt": 3.7, "tau": 1577},
        "HIPS": {"A_Pt": 0.1, "tau": 0}
    }

    if material in material_parameters:
        return material_parameters[material]
    else:
        raise ValueError(f"Unbekanntes Material: {material}")

def diffusion_coefficient_Piringer(M_r, T_C, material_params):
    """
    Berechnet den Diffusionskoeffizienten nach dem Piringer-Modell basierend auf der relativen Molekülmasse und der Temperatur.

    Parameter:
        M_r (float): Relative Molekülmasse des Migranten in g/mol.
        T_C (float): Temperatur in °C.
        material_params (dict): Materialbezogene Parameter wie 'A_Pt' und 'tau'.

    Rückgabe:
        float: Der berechnete Diffusionskoeffizient in cm²/s.

    Raises:
        ValueError: Wenn die relative Molekülmasse über 4000 g/mol liegt.
    """

    A_Pt, tau = material_params['A_Pt'], material_params['tau']
    T = 273.15 + T_C  # Temperatur in K
    R = 8.3145  # Gaskonstante (J/(mol*K))
    E_A = (10454 + tau) * R  # Diffusionsaktivierungsenergie

    A_P = A_Pt - (tau / T)
    D_0 = 1e4  # D_0 nach Piringer Modell

    if M_r <= 4000:
        D_P = D_0 * np.exp(A_P - 0.1351 * M_r**(2/3) + 0.003 * M_r - (E_A / (R * T)))
    else:
        raise ValueError("M_r über 4000 Da; andere Berechnung von D_P nötig!")

    return D_P

def initialize_grid(layers):
    """
    Initialisiert das räumliche Gitter basierend auf den Schichten im Modell.

    Parameter:
        layers (list von Layer): Eine Liste der Layer-Objekte, die die Schichten im Modell repräsentieren.

    Rückgabe:
        np.ndarray: Das räumliche Gitter, das die Diskretisierung aller Schichten umfasst.
    """

    x = []

    for i, layer in enumerate(layers):
        d = layer.d
        nx = layer.nx

        x_start = sum(l.d for l in layers[:i])
        x_end = x_start + d
        x_layer = np.linspace(x_start, x_end, nx, endpoint=True)
        x.append(x_layer)

    x = np.concatenate(x)
    return x

def initialize_concentration(layers, x):
    """
    Initialisiert die Konzentrationsprofile über das gesamte Gitter basierend auf den Anfangskonzentrationen der Schichten.

    Parameter:
        layers (list von Layer): Liste der Schichtenobjekte.
        x (np.ndarray): Das räumliche Gitter.

    Rückgabe:
        tuple: Ein Tuple aus zwei Arrays: 
            - Das initiale Konzentrationsprofil (C_init)
            - Eine Kopie des initialen Konzentrationsprofils, welches für die weitere Berechnung verwendet wird
    """

    Nx = sum(layer.nx for layer in layers)
    C_init = np.zeros(Nx)

    start_idx = 0
    for layer in layers:
        end_idx = start_idx + layer.nx
        C_init[start_idx:end_idx] = layer.C_init
        start_idx = end_idx

    return C_init.copy(), C_init

def initialize_matrices(layers, tabler):
    """
    Initialisiert die Koeffizientenmatrizen A und B für das Crank-Nicolson-Verfahren, das zur Lösung der Diffusionsgleichung verwendet wird.

    Parameter:
        layers (list von Layer): Liste der Schichtenobjekte.
        tabler (float): Zeitschrittgröße.

    Rückgabe:
        tuple: Zwei Matrizen (A, B) für das Crank-Nicolson-Verfahren.

    Hinweise:
        - Berücksichtigt die Randbedingungen (No-Flux) und die Übergangsbedingung (Flux-continuity) an den Schichtgrenzen.
    """

    D = [layer.D for layer in layers]
    nx = [layer.nx for layer in layers]
    d = [layer.d for layer in layers]
    K_values = [layer.K_value for layer in layers if layer.K_value is not None]
    
    # Extrahiere K_values für die Schnittstellen zwischen den Schichten
    K_values = []
    for i in range(len(layers) - 1):
        K_left = layers[i].K_value if layers[i].K_value is not None else 1.0
        K_values.append(K_left)
        
    # Gesamtzahl der Gitterpunkte
    Nx = sum(nx)
    
    # Räumlicher Schritt für jede Schicht
    dx = [d[i] / (nx[i] - 1) for i in range(len(d))]

    # Initialisiere Matrizen A und B
    A = np.zeros((Nx, Nx))
    B = np.zeros((Nx, Nx))
    
    # Definiere Alpha-Werte für jede Schicht
    alphas = [D[i] * tabler / (2 * dx[i]**2) for i in range(len(D))]
    
    # Auffüllen der Matrizen A und B
    start_idx = 0
    for i in range(len(D)):
        alpha = alphas[i]
        end_idx = start_idx + nx[i]

        for j in range(start_idx + 1, end_idx - 1):
            A[j, j] = 1 + 2 * alpha
            A[j, j - 1] = A[j, j + 1] = -alpha
            B[j, j] = 1 - 2 * alpha
            B[j, j - 1] = B[j, j + 1] = alpha

        start_idx = end_idx
    
    # Randbedingung an den äußeren Rändern (No-Flux-BC)
        
    # Linker Rand
    A[0, 0] = 1 + 2 * alphas[0]
    A[0, 1] = -2 * alphas[0]
    B[0, 0] = 1 - 2 * alphas[0]
    B[0, 1] = 2 * alphas[0]
    
    # Rechter Rand
    A[-1, -1] = 1 + 2 * alphas[-1]
    A[-1, -2] = -2 * alphas[-1]
    B[-1, -1] = 1 - 2 * alphas[-1]
    B[-1, -2] = 2 * alphas[-1]

    # Partitionierungsbedingungen und Flusskontinuität an den Schnittstellen
    for i in range(1, len(D)):
        if K_values and i <= len(K_values):
            idx = sum(nx[:i])  # Schnittstellenindex zwischen Schicht i-1 und i
            
            D1 = D[i-1]
            D2 = D[i]
            alpha1 = alphas[i-1]
            alpha2 = alphas[i]
            K = K_values[i-1]

            # Einführen von theta und phi für aus coeff.ipynb
            theta = D1 / (D1 + D2)
            phi = D2 / (D1 + D2)

            # Übergangsbedingung für "linke Seite" der Grenzfläche
            A[idx-1, idx-2] = -alpha1
            A[idx-1, idx-1] = (1 + 2 * alpha1 - theta * alpha1 + phi * alpha1)
            A[idx-1, idx] = -2 * alpha1 * phi * K

            B[idx-1, idx-2] = alpha1
            B[idx-1, idx-1] = (1 - 2 * alpha1 + theta * alpha1 - phi * alpha1)
            B[idx-1, idx] = 2 * alpha1 * phi * K

            # # Übergangsbedingung für "recht Seite" der Grenzfläche
            A[idx, idx-1] = -2 * alpha2 * theta / K
            A[idx, idx] = (1 + 2 * alpha2 - phi * alpha2 + theta * alpha2)
            A[idx, idx+1] = -alpha2

            B[idx, idx-1] = 2 * alpha2 * theta / K
            B[idx, idx] = (1 - 2 * alpha2 + phi * alpha2 - theta * alpha2)
            B[idx, idx+1] = alpha2
            
    return A, B

def solve_timestep(A, B, C_current):
    """
    Löst das lineare Gleichungssystem für den aktuellen Zeitschritt.

    Parameter:
        A (np.ndarray): Koeffizientenmatrix A.
        B (np.ndarray): Koeffizientenmatrix B.
        C_current (np.ndarray): Konzentrationsarray zum aktuellen Zeitpunkt.

    Rückgabe:
        np.ndarray: Aktualisiertes Konzentrationsarray für den nächsten Zeitschritt.
    """
    # Rechte Seite des Gleichungssystems berechnen
    b = B @ C_current

    # Lineares Gleichungssystem lösen
    C_new = np.linalg.solve(A, b)

    return C_new

def check_partitioning(layers, C_values):
    """
    Überprüft die Partitionierungsbedingungen an den Schnittstellen zwischen den Schichten.

    Parameter:
        layers (list von Layer): Liste der Layer-Objekte.
        C_values (list von np.ndarray): Liste der Konzentrationsarrays zu verschiedenen Zeiten.

    Rückgabe:
        list von list: Liste der Partitionierungsverhältnisse über die Zeit für jede Schnittstelle.
    """
    K_values = [layer.K_value for layer in layers if layer.K_value is not None]
    nx = [layer.nx for layer in layers]
    
    partitioning_checks = [[] for _ in range(len(K_values))]  # Eine Liste für jede Schnittstelle
    
    # Schleife über die gespeicherten Zeitschritte
    for C in C_values:
        # Schleife über alle Schnittstellen zwischen den Schichten
        for interface_idx in range(len(K_values)):
            idx_left = sum(nx[:interface_idx + 1]) - 1  # Letzter Index der linken Schicht
            idx_right = idx_left + 1  # Erster Index der rechten Schicht

            # Füge eine Überprüfung hinzu, um sicherzustellen, dass idx_right innerhalb der Grenzen von C liegt
            if idx_right >= len(C):
                continue  # Überspringe diese Iteration, wenn der Index außerhalb des Bereichs liegt
            
            C_left = C[idx_left]
            C_right = C[idx_right]
            
            # Vermeidung von Division durch Null
            if C_right == 0:
                K_calc = np.inf  
            else:
                K_calc = C_left / C_right
            
            # Speichern des berechneten Verhältnisses
            partitioning_checks[interface_idx].append(K_calc / K_values[interface_idx])
    
    return partitioning_checks

def run_simulation(layers, t_max, tabler):
    """
    Führt die Simulation über die angegebene Zeit durch und gibt die relevanten Daten zurück.

    Parameter:
        layers (list von Layer): Liste der Schichtenobjekte.
        t_max (float): Gesamte Simulationszeit in Sekunden.
        tabler (float): Zeitschrittgröße in Sekunden.

    Rückgabe:
        tuple: 
            - C_values: Liste der Konzentrationsprofile zu verschiedenen Zeitpunkten.
            - C_init: Initiales Konzentrationsprofil.
            - total_masses: Liste der Gesamtmassen zu verschiedenen Zeitpunkten.
            - x: Das räumliche Gitter.
            - partitioning_checks: Überprüfung der Partitionierungsverhältnisse an den Schichtgrenzen.
    """
    
    x = initialize_grid(layers)
    C_current, C_init = initialize_concentration(layers, x)
    A, B = initialize_matrices(layers, tabler)

    Nt = int(t_max / tabler)
    total_masses = []
    C_values = []
    
    # Für Partitionierungsüberprüfungen
    partitioning_checks = []

    # Zeitschleife über Migrationszeit
    for n in range(Nt):
        C_new = solve_timestep(A, B, C_current)
        C_current = C_new
        C_values.append(C_current.copy())

        total_mass = np.trapz(C_current, x)
        total_masses.append(total_mass)

    partitioning_checks = check_partitioning(layers, C_values)

    return C_values, C_init, total_masses, x, partitioning_checks

def calculate_migrated_mass_over_time(C_values, x, layers, tabler, calc_interval):
    """
    Berechnet die migrierte Masse im letzten Layer über die Zeit.
    
    Parameter:
        C_values (list von np.ndarray): Konzentrationsprofile über die Zeit.
        x (np.ndarray): Räumliches Gitter.
        layers (list von Layer): Liste der Schichtobjekte.
        tabler (float): Zeitschrittgröße [s].
        calc_interval (int): Intervall der Berechnung.

    Rückgabe:
        migrated_mass_over_time (np.ndarray): Liste der migrierten Massen über die Zeit.
        time_points (list): Liste der Zeitpunkte [s].
    """
    # Extrahiere den letzten Layer
    last_layer = layers[-1]
    nx_last = last_layer.nx
    density_last = last_layer.density
    
    # Bestimme den Start- und Endindex für den letzten Layer im Gitter
    start_idx = sum([layer.nx for layer in layers[:-1]])
    end_idx = start_idx + nx_last
    
    # Extrahiere die räumlichen Koordinaten des letzten Layers
    x_last_layer = x[start_idx:end_idx]
    
    # Speichert die migrierte Masse über die Zeit
    concentration_integrals_over_time = []
    
    # Speichert die entsprechenden Zeitpunkte
    time_points = []
    
    # Schleife über die gespeicherten Konzentrationsprofile in C_values mit dem angegebenen Intervall
    for i in range(0, len(C_values), calc_interval):
        # Extrahiere das Konzentrationsprofil im letzten Layer zu jedem Zeitschritt
        C_last_layer = C_values[i][start_idx:end_idx]
        
        # Berechne die migrierte Masse mittels der Trapezregel
        concentration_integral_last_layer = np.trapz(C_last_layer, x_last_layer)
        
        # Speichere die migrierte Masse für den aktuellen Zeitschritt
        concentration_integrals_over_time.append(concentration_integral_last_layer)
        
        # Berechne und speichere die entsprechende Zeit in Sekunden
        time_points.append(i * tabler)
        
    migrated_mass_over_time = np.array(concentration_integrals_over_time) * (density_last / 10)
    
    return migrated_mass_over_time, time_points

def plot_results(C_values, C_init, x, layers, tabler,
                 log_scale=False, steps_to_plot=10, save_path=None, show=True):
    """
    Erstellt einen Plot der Konzentrationsprofile zu verschiedenen Zeitpunkten während der Simulation.
    Nutzt automatisch tight_layout, damit Legende und Labels nicht abgeschnitten werden.
    """
    def get_time_label(t, tabler):
        s = t * tabler
        if s < 3600:
            return f't={s:.0f} s'
        if s < 3600 * 24:
            return f't={s/3600:.1f} h'
        return f't={s/(3600*24):.1f} d'

    Nt = len(C_values)
    if log_scale:
        ts = np.unique(np.logspace(0, np.log10(Nt-1),
                                   num=steps_to_plot, dtype=int))
        time_steps = np.insert(ts, 0, 0)
    else:
        time_steps = np.linspace(0, Nt-1, num=steps_to_plot, dtype=int).astype(int)

    fig, ax = plt.subplots(figsize=(10, 6))

    # Zeitlinien plotten
    time_lines = []
    for t in time_steps:
        lbl = get_time_label(t, tabler)
        if t == 0:
            ln, = ax.plot(x, C_init, color='k', linewidth=1.5, label=lbl)
        else:
            ln, = ax.plot(x, C_values[t], linewidth=1.5, label=lbl)
        time_lines.append(ln)

    # Layer-Flächen einzeichnen
    colors = {
        'LDPE': '#f16d1d','LLDPE': '#f16d1d','HDPE': '#32c864',
        'PP': '#c832ee','PET': '#646464','Kontaktphase': '#64e6df',
        'PS': '#8c564b','PEN': '#e377c2','HIPS': '#7f7f7f'
    }
    added = set()
    start_pos = x[0]
    ymin, ymax = ax.get_ylim()   # aktuelle Achsen-Limits holen
    for layer in layers:
        end_pos = start_pos + layer.d
        col = colors.get(layer.material, '#cccccc')
        lbl = layer.material if layer.material not in added else None
        ax.axvspan(start_pos, end_pos, ymin=0, ymax=1,
                facecolor=col, alpha=0.3, label=lbl)
        added.add(layer.material)
        start_pos = end_pos

    # Achsen , Labels
    ax.set_xlim(x[0], x[-1])
    ymin, ymax = 0, max(C_values[0]) + 0.1 * max(C_values[0])
    ax.set_ylim(ymin, ymax)
    ax.set_xlabel('Position x [cm]', fontsize=14)
    ax.set_ylabel('Konzentration [mg/kg]', fontsize=14)
    ax.tick_params(labelsize=12)

    # Layer-Hintergründe über gesamte Höhe mit axvspan
    added = set()
    start = x[0]
    for layer in layers:
        end = start + layer.d
        col = colors.get(layer.material, '#cccccc')
        # Label nur beim ersten Mal hinzufügen
        lbl = layer.material if layer.material not in added else None
        ax.axvspan(start, end, ymin=0, ymax=1, facecolor=col, alpha=0.3, label=lbl)
        added.add(layer.material)
        start = end

    # Legenden
    legend1 = ax.legend(handles=time_lines,
                        loc='upper right',
                        title='Zeitpunkte',
                        fontsize=12)
    ax.add_artist(legend1)
    layer_labels = []
    for layer in layers:
        if layer.material not in layer_labels:
            layer_labels.append(layer.material)

    # Dummy-Patches für die Legende
    legend_handles = [
        Patch(facecolor=colors[label], edgecolor='none', alpha=0.3, label=label)
        for label in layer_labels
    ]

    legend2 = ax.legend(handles=legend_handles,
                        loc='upper left',
                        title='Layer',
                        fontsize=12, 
                        bbox_to_anchor=(1, 1))
    ax.add_artist(legend2)

    # Zusätzlichen Rand lassen, damit die Layer-Legende rechts nicht abgeschnitten wird
    fig.subplots_adjust(left=0.1, right=0.8, top=0.95, bottom=0.12)

    # Speichern und Anzeigen
    if save_path:
        fn = os.path.join(save_path, 'concentration_plot.pdf')
        fig.savefig(fn)
        print(f"Konzentrationsplot gespeichert unter: {fn}")

    if show:
        plt.show()

    return fig



def plot_mass_conservation(total_masses, total_mass_init, t_max, Nt, plot_interval, save_path=None):
    """
    Plottet die rel. Abweichung der Gesamtmasse während der Simulation.
    
    Parameter:
        total_masses (list): Liste der Gesamtmassen während der Simulation.
        total_mass_init (float): Anfangsmasse.
        t_max (float): Gesamte Simulationszeit [s].
        Nt (int): Anzahl der Zeitschritte.
        plot_interval (int): Intervall, in dem geplottet wird.
        save_path (str, optional): Verzeichnis, in dem der Plot gespeichert wird.
    """
    # Berechnung der relativen Abweichung von der Anfangsmasse
    rel_deviation = ((np.array(total_masses) - total_mass_init) / total_mass_init) * 100
    
    # Zeitwerte für die Simulation
    time_values = np.linspace(0, t_max, Nt)
    
    # Plot erstellen
    plt.figure(figsize=(10, 6))
    plt.plot(time_values[::plot_interval] / (3600 * 24), rel_deviation[::plot_interval], 
             label=r'$\Delta c_{{\%}} = \frac{\int c(t) \, dx - \int c_{\mathrm{init}} \, dx}{\int c_{\mathrm{init}} \, dx} * 100$', 
             linewidth=2, color='#F06D1D')
    plt.axhline(0, color='k', linestyle='--', label="$\Delta c_{{\%}}$ = 0", linewidth=2)
    
    # Achsenbeschriftungen und Titel
    plt.xlabel("Zeit $[Tage]$", fontsize=14)
    plt.ylabel("$\Delta c_{{\%}}$ $[\%]$", fontsize=14)
    plt.xticks(fontsize=14)
    plt.yticks(fontsize=14)
    plt.legend(fontsize=14)

    # Plot speichern, wenn ein Pfad angegeben wurde
    if save_path:
        plot_filename = os.path.join(save_path, 'mass_conservation_plot.pdf')
        plt.savefig(plot_filename, bbox_inches='tight')
        print(f"Plot der Massenerhaltung gespeichert unter: {plot_filename}")
    
    plt.show()


def plot_migrated_mass_over_time(migrated_mass_over_time, time_points, save_path=None, show=True):
    """
    Plottet die spezifische Migrationsmenge im Verlauf der Zeit.
    
    Parameter:
        migrated_mass_over_time (list): Liste der migrierten Massen.
        time_points (list): Zeitschritte der Simulation [s].
        save_path (str, optional): Verzeichnis, in dem der Plot gespeichert wird.
    """
    # Konvertiere Zeitpunkte in Tage
    time_points_days = np.array(time_points) / (3600 * 24)
    
    # Plot der migrierten Masse
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(time_points_days, migrated_mass_over_time, linewidth=2, color='#F06D1D')

    # Finde den Punkt, an dem die migrierte Masse einen bestimmten Schwellenwert überschreitet
    threshold_index = np.argmax(migrated_mass_over_time > 1e-5)
    if migrated_mass_over_time[threshold_index] > 1e-5 and threshold_index != 0:
        threshold_time = time_points_days[threshold_index]
        ax.axvline(x=threshold_time, color='black', linestyle='--', label=f'$m_{{F}}(t)/A_{{P,F}} > 10^{{-5}} mg/dm^2$ nach {threshold_time:.2f} Tagen')

    # Achsenbeschriftungen und Titel
    ax.set_xlabel('Zeit $[Tage]$', fontsize=14)
    ax.set_ylabel('spez. Migrationsmenge $[mg/dm^2]$', fontsize=14)
    ax.tick_params(labelsize=14)
    
    if threshold_index != 0:
        ax.legend(fontsize=14)

    # Plot speichern, wenn ein Pfad angegeben wurde
    if save_path:
        plot_filename = os.path.join(save_path, 'migrated_mass_plot.pdf')
        fig.savefig(plot_filename, bbox_inches='tight')
        print(f"Migrationsplot gespeichert unter: {plot_filename}")
    
    if show:
        plt.show()

    return fig
