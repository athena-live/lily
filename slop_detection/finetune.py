import io
import json
import os
from datetime import datetime

import requests


def _openai_base():
    return os.environ.get("OPENAI_API_BASE_URL", "https://api.openai.com/v1")


def _openai_key():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return api_key


def build_training_jsonl(corrections):
    lines = []
    for correction in corrections:
        original = correction.original_text.strip()
        corrected = correction.corrected_text.strip()
        if not original or not corrected:
            continue
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a precise editor that removes filler and fixes errors without changing meaning.",
                },
                {
                    "role": "user",
                    "content": f"Correct this content:\n\n{original}",
                },
                {"role": "assistant", "content": corrected},
            ]
        }
        lines.append(json.dumps(payload, ensure_ascii=True))
    return "\n".join(lines) + ("\n" if lines else "")


def upload_training_file(jsonl_text):
    api_key = _openai_key()
    base_url = _openai_base()
    filename = f"slop-corrections-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.jsonl"

    files = {
        "file": (filename, io.BytesIO(jsonl_text.encode("utf-8")), "application/jsonl"),
    }
    data = {"purpose": "fine-tune"}
    response = requests.post(
        f"{base_url}/files",
        headers={"Authorization": f"Bearer {api_key}"},
        files=files,
        data=data,
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def create_fine_tune_job(training_file_id, model):
    api_key = _openai_key()
    base_url = _openai_base()
    payload = {"training_file": training_file_id, "model": model}
    response = requests.post(
        f"{base_url}/fine_tuning/jobs",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def get_fine_tune_job(job_id):
    api_key = _openai_key()
    base_url = _openai_base()
    response = requests.get(
        f"{base_url}/fine_tuning/jobs/{job_id}",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()
