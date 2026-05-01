from datetime import datetime, time as dt_time, date
from typing import List, Callable

import schedule

from database.models import Medication


def _parse_time_str(time_str: str) -> dt_time | None:
    try:
        hour, minute = map(int, time_str.split(":"))
        return dt_time(hour=hour, minute=minute)
    except Exception:
        return None


def schedule_daily_medication_reminders(
    medications: List[Medication],
    callback: Callable[[Medication], None],
) -> None:
    """
    Register scheduled reminder jobs for the provided medications.
    This uses the 'schedule' library; you must call schedule.run_pending()
    in a loop from a background thread or separate process.
    """
    today = date.today()

    for med in medications:
        if med.start_date and med.start_date > today:
            continue
        if med.end_date and med.end_date < today:
            continue

        parsed = _parse_time_str(med.schedule_time)
        if not parsed:
            continue

        at_str = parsed.strftime("%H:%M")

        def make_job(m: Medication):
            def job():
                callback(m)

            return job

        schedule.every().day.at(at_str).do(make_job(med))


def run_scheduler_forever():
    """
    Convenience loop. In a real deployment, run this in a dedicated worker.
    """
    import time

    while True:
        schedule.run_pending()
        time.sleep(1)

