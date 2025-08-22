import requests

def generate_questions(pdf_data):
    questions = []
    for chunk in pdf_data.get("chunks", []):
        prompt = f"""
        Generate a multiple choice medical question from this text:

        "{chunk}"

        Return format:
        Q: ...
        A. ...
        B. ...
        C. ...
        D. ...
        Correct Answer: ...
        """
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "mistral", "prompt": prompt, "stream": False}
        )
        content = response.json()['response']
        questions.append(parse_mcq(content))
    return questions

def parse_mcq(text):
    # Very naive parse — you'd want regex or NLP to clean up better
    lines = text.strip().split("\n")
    q = {"type": "mcq", "prompt": lines[0], "options": lines[1:5], "answer": lines[-1]}
    return q

