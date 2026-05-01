import os
import sys
from pathlib import Path

# Add project root to path so imports work when running: python backend/app.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_bcrypt import Bcrypt
from flask_cors import CORS

from database.models import (
    init_db,
    db,
    User,
    Medication,
    Adherence,
    CaregiverLink,
)
from backend.ocr_module import extract_text_from_image, parse_medications_from_text, save_uploaded_image
from backend.chatbot_api import ai_response
from backend.drug_interaction import check_interactions
from notifications.alert_service import send_email_alert, format_missed_dose_alert


load_dotenv()


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///meds.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    init_db(app)
    bcrypt = Bcrypt(app)

    # ---------- Helper utilities ----------

    def hash_password(password: str) -> str:
        return bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(password: str, pw_hash: str) -> bool:
        return bcrypt.check_password_hash(pw_hash, password)

    def get_user_from_request() -> User | None:
        """
        Simplified auth: expects 'X-User-Id' header.
        In a production app, use JWT or session-based auth.
        """
        user_id = request.headers.get("X-User-Id")
        if not user_id:
            return None
        try:
            return db.session.get(User, int(user_id))
        except Exception:
            return None

    # ---------- Auth & Users ----------

    @app.post("/api/register")
    def register():
        data = request.get_json(force=True)
        name = data.get("name")
        email = data.get("email")
        password = data.get("password")
        role = data.get("role", "patient")
        caregiver_email = data.get("caregiver_email")
        relationship = data.get("relationship")

        if not all([name, email, password, role]):
            return jsonify({"error": "Missing required fields"}), 400

        if db.session.query(User).filter_by(email=email).first():
            return jsonify({"error": "Email already registered"}), 400

        user = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=role.lower(),
        )
        db.session.add(user)
        db.session.commit()

        # Optional caregiver linking
        if role.lower() == "patient" and caregiver_email:
            caregiver = db.session.query(User).filter_by(email=caregiver_email).first()
            if caregiver:
                link = CaregiverLink(
                    patient_id=user.id,
                    caregiver_id=caregiver.id,
                    relationship=relationship,
                )
                db.session.add(link)
                db.session.commit()

        return jsonify({"user": user.to_dict()}), 201

    @app.post("/api/login")
    def login():
        data = request.get_json(force=True)
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "Email and password required"}), 400

        user = db.session.query(User).filter_by(email=email).first()
        if not user or not check_password(password, user.password_hash):
            return jsonify({"error": "Invalid credentials"}), 401

        # For now, return user id which frontend can use as X-User-Id
        return jsonify({"user": user.to_dict(), "token": str(user.id)})

    # ---------- OCR & Medication Scheduler ----------

    @app.post("/api/ocr/scan")
    def ocr_scan():
        user = get_user_from_request()
        if not user or user.role != "patient":
            return jsonify({"error": "Unauthorized"}), 401

        if "file" not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400

        upload_dir = os.path.join(os.getcwd(), "uploads")
        image_path = save_uploaded_image(file, upload_dir)

        text = extract_text_from_image(image_path)
        meds = parse_medications_from_text(text)

        return jsonify({"raw_text": text, "parsed_medications": meds})

    @app.post("/api/medications")
    def create_medications():
        user = get_user_from_request()
        if not user or user.role != "patient":
            return jsonify({"error": "Unauthorized"}), 401

        data = request.get_json(force=True)
        medications_data = data.get("medications", [])
        created = []

        for m in medications_data:
            try:
                medicine_name = m["medicine_name"]
                dosage = m.get("dosage")
                schedule_time = m["schedule_time"]
                start_date_str = m.get("start_date")
                end_date_str = m.get("end_date")

                start_date_val = (
                    date.fromisoformat(start_date_str) if start_date_str else date.today()
                )
                end_date_val = date.fromisoformat(end_date_str) if end_date_str else None

                med = Medication(
                    user_id=user.id,
                    medicine_name=medicine_name,
                    dosage=dosage,
                    schedule_time=schedule_time,
                    start_date=start_date_val,
                    end_date=end_date_val,
                )
                db.session.add(med)
                created.append(med)
            except Exception:
                continue

        db.session.commit()

        return jsonify({"medications": [m.to_dict() for m in created]}), 201

    @app.get("/api/medications")
    def list_medications():
        user = get_user_from_request()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401

        meds = db.session.query(Medication).filter_by(user_id=user.id).all()
        return jsonify({"medications": [m.to_dict() for m in meds]})

    # ---------- Adherence Tracking ----------

    @app.post("/api/adherence")
    def record_adherence():
        user = get_user_from_request()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401

        data = request.get_json(force=True)
        medication_id = data.get("medication_id")
        status = data.get("status")  # "taken", "missed", "skipped"

        if status not in {"taken", "missed", "skipped"}:
            return jsonify({"error": "Invalid status"}), 400

        med = db.session.get(Medication, medication_id)
        if not med or med.user_id != user.id:
            return jsonify({"error": "Medication not found"}), 404

        record = Adherence(
            medication_id=med.id,
            date=date.today(),
            status=status,
        )
        db.session.add(record)
        db.session.commit()

        # If missed, send alerts to caregivers (email stub)
        if status == "missed":
            links = (
                db.session.query(CaregiverLink)
                .filter_by(patient_id=user.id)
                .all()
            )
            caregiver_ids = [l.caregiver_id for l in links]
            caregivers = (
                db.session.query(User)
                .filter(User.id.in_(caregiver_ids))
                .all()
            )
            to_emails = [c.email for c in caregivers]
            if to_emails:
                subject = "Missed medication alert"
                body = format_missed_dose_alert(
                    patient_name=user.name,
                    medicine_name=med.medicine_name,
                    time_str=med.schedule_time,
                )
                send_email_alert(to_emails, subject, body)

        return jsonify({"adherence": record.to_dict()}), 201

    @app.get("/api/adherence/summary")
    def adherence_summary():
        user = get_user_from_request()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401

        meds = db.session.query(Medication).filter_by(user_id=user.id).all()
        summary = []

        for med in meds:
            records = db.session.query(Adherence).filter_by(medication_id=med.id).all()
            total = len(records)
            taken = len([r for r in records if r.status == "taken"])
            missed = len([r for r in records if r.status == "missed"])
            adherence_pct = (taken / total * 100) if total > 0 else 0.0
            summary.append(
                {
                    "medication": med.medicine_name,
                    "taken": taken,
                    "missed": missed,
                    "total": total,
                    "adherence_pct": round(adherence_pct, 1),
                }
            )

        return jsonify({"summary": summary})

    # ---------- Drug Interaction Checker ----------

    @app.post("/api/drug/interactions")
    def drug_interactions():
        user = get_user_from_request()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401

        data = request.get_json(force=True)
        meds = data.get("medicines") or []
        results = check_interactions(meds)
        return jsonify({"interactions": results})

    # ---------- Caregiver Dashboard ----------

    @app.get("/api/caregiver/patients")
    def caregiver_patients():
        user = get_user_from_request()
        if not user or user.role != "caregiver":
            return jsonify({"error": "Unauthorized"}), 401

        links = db.session.query(CaregiverLink).filter_by(caregiver_id=user.id).all()
        patient_ids = [l.patient_id for l in links]

        patients = (
            db.session.query(User)
            .filter(User.id.in_(patient_ids))
            .all()
        )

        result = []
        for p in patients:
            meds = db.session.query(Medication).filter_by(user_id=p.id).all()
            result.append(
                {
                    "patient": p.to_dict(),
                    "medications": [m.to_dict() for m in meds],
                }
            )

        return jsonify({"patients": result})

    # ---------- Chatbot ----------

    @app.post("/api/chatbot")
    def chatbot():
        user = get_user_from_request()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401

        data = request.get_json(force=True)
        question = data.get("question", "")
        if not question:
            return jsonify({"error": "Question is required"}), 400

        # Optionally include simple context (current medications)
        meds = (
            db.session.query(Medication)
            .filter_by(user_id=user.id)
            .all()
        )
        context = {
            "medications": [m.to_dict() for m in meds],
        }

        answer = ai_response(question, patient_context=context)
        return jsonify({"answer": answer})

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/")
    def index():
        return jsonify({
            "message": "Medication Reminder API",
            "docs": "Use /api/* endpoints. Try GET /api/health to verify.",
            "endpoints": [
                "POST /api/register",
                "POST /api/login",
                "POST /api/ocr/scan",
                "GET/POST /api/medications",
                "POST /api/adherence",
                "GET /api/adherence/summary",
                "POST /api/chatbot",
                "POST /api/drug/interactions",
                "GET /api/caregiver/patients",
            ],
        })

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(debug=True)

