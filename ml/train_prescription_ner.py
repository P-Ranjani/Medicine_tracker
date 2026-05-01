"""
Train a prescription NER model on 100-200 labeled JSONL datasets.

Reads: ml/datasets/prescription_train.jsonl (and optional prescription_val.jsonl)
Saves: ml/models/prescription_ner

Each JSONL line: {"text": "...", "medications": [{"medicine_name", "dosage", "frequency", "when", "duration", "precautions"}, ...]}
Labels: MED_NAME, DOSAGE, FREQUENCY, WHEN, DURATION, PRECAUTION
"""

import json
import random
from pathlib import Path

try:
    import spacy
    from spacy.training import Example
    from spacy.util import minibatch, compounding
except ImportError:
    raise SystemExit("Install ML deps: pip install -r ml/requirements-ml.txt && python -m spacy download en_core_web_sm")

# Paths
BASE = Path(__file__).resolve().parent
DATASETS_DIR = BASE / "datasets"
MODELS_DIR = BASE / "models"
TRAIN_PATH = DATASETS_DIR / "prescription_train.jsonl"
VAL_PATH = DATASETS_DIR / "prescription_val.jsonl"
MODEL_OUT = MODELS_DIR / "prescription_ner"

ENTITY_LABELS = ["MED_NAME", "DOSAGE", "FREQUENCY", "WHEN", "DURATION", "PRECAUTION"]


def find_span(text: str, value: str) -> tuple[int, int] | None:
    """Find first occurrence of value in text (case-insensitive), return (start, end) or None."""
    if not value or not value.strip():
        return None
    value = value.strip()
    low = text.lower()
    idx = low.find(value.lower())
    if idx == -1:
        return None
    return (idx, idx + len(value))


def medication_to_entities(text: str, med: dict) -> list[tuple[int, int, str]]:
    """Convert one medication dict to list of (start, end, label) for spans that appear in text."""
    entities = []
    seen = set()  # avoid duplicate spans
    for key, label in [
        ("medicine_name", "MED_NAME"),
        ("dosage", "DOSAGE"),
        ("frequency", "FREQUENCY"),
        ("when", "WHEN"),
        ("duration", "DURATION"),
        ("precautions", "PRECAUTION"),
    ]:
        val = med.get(key)
        if not val or not str(val).strip():
            continue
        span = find_span(text, str(val))
        if span and span not in seen:
            entities.append((span[0], span[1], label))
            seen.add(span)
    return entities


def load_jsonl(path: Path) -> list[dict]:
    out = []
    if not path.exists():
        return out
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def jsonl_to_spacy_training(data: list[dict]) -> list[tuple[str, dict]]:
    """Convert JSONL items to (text, {"entities": [(start, end, label), ...]})."""
    training = []
    for item in data:
        text = item.get("text", "")
        meds = item.get("medications", [])
        if not text or not meds:
            continue
        all_entities = []
        for med in meds:
            all_entities.extend(medication_to_entities(text, med))
        # Sort by start; merge or drop overlapping if any (keep first)
        all_entities.sort(key=lambda x: x[0])
        # Remove overlaps: if next start < prev end, skip next
        filtered = []
        for e in all_entities:
            if filtered and e[0] < filtered[-1][1]:
                continue
            filtered.append(e)
        training.append((text, {"entities": filtered}))
    return training


def train_prescription_ner(
    train_path: Path = TRAIN_PATH,
    val_path: Path = VAL_PATH,
    model_out: Path = MODEL_OUT,
    n_iter: int = 30,
    dropout: float = 0.35,
) -> None:
    """Train spaCy NER and save to model_out."""
    # Use example dataset if train not present
    if not train_path.exists():
        example = DATASETS_DIR / "example_dataset.jsonl"
        if example.exists():
            train_path = example
            print(f"Using example dataset: {train_path}")
        else:
            raise FileNotFoundError(
                f"Create {train_path} with 100-200 labeled prescription lines. See ml/README.md."
            )

    train_data = load_jsonl(train_path)
    if not train_data:
        raise ValueError(f"No valid lines in {train_path}")

    spacy_training = jsonl_to_spacy_training(train_data)
    if not spacy_training:
        raise ValueError("No training examples after converting to spaCy format.")

    print(f"Training examples: {len(spacy_training)}")

    # Try to load base model; otherwise start blank
    try:
        nlp = spacy.load("en_core_web_sm")
        print("Using base model: en_core_web_sm")
    except OSError:
        nlp = spacy.blank("en")
        print("Using blank model: en")

    if "ner" not in nlp.pipe_names:
        ner = nlp.add_pipe("ner")
        for label in ENTITY_LABELS:
            ner.add_label(label)
    else:
        ner = nlp.get_pipe("ner")
        for label in ENTITY_LABELS:
            if label not in ner.labels:
                ner.add_label(label)

    # Build Example list for spaCy 3
    examples = []
    for text, annotations in spacy_training:
        doc = nlp.make_doc(text)
        examples.append(Example.from_dict(doc, annotations))

    # Disable other pipes during training
    other_pipes = [p for p in nlp.pipe_names if p != "ner"]
    with nlp.disable_pipes(*other_pipes):
        try:
            nlp.initialize(get_examples=lambda: examples)
        except TypeError:
            # spaCy 2 fallback
            nlp.begin_training()
        for iteration in range(n_iter):
            losses = {}
            random.shuffle(examples)
            for batch in minibatch(examples, size=compounding(4.0, 32.0, 1.001)):
                nlp.update(batch, drop=dropout, losses=losses)
            print(f"Iteration {iteration + 1}/{n_iter}  loss: {losses.get('ner', 0):.4f}")

    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    nlp.to_disk(MODEL_OUT)
    print(f"Model saved to: {MODEL_OUT}")


if __name__ == "__main__":
    train_prescription_ner()
