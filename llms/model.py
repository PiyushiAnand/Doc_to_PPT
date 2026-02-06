

import json
import ollama
import re

# MODEL_NAME = "phi3.5"


import json

def load_prompt(prompt_path, data):
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt = f.read()

    if isinstance(data, dict):
        data = json.dumps(data, indent=2)

    prompt = prompt.replace("{{COMPANY_DATA}}", data)
    prompt = prompt.replace("{{STRUCTURED_JSON}}", data)

    return prompt



def extract_json(text):
    """
    Robust extraction that handles nested JSON and strips markdown/comments.
    """
    # 1. Strip Markdown Code Blocks (```json ... ```)
    text = re.sub(r'```json\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'```\s*', '', text)
    
    # 2. Strip Single-Line Comments (//) which break JSON
    text = re.sub(r'//.*', '', text)

    # 3. Find the starting bracket
    start_idx = text.find('{')
    if start_idx == -1:
        raise ValueError("No JSON object found (missing '{')")

    # 4. Smart Balance Check (The "Stack" Method)
    balance = 0
    for i in range(start_idx, len(text)):
        char = text[i]
        if char == '{':
            balance += 1
        elif char == '}':
            balance -= 1
            # If we hit zero, we found the EXACT matching closing brace
            if balance == 0:
                json_str = text[start_idx : i+1]
                return json_str
    
    # Fallback: If balance never hit 0, try the old greedy way
    end_idx = text.rfind('}')
    if end_idx != -1:
        return text[start_idx : end_idx+1]
        
    raise ValueError("Unbalanced JSON brackets")


def get_response_from_llm(model,prompt_path, data,temp, retries=2):
    prompt = load_prompt(prompt_path, data)

    for attempt in range(retries + 1):
        # response = ollama.generate(
        #     model=MODEL_NAME,
        #     prompt=prompt,
        #     stream=False
        # )["response"]
        response = ollama.generate(
            model,
            prompt=prompt,
            stream=False,
            options={
                "temperature": temp,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
                "num_ctx": 4096
            }
        )["response"]


        # print(response)
        try:
            json_text = extract_json(response)
            return json.loads(json_text)
        except Exception as e:
            if attempt == retries:
                raise RuntimeError(
                    f"LLM failed to return valid JSON after {retries+1} attempts"
                )

            # 🔁 Repair prompt
            prompt = f"""
                You MUST output exactly ONE JSON object.

                Rules:
                - Output ONLY valid JSON
                - No comments
                - No markdown
                - No explanations
                - No trailing commas
                - No undefined / null unless valid JSON
                - Double quotes only
                - Match this schema EXACTLY

                Schema:
                {{
                "slides": [
                    {{
                    "title": string,
                    "bullets": [
                        {{
                        "text": string,
                        "fact_ids": [string]
                        }}
                    ]
                    }}
                ]
                }}

                Rewrite the content below to match the schema.

                CONTENT:
                {response}
                """

