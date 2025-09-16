import io, re, json, requests
import pandas as pd
try:
    import pdfplumber
except Exception:
    pdfplumber = None

def extract_from_pdf(file_bytes):
    text = ""
    tables = []
    if pdfplumber is None:
        return {"text":"pdfplumber not installed - cannot parse PDF.", "tables": []}
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
            try:
                page_tables = page.extract_tables()
                if page_tables:
                    for t in page_tables:
                        df = pd.DataFrame(t[1:], columns=t[0])
                        tables.append(df)
            except Exception:
                pass
    return {"text": text, "tables": tables}

def extract_from_excel(file_bytes):
    try:
        excel = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)
        text = ""
        tables = []
        for name, df in excel.items():
            text += f"Sheet: {name}\n"
            text += df.to_csv(index=False) + "\n"
            tables.append(df)
        return {"text": text, "tables": tables}
    except Exception as e:
        return {"text": f"Failed to read Excel: {e}", "tables": []}

def build_context(parsed):
    text = parsed.get("text","")
    tables = parsed.get("tables",[])
    lines = [text.strip()]
    for i,df in enumerate(tables):
        lines.append(f"--- Table {i+1} ---")
        try:
            lines.append(df.head(20).to_csv(index=False))
        except Exception:
            lines.append(str(df))
    return "\n".join(lines)

def ask_ollama_or_fallback(question, context, model="gemma3"):
    prompt = f"""You are a helpful financial assistant. Use the context below (from an uploaded financial document) to answer the user's question. If not found, say so.

CONTEXT:
{context}

QUESTION: {question}

Answer concisely with numbers and a brief explanation."""
    try:
        url = "http://localhost:11434/api/generate"
        payload = {"model": model, "prompt": prompt, "stream": False}
        resp = requests.post(url, json=payload, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("response") or data.get("text") or json.dumps(data)
        else:
            return fallback_answer(question, context, note=f"Ollama returned {resp.status_code}")
    except Exception as e:
        return fallback_answer(question, context, note=f"Ollama call failed: {e}")

def fallback_answer(question, context, note=None):
    q = question.lower()
    candidates = []
    for line in context.splitlines():
        l = line.strip()
        if not l: continue
        if any(k in l.lower() for k in ["revenue","sales","net income","profit","expense","ebitda","assets","liabilities","cash"]):
            if re.search(r"\d", l):
                candidates.append(l)
    out = ""
    if note: out += note + "\n\n"
    if candidates:
        out += "I found these relevant lines in the document:\n\n"
        out += "\n".join(candidates[:20])
    else:
        out += "Couldn't find clear numeric lines matching the question. Try rephrasing or upload a clearer statement."
    return out
