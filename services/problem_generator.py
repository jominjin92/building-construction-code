import openai
import json
import logging

# GPT 문제 생성
def generate_openai_problem(question_type, problem_source):
    if question_type == "객관식":
        prompt = f"""
        당신은 건축시공학 교수입니다. 건축시공학과 관련된 객관식 4지선다형 문제를 하나 출제하세요.
        아래 형식의 JSON 으로 출력하세요. JSON 외의 텍스트는 출력하지 마세요.

        {{
          "문제": "...",
          "선택지1": "...",
          "선택지2": "...",
          "선택지3": "...",
          "선택지4": "...",
          "정답": "1",
          "해설": "..."
        }}
        """
    else:
        prompt = f"""
        당신은 건축시공학 교수입니다. 건축시공학과 관련된 주관식 문제를 하나 출제하세요.
        아래 형식의 JSON 으로 출력하세요. JSON 외의 텍스트는 출력하지 마세요.

        {{
          "문제": "...",
          "모범답안": "...",
          "해설": "..."
        }}
        """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        result = response['choices'][0]['message']['content']
        result_json = json.loads(result)

        if question_type == "주관식":
            return {
                "문제": result_json.get("문제", ""),
                "선택지": ["", "", "", ""],
                "정답": result_json.get("모범답안", ""),
                "문제출처": problem_source,
                "문제형식": question_type,
                "해설": result_json.get("해설", ""),
                "id": None
            }
        else:
            return {
                "문제": result_json.get("문제", ""),
                "선택지": [
                    result_json.get("선택지1", ""),
                    result_json.get("선택지2", ""),
                    result_json.get("선택지3", ""),
                    result_json.get("선택지4", "")
                ],
                "정답": result_json.get("정답", ""),
                "문제출처": problem_source,
                "문제형식": question_type,
                "해설": result_json.get("해설", ""),
                "id": None
            }

    except Exception as e:
        logging.error(f"GPT 문제 생성 오류: {e}")
        return None

def generate_question_from_lecture(lecture_text):
    prompt = f"""
    당신은 건축시공학 교수입니다. 아래 강의 내용을 바탕으로 객관식 4지선다형 문제를 하나 출제해주세요.
    JSON 형식으로 출력해주세요. JSON 외의 텍스트는 출력하지 마세요.

    [강의 내용]
    {lecture_text[:1500]}

    아래 형식으로 출력하세요:
    {{
      "문제": "...",
      "선택지1": "...",
      "선택지2": "...",
      "선택지3": "...",
      "선택지4": "...",
      "정답": "1",
      "해설": "..."
    }}
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        result = response['choices'][0]['message']['content']
        result_json = json.loads(result)

        return {
            "문제": result_json.get("문제", ""),
            "선택지": [
                result_json.get("선택지1", ""),
                result_json.get("선택지2", ""),
                result_json.get("선택지3", ""),
                result_json.get("선택지4", "")
            ],
            "정답": result_json.get("정답", ""),
            "해설": result_json.get("해설", ""),
            "문제출처": "강의자료 기반",
            "문제형식": "객관식",
            "id": None
        }

    except Exception as e:
        logging.error(f"강의자료 기반 문제 생성 오류: {e}")
        return None

def generate_question_by_keyword(keyword: str) -> dict:
    prompt = f"""
    아래 키워드와 관련된 건축시공학 분야의 객관식 문제를 1개 생성해줘.
    - 키워드: {keyword}
    - 형식: 문제, 선택지 4개, 정답, 해설
    - 형식 예시:
    Q: 콘크리트의 압축강도는 무엇을 의미하는가?
    A. 인장강도  B. 휨강도  C. 압축에 대한 저항력  D. 전단강도
    정답: C
    해설: 압축강도는 콘크리트가 압축 하중에 견디는 능력을 의미한다.
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=500
    )
    return response.choices[0].message.content.strip()