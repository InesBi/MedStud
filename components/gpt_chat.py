import streamlit as st

def gpt5_chat_window():
    st.header(" GPT‑5 Assistant")
    st.write("This is a GPT‑5 powered assistant. Requires ChatGPT login.")
    st.markdown("""
    <iframe src="https://chat.openai.com/chat"
            width="100%" height="600px" frameborder="0">
    </iframe>
    """, unsafe_allow_html=True)
