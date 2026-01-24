

import json
import ollama
import re

MODEL_NAME = "llama3.2:1b"


import json

def load_prompt(prompt_path, company_data):
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt = f.read()

    if isinstance(company_data, dict):
        company_data = json.dumps(company_data, indent=2)

    return prompt.replace("{{COMPANY_DATA}}", company_data)


def extract_json(text):
    """Extract first JSON object from text"""
    match = re.search(r'\{[\s\S]*\}', text)
    if not match:
        raise ValueError("No JSON object found")
    return match.group(0)


def get_response_from_llm(prompt_path, data, retries=2):
    prompt = load_prompt(prompt_path, data)

    for attempt in range(retries + 1):
        response = ollama.generate(
            model=MODEL_NAME,
            prompt=prompt,
            stream=False
        )["response"]

        print(response)
        try:
            json_text = extract_json(response)
            return json.loads(json_text)
        except Exception as e:
            if attempt == retries:
                raise RuntimeError(
                    f"LLM failed to return valid JSON after {retries+1} attempts"
                )

            # 🔁 Repair prompt
            prompt = (
                "FIX THE OUTPUT.\n"
                "Return ONLY valid JSON.\n"
                "No explanations. No markdown. No text.\n\n"
                + response
            )
