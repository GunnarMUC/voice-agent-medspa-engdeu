"""
GDPR-Filter – Entfernt personenbezogene Daten aus gescraptem Content.
Reduziert Risiko, dass Patientendaten in die Wissensbasis gelangen.
"""

import re
from typing import List, Optional


# Muster für potenziell personenbezogene Daten (Deutsch/Englisch)
PATTERNS = [
    # E-Mail
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]"),
    # Telefon (DE: 0123-456789, +49..., 0049...)
    (r"\+49\s*\d[\d\s/-]{6,14}\b", "[TELEFON]"),
    (r"0\d{2,4}[\s/-]?\d{3,}[\s/-]?\d{2,4}\b", "[TELEFON]"),
    (r"0049\s*\d[\d\s/-]{6,14}\b", "[TELEFON]"),
    # Geburtsdatum (DD.MM.YYYY, DD/MM/YYYY)
    (r"\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b", "[DATUM]"),
    # Patientennummern (typisch 6-10 Ziffern)
    (r"\bPat[- ]?Nr\.?\s*:?\s*\d{6,10}\b", "[PAT-NR]"),
    (r"\bPatientennummer\s*:?\s*\d{6,10}\b", "[PAT-NR]"),
    # IBAN (anonymisieren)
    (r"\bDE\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{2}\b", "[IBAN]"),
    # Adresszeilen mit Hausnummer (einfaches Muster)
    (r"\b(Straße|Str\.|Strassen|Weg|Platz|Allee)\s+[\w.-]+\s+\d+[a-z]?\b", "[ADRESSE]"),
]


def clean_text(text: str, extra_patterns: Optional[List[tuple]] = None) -> str:
    """
    Ersetzt personenbezogene Daten durch Platzhalter.

    Args:
        text: Roher Text (z.B. aus Markdown)
        extra_patterns: Zusätzliche (regex, replacement) Tupel

    Returns:
        Bereinigter Text
    """
    result = text
    all_patterns = PATTERNS + (extra_patterns or [])

    for pattern, replacement in all_patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result


def clean_document(doc: str) -> str:
    """
    Bereinigt ein ganzes Dokument.
    Entfernt auch übermäßige Leerzeilen und normalisiert Whitespace.
    """
    cleaned = clean_text(doc)
    # Mehrfache Leerzeilen reduzieren
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    return cleaned.strip()


def is_likely_safe(text: str) -> bool:
    """
    Heuristik: Enthält der Text wahrscheinlich sensible Daten?
    Gibt False zurück wenn Verdacht auf personenbezogene Daten.
    """
    suspicious = [
        "[EMAIL]",
        "[TELEFON]",
        "[PAT-NR]",
        "[IBAN]",
        "Patientennummer",
        "Versicherungsnummer",
        "Sozialversicherungs",
    ]
    lower = text.lower()
    return not any(s.lower() in lower for s in suspicious)
