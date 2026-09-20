# Hesham

تقييم تكيّفي بالذكاء الاصطناعي. ترفع محاضرة PDF، وهشام يسألك أسئلة مفتوحة، ويحلل إجابتك ويحدد الفهم الغلط بالظبط، وبعدين يعمل سؤال يستهدف الغلط ده ويعدّل الصعوبة، وفي الآخر يطلّعلك تقرير.

Adaptive assessment: upload a lecture PDF, answer open-ended questions, and Gemini finds the specific
misconception in each answer. The next question targets that gap and the difficulty adapts.
After two wrong answers in a row Hesham gives a short explanation. At the end you get a performance report.

## Run

Use Python 3.12 or 3.13 (Python 3.15 can't build `pyarrow`, which Streamlit needs).

```
python -m venv venv
venv\Scripts\activate            # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env           # macOS/Linux: cp .env.example .env
notepad .env                     # put your GOOGLE_API_KEY (https://aistudio.google.com/app/apikey)
streamlit run app.py
```

Never commit `.env`. On Codespaces, add `GOOGLE_API_KEY` as a Codespaces secret instead.

## Files

| File | What it does |
|---|---|
| `app.py` | Streamlit UI and the adaptive session flow |
| `engine.py` | Question generation, answer analysis, difficulty, explanation, report |
| `llm.py` | The only file that talks to Gemini (retries, JSON parsing, friendly errors) |
| `pdf_utils.py` | Text extraction from PDFs |
| `test_engine.py` | Engine tests that need no API key: `python test_engine.py` |

## Adaptive rules

```
correct -> harder question
close   -> same level, question targets the missing/confused idea
far     -> easier question on the gap; two "far" in a row -> short explanation first
```

Change the model without touching code: set `GEMINI_MODEL` in `.env`.
