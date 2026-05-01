from typing import List


def send_email_alert(to_emails: List[str], subject: str, body: str) -> None:
    """
    Placeholder email alert sender.

    In a real deployment you would integrate an email service (e.g. SMTP, SendGrid).
    For now, this function is a stub that could be wired to logging or a future
    notification system.
    """
    # TODO: Integrate with real email/SMS provider.
    print(f"[ALERT] To={to_emails} | Subject={subject} | Body={body}")


def format_missed_dose_alert(patient_name: str, medicine_name: str, time_str: str) -> str:
    return f"{patient_name} missed the {time_str} dose of {medicine_name}."

