import streamlit as st
import datetime

def planner_section():
    st.header("Step 3: Task Planner")
    if "tasks" not in st.session_state:
        st.session_state["tasks"] = []

    new_task = st.text_input("New Task")
    due = st.date_input("Due Date", datetime.date.today())
    if st.button("Add Task"):
        st.session_state["tasks"].append({"task": new_task, "due": due})
        st.success("Task added!")

    st.subheader("Upcoming Tasks")
    for t in sorted(st.session_state["tasks"], key=lambda x: x["due"]):
        st.write(f"- {t['task']} (due {t['due']})")
