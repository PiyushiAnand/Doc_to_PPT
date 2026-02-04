# doc_engine.py
from docx import Document

def generate_citation_doc(ppt_data, filename):
    doc = Document()
    doc.add_heading('Citation Reference Document', 0)
    
    for slide in ppt_data["slides"]:
        doc.add_heading(slide["title"], level=1)
        
        if "citations" in slide:
            for cit in slide["citations"]:
                p = doc.add_paragraph()
                p.add_run(f"Fact ID: {cit.get('fact_id', 'N/A')}").bold = True
                p.add_run(f"\nSource: {cit.get('section', 'General')}")
                p.add_run(f"\nExcerpt: \"{cit.get('line_excerpt', '')}\"")
                p.add_run("\n" + "-"*20)
                
    doc.save(filename)
    print(f"Citation Doc Saved: {filename}")