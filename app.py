import streamlit as st
from utils import extract_from_pdf, extract_from_excel, build_context, ask_ollama_or_fallback

st.set_page_config(page_title="Financial Doc Q&A Assistant", layout="wide")

st.title("Financial Q&A Assistant")
st.write("Upload a PDF or Excel containing financial statements (income statement, balance sheet, cash flows) and ask questions in natural language.")

# Upload Section
uploaded = st.file_uploader("Upload PDF or Excel", type=["pdf","xlsx","xls"], accept_multiple_files=False)
if uploaded:
    file_bytes = uploaded.read()
    st.session_state['filename'] = uploaded.name
    st.info(f"Processing {uploaded.name} ...")
    if uploaded.type == "application/pdf" or uploaded.name.lower().endswith(".pdf"):
        parsed = extract_from_pdf(file_bytes)
    else:
        parsed = extract_from_excel(file_bytes)
    st.success("Extraction complete — preview below.")
    st.subheader("Extracted Text / Tables (preview)")
    st.code(parsed['text'][:4000] + ("..." if len(parsed['text']) > 4000 else ""))
    st.session_state['context'] = build_context(parsed)
else:
    st.info("No file uploaded yet. You can try the sample files in the repo.")

# Sidebar QA Chat
st.sidebar.header("QA Chat")
qa = st.sidebar.text_area("Ask a question about the uploaded document", height=120)
model = st.sidebar.text_input("Ollama model (optional)", value="gemma3")

if st.sidebar.button("Ask") and qa.strip():
    context = st.session_state.get('context', None)
    if context is None:
        st.sidebar.error("Please upload and process a document first.")
    else:
        with st.spinner("Generating answer..."):
            answer = ask_ollama_or_fallback(question=qa, context=context, model=model)
        st.sidebar.markdown("**Answer:**")
        st.sidebar.write(answer)
