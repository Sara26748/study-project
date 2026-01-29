import os

# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
SYSTEM_PROMPT_PATH = os.getenv('SYSTEM_PROMPT_PATH')
SYSTEM_PROMPT = os.getenv('SYSTEM_PROMPT')

def get_system_prompt(columns=None, num_requirements=None, product_system=None, has_excel_context=False, has_pdf_context=False, improve_only=False, extend_existing=False, output_language=None, num_requirements_mode=None, num_requirements_value=None):
    """
    Get system prompt, optionally customized for dynamic columns.
    """
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
- Fülle alle Felder sinnvoll.
- Wenn Informationen fehlen, triff sinnvolle, konservative Annahmen.
"""
    base_prompt = DEFAULT_SYSTEM_PROMPT

    # Set up all variables for prompt construction
    json_fields = []
    count_instruction = ""
    product_context = ""
    language_instruction = ""
    excel_instruction = ""
    pdf_instruction = ""
    improve_instruction = ""
    extend_instruction = ""

    # If columns are provided, customize the prompt
    if columns and isinstance(columns, list):
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
                json_fields.append(f'"{col}": ""')

    # Count instruction
    if num_requirements_mode == "exact" and num_requirements_value and num_requirements_value > 0:
        count_instruction = f"\n- Generiere EXAKT {num_requirements_value} Requirements."
    elif num_requirements_mode == "min" and num_requirements_value and num_requirements_value > 0:
        count_instruction = (
            f"\n- Generiere MINDESTENS {num_requirements_value} Requirements."
            "\n- Bestimme zuerst die Komplexität des Produkts (einfach / mittel / komplex / sehr komplex)."
            "\n- Leite daraus eine angemessene Anzahl an Anforderungen ab."
            "\n- Falls eine Mindestanzahl angegeben ist, darf die Anzahl nicht darunter liegen, soll aber überschritten werden, wenn es die Komplexität erfordert."
            "\n- Setze eine harte Obergrenze: Erzeuge maximal 30 Anforderungen."
            "\n- Wenn für ein sehr komplexes Produkt mehr nötig wären, priorisiere die wichtigsten Anforderungen und fasse ähnliche Anforderungen zusammen, statt mehr als 30 zu erzeugen."
        )
    elif num_requirements_mode == "max" and num_requirements_value and num_requirements_value > 0:
        count_instruction = f"\n- Generiere MAXIMAL {num_requirements_value} Requirements."

    # Product context
    if product_system and product_system.strip():
        product_context = f"\n- Alle Anforderungen beziehen sich auf das Produktsystem: {product_system.strip()}"

    # Language instruction
    if output_language and output_language.strip():
        language_instruction = f"\n- Formuliere alle Inhalte ausschließlich auf {output_language.strip()}."

    # Excel context instruction
    if has_excel_context:
        excel_instruction = (
            "\nWICHTIG - Excel-Kontext vorhanden:"
            "\n- Im User-Input findest du bestehende Anforderungen aus einer Excel-Datei (markiert mit '--- KONTEXT AUS EXCEL-DATEI ---')."
            "\n- Du MUSST diese bestehenden Anforderungen verbessern, aktualisieren und in deine Ausgabe aufnehmen."
            "\n- Zusätzlich sollst du neue Anforderungen erstellen, die der User explizit anfordert oder die zum Kontext passen."
            "\n- Die bestehenden Anforderungen aus Excel sollen verbessert/vervollständigt werden, nicht ignoriert."
            "\n- Wenn der User explizit neue Anforderungen anfordert (z.B. 'erstelle auch eine Anforderung über X'), musst du diese zusätzlich erstellen."
            "\n- Die Gesamtzahl der Requirements sollte die bestehenden aus Excel + die neuen explizit angeforderten + weitere passende Anforderungen umfassen."
        )

    # PDF context instruction
    if 'has_pdf_context' in locals() and has_pdf_context:
        pdf_instruction = (
            "\nWICHTIG - PDF-Kontext vorhanden:"
            "\n- Im User-Input findest du Auszüge aus einem Pflichtenheft (markiert mit '--- KONTEXT AUS PDF (PFLICHTENHEFT) ---')."
            "\n- Nutze den PDF-Text als zusätzliche Quelle für Anforderungen und Kontext."
            "\n- Falls keine Excel-Anforderungen vorhanden sind, extrahiere Anforderungen direkt aus dem PDF-Kontext."
        )

    # Improve only instruction
    if improve_only:
        improve_instruction = (
            "\nWICHTIG - NUR BESTEHENDE ANFORDERUNGEN VERBESSERN:"
            "\nDu bist ein erfahrener Requirements Engineer und Software-Architekt mit Fokus auf saubere, prüfbare und umsetzbare Projektanforderungen (nach ISO/IEC 25010, SMART, und Best Practices aus dem Requirements Engineering)."
            "\nBitte führe folgende Schritte aus (INTERN, NICHT IM OUTPUT):"
            "\n1. Analysiere jede Anforderung auf:"
            "\n   - Unklarheit"
            "\n   - Mehrdeutigkeit"
            "\n   - Fehlende Messbarkeit"
            "\n   - Fehlenden Kontext"
            "\n   - Technische oder fachliche Ungenauigkeit"
            "\n2. Formuliere jede Anforderung neu, sodass sie:"
            "\n   - eindeutig"
            "\n   - messbar (wo sinnvoll)"
            "\n   - testbar"
            "\n   - realistisch"
            "\n   - konsistent mit Softwareprojekten ist"
            "\n3. Ergänze, falls sinnvoll:"
            "\n   - Akzeptanzkriterien"
            "\n   - Metriken / KPIs"
            "\n   - technische Randbedingungen"
            "\n   - Abhängigkeiten"
            "\n4. Behalte die ursprüngliche Bedeutung bei, verbessere aber Struktur, Präzision und Professionalität."
            "\nRESTRIKTIONEN:"
            "\n- Du darfst KEINE neuen Anforderungen hinzufügen."
            "\n- Du darfst KEINE Anforderungen löschen."
            "\n- Die Anzahl der Requirements im Output muss EXAKT der Anzahl im Input entsprechen."
            "\n- Behalte die IDs zwingend bei, damit sie zugeordnet werden können."
        )

    # Extend existing instruction
    if extend_existing:
        extend_instruction = (
            "\nWICHTIG - BESTEHENDE ANFORDERUNGEN ERGÄNZEN:"
            "\n- Im User-Input findest du eine Liste bestehender Anforderungen ('--- BESTEHENDE PROJEKT-ANFORDERUNGEN ---')."
            "\n- Deine Aufgabe ist es, NEUE Anforderungen zu generieren, die dieses Projekt sinnvoll ergänzen und erweitern."
            "\n- Du darfst die bestehenden Anforderungen NICHT wiederholen oder verändern."
            "\n- Generiere NUR die neuen, zusätzlichen Anforderungen."
            "\n- Analysiere die Lücken in den bestehenden Anforderungen und fülle diese."
        )

    # Compose the prompt if columns are provided
    if columns and isinstance(columns, list):
        json_structure = ',\n        '.join(json_fields)
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
- WICHTIG: Antworte NUR und AUSSCHLIESSLICH mit dem JSON-Objekt. Kein einleitender Text, keine Erklärungen.{count_instruction}{product_context}{language_instruction}{excel_instruction}{pdf_instruction}{improve_instruction}{extend_instruction}
"""
        return custom_prompt

    # Fallback: use base prompt
    if SYSTEM_PROMPT_PATH and os.path.exists(SYSTEM_PROMPT_PATH):
        with open(SYSTEM_PROMPT_PATH, 'r', encoding='utf-8') as f:
            base_prompt = f.read().strip()
    elif SYSTEM_PROMPT:
        base_prompt = SYSTEM_PROMPT
    else:
        base_prompt = DEFAULT_SYSTEM_PROMPT

    return base_prompt
