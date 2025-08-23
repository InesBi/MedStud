import streamlit as st
from components.upload_pdf import upload_pdf_section
from components.quiz import quiz_section
from components.planner import planner_section
from components.recommendations import recommendations_section
def ensure_state():
    ss = st.session_state
    ss.setdefault("pdf_data", None)
    ss.setdefault("questions", [])
    ss.setdefault("q_idx", 0)
    ss.setdefault("score", 0)
    ss.setdefault("finished", False)
def main():
    ensure_state()
    st.set_page_config(page_title="MedStud", layout="wide")
    st.title("Medical Study Companion")

    menu = ["Upload & Quiz", "Planner", "Recommendations", "Insights"]
    choice = st.sidebar.radio("Navigate", menu)

    if choice == "Upload & Quiz":
        upload_pdf_section()
        quiz_section()
    elif choice == "Planner":
        planner_section()
    elif choice == "Recommendations":
        recommendations_section()
    elif choice == "Insights":
        st.write("Insights dashboard coming soon...")

if __name__ == "__main__":
    main()
