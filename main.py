import json
import os
from llms import model
import tools
import ppt_engine
import doc_engine
import argparse
import re
def scrub_company_names(ppt_json, company_name):
    ppt_str = json.dumps(ppt_json)

    patterns = [
        re.escape(company_name),
        re.escape(company_name + " Ltd"),
        re.escape(company_name + " Limited"),
        re.escape(company_name + " Pvt Ltd"),
        re.escape(company_name + " Private Limited"),
    ]

    for pat in patterns:
        ppt_str = re.sub(pat, "the company", ppt_str, flags=re.IGNORECASE)

    return json.loads(ppt_str)


# 1. READ DATA
def ingest_data(file_path):
    if not os.path.exists(file_path):
        print(f"ERROR: File not found at {file_path}")
        return ""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate PPT and citations from company markdown")

    parser.add_argument(
        "--company",
        required=True,
        help="Company name (used for search and output filenames)"
    )

    parser.add_argument(
        "--file",
        required=True,
        help="Markdown file name (must be in the same folder as this script)"
    )

    args = parser.parse_args()

    company_name = args.company
    input_file = args.file

    
    # STEP 1: LOAD DATA
    raw_text = ingest_data(input_file)
    if not raw_text:
        exit()

    # STEP 1.1: LOAD PUBLICLY AVAILABLE INFO (RAW TEXT ONLY)
    public_info = tools.search_web(
        f"{company_name} business model manufacturing capacity financials",
        max_results=3
    )

    public_text_blocks = []
    for item in public_info:
        if isinstance(item, dict) and "text" in item:
            public_text_blocks.append(
                f"Source: {item.get('source', 'Public Source')}\n{item['text']}"
            )

    public_text = "\n\n".join(public_text_blocks)

    # STEP 1.2: MERGE RAW + PUBLIC DATA
    combined_text = raw_text

    if public_text:
        combined_text += "\n\n--- PUBLICLY AVAILABLE INFORMATION ---\n"
        combined_text += public_text

    # STEP 2: ANALYZE (STRICT FACT EXTRACTION)
    print("\n[1/4] Analyzing Data (LLM)...")

    structured_output = model.get_response_from_llm(
        model="mistral:7b",
        prompt_path="llms/prompts/analyzer.txt",
        data=combined_text,
        temp=0.0
    )

    # DEBUG: Check if analyzer worked
    if not structured_output:
        print("ERROR: Analyzer returned empty data.")
        exit()

    print(f"      Extracted {len(str(structured_output))} characters of data.")
    print(structured_output)  # Print the structured output for debugging

    # STEP 3: GENERATE CONTENT (Draft Slides)
    print("\n[2/4] Drafting Slides (LLM)...")
    # Pass the JSON string to the prompt
    ppt_points = model.get_response_from_llm("phi3:mini",
        "llms/prompts/slide_gen.txt",
        json.dumps(structured_output) , temp=0.0 
    )

    print(ppt_points)  # Print the raw output for debugging

    # DEBUG: Print the first slide to verify it's not a placeholder
    try:
        first_bullet = ppt_points['slides'][0]['bullets'][0]['text']
        print(f"      Preview: {first_bullet[:50]}...")
        if "fact_1" in str(ppt_points):
            print("WARNING: Model returned placeholders! Retrying might be needed.")
    except:
        print("WARNING: Could not preview slides. Output might be malformed.")

    # STEP 4: GENERATE PPT
    print("\n[3/4] Creating PowerPoint...")
    ppt_points = scrub_company_names(ppt_points,company_name)
    ppt_engine.generate_styled_ppt(ppt_points, f"Blind_Teaser_{company_name}_Final.pptx")
   

    # STEP 5: GENERATE CITATIONS
    print("\n[4/4] Creating Citation Doc...")

    # ---- SAFE FACT NORMALIZATION ----
    facts = structured_output.get("facts")

    if not isinstance(facts, list):
        facts = []

    fact_registry = {}

    for f in facts:
        if not isinstance(f, dict):
            continue

        fact_id = f.get("fact_id")
        if not fact_id:
            continue

        fact_registry[fact_id] = {
            "text": f.get("text", ""),
            "source": f.get("source", {})
        }

    # ---- GENERATE CITATION DOC ----
    doc_engine.generate_citation_doc(
        ppt_data=ppt_points,
        fact_registry=fact_registry,
        filename=f"{company_name}_Citations.docx"
    )


    print("\n--- SUCCESS: Files Generated ---")