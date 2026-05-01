from datetime import datetime, date

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # "patient" or "caregiver"

    medications = db.relationship("Medication", backref="user", lazy=True)
    caregiver_links_as_patient = db.relationship(
        "CaregiverLink",
        foreign_keys="CaregiverLink.patient_id",
        backref="patient",
        lazy=True,
    )
    caregiver_links_as_caregiver = db.relationship(
        "CaregiverLink",
        foreign_keys="CaregiverLink.caregiver_id",
        backref="caregiver",
        lazy=True,
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
        }


class Medication(db.Model):
    __tablename__ = "medications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    medicine_name = db.Column(db.String(120), nullable=False)
    dosage = db.Column(db.String(120), nullable=True)
    schedule_time = db.Column(db.String(50), nullable=False)  # "08:00", "20:00"
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    end_date = db.Column(db.Date, nullable=True)

    adherence_records = db.relationship("Adherence", backref="medication", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "medicine_name": self.medicine_name,
            "dosage": self.dosage,
            "schedule_time": self.schedule_time,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
        }


class Adherence(db.Model):
    __tablename__ = "adherence"

    id = db.Column(db.Integer, primary_key=True)
    medication_id = db.Column(db.Integer, db.ForeignKey("medications.id"), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(
        db.String(20), nullable=False
    )  # "taken", "missed", "skipped"
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "medication_id": self.medication_id,
            "date": self.date.isoformat(),
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
        }


class CaregiverLink(db.Model):
    __tablename__ = "caregiver_link"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    caregiver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    relationship = db.Column(db.String(120), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "caregiver_id": self.caregiver_id,
            "relationship": self.relationship,
        }


def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()

