from typing import List, Dict

import requests


OPENFDA_BASE = "https://api.fda.gov/drug/label.json"


def check_interactions(medicine_names: List[str]) -> List[Dict]:
    """
    Very high-level placeholder for drug interaction checks.
    In a production system you would use a structured interaction API or dataset.

    Here we:
    - For each medicine, query OpenFDA (best-effort, may fail silently)
    - Look for sections mentioning 'interactions'
    - Return a summary list. This is not clinically reliable and should be
      clearly marked as informational only.
    """
    results: List[Dict] = []

    unique_names = {name.strip() for name in medicine_names if name.strip()}

    for name in unique_names:
        try:
            resp = requests.get(
                OPENFDA_BASE,
                params={
                    "search": f"openfda.generic_name:\"{name}\"",
                    "limit": 1,
                },
                timeout=5,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            if not data.get("results"):
                continue
            result = data["results"][0]

            interaction_texts = []
            for key in ["drug_interactions", "drug_interaction", "interactions"]:
                section = result.get(key)
                if isinstance(section, list):
                    interaction_texts.extend(section)

            if not interaction_texts:
                continue

            results.append(
                {
                    "medicine": name,
                    "raw_interaction_info": interaction_texts[:3],
                    "note": "This is informational only. Always consult a healthcare professional.",
                }
            )
        except Exception:
            # Network errors or unexpected JSON formats are ignored for now.
            continue

    return results

