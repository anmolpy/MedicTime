from __future__ import annotations

from huggingface_hub import InferenceClient

try:
    from .config import settings
    from .kb import retrieve_context
except ImportError:
    from config import settings
    from kb import retrieve_context


def _client() -> InferenceClient:
    if not settings.hf_token:
        raise RuntimeError("HF_TOKEN is missing. Set it in your Render environment.")
    return InferenceClient(model=settings.hf_model, token=settings.hf_token, timeout=60)


def receptionist_response(message: str) -> str:
    context = retrieve_context(message)
    prompt = f"""
You are a helpful, concise medical receptionist for {settings.clinic_name}.

Rules:
- Answer as front-desk staff, not a clinician.
- Do not diagnose or prescribe.
- If the user mentions urgent symptoms, advise immediate medical attention.
- Keep answers brief and practical.

Reference clinic knowledge:
{context or 'No matching clinic FAQ was found. Use safe, generic clinic guidance.'}
""".strip()

    response = _client().chat_completion(
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": message},
        ],
        max_tokens=220,
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()


def generate_soap_note(transcript: str) -> str:
    user_prompt = f"""
You are an expert clinical medical scribe. Extract a professional SOAP note from the transcript.

Rules:
- First, infer which speaker is the doctor and which is the patient from context.
- Return only the SOAP note.
- Use sections titled SUBJECTIVE, OBJECTIVE, ASSESSMENT, and PLAN.
- If a section is not supported by the transcript, write \"None reported\".
- Be concise and medically professional.

Transcript:
{transcript}
""".strip()

    response = _client().chat_completion(
        messages=[
            {
                "role": "system",
                "content": "You produce concise clinical SOAP notes from conversation transcripts.",
            },
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=800,
        temperature=0.1,
    )
    return response.choices[0].message.content.strip()
