#  Medical Study Companion (Streamlit + Ollama + SciSpaCy)

A free, student‑friendly web app that:
- Ingests **PDF** lecture notes
- Generates **quizzes** (MCQ, T/F, short‑answer, fill‑in‑the‑blank, essay) using a **local LLM** (Ollama)
- Tracks performance with **SRS (spaced repetition)** for better retention
- Offers a **task planner** (goals, due dates) and **insights**
- (Optional) embeds **GPT‑5 Chat** via the official ChatGPT website for premium assistance (students log in themselves)

> Zero API keys required for the core functionality. Fully local on your machine.

---

##  Features

- **PDF → Concepts:** Clean extraction with PyMuPDF and medical NER via SciSpaCy (`en_core_sci_md`)
- **Local LLM (Free):** Uses **Ollama** (e.g., ```mistral``` or ```llama3:8b```) to generate questions
- **Quiz Engine:** Mixed formats + correctness checks
- **SRS Memory Model:** Leitner/SM‑2 style scheduling for reviews
- **Planner:** Create tasks, set due dates, view upcoming study items
- **Insights (starter):** Accuracy, progress, and upcoming reviews
- **Optional GPT‑5 panel:** Embedded ChatGPT window for students who want it (no cost to you)

---

##  Project Structure
```
├── app.py
├── components/
│ ├── upload_pdf.py
│ ├── quiz.py
│ ├── planner.py
│ ├── recommendations.py
│ └── utils.py
├── services/
│ ├── pdf_processor.py
│ ├── question_generator.py
│ ├── task_scheduler.py
│ ├── recommender.py
│ └── srs.py
├── requirements.txt
├── Procfile
└── README.md
```

##  Prerequisites

- **Python 3.10–3.12** recommended
- **Ollama** (for local LLM)
- Platform: macOS / Linux / Windows

### Install Ollama
- **macOS / Linux / WSL:**
  ```bash
  curl -fsSL https://ollama.com/install.sh | sh
  ```
## Local Setup

Clone the repo

```
git clone <your-repo-url>
cd MedStud
```

Create a virtual environment
```
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
```

Install Python deps
```
pip install -r requirements.txt  #(First run only)
```

## Verify SciSpaCy model
We include the model in requirements.txt via URL. If your environment blocks it, run:
```
python -m spacy download en_core_sci_md
```

Then update services/pdf_processor.py to load it if needed.
Ensure Ollama is running In a separate terminal:
```
ollama serve     # usually auto-starts with first call
ollama pull mistral
```

Run the app
```
streamlit run app.py
```

## How It Works (Core Logic)
### PDF Processing & NER
PyMuPDF (pymupdf) extracts clean text per page.

SciSpaCy (en_core_sci_md) identifies medical entities (diseases, drugs, anatomy).

We segment text into learning chunks (sentences/paragraphs with entities) to feed the generator.

### Question Generation (Local)

We call Ollama’s HTTP API (/api/generate) with prompt templates to produce:

- MCQs with distractors

- Short‑answer/fill‑in‑the‑blank

- True/False and Essay prompts

Parsing is done with simple regex/format rules (can be upgraded anytime).

### SRS (Spaced Repetition)

Each question has an SRS record:

- ease_factor, repetitions, interval, next_review

- Correct answers increase interval & EF; wrong answers decrease EF and reset interval.

The Planner page surfaces today’s due reviews automatically.