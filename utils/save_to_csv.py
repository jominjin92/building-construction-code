import pandas as pd
import os

def save_problem_to_csv(problem_data: dict, filename: str = "generated_problems.csv"):
    df = pd.DataFrame([{
        "id": problem_data["id"],
        "문제": problem_data["문제"],
        "선택지1": problem_data["선택지"][0],
        "선택지2": problem_data["선택지"][1],
        "선택지3": problem_data["선택지"][2],
        "선택지4": problem_data["선택지"][3],
        "정답": problem_data["정답"],
        "해설": problem_data["해설"],
        "문제출처": problem_data["문제출처"],
        "문제형식": problem_data["문제형식"],
        "키워드": problem_data["키워드"],
        "난이도": problem_data["난이도"]
    }])

    if os.path.exists(filename):
        df.to_csv(filename, mode='a', index=False, header=False, encoding='utf-8-sig')
    else:
        df.to_csv(filename, index=False, encoding='utf-8-sig')