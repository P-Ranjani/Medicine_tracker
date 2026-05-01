from typing import Dict

import os

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore


def simple_rule_based_response(question: str) -> str:
    """Fallback rule-based responses for common medication questions."""
    q = question.lower()

    if "paracetamol" in q:
        return (
            "Paracetamol is commonly used to reduce fever and relieve mild to "
            "moderate pain. Do not exceed the daily maximum dose specified by your doctor."
        )
    if "amoxicillin" in q:
        return (
            "Amoxicillin is an antibiotic used to treat bacterial infections. "
            "Complete the full course as prescribed, even if you feel better."
        )
    if "side effect" in q or "side effects" in q:
        return (
            "Common side effects depend on the medicine. If you experience severe "
            "allergic reactions (rash, breathing difficulty, swelling), seek emergency care."
        )
    if "interaction" in q:
        return (
            "Some medicines can interact and increase side effects or reduce effectiveness. "
            "Always inform your doctor about all medicines and supplements you take."
        )

    return (
        "I'm a simple healthcare assistant. Please provide the medicine name and your question, "
        "and always follow your doctor's instructions."
    )


def ai_response(question: str, patient_context: Dict | None = None) -> str:
    """
    If OPENAI_API_KEY is set and openai library is available, use a chat model.
    Otherwise fall back to the rule-based response.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return simple_rule_based_response(question)

    client = OpenAI(api_key=api_key)

    system_prompt = (
        "You are a cautious healthcare assistant focusing on medication guidance. "
        "You must not diagnose or prescribe. Encourage users to follow their doctor's "
        "instructions and consult a professional for urgent or serious issues."
    )

    context_text = ""
    if patient_context:
        context_text = f"Patient schedule and adherence info: {patient_context}."

    msg = (
        f"{context_text}\n\nUser question: {question}\n\n"
        "Give a concise, patient-friendly answer."
    )

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": msg},
            ],
            max_tokens=300,
        )
        return completion.choices[0].message.content or simple_rule_based_response(question)
    except Exception:
        return simple_rule_based_response(question)

