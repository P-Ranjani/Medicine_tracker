# 💊 Medication Reminder & Adherence Tracker

Full-stack app for prescription OCR, automatic medication scheduling, reminders, adherence tracking, AI chatbot, and caregiver monitoring.

## Backend (Flask) – Quick Start

1. **Create & activate virtual environment (optional but recommended)**

```bash
cd Medicine_tracker
python -m venv venv
venv\Scripts\activate  # Windows PowerShell
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Set environment variables (development)**

Create a `.env` file in the project root:

```bash
FLASK_ENV=development
SECRET_KEY=change-this-secret
DATABASE_URL=sqlite:///meds.db
OPENAI_API_KEY=your-openai-key-optional
```

4. **Run the backend API**

```bash
python backend/app.py
```

The API will run on `http://127.0.0.1:5000`.

## Project Structure

- `backend/` – Flask app, OCR, chatbot, reminder engine, drug interaction
- `database/` – Database models and initialization
- `notifications/` – Email / alert helpers
- `frontend/` – React / JS frontend (to be added)

## Main Features

- Prescription OCR scanning (Tesseract)
- **Trained prescription model** – optional NER model (train on 100–200 labeled lines) to read prescriptions clearly and extract: medicine name, dosage, how many times, when to use, duration, and what to do further (precautions). See `ml/README.md`.
- Automatic medication scheduling
- Reminder engine + notification hooks
- Drug interaction checker (OpenFDA / external APIs)
- Adherence tracking & analytics
- AI healthcare chatbot
- Caregiver dashboard & alerts

