# Doc_to_PPT
#### Data Pack
#### ↓
#### LLM #1 (Extract & Understand)
#### ↓
#### Structured Company Data
#### ↓
#### Validation & Masking Layer (Blind Logic)
#### ↓
#### LLM #2 (Generate Slide Points)
#### ↓
#### Slide JSON
#### ↓
#### Python PPT Renderer


OLLAMA_MODELS="/Volumes/Seag/ollama_models" ollama serve
 python -m main --company "Gati" --file "/Volumes/Seag/AIML_GC/Company Data/logistics-gati/Gati-OnePager.md"