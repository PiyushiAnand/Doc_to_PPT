import json
import os
from llms import model
import tools
import ppt_engine
import doc_engine
import argparse

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

    
    print(f"--- STARTING PIPELINE FOR {company_name} ---")

    # STEP 1: LOAD DATA
    raw_text = ingest_data(input_file)
    if not raw_text:
        exit()
    
    # STEP 2: ANALYZE (Extract Facts)
    print("\n[1/4] Analyzing Data (LLM)...")
    structured_output = model.get_response_from_llm(model="qwen2.5:7b-instruct",
        prompt_path="llms/prompts/analyzer.txt",
        data=raw_text, temp=0.5
    )
    # DEBUG: Check if analyzer worked
    if not structured_output:
        print("ERROR: Analyzer returned empty data.")
        exit()
    print(f"      Extracted {len(str(structured_output))} characters of data.")


    #add publiclity availabile info 
    public_info = tools.search_web(f"{company_name} business model and market sentiment", max_results=3)
    structured_output.setdefault("facts", [])
    structured_output["facts"].extend(public_info)

    print("\n--- Publicly Available Information ---")
    for info in public_info:
        print(f" • {info['source']}: {info['text'][:75]}...")
        
    # STEP 3: GENERATE CONTENT (Draft Slides)
    print("\n[2/4] Drafting Slides (LLM)...")
    # Pass the JSON string to the prompt
    ppt_points = model.get_response_from_llm("llama3.1:8b",
        "llms/prompts/slide_gen.txt",
        json.dumps(structured_output) , temp=0.0 
    )

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
    ppt_engine.generate_styled_ppt(ppt_points, f"Blind_Teaser_{company_name}_Final.pptx")
    
    # STEP 5: GENERATE CITATIONS
    print("\n[4/4] Creating Citation Doc...")
    # doc_engine.generate_citation_doc(structured_output["facts"], f"Blind_Teaser_{company_name}_Citations.docx")
    # Build registry once
    fact_registry = {
        f["fact_id"]: {
            "text": f.get("text", ""),
            "source": f.get("source", "Unknown")
        }
        for f in structured_output["facts"]
    }

    doc_engine.generate_citation_doc(
        ppt_data=ppt_points,
        fact_registry=fact_registry,
        filename=f"{company_name}_Citations.docx"
    )

    print("\n--- SUCCESS: Files Generated ---")