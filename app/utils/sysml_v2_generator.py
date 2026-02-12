# Kopie von script_SysML/sysml_v2_generator.py für App-Import
# (Originaldatei bleibt erhalten)

import os
import pandas as pd
from pathlib import Path
from datetime import datetime
import subprocess
import sys

try:
    import openpyxl
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl", "--break-system-packages"])
    import openpyxl

def sanitize_package_name(category):
    if pd.isna(category):
        return "Uncategorized"
    return str(category).replace("-", "_").replace(" ", "_").replace(".", "_")

def sanitize_requirement_id(req_id):
    return str(req_id).replace("-", "_").replace(" ", "_").replace(".", "_")

def escape_string(text):
    if pd.isna(text):
        return ""
    text = str(text)
    text = text.replace("\\", "\\\\")
    text = text.replace('"', '\\"')
    return text

def generate_sysmlv2_code(df, output_path):
    categories = df["Kategorie"].unique()
    sysml_code = []
    sysml_code.append("// SysML v2 Requirements Model")
    sysml_code.append("// Automatisch generiert am " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    sysml_code.append("")
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
    sysml_code.append("package 'Requirements' {")
    sysml_code.append("view 'Requirements' : DS_Views::SymbolicViews::gv {")
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
            sysml_code.append("}")
            sysml_code.append("}")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(sysml_code))
    except Exception as e:
        print(f"Fehler beim Schreiben der Datei: {e}")
