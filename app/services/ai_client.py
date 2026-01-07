import os
import json
import re
import sys
from pathlib import Path
from openai import OpenAI

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import config

def generate_requirements(user_description: str | None, inputs: dict, columns: list = None, ai_model: str = None, num_requirements: int = None, product_system: str = None, has_excel_context: bool = False, improve_only: bool = False, extend_existing: bool = False) -> list[dict]:
    """
    Calls OpenAI API to generate requirements based on user description and inputs.

    Args:
        user_description (str | None): Optional user description of requirements.
        inputs (dict): Key-value pairs for additional context.
        columns (list): Optional list of column names for the project.
        ai_model (str): Optional AI model to use (overrides config default).
        num_requirements (int): Optional number of requirements to generate.
        product_system (str): Optional product system name for context.
        has_excel_context (bool): Whether Excel context is present in user_description.
        improve_only (bool): Whether to only improve existing requirements.
        extend_existing (bool): Whether to extend existing requirements.

    Returns:
        list[dict]: List of requirement dicts with dynamic columns based on project.
    
    Raises:
        ValueError: If OPENAI_API_KEY is not set.
        RuntimeError: If OpenAI API call fails or response is invalid.
    """
    # Get configuration
    api_key = config.OPENAI_API_KEY
    model = ai_model or config.OPENAI_MODEL or "gpt-4o-mini"
    system_prompt = config.get_system_prompt(columns, num_requirements, product_system, has_excel_context, improve_only, extend_existing)

    # ... rest of the function stays the same

    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable must be set.")

    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)

    # Build user message from user_description and inputs
    user_message_parts = []
    
    if product_system and product_system.strip():
        user_message_parts.append(f"Produktsystem: {product_system.strip()}")
    
    if user_description and user_description.strip():
        user_message_parts.append(f"Beschreibung: {user_description.strip()}")
    
    if inputs:
        user_message_parts.append("\nZusätzliche Informationen:")
        for key, value in inputs.items():
            if key and value:
                user_message_parts.append(f"- {key}: {value}")
    
    if not user_message_parts:
        user_message = "Bitte generiere allgemeine Software-Anforderungen."
    else:
        user_message = "\n".join(user_message_parts)

    # Build developer message with dynamic JSON schema
    if columns and isinstance(columns, list):
        # Build JSON structure based on columns
        json_fields = []
        for col in columns:
            col_lower = col.lower()
            if col_lower in ['titel', 'title']:
                json_fields.append(f'      "{col}": "Kurzer, prägnanter Titel"')
            elif col_lower in ['beschreibung', 'description']:
                json_fields.append(f'      "{col}": "Detaillierte Beschreibung mit Akzeptanzkriterien"')
            elif col_lower in ['kategorie', 'category']:
                json_fields.append(f'      "{col}": "Kategorie (z.B. Funktional, Nicht-Funktional, etc.)"')
            elif col_lower in ['status']:
                json_fields.append(f'      "{col}": "Offen"')
            else:
                json_fields.append(f'      "{col}": "Passender Wert für {col}"')
        
        # Add is_quantifiable field
        json_fields.append('      "is_quantifiable": true oder false')
        
        json_example = "{\n" + ",\n".join(json_fields) + "\n    }"
        
        developer_message = f"""Du musst ausschließlich mit gültigem JSON antworten.
Das JSON-Format muss exakt dieser Struktur folgen:
{{
  "requirements": [
    {json_example}
  ]
}}

Wichtig: 
- Fülle ALLE Spalten ({', '.join(columns)}) mit sinnvollen Werten.
- Setze "is_quantifiable" auf true, wenn die Anforderung quantitativ messbar ist (z.B. Performance-Werte, Zeitlimits, Durchsatz, Speicherverbrauch, etc.).
- Setze "is_quantifiable" auf false für qualitative Anforderungen (z.B. Benutzerfreundlichkeit, Design, etc.).
Antworte NUR mit diesem JSON, ohne zusätzlichen Text davor oder danach."""
    else:
        # Fallback to default structure
        developer_message = """Du musst ausschließlich mit gültigem JSON antworten.
Das JSON-Format muss exakt dieser Struktur folgen:
{
  "requirements": [
    {
      "title": "Kurzer, prägnanter Titel",
      "description": "Detaillierte Beschreibung mit Akzeptanzkriterien",
      "category": "Kategorie (z.B. Funktional, Nicht-Funktional, etc.)",
      "status": "Offen",
      "is_quantifiable": true oder false
    }
  ]
}

Wichtig: 
- Setze "is_quantifiable" auf true, wenn die Anforderung quantitativ messbar ist (z.B. Performance-Werte, Zeitlimits, Durchsatz, etc.).
- Setze "is_quantifiable" auf false für qualitative Anforderungen (z.B. Benutzerfreundlichkeit, Design, etc.).

Antworte NUR mit diesem JSON, ohne zusätzlichen Text davor oder danach."""

    try:
        # Call OpenAI Chat Completions API
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "developer", "content": developer_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.2,
            max_tokens=4000
        )

        # Extract response content
        response_text = response.choices[0].message.content.strip()

        # Parse JSON response
        requirements = _parse_json_response(response_text, columns, num_requirements)
        
        return requirements

    except Exception as e:
        raise RuntimeError(f"OpenAI request failed: {str(e)}")


def _parse_json_response(response_text: str, columns: list = None, num_requirements: int = None) -> list[dict]:
    """
    Robustly parse JSON response from OpenAI, with fallback to regex extraction.

    Args:
        response_text (str): Raw response text from OpenAI.
        columns (list): Optional list of column names for validation.
        num_requirements (int): Optional number of requirements to return.

    Returns:
        list[dict]: List of validated and normalized requirement dicts.
    
    Raises:
        RuntimeError: If JSON cannot be parsed or is invalid.
    """
    # Try direct JSON parsing first
    try:
        data = json.loads(response_text)
        if isinstance(data, dict) and "requirements" in data:
            return _validate_and_normalize_requirements(data["requirements"], columns, num_requirements)
    except json.JSONDecodeError:
        pass

    # Fallback: Extract JSON block using regex
    # Look for JSON object that contains "requirements"
    json_pattern = r'\{[^{}]*"requirements"[^{}]*\[[^\]]*\][^{}]*\}'
    # More robust pattern that handles nested structures
    json_pattern = r'\{(?:[^{}]|\{[^{}]*\})*"requirements"(?:[^{}]|\{[^{}]*\})*\[(?:[^\[\]]|\[[^\[\]]*\])*\](?:[^{}]|\{[^{}]*\})*\}'
    
    matches = re.findall(json_pattern, response_text, re.DOTALL)
    
    for match in matches:
        try:
            data = json.loads(match)
            if isinstance(data, dict) and "requirements" in data:
                return _validate_and_normalize_requirements(data["requirements"], columns, num_requirements)
        except json.JSONDecodeError:
            continue

    # If still no valid JSON found, try to extract just the array
    array_pattern = r'\[\s*\{[^\]]+\}\s*\]'
    array_matches = re.findall(array_pattern, response_text, re.DOTALL)
    
    for match in array_matches:
        try:
            data = json.loads(match)
            if isinstance(data, list):
                return _validate_and_normalize_requirements(data, columns, num_requirements)
        except json.JSONDecodeError:
            continue

    raise RuntimeError("Invalid JSON response from model: Could not parse requirements structure.")


def _validate_and_normalize_requirements(requirements: list, columns: list = None, num_requirements: int = None) -> list[dict]:
    """
    Validate and normalize requirements list with support for dynamic columns.

    Args:
        requirements (list): Raw requirements list from parsed JSON.
        columns (list): Optional list of column names to validate against.
        num_requirements (int): Optional number of requirements to return.

    Returns:
        list[dict]: Validated and normalized requirements.
    
    Raises:
        RuntimeError: If requirements structure is invalid.
    """
    if not isinstance(requirements, list):
        raise RuntimeError("Requirements must be a list.")

    normalized = []
    
    for req in requirements:
        if not isinstance(req, dict):
            continue
        
        # If columns are provided, use them for validation
        if columns and isinstance(columns, list):
            normalized_req = {}
            has_required_data = False
            
            for col in columns:
                value = str(req.get(col, "")).strip()
                normalized_req[col] = value
                
                # Check if we have at least some meaningful data
                if value:
                    has_required_data = True
            
            # Only add if we have at least some data
            if has_required_data:
                normalized.append(normalized_req)
        else:
            # Fallback to default validation (backward compatibility)
            title = req.get("title", "").strip()
            description = req.get("description", "").strip()
            
            if not title or not description:
                continue  # Skip invalid requirements
            
            # Set defaults for optional fields
            category = req.get("category", "").strip()
            status = req.get("status", "Offen").strip()
            
            # Ensure status is "Offen" as per requirements
            if status != "Offen":
                status = "Offen"
            
            normalized.append({
                "title": title,
                "description": description,
                "category": category,
                "status": status
            })
    
    if not normalized:
        raise RuntimeError("No valid requirements found in response.")
    
    # Limit to specified number or default to 10
    limit = num_requirements if num_requirements and num_requirements > 0 else 10
    return normalized[:limit]


def detect_conflicts(requirements_list: list[dict]) -> list[dict]:
    """
    Analyzes a list of requirements for logical contradictions using AI.

    Args:
        requirements_list (list[dict]): List of dicts representing requirements (title, description).

    Returns:
        list[dict]: List of detected conflicts.
    """
    # Get configuration
    api_key = config.OPENAI_API_KEY
    model = config.OPENAI_MODEL or "gpt-4o-mini"
    
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable must be set.")
    
    if not requirements_list or len(requirements_list) < 2:
        return []

    client = OpenAI(api_key=api_key)

    # Prepare requirements text
    req_text = ""
    for idx, req in enumerate(requirements_list):
        req_text += f"ID {req['id']}: {req['title']}\nDescription: {req['description']}\n\n"

    system_prompt = """
    Du bist ein Experte für Requirements Engineering und Logik-Prüfung.
    Deine Aufgabe ist es, eine Liste von Anforderungen auf logische Widersprüche (Konflikte) zu analysieren.
    
    Analysiere die Anforderungen sorgfältig. Ein Konflikt besteht, wenn zwei Anforderungen nicht gleichzeitig erfüllt werden können.
    
    Antworte ausschließlich mit gültigem JSON in folgender Struktur:
    {
      "conflicts": [
        {
          "req_id_1": "ID der ersten Anforderung",
          "req_id_2": "ID der zweiten Anforderung",
          "description": "Erklärung des Konflikts",
          "severity": "Hoch" (oder "Mittel", "Niedrig")
        }
      ]
    }
    
    Wenn keine Konflikte gefunden werden, antworte mit: {"conflicts": []}
    """

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Hier sind die Anforderungen:\n\n{req_text}"}
            ],
            temperature=0.1,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )

        response_text = response.choices[0].message.content.strip()
        data = json.loads(response_text)
        return data.get("conflicts", [])

    except Exception as e:
        print(f"Error checking conflicts: {e}")
        return []


def generate_test_cases(title: str, description: str) -> str:
    """
    Generates Gherkin test cases and acceptance criteria for a single requirement.

    Args:
        title (str): Requirement title.
        description (str): Requirement description.

    Returns:
        str: Generated test cases text.
    """
    api_key = config.OPENAI_API_KEY
    model = config.OPENAI_MODEL or "gpt-4o-mini"
    
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    client = OpenAI(api_key=api_key)

    system_prompt = """
    Du bist ein QA-Test-Ingenieur.
    Deine Aufgabe ist es, für eine gegebene Software-Anforderung detaillierte Testfälle zu erstellen.
    
    Format:
    1. Akzeptanzkriterien (Liste)
    2. Gherkin Szenarien (Given-When-Then)
    
    Antworte direkt mit dem Text (Markdown), ohne JSON-Formatierung.
    """
    
    user_message = f"Anforderung: {title}\nBeschreibung: {description}\n\nBitte erstelle Testfälle."

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
            max_tokens=800
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Fehler bei der Generierung: {str(e)}"
