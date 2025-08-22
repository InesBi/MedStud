import streamlit as st
from services.question_generator import generate_questions

def quiz_section():
    if "pdf_data" not in st.session_state:
        st.warning("Upload a PDF first.")
        return

    st.header("Step 2: Quiz Time!")
    if st.button("Generate Quiz"):
        with st.spinner("Generating questions..."):
            questions = generate_questions(st.session_state["pdf_data"])
        st.session_state["questions"] = questions
        st.session_state["q_idx"] = 0

    if "questions" in st.session_state:
        idx = st.session_state["q_idx"]
        q = st.session_state["questions"][idx]
        st.markdown(f"**Q{idx+1}:** {q['prompt']}")
        answer = st.radio("Choose an answer", q["options"])
        if st.button("Submit"):
            is_correct = q["answer"].strip().endswith(answer[0])
            st.success("✅ Correct!") if is_correct else st.error(f"❌ Wrong — Correct: {q['answer']}")
            st.session_state["q_idx"] += 1
            if st.session_state["q_idx"] >= len(st.session_state["questions"]):
                st.success("🎉 Quiz complete!")