# Modellierung des Migrationsverhaltens
Dieses Projekt umfasst zwei Modelle zur Berechnung der Migration von Additiven in Kunststoffen: das **Single-Layer (SL) Modell** und das **Multi-Layer (ML) Modell**. Beide Modelle bieten eine Python-basierte Simulation zur Analyse der Migration von Substanzen in verschiedenen Schichten von Polymermaterialien.

## Inhaltsverzeichnis
- [Überblick](#überblick)
- [Voraussetzungen](#voraussetzungen)
- [Installation unter Windows](#installation-unter-windows)
- [Anwendung starten](#anwendung-starten)
- [EXE-Build (One-Folder) unter Windows](#exe-build-one-folder-unter-windows)

## Überblick
Das **SL-Modell** (Single-Layer) simuliert die Migration von Substanzen aus einer einzigen Polymerschicht in Kontakt mit einem Medium, während das **ML-Modell** (Multi-Layer) den Einfluss mehrerer Schichten auf die Migration untersucht. Beide Modelle berücksichtigen Diffusionsprozesse und thermodynamische Parameter und verwenden numerische Methoden, um die Migrationsprozesse über die Zeit zu analysieren.

## Voraussetzungen
- Windows 10/11
- Python 3.10+ (empfohlen: aktuelles Python 3.x)
- Git (optional, für das Klonen des Repos)

## Installation unter Windows
1) Repository klonen oder als ZIP herunterladen.
2) Ordner öffnen und eine virtuelle Umgebung erstellen:

```bash
python -m venv .venv
```

3) Virtuelle Umgebung aktivieren:

```bash
.venv\Scripts\activate
```

4) Abhängigkeiten installieren:

```bash
pip install -r requirements.txt
```

## Anwendung starten
```bash
python gui\main.py
```

## EXE-Build (One-Folder) unter Windows
Wichtig: Der Build muss auf Windows erfolgen (PyInstaller cross-compiliert nicht zuverlässig von macOS/Linux).

1) Stelle sicher, dass die venv aktiv ist und die Abhängigkeiten installiert sind.
2) Build starten:

```bash
pyinstaller --noconfirm --clean fdm_migration.spec
```

3) Ergebnis:
- `dist\FDM-Migration\FDM-Migration.exe`

Hinweis:
- Wenn du zur Laufzeit auf externe Dateien zugreifen willst (z. B. `data/`), musst du diese als `datas` in der Spec mitgeben oder neben die EXE legen.
