import json
import os
from llms import model
import tools
import ppt_engine
import doc_engine

# 1. READ DATA
def ingest_data(file_path):
    if not os.path.exists(file_path):
        print(f"ERROR: File not found at {file_path}")
        return ""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    # CONFIG
    company_name = "Kalyani Forge"
    input_file = "Company Data/automotive-kalyani-forge/Kalyani Forge-OnePager.md"
    
    print(f"--- STARTING PIPELINE FOR {company_name} ---")

    # STEP 1: LOAD DATA
    raw_text = ingest_data(input_file)
    if not raw_text:
        exit()
    
    # STEP 2: ANALYZE (Extract Facts)
    print("\n[1/4] Analyzing Data (LLM)...")
    structured_output = model.get_response_from_llm(
        "llms/prompts/analyzer.txt",
        raw_text
    )
    # DEBUG: Check if analyzer worked
    if not structured_output:
        print("ERROR: Analyzer returned empty data.")
        exit()
    print(f"      Extracted {len(str(structured_output))} characters of data.")

    # STEP 3: GENERATE CONTENT (Draft Slides)
    print("\n[2/4] Drafting Slides (LLM)...")
    # Pass the JSON string to the prompt
    ppt_points = model.get_response_from_llm(
        "llms/prompts/slide_gen.txt",
        json.dumps(structured_output) 
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
    ppt_engine.generate_styled_ppt(ppt_points, "Blind_Teaser_Final.pptx")
    
    # STEP 5: GENERATE CITATIONS
    print("\n[4/4] Creating Citation Doc...")
    doc_engine.generate_citation_doc(ppt_points, "Citations_Final.docx")
    
    print("\n--- SUCCESS: Files Generated ---")