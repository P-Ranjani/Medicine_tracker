# Prescription Reading Model – Train on 100–200 Datasets

This folder contains everything to **train a model** that reads prescription text clearly and extracts:

- **What medicine** – name
- **How many times** – frequency (e.g. once/twice daily, every 8 hours)
- **When to use** – time of day or condition (e.g. morning, after food, at bedtime)
- **Duration** – how long to take (e.g. 5 days, 2 weeks)
- **What to do further** – precautions, follow-up, avoid (e.g. avoid alcohol, take after meals, complete full course)

You train with **100–200 labeled prescription lines (or full prescriptions)** so the model learns to extract these fields accurately.

---

## 1. Dataset format

Each **dataset item** is one prescription line (or one full prescription). Save as **JSONL**: one JSON object per line.

**File:** `ml/datasets/prescription_train.jsonl`

Each line must look like:

```json
{"text": "Paracetamol 500mg twice daily morning and evening for 5 days. Take after food. Avoid alcohol.", "medications": [{"medicine_name": "Paracetamol", "dosage": "500mg", "frequency": "twice daily", "when": "morning and evening", "duration": "5 days", "precautions": "Take after food. Avoid alcohol."}]}
```

**Fields in `medications[]`:**

| Field | Meaning | Example |
|-------|--------|--------|
| `medicine_name` | Drug name | Paracetamol, Amoxicillin |
| `dosage` | Strength / amount | 500mg, 250mg, 5ml |
| `frequency` | How many times per day | once daily, twice daily, every 8 hours |
| `when` | When to take | morning, after food, at bedtime |
| `duration` | How long to take | 5 days, 2 weeks, until finished |
| `precautions` | What to do / avoid / follow-up | Take after food. Avoid alcohol. Complete full course. |

- One line can have **one or more** medicines (e.g. two drugs on same line → two objects in `medications`).
- You need **100–200 such lines** (or full prescriptions split into lines) for training.

---

## 2. What you need to do

### Step 1: Collect 100–200 prescription texts

- Use **real prescription text** (typed or OCR from images).
- Prefer lines that look like:  
  `MedicineName strength frequency when duration. Precautions.`
- You can mix:
  - Single-line items (one medicine per line).
  - Multi-line or full prescriptions (one JSON object = one logical “item” with one or more medicines).

### Step 2: Label each item

For each text, fill:

- **medicine_name**, **dosage**, **frequency**, **when**, **duration**, **precautions** for each medicine in that text.

Keep labels **consistent** (e.g. always “twice daily” not sometimes “2 times daily”).

### Step 3: Save as JSONL

- One JSON object per line in `ml/datasets/prescription_train.jsonl`.
- Optionally use `prescription_val.jsonl` for validation (same format).

### Step 4: Install training dependencies

```bash
pip install -r ml/requirements-ml.txt
python -m spacy download en_core_web_sm
```

### Step 5: Train the model

```bash
cd ml
python train_prescription_ner.py
```

- Reads `datasets/prescription_train.jsonl` (and `prescription_val.jsonl` if present).
- Trains a small NER model to tag: `MED_NAME`, `DOSAGE`, `FREQUENCY`, `WHEN`, `DURATION`, `PRECAUTION`.
- Saves the model under `ml/models/prescription_ner` (or path set in the script).

### Step 6: Use the trained model in the app

- The backend will load the model from `ml/models/prescription_ner` if it exists.
- After OCR (Tesseract), the app runs the trained model on the extracted text to get structured fields (medicine, dosage, frequency, when, duration, precautions).

---

## 3. File layout

```
ml/
├── README.md                      # This file
├── requirements-ml.txt            # Training dependencies
├── datasets/
│   ├── prescription_train.jsonl  # 100–200 labeled lines (you create)
│   └── prescription_val.jsonl    # Optional validation
├── train_prescription_ner.py     # Training script
├── models/
│   └── prescription_ner/         # Saved model (after training)
└── example_dataset.jsonl         # Example 10 lines (copy/expand for your data)
```

---

## 4. Tips for good results with 100–200 datasets

- **Consistent wording** in labels (e.g. “twice daily” everywhere).
- **Cover variation**: different medicines, dosages, frequencies, “when”, durations, precautions.
- **Include edge cases**: “as needed”, “every 8 hours”, “with food”, “avoid driving”.
- **Validation set**: put 10–20% of data in `prescription_val.jsonl` to monitor overfitting.

After training, the app will use this model to read prescriptions more clearly and show **what medicine**, **how many times**, **when**, **duration**, and **what to do further** in a structured way.
