import streamlit as st
from services.pdf_processor import process_pdf

def upload_pdf_section():
    st.header("Step 1: Upload Your Study Materials")
    uploaded = st.file_uploader("Upload lecture PDF", type=["pdf"])
    if uploaded:
        st.success("PDF uploaded! Processing...")
        data = process_pdf(uploaded)
        st.session_state["pdf_data"] = data
        st.write("Extracted sections:")
        for heading in data.get("headings", []):
            st.write("•", heading)
