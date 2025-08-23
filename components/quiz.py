import streamlit as st
from services.question_generator import generate_questions

def _init_quiz_state():
    ss = st.session_state
    ss.setdefault("questions", [])
    ss.setdefault("q_idx", 0)
    ss.setdefault("score", 0)
    ss.setdefault("finished", False)

def quiz_section():
    _init_quiz_state()
    if not st.session_state.get("pdf_data"):
        st.warning("No PDF loaded. Go to **Upload** page first.")
        st.stop()
    model = st.selectbox(
          "LLM model (Ollama)",
          ["llama3.2:3b-instruct", "qwen2.5:3b-instruct", "phi3:mini", "mistral"],
          index=0
      )
    mode = st.radio("Speed vs Quality", ["fast", "quality", "template"], index=0, horizontal=True)
    nq = st.slider("Questions to generate", 5, 20, 10, 1)
      # when you call generate:
    qs = generate_questions(st.session_state["pdf_data"], n_questions=nq, model=model, mode=mode)

    if "pdf_data" not in st.session_state:
        st.warning("Upload a PDF first.")
        return

    st.header("Step 2: Quiz Time!")
    c1, c2 = st.columns(2)

    with c1:
        if st.button("🔄 Generate Quiz", use_container_width=True):
            with st.spinner("Generating questions..."):
                qs = generate_questions(st.session_state["pdf_data"])
            if not qs:
                st.error("No questions were generated. Try a different PDF.")
                return
            st.session_state["questions"] = qs
            st.session_state["q_idx"] = 0
            st.session_state["score"] = 0
            st.session_state["finished"] = False

    with c2:
        if st.button("⏮️ Restart Quiz", use_container_width=True):
            if st.session_state["questions"]:
                st.session_state["q_idx"] = 0
                st.session_state["score"] = 0
                st.session_state["finished"] = False

    qs = st.session_state["questions"]
    if not qs:
        st.info("Click **Generate Quiz** to start.")
        return

    idx = st.session_state["q_idx"]
    total = len(qs)

    # bound check → if finished, show summary
    if idx >= total:
        st.session_state["finished"] = True

    if st.session_state["finished"]:
        st.success(f"🎉 Quiz complete! Score: {st.session_state['score']}/{total}")
        if st.button("Take Again"):
            st.session_state["q_idx"] = 0
            st.session_state["score"] = 0
            st.session_state["finished"] = False
        return

    # render current question
    q = qs[idx]
    st.progress((idx) / max(total, 1))
    st.subheader(f"Q{idx + 1} / {total}")
    st.markdown(f"**{q.get('prompt', '—')}**")

    # input widget by type
    key = f"user_answer_{idx}"
    qtype = q.get("type", "mcq").lower()
    user_answer = None

    if qtype == "mcq" and "options" in q:
        user_answer = st.radio("Choose an answer:", q["options"], key=key)
    elif qtype in {"truefalse", "true_false", "tf"}:
        user_answer = st.radio("True or False?", ["True", "False"], key=key)
    elif qtype in {"short", "short-answer", "fill-in-the-blank", "fill"}:
        user_answer = st.text_input("Your answer:", key=key)
    else:  # essay or unknown → free text
        user_answer = st.text_area("Your answer:", key=key, height=140)

    col_a, col_b = st.columns([1, 1])

    def _advance(correct: bool, reveal: str | None = None):
        if correct:
            st.session_state["score"] += 1
            st.success("✅ Correct!")
        else:
            if reveal:
                st.error(f"❌ Incorrect. Correct answer: {reveal}")
            else:
                st.info("📝 Saved. (Manually graded item)")
        st.session_state["q_idx"] = min(st.session_state["q_idx"] + 1, total)
        # Streamlit 1.36+: st.rerun(); older: experimental_rerun
        try:
            st.rerun()
        except Exception:
            st.experimental_rerun()

    with col_a:
        if st.button("Submit"):
            ans = (q.get("answer") or "").strip()
            correct = False
            reveal = ans

            if qtype == "mcq":
                # consider first letter (A/B/C/D) or full string match
                if user_answer:
                    ua = user_answer.strip().lower()
                    a0 = ans[:1].lower()
                    correct = (ua.startswith(a0)) or (ua == ans.strip().lower())
            elif qtype in {"truefalse", "true_false", "tf"}:
                correct = (str(user_answer).strip().lower() == ans.lower())
            elif qtype in {"short", "short-answer", "fill-in-the-blank", "fill"}:
                correct = (str(user_answer).strip().lower() == ans.lower())
            else:
                # essay / long answer → no auto-grading
                reveal = None

            _advance(correct, reveal)

    with col_b:
        if st.button("Skip"):
            _advance(False, q.get("answer"))
