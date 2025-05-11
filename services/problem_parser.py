import re

def parse_gpt_problem(text: str):
    # 문제
    q_match = re.search(r"Q[:：]\s*(.*)", text)
    question = q_match.group(1).strip() if q_match else ""

    # 선택지 (A. ~ D.)
    choices_match = re.findall(r"[A-D][.．]\s*(.*?)(?=\s*[A-D][.．]|정답:|해설:|$)", text, re.DOTALL)
    choices = [c.strip() for c in choices_match]

    # 정답
    answer_match = re.search(r"정답[:：]?\s*([A-D])", text)
    answer_letter = answer_match.group(1).strip() if answer_match else ""
    answer_index = "ABCD".index(answer_letter) + 1 if answer_letter in "ABCD" else ""

    # 해설
    explanation_match = re.search(r"해설[:：]?\s*(.*)", text)
    explanation = explanation_match.group(1).strip() if explanation_match else ""

    return {
        "문제": question,
        "선택지": choices,
        "정답": str(answer_index),
        "해설": explanation
    }
