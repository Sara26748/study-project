#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SysML v2 Requirements Generator
Liest Excel/CSV Anforderungstabellen und generiert SysML v2 textüllen Code
"""

import os
import pandas as pd
from pathlib import Path
from datetime import datetime

import subprocess
import sys

# Installiere fehlende Pakete automatisch
try:
    import openpyxl
except ImportError:
    print("Installiere openpyxl...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl", "--break-system-packages"])
    import openpyxl


def find_latest_requirements_file(downloads_folder):
    """
    Findet die neüste Excel- oder CSV-Datei im Downloads-Ordner

    Parameter:
        downloads_folder: Pfad zum Downloads-Ordner

    Rückgabe:
        Pfad zur neüsten Datei oder None
    """
    # Unterstuetzte Dateiformate
    extensions = ["*.xlsx", "*.xls", "*.csv"]

    # Alle passenden Dateien finden
    files = []
    for ext in extensions:
        files.extend(Path(downloads_folder).glob(ext))

    if not files:
        print("Keine Excel- oder CSV-Dateien im Downloads-Ordner gefunden!")
        return None

    # Nach Aenderungsdatum sortieren und neueste Datei zurueckgeben
    latest_file = max(files, key=lambda f: f.stat().st_mtime)
    print(f"Neueste Datei gefunden: {latest_file.name}")
    return latest_file


def read_requirements_table(file_path):
    """
    Liest die Anforderungstabelle aus Excel oder CSV

    Parameter:
        file_path: Pfad zur Datei

    Rückgabe:
        pandas DataFrame mit den Anforderungen
    """
    file_extension = file_path.suffix.lower()

    try:
        if file_extension == ".csv":
            # CSV-Datei einlesen
            df = pd.read_csv(file_path, encoding="utf-8")
        elif file_extension in [".xlsx", ".xls"]:
            # Excel-Datei einlesen
            df = pd.read_excel(file_path)
        else:
            print(f"Nicht unterstuetztes Dateiformat: {file_extension}")
            return None

        print(f"{len(df)} Anforderungen eingelesen")
        return df

    except Exception as e:
        print(f"Fehler beim Einlesen der Datei: {e}")
        return None


def sanitize_package_name(category):
    """
    Wandelt Kategorienamen in gültige SysML v2 Package-Namen um
    z.B. "Sicherheit" -> "SafetyRequirements"

    Parameter:
        category: Kategorienname aus der Tabelle

    Rückgabe:
        Gültiger Package-Name
    """
    # Mapping von deutschen Kategorien zu englischen Package-Namen
    category_mapping = {
        "Sicherheit": "SafetyRequirements",
        "Leistung": "PerformanceRequirements",
        "Funktional": "FunctionalRequirements",
        "Nicht-Funktional": "NonFunctionalRequirements",
        "Usability": "UsabilityRequirements",
        "Zuverlässigkeit": "ReliabilityRequirements",
        "Wartbarkeit": "MaintainabilityRequirements",
        "Kompatibilität": "CompatibilityRequirements",
    }

    # Wenn Mapping existiert, verwende es
    if category in category_mapping:
        return category_mapping[category]

    # Ansonsten: Leerzeichen entfernen und "Requirements" anhaengen
    sanitized = category.replace(" ", "").replace("-", "").replace("_", "")
    return f"{sanitized}Requirements"


def sanitize_requirement_id(req_id):
    """
    Wandelt Requirement-IDs in gültige SysML v2 Namen um
    z.B. "REQ-001" -> "REQ_001"

    Parameter:
        req_id: Requirement-ID aus der Tabelle

    Rückgabe:
        Gültiger Requirement-Name
    """
    # Ersetze Bindestriche durch Unterstriche
    return str(req_id).replace("-", "_").replace(" ", "_").replace(".", "_")


def escape_string(text):
    """
    Maskiert Sonderzeichen in Strings für SysML v2

    Parameter:
        text: Zu maskierender Text

    Rückgabe:
        Maskierter Text
    """
    if pd.isna(text):
        return ""

    text = str(text)
    # Backslashes und Anfuehrungszeichen maskieren
    text = text.replace("\\", "\\\\")
    text = text.replace('"', '\\"')
    return text


def generate_sysmlv2_code(df, output_path):
    """
    Generiert SysML v2 Code aus dem DataFrame

    Parameter:
        df: pandas DataFrame mit Anforderungen
        output_path: Pfad für die Ausgabedatei
    """
    # Spalten aus der Tabelle (in der angegebenen Reihenfolge)
    # Verantwortlicher, Revision, Version, ID, Anforderung, Beschreibung, Kategorie, Status

    # Sammle alle einzigartigen Kategorien
    categories = df["Kategorie"].unique()

    # Start der SysML v2 Datei
    sysml_code = []
    sysml_code.append("// SysML v2 Requirements Model")
    sysml_code.append("// Automatisch generiert am " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    sysml_code.append("")

    # Metadaten-Definition
    sysml_code.append("// ========================================")
    sysml_code.append("// Metadaten-Definition")
    sysml_code.append("// ========================================")
    sysml_code.append("")
    sysml_code.append("metadata def RequirementMetadata {")
    sysml_code.append("    attribute 'verantwortlicher';")
    sysml_code.append("    attribute 'revision';")
    sysml_code.append("    attribute 'version';")
    sysml_code.append("    attribute 'status';")
    sysml_code.append("}")
    sysml_code.append("")

    # Req package und view oeffnen
    sysml_code.append("package 'Requirements' {")
    sysml_code.append("view 'Requirements' : DS_Views::SymbolicViews::gv {")

    # Requirements generieren
    sysml_code.append("// ========================================")
    sysml_code.append("// Requirements Definitionen")
    sysml_code.append("// ========================================")
    sysml_code.append("")

    for index, row in df.iterrows():
        req_id = sanitize_requirement_id(row["ID"])
        req_name = escape_string(row["Anforderung"])
        req_description = escape_string(row["Beschreibung"])
        verantwortlicher = escape_string(row["Verantwortlicher"]).split("@", 1)[0]
        revision = escape_string(row["Revision"])
        if revision.lower() == "entwurf":
            revision = ""
        version = escape_string(row["Version"])
        status = escape_string(row["Status"])
        category = row["Kategorie"]

        sysml_code.append(f"requirement <REQ{req_id}> '{req_name}' {{")
        sysml_code.append("    doc /*")
        sysml_code.append(f"    {req_description}")
        sysml_code.append("    */")
        sysml_code.append("    ")
        sysml_code.append("    metadata RequirementMetadata {")
        sysml_code.append(f"        verantwortlicher = \"{verantwortlicher}\";")
        sysml_code.append(f"        revision = \"{revision}\";")
        sysml_code.append(f"        version = \"{version}\";")
        sysml_code.append(f"        status = \"{status}\";")
        sysml_code.append("    }")
        sysml_code.append("}")
        sysml_code.append("")

    sysml_code.append("}")
    sysml_code.append("}")

    # Package-Definitionen fuer jede Kategorie
    sysml_code.append("")
    sysml_code.append("// ========================================")
    sysml_code.append("// Requirement-Kategorien als Packages")
    sysml_code.append("// ========================================")
    sysml_code.append("")

    package_names = {}
    for category in categories:
        if category == "-":
            continue
        if pd.notna(category):
            package_name = sanitize_package_name(category)
            package_names[category] = package_name
            sysml_code.append(f"package '{package_name}' {{")
            sysml_code.append(f"    view '{package_name}' : DS_Views::SymbolicViews::gv {{")
            sysml_code.append("")

            for index, row in df.iterrows():
                req_id = sanitize_requirement_id(row["ID"])
                req_name = escape_string(row["Anforderung"])
                req_description = escape_string(row["Beschreibung"])
                verantwortlicher = escape_string(row["Verantwortlicher"])
                revision = escape_string(row["Revision"])
                if revision.lower() == "entwurf":
                    revision = ""
                version = escape_string(row["Version"])
                status = escape_string(row["Status"])
                category_ = row["Kategorie"]

                if sanitize_package_name(category_) == package_name:

                    sysml_code.append(f"requirement <REQ{req_id}> '{req_name}' {{")
                    sysml_code.append("    doc /*")
                    sysml_code.append(f"    {req_description}")
                    sysml_code.append("    */")
                    sysml_code.append("    ")
                    sysml_code.append("    metadata RequirementMetadata {")
                    sysml_code.append(f"        verantwortlicher = \"{verantwortlicher.split('@', 1)[0]}\";")
                    sysml_code.append(f"        revision = \"{revision}\";")
                    sysml_code.append(f"        version = \"{version}\";")
                    sysml_code.append(f"        status = \"{status}\";")
                    sysml_code.append("    }")
                    sysml_code.append("}")
                    sysml_code.append("")

                continue

            sysml_code.append("}")
            sysml_code.append("}")

    # Code in Datei schreiben
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(sysml_code))
        print(f"SysML v2 Code erfolgreich generiert: {output_path}")
        print(f"{len(df)} Requirements verarbeitet")
        print(f"{len(categories)} Kategorien gefunden")
        print(f"{len(categories) + 1} Views erstellt (1 Gesamtview + {len(categories)} Kategorie-Views)")

    except Exception as e:
        print(f"Fehler beim Schreiben der Datei: {e}")


def main():
    """
    Hauptfunktion - Orchestriert den gesamten Prozess
    """
    print("=" * 60)
    print("SysML v2 Requirements Generator")
    print("=" * 60)
    print()

    # 1. Downloads-Ordner finden
    downloads_folder = Path.home() / "Downloads"

    if not downloads_folder.exists():
        print(f"Downloads-Ordner nicht gefunden: {downloads_folder}")
        return

    print(f"Downloads-Ordner gefunden: {downloads_folder}")
    print()

    # 2. Neueste Requirements-Datei finden
    input_file = find_latest_requirements_file(downloads_folder)
    if input_file is None:
        return
    print()

    # 3. Tabelle einlesen
    df = read_requirements_table(input_file)
    if df is None:
        return
    print()

    # 4. Spaltennamen ueberpruefen
    expected_columns = [
        "Verantwortlicher",
        "Revision",
        "Version",
        "ID",
        "Anforderung",
        "Beschreibung",
        "Kategorie",
        "Status",
    ]

    if not all(col in df.columns for col in expected_columns):
        print("Die Tabelle enthält nicht alle erforderlichen Spalten!")
        print(f"   Erwartet: {expected_columns}")
        print(f"   Gefunden: {list(df.columns)}")
        return

    print("Alle erforderlichen Spalten vorhanden")
    print()

    # 5. SysML v2 Code generieren
    output_file = downloads_folder / "Req_SysMLv2_Code.txt"
    generate_sysmlv2_code(df, output_file)
    print()
    print("=" * 60)
    print("Fertig!")
    print("=" * 60)


# Skript ausfuehren
if __name__ == "__main__":
    main()
