from pathlib import Path
from typing import List, Dict, Optional

import pytesseract
from PIL import Image

# Trained NER model (loaded lazily)
_prescription_ner_model = None


def _get_ml_base() -> Path:
    """Project root: parent of backend/."""
    return Path(__file__).resolve().parent.parent


def _load_prescription_ner_model():
    """Load trained prescription NER model from ml/models/prescription_ner if present."""
    global _prescription_ner_model
    if _prescription_ner_model is not None:
        return _prescription_ner_model
    model_path = _get_ml_base() / "ml" / "models" / "prescription_ner"
    if not model_path.exists():
        return None
    try:
        import spacy
        _prescription_ner_model = spacy.load(str(model_path))
        return _prescription_ner_model
    except Exception:
        return None


def _parse_line_with_ner(nlp, line: str) -> Optional[Dict]:
    """Run NER on one line; return one medication dict with medicine_name, dosage, frequency, when, duration, precautions."""
    doc = nlp(line)
    if not doc.ents:
        return None
    out = {
        "medicine_name": "",
        "dosage": "",
        "frequency": "",
        "when": "",
        "duration": "",
        "precautions": "",
    }
    for ent in doc.ents:
        val = ent.text.strip()
        if ent.label_ == "MED_NAME":
            out["medicine_name"] = val
        elif ent.label_ == "DOSAGE":
            out["dosage"] = val
        elif ent.label_ == "FREQUENCY":
            out["frequency"] = val
        elif ent.label_ == "WHEN":
            out["when"] = val
        elif ent.label_ == "DURATION":
            out["duration"] = val
        elif ent.label_ == "PRECAUTION":
            out["precautions"] = val
    if not out["medicine_name"]:
        return None
    return out


def parse_medications_with_ner(text: str) -> List[Dict]:
    """
    Parse prescription text using the trained NER model.
    Returns list of medication dicts with: medicine_name, dosage, frequency, when, duration, precautions.
    Also includes schedule_text for backward compatibility (frequency + when).
    """
    nlp = _load_prescription_ner_model()
    if nlp is None:
        return []
    medications: List[Dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) < 3:
            continue
        med = _parse_line_with_ner(nlp, line)
        if med:
            schedule_text = " ".join(
                filter(None, [med["frequency"], med["when"], med["duration"], med["precautions"]]))
            med["schedule_text"] = schedule_text
            medications.append(med)
    return medications


def extract_text_from_image(image_path: str) -> str:
    """Run OCR on a prescription image and return raw text."""
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img)
    return text


def parse_medications_from_text(text: str) -> List[Dict]:
    """
    Parse prescription text into medication list. Uses trained NER model if available
    (ml/models/prescription_ner); otherwise falls back to heuristic parser.
    Returns items with: medicine_name, dosage, schedule_text, and when using NER also
    frequency, when, duration, precautions.
    """
    # Prefer trained model for clearer reading and full detail
    ner_meds = parse_medications_with_ner(text)
    if ner_meds:
        return ner_meds

    # Fallback: simple heuristic
    medications: List[Dict] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if " " not in line:
            continue

        for sep in [" - ", " – ", " — "]:
            if sep in line:
                name_dose, schedule = line.split(sep, 1)
                break
        else:
            name_dose, schedule = line, ""

        parts = name_dose.split()
        if not parts:
            continue

        medicine_name = " ".join(parts[:-1]) if len(parts) > 1 else parts[0]
        dosage = parts[-1] if len(parts) > 1 else ""

        medications.append(
            {
                "medicine_name": medicine_name.strip(),
                "dosage": dosage.strip(),
                "schedule_text": schedule.strip(),
                "frequency": "",
                "when": "",
                "duration": "",
                "precautions": "",
            }
        )

    return medications


def save_uploaded_image(file_storage, upload_dir: str) -> str:
    """
    Save an uploaded file (Flask's FileStorage) to disk and return its path.
    """
    upload_path = Path(upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)
    filename = file_storage.filename or "prescription.jpg"
    dest = upload_path / filename
    file_storage.save(dest)
    return str(dest)

