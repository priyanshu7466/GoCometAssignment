# Nova Trade Document Pipeline

A multi-agent AI system that automatically extracts, validates, and routes trade documents (like Bills of Lading and Commercial Invoices) to replace manual data entry in logistics.


## 🚀 Quick Start

**1. Install Dependencies**
```bash
pip install -r requirements.txt
```

**2. Set up Groq API Key**

*Windows (Command Prompt):*
```cmd
set GROQ_API_KEY=your_api_key_here
```
*Mac/Linux:*
```bash
export GROQ_API_KEY="your_api_key_here"
```

**3. Run the Server**
```bash
python api/main.py
```

**4. Try it out!**
Open `http://localhost:8000` in your browser. 
You can use the provided sample documents located in the `sample_docs/` folder:
- Try uploading `clean_bill_of_lading.pdf` to see an Auto-Approve workflow.
- Try uploading `messy_bill_of_lading.pdf` to see the system catch errors and draft an amendment email!

## 🧠 How it Works (The Architecture)

This pipeline uses three specialized AI agents working together:

1. **Extractor Agent (Vision AI):** Uses `llama-4-scout` (via Groq) to look at the PDF image and extract 10 key fields (like Consignee Name, HS Code) into structured JSON data. It also assigns a confidence score to every field.
2. **Validator Agent (Deterministic Code):** Takes the extracted data and runs it through strict Python business rules (found in `rules/customer_rules.json`). It catches spelling mistakes, mismatched codes, and missing fields perfectly without hallucinating.
3. **Router Agent (Text AI):** Uses `llama-3.3-70b-versatile` to look at the validation results. If everything is perfect, it Auto-Approves. If there are mismatches, it flags the document and automatically drafts a polite email to the supplier asking for corrections.

## 📂 Project Structure

- `/agents`: The 3 core agents (Extractor, Validator, Router).
- `/api`: The FastAPI server that wires everything together.
- `/ui`: The frontend HTML/CSS/JS dashboard.
- `/storage`: SQLite database setup and Natural Language to SQL query engine.
- `/sample_docs`: Test PDFs you can use to demo the system.

## 💬 Natural Language Search
Because all extractions and decisions are saved to a SQLite database, there is a built-in "Chat" feature on the UI. You can ask questions like:
- *"How many shipments had mismatches?"*
- *"Show me all shipments going to Germany."*
The AI will translate your question into SQL, run it against the database, and give you the answer!
