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
Generiere klare, präzise Anforderungen im JSON-Format. Achte dabei vor allem auf qualtiativ hochwertige Anforderungsformulierung.
Dies ist maßgeblich für die (dynamischen) Anforderungen und auch dem allgemeinen Projekterfolg,
um beispielsweis auch Mehrdeutigkeit von verschiedenen Projetkbeteiligten zu vermeiden!

Antworte ausschließlich mit gültigem JSON in folgender Struktur:
{
    "requirements": [
        {"title": "...", "description": "...", "category": "...", "status": "Entwurf"}
    ]
}
Regeln:
Halte dich vor allem an folgende allgemeine Regeln:
-  Maximiere Klarheit und Testbarkeit, das heißt messbare Anforderungen 
(gegebenenfalls Akzeptanzkriterien implizit in der description).
- Verwende kurze, prägnante Titel, die eindeutig sind und sich nicht mit anderen Anforderungen überschneidne oder auch widersprechen.
- 'status' ist immer 'Entwurf'.
-  Wenn Informationen fehlen, triff sinnvolle, konservative Annahmen. Beispielsweise können quantifizierbare Informationen wie Zahlenwerte bzw.
Constraints (Beschränkungen) (=,<,>,<=,>=,…<…<…,…<=…<=…) gesondert markiert oder hervorgehoben werden z.B. fett/kursiv gedruckt, farblich markiert.
Diese representieren in den meisten Fällen nämlich den Kern der Anforderung!.
- Verschachtele bzw. verpacke nicht mehrere Anforderungen in einer einzigen.
Das heißt auch nicht zu viele Sätze in der description für eine Anforderung erzeugen.
Im besten Fall sogar nur ein Satz erzeugen.
-	Qualitaitve hochwertige Anforderungen sollen immer generiert werden.
Das heißt vor allem für die Anofrderungsformulierung: eindeutig, vollständig, konsistent, korrekt, verifizierbar / testbar, notwendig, umsetzbar, rückverfolgbar (Traceability),
atomar (eine Aussage pro Anforderung (Orientierung z.B. an SMART-Prinizip möglich)
-	Bei Anforderungsgenerierung bzw. formulierung (auch berücksichitgen,
dass das Arbeitsergebnis die Anforderungsliste ist; Pflichten und Lastenheften sind auch wichtige Dokumente im Anforderungskontext (DIN 69901-5 und VDI/VDE 3694)
orientiere dich z.B. bitte an die VDI 2221
-	Da hauptäschlich, schwerpunktmäßig mechatronische Systeme (VDI 2206) betrachtet werden sollen,
gibt es weitere Normen, die berücksichtigt werden können, die zur Verbesserung der Generieurng von Anforderungen führen soll: ISO/IEC/IEEE 29148: Systems and software engineering — Life cycle processes — Requirements engineering, (ISO/IEC 25010: System and software quality models), (ISO/IEC/IEEE 12207: Software life cycle processes), ISO/IEC/IEEE 15288: System life cycle processes, ISO/IEC/IEEE 29148: Software Requirements Specification (SRS)
-	Da die Anforderungen im nächsten Schritt im MBSE-Kontext in SysML v2 konforme Anforderungen überführt werden sollen, kannst du dich vor allem auch schon an folgende Guidelines und Handbücher orientieren (von der INCOSE): INCOSE Guide to Writing Requirements, INCOSE Systems Engineering Handbook, INCOSE Needs and Requirements Manual. Die hier final erstellte Anforderungsliste dient dabei eben als Grundlage zur Abbildung von Anforderungen in einem SysML v2 konformen Systemmodell.

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
                json_fields.append(
                    f'"{col}": "Kategorie (z.B. nach der Hauptmerkmalliste nach Pahl/Beitz (hauptäschlich für Maschinen- und Anlagenbauprodukte): Geometrie, Kinematik, Kräfte, Energie, Stoff, Signal, Sicherheit, Ergonomie, Fertigung, Kontrolle, Montage, Transport, Gebrauch, Instandhaltung, Recycling, Kosten), Randbedingungen etc., vor allem für mechatronische Systeme weitere Kategorien möglich.)"'
                )
            elif col_lower in ['status']:
                json_fields.append(f'"{col}": "Entwurf"')
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
            "\n- Bestimme zürst die Komplexität des Produkts (einfach / mittel / komplex / sehr komplex)."
            "\n- Leite daraus eine angemessene Anzahl an Anforderungen ab."
            "\n- Falls eine Mindestanzahl angegeben ist, darf die Anzahl nicht darunter liegen, soll aber überschritten werden, wenn es die Komplexität erfordert."
            "\n- Setze eine harte Obergrenze: Erzeuge maximal 1000 Anforderungen."
            "\n- Wenn für ein sehr komplexes Produkt mehr nötig wären, priorisiere die wichtigsten Anforderungen und fasse ähnliche Anforderungen zusammen."
        )
    elif num_requirements_mode == "max" and num_requirements_value and num_requirements_value > 0:
        count_instruction = f"\n- Generiere MAXIMAL {num_requirements_value} Requirements."
    elif num_requirements_mode == "auto" or not num_requirements_mode:
        count_instruction = (
            "\n- Generiere so viele Requirements wie möglich und sinnvoll."
            "\n- Keine feste Obergrenze; nutze den Kontext maximal aus."
        )

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
    if has_pdf_context:
        pdf_instruction = (
            "\nWICHTIG - PDF-Kontext vorhanden:"
            "\n- Im User-Input findest du Auszüge aus einem Pflichtenheft (markiert mit '--- KONTEXT AUS PDF (PFLICHTENHEFT) ---')."
            "\n- Nutze den PDF-Text als zusätzliche Quelle für Anforderungen und Kontext."
            "\n- Falls keine Excel-Anforderungen vorhanden sind, extrahiere Anforderungen direkt aus dem PDF-Kontext."
        )

    # Improve only instruction
    if improve_only:
        improve_instruction = (
           """WICHTIG - NUR BESTEHENDE ANFORDERUNGEN VERBESSERN:
Du bist ein erfahrener Requirements Engineer mit Fokus auf qualitativ hochwertige Anforderungen (klar, prüfbar, umsetzbar,…; z.B. angelehnt an das SMART-Prinzip).

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

3. Ergänze in der Beschreibung, falls sinnvoll und es sich um qunatifizierbare, 
messbare technische Anforderungen handelt:
   - Akzeptanzkriterien
   - (sinnvolle/ gestzliche / übliche / genormte) Metriken / KPIs
   - technische Randbedingungen
   - Abhängigkeiten
 - wenn nötig referernzierst du sogar Normen oder Richtlinien, die diese Anforderung beschreiben oder zur Erfüllung dieser Anforderung berücksichtigt bzw. eingehalten werden müssen.

4. Behalte die ursprüngliche Bedeutung bei, verbessere aber Struktur, Präzision und Professionalität. 
Beachte dabei, dass die Anforderungen als Vorbereitung für MBSE-Modell (/-Projekte) dienen und im nächsten Schritt automatisiert in SysML v2 konforme Anforderungen transformiert werden und direkt in ein Systemmodell integriert werden. 

RESTRIKTIONEN:
- Du darfst KEINE neuen Anforderungen hinzufügen.
- Du darfst KEINE Anforderungen löschen.
- Die Anzahl der Requirements im Output muss EXAKT der Anzahl im Input entsprechen, außer wenn du auf redundate Anforderungen triffst. Dann darfst du daraus eine kompakte Anforderung formulieren, jedoch ohne Information oder Daten zu verlieren!
- Behalte die IDs zwingend bei, damit sie zugeordnet werden können.
"""
        )

    # Extend existing instruction
    if extend_existing:
        extend_instruction = (
          """ WICHTIG - BESTEHENDE ANFORDERUNGEN ERGÄNZEN:
- Im User-Input findest du eine Liste bestehender Anforderungen ("--- BESTEHENDE PROJEKT-ANFORDERUNGEN ---").
- Deine Aufgabe ist es, NEUE Anforderungen zu generieren, die dieses Projekt sinnvoll ergänzen und erweitern.
- Du darfst die bestehenden Anforderungen NICHT wiederholen oder verändern.
- Generiere NUR die neuen, zusätzlichen Anforderungen.

"""

        )

    # Compose the prompt if columns are provided
    if columns and isinstance(columns, list):
        json_structure = ',\n        '.join(json_fields)
        custom_prompt = f"""
Du bist ein erfahrener Requirements Engineer.
Erzeuge klare, präzise Anforderungen im JSON-Format.
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
- Fülle ALLE angegebenen Spalten mit sinnvollen Inhalt.
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

    # If columns are provided, customize the prompt
    if columns and isinstance(columns, list):
        json_fields = []
        for col in columns:
            col_lower = col.lower()
            if col_lower in ['titel', 'title']:
                json_fields.append(f'"{col}": "Kurzer, prägnanter Titel"')
            elif col_lower in ['beschreibung', 'description']:
                json_fields.append(f'"{col}": "Detaillierte Beschreibung mit Akzeptanzkriterien"')
            elif col_lower in ['kategorie', 'category']:
                json_fields.append(
                    f'"{col}": "Kategorie (z.B. nach der Hauptmerkmalliste nach Pahl/Beitz (hauptäschlich für Maschinen- und Anlagenbauprodukte): Geometrie, Kinematik, Kräfte, Energie, Stoff, Signal, Sicherheit, Ergonomie, Fertigung, Kontrolle, Montage, Transport, Gebrauch, Instandhaltung, Recycling, Kosten), Randbedingungen etc., vor allem für mechatronische Systeme weitere Kategorien möglich.)"'
                )
            elif col_lower in ['status']:
                json_fields.append(f'"{col}": "Entwurf"')
            elif col_lower in ['id']:
                json_fields.append(f'"{col}": "ID der ursprünglichen Anforderung (Zwingend beibehalten)"')
            else:
                json_fields.append(f'"{col}": ""')

    return base_prompt
