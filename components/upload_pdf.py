# components/upload_pdf.py
import streamlit as st
from services.pdf_processor import process_pdf

def upload_pdf_section():
    st.header("Step 1: Upload Your Study Materials")
    uploaded = st.file_uploader("Upload lecture PDF", type=["pdf"])

    if uploaded:
        with st.spinner("Processing PDF..."):
            data = process_pdf(uploaded)
        st.session_state["pdf_data"] = data

        # reset quiz state whenever a new PDF is loaded
        st.session_state["questions"] = []
        st.session_state["q_idx"] = 0
        st.session_state["score"] = 0
        st.session_state["finished"] = False

        meta = data.get("meta", {})
        st.success(f"Processed {meta.get('pages','?')} page(s) with model '{meta.get('model','?')}'.")
        if meta.get("note"):
            st.warning(meta["note"])

        with st.expander("Detected headings (first 10)"):
            st.write(data.get("headings", [])[:10])
        with st.expander("Sample chunks (first 5)"):
            for c in data.get("chunks", [])[:5]:
                st.write("•", c)
