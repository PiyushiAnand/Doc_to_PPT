# Doc_to_PPT
#### Data Pack
#### ↓
#### LLM #1 (Extract & Understand)
#### ↓
#### Structured Company Data
#### ↓
#### LLM #2 (Generate Slide Points)
#### ↓
#### Slide JSON
#### ↓
#### Python PPT Renderer


## Steps to Reproduce the Results

1. Create a Python virtual environment.

2. Download and install Ollama on your system.

3. Activate the virtual environment, install dependencies, start the Ollama server, and pull the required models:

```bash
source .venv/bin/activate
pip install -r requirements.txt
OLLAMA_MODELS=<path_to_model_directory> ollama serve
ollama pull qwen2.5:7b-instruct
ollama pull phi3:mini
```

### Example
```bash
 OLLAMA_MODELS="/Volumes/Seag/ollama_models" ollama serve
```
4. Run:
```bash
 python -m main --company "<company_name>" --file "<path_to_company_file>"
 ```
### Example
```bash
python -m main --company "Gati" --file "/Volumes/Seag/AIML_GC/Company Data/logistics-gati/Gati-OnePager.md"
```
