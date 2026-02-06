import json
import os
import re
import argparse
from llms import model
import tools
import ppt_engine
import doc_engine

# ---------------------------------------------------------
# SCRUB COMPANY NAMES
# ---------------------------------------------------------
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

# ---------------------------------------------------------
# READ DATA
# ---------------------------------------------------------
def ingest_data(file_path):
    if not os.path.exists(file_path):
        print(f"ERROR: File not found at {file_path}")
        return ""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

# ---------------------------------------------------------
# ASSIGN FACT IDs & PREPARE METRICS
# ---------------------------------------------------------
def normalize_facts_and_metrics(structured_output, public_text_blocks):
    fact_registry = {}

    # 1. Assign fallback fact_ids to structured facts
    for i, f in enumerate(structured_output.get("facts", [])):
        if not isinstance(f, dict):
            continue
        fid = f.get("fact_id") or f"F{i+1}"
        f["fact_id"] = fid
        fact_registry[fid] = {
            "text": f.get("text", ""),
            "source": f.get("source", {"name": "Unknown"})
        }

    # 2. Include public sources as facts
    for i, block in enumerate(public_text_blocks):
        fid = f"PUBLIC_{i+1}"
        fact_registry[fid] = {
            "text": block.split("\n", 1)[-1],  # remove Source: line
            "source": {"name": block.split("\n", 1)[0].replace("Source: ", "")}
        }

    # 3. Prepare metrics across years for chart_data
    metric_registry = structured_output.get("metrics", {})  # expect {metric_name: {year: value}}
    chart_data_dict = {}
    for metric_name, yearly_values in metric_registry.items():
        if len(yearly_values) >= 3:
            # Chart only if ≥3 years
            labels = sorted(yearly_values.keys())
            values = [yearly_values[y] for y in labels]
            chart_data_dict[metric_name] = {
                "title": f"{metric_name} Trend",
                "labels": labels,
                "values": values
            }

    return fact_registry, chart_data_dict

# ---------------------------------------------------------
# ENRICH PPT POINTS WITH IMAGE/CHART
# ---------------------------------------------------------
def enrich_slides(ppt_points, chart_data_dict):
    for slide in ppt_points.get("slides", []):
        # IMAGE QUERY
        title = slide.get("title", "").lower()
        if "business profile" in title:
            slide['image_query'] = "factory operations"
        elif "investment highlights" in title:
            slide['image_query'] = "manufacturing achievement"
        else:
            slide['image_query'] = None

        # CHART DATA: assign if any metrics match
        if "financial" in title or "operational" in title:
            # check each bullet's metric_id
            metrics_in_slide = []
            for b in slide.get("bullets", []):
                for mid in b.get("metric_ids", []):
                    if mid in chart_data_dict:
                        metrics_in_slide.append(mid)
            # Use first metric found for chart_data
            if metrics_in_slide:
                slide['chart_data'] = chart_data_dict[metrics_in_slide[0]]
                slide['image_query'] = None  # required per rules
            else:
                slide['chart_data'] = None
        else:
            slide['chart_data'] = None

        # Ensure every bullet has at least one fact_id or metric_id
        for idx, b in enumerate(slide.get("bullets", [])):
            if not b.get("fact_ids") and not b.get("metric_ids"):
                # fallback
                b['fact_ids'] = [f"F{idx+1}"]

    return ppt_points

# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate PPT and citations from company markdown")
    parser.add_argument("--company", required=True, help="Company name (used for search and output filenames)")
    parser.add_argument("--file", required=True, help="Markdown file name (must be in the same folder as this script)")
    args = parser.parse_args()

    company_name = args.company
    input_file = args.file

    # ------------------------
    # STEP 1: LOAD RAW DATA
    # ------------------------
    raw_text = ingest_data(input_file)
    if not raw_text:
        exit()

    # STEP 1.1: LOAD PUBLICLY AVAILABLE INFO
    print(f"Searching web for: {company_name} business model manufacturing capacity financials...")
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

    # ------------------------
    # STEP 2: ANALYZE (LLM)
    # ------------------------
    print("\n[1/4] Analyzing Data (LLM)...")
    structured_output = model.get_response_from_llm(
        model="mistral:7b",
        prompt_path="llms/prompts/analyzer.txt",
        data=combined_text,
        temp=0.0
    )

    if not structured_output:
        print("ERROR: Analyzer returned empty data.")
        exit()

    print(structured_output)  # For debugging
    print(f"      Extracted {len(str(structured_output))} characters of data.")

    # ------------------------
    # STEP 3: GENERATE CONTENT (DRAFT SLIDES)
    # ------------------------
    print("\n[2/4] Drafting Slides (LLM)...")
    # First ensure fallback fact_ids & chart metrics
    fact_registry, chart_data_dict = normalize_facts_and_metrics(structured_output, public_text_blocks)

    ppt_points = model.get_response_from_llm(
        model="phi3:mini",
        prompt_path="llms/prompts/slide_gen.txt",
        data=json.dumps(structured_output),
        temp=0.0
    )


    # Enrich with images and charts
    ppt_points = enrich_slides(ppt_points, chart_data_dict)
    # print(f"      Preview: {ppt_points['slides'][0]['bullets'][0]['text'][:50]}...")
    print(ppt_points)  # For debugging
    # ------------------------
    # STEP 4: CREATE POWERPOINT
    # ------------------------
    
    print("\n[3/4] Creating PowerPoint...")
    ppt_points = scrub_company_names(ppt_points, company_name)
    ppt_engine.generate_styled_ppt(ppt_points, f"Blind_Teaser_{company_name}_Final.pptx")

    # -----------------------------
    # STEP 5: GENERATE CITATIONS
    # -----------------------------
    print("\n[4/4] Creating Citation Doc...")

    # ---- BUILD FACT REGISTRY FROM SLIDES ----
    fact_registry = {}

    for slide in ppt_points.get("slides", []):
        for bullet in slide.get("bullets", []):
            text = bullet.get("text", "").strip()
            if not text:
                continue
            # Attach all fact_ids
            for fid in bullet.get("fact_ids", []):
                if fid not in fact_registry:
                    # Assign text and temporary source
                    fact_registry[fid] = {
                        "text": text,
                        "source": {"source": "From the given .md file"}  # default source
                    }

    # ---- MERGE PUBLIC SOURCES ----
    for item in public_info:
        if isinstance(item, dict) and "text" in item:
            source_name = item.get("source", "Public Source")
            excerpt_text = item["text"].strip()
            # Attach this public source to all facts that do not yet have a better source
            for fid, fdata in fact_registry.items():
                # Only overwrite if source is default
                if fdata.get("source", {}).get("source") == "LLM Generated":
                    fdata["source"] = {"source": source_name}
                    # Optionally, append snippet from public text if fact text is empty
                    if not fdata["text"]:
                        fdata["text"] = excerpt_text[:200]  # first 200 chars

    # ---- GENERATE DOC ----
    doc_engine.generate_citation_doc(
        ppt_data=ppt_points,
        fact_registry=fact_registry,
        filename=f"{company_name}_Citations.docx"
    )
