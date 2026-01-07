import os

# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
SYSTEM_PROMPT_PATH = os.getenv('SYSTEM_PROMPT_PATH')
SYSTEM_PROMPT = os.getenv('SYSTEM_PROMPT')

# Default System Prompt if none provided
DEFAULT_SYSTEM_PROMPT = """
Du bist ein erfahrener Requirements Engineer.
Erzeuge klare, testbare, präzise Software-Anforderungen im JSON-Format.
Antworte ausschließlich mit gültigem JSON in folgender Struktur:
{
  "requirements": [
    {"title": "...", "description": "...", "category": "...", "status": "Offen"}
  ]
}
Regeln:
- Maximiere Klarheit und Testbarkeit (Akzeptanzkriterien implizit in description).
- Verwende kurze, prägnante Titel.
- 'status' ist immer 'Offen'.
- Wenn Informationen fehlen, triff sinnvolle, konservative Annahmen.
"""

def get_system_prompt(columns=None, num_requirements=None, product_system=None, has_excel_context=False, improve_only=False, extend_existing=False):
    """
    Get system prompt, optionally customized for dynamic columns.
    
    Args:
        columns (list): Optional list of column names for the project
        num_requirements (int): Optional number of requirements to generate
        product_system (str): Optional product system name for context
        has_excel_context (bool): Whether Excel context is provided
        improve_only (bool): Whether to only improve existing requirements
        extend_existing (bool): Whether to extend existing requirements (add new ones)
    
    Returns:
        str: System prompt text
    """
    if SYSTEM_PROMPT_PATH and os.path.exists(SYSTEM_PROMPT_PATH):
        with open(SYSTEM_PROMPT_PATH, 'r', encoding='utf-8') as f:
            base_prompt = f.read().strip()
    elif SYSTEM_PROMPT:
        base_prompt = SYSTEM_PROMPT
    else:
        base_prompt = DEFAULT_SYSTEM_PROMPT
    
    # If columns are provided, customize the prompt
    if columns and isinstance(columns, list):
        # Build JSON structure based on columns
        json_fields = []
        for col in columns:
            col_lower = col.lower()
            if col_lower in ['titel', 'title']:
                json_fields.append(f'"{col}": "Kurzer, prägnanter Titel"')
            elif col_lower in ['beschreibung', 'description']:
                json_fields.append(f'"{col}": "Detaillierte Beschreibung mit Akzeptanzkriterien"')
            elif col_lower in ['kategorie', 'category']:
                json_fields.append(f'"{col}": "Kategorie (z.B. Funktional, Nicht-Funktional, etc.)"')
            elif col_lower in ['status']:
                json_fields.append(f'"{col}": "Offen"')
            elif col_lower in ['id']:
                 json_fields.append(f'"{col}": "ID der ursprünglichen Anforderung (Zwingend beibehalten)"')
            else:
                json_fields.append(f'"{col}": "Passender Wert für {col}"')
        
        json_structure = "{\n      " + ",\n      ".join(json_fields) + "\n    }"
        
        # Build requirement count instruction
        count_instruction = ""
        if improve_only:
             count_instruction = "\n- WICHTIG: Die Anzahl der Anforderungen muss EXAKT der Anzahl der eingelesenen Anforderungen entsprechen. Füge KEINE neuen hinzu."
        elif num_requirements and num_requirements > 0:
            count_instruction = f"\n- Generiere EXAKT {num_requirements} Requirements."
        else:
            count_instruction = "\n- Die Anzahl der Requirements hängt vom User-Input ab. Wenn der User eine konkrete Anzahl fordert (z.B. 'Erstelle eine Anforderung'), halte dich strikt daran. Ansonsten generiere passend zum Umfang 3-10 Requirements."
        
        # Build product system context
        product_context = ""
        if product_system and product_system.strip():
            product_context = f"\n- Alle Anforderungen beziehen sich auf das Produktsystem: {product_system.strip()}"
        
        # Build Excel context instruction
        excel_instruction = ""
        if has_excel_context:
            excel_instruction = """
WICHTIG - Excel-Kontext vorhanden:
- Im User-Input findest du bestehende Anforderungen aus einer Excel-Datei (markiert mit "--- KONTEXT AUS EXCEL-DATEI ---").
- Du MUSST diese bestehenden Anforderungen verbessern, aktualisieren und in deine Ausgabe aufnehmen.
- Zusätzlich sollst du neue Anforderungen erstellen, die der User explizit anfordert oder die zum Kontext passen.
- Die bestehenden Anforderungen aus Excel sollen verbessert/vervollständigt werden, nicht ignoriert.
- Wenn der User explizit neue Anforderungen anfordert (z.B. "erstelle auch eine Anforderung über X"), musst du diese zusätzlich erstellen.
- Die Gesamtzahl der Requirements sollte die bestehenden aus Excel + die neuen explizit angeforderten + weitere passende Anforderungen umfassen."""

        # Build Improve Only instruction
        improve_instruction = ""
        if improve_only:
            improve_instruction = """
WICHTIG - NUR BESTEHENDE ANFORDERUNGEN VERBESSERN:
Du bist ein erfahrener Requirements Engineer und Software-Architekt mit Fokus auf saubere, prüfbare und umsetzbare Projektanforderungen (nach ISO/IEC 25010, SMART, und Best Practices aus dem Requirements Engineering).

Bitte führe folgende Schritte aus (INTERN, NICHT IM OUTPUT):
1. Analysiere jede Anforderung auf:
   - Unklarheit
   - Mehrdeutigkeit
   - Fehlende Messbarkeit
   - Fehlenden Kontext
   - Technische oder fachliche Ungenauigkeit

2. Formuliere jede Anforderung neu, sodass sie:
   - eindeutig
   - messbar (wo sinnvoll)
   - testbar
   - realistisch
   - konsistent mit Softwareprojekten ist

3. Ergänze, falls sinnvoll:
   - Akzeptanzkriterien
   - Metriken / KPIs
   - technische Randbedingungen
   - Abhängigkeiten

4. Behalte die ursprüngliche Bedeutung bei, verbessere aber Struktur, Präzision und Professionalität.

RESTRIKTIONEN:
- Du darfst KEINE neuen Anforderungen hinzufügen.
- Du darfst KEINE Anforderungen löschen.
- Die Anzahl der Requirements im Output muss EXAKT der Anzahl im Input entsprechen.
- Behalte die IDs zwingend bei, damit sie zugeordnet werden können.
"""
        # Build Extend Existing instruction
        extend_instruction = ""
        if extend_existing:
             extend_instruction = """
WICHTIG - BESTEHENDE ANFORDERUNGEN ERGÄNZEN:
- Im User-Input findest du eine Liste bestehender Anforderungen ("--- BESTEHENDE PROJEKT-ANFORDERUNGEN ---").
- Deine Aufgabe ist es, NEUE Anforderungen zu generieren, die dieses Projekt sinnvoll ergänzen und erweitern.
- Du darfst die bestehenden Anforderungen NICHT wiederholen oder verändern.
- Generiere NUR die neuen, zusätzlichen Anforderungen.
- Analysiere die Lücken in den bestehenden Anforderungen und fülle diese.
"""
        
        custom_prompt = f"""
Du bist ein erfahrener Requirements Engineer.
Erzeuge klare, testbare, präzise Software-Anforderungen im JSON-Format.

Das Projekt verwendet folgende Spalten: {', '.join(columns)}

Antworte ausschließlich mit gültigem JSON in folgender Struktur:
{{
  "requirements": [
    {json_structure}
  ]
}}

Regeln:
- Maximiere Klarheit und Testbarkeit (Akzeptanzkriterien implizit in Beschreibung).
- Verwende kurze, prägnante Titel.
- Fülle ALLE angegebenen Spalten mit sinnvollen Werten.
- Wenn Informationen fehlen, triff sinnvolle, konservative Annahmen.
- WICHTIG: Antworte NUR und AUSSCHLIESSLICH mit dem JSON-Objekt. Kein einleitender Text, keine Erklärungen.{count_instruction}{product_context}{excel_instruction}{improve_instruction}{extend_instruction}
"""
        return custom_prompt
    
    return base_prompt