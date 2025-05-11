import streamlit as st
import pandas as pd
import uuid
import os
from db.query import record_attempt, record_feedback
from db.query import save_result_to_csv
from db.query import save_problem_to_db
from db.query import load_problems_from_db
from services.problem_generator import generate_question_by_keyword
from utils.save_to_csv import save_problem_to_csv
from services.problem_parser import parse_gpt_problem
from services.keyword_extractor import extract_keywords_tfidf

keyword_to_chapter = {
    "가설": "가설공사", "안전펜스": "가설공사", "가림막": "가설공사",
    "토공": "토공사", "흙막이": "토공사", "절토": "토공사",
    "기초": "지정 및 기초공사", "지정": "지정 및 기초공사", "말뚝": "지정 및 기초공사",
    "거푸집": "거푸집공사", "폼타이": "거푸집공사",
    "철근": "철근공사", "배근": "철근공사", "이음": "철근공사",
    "콘크리트": "콘크리트공사", "양생": "콘크리트공사", "타설": "콘크리트공사",
    "철골": "철골공사", "용접": "철골공사",
    "조적": "조적공사", "벽돌": "조적공사",
    "방수": "방수공사", "도막": "방수공사",
    "지붕": "지붕 및 홈통공사", "홈통": "지붕 및 홈통공사",
    "미장": "미장공사", "몰탈": "미장공사",
    "타일": "타일 및 돌공사", "석재": "타일 및 돌공사",
    "창호": "창호 및 유리공사", "유리": "창호 및 유리공사",
    "금속": "금속공사", "철물": "금속공사",
    "도장": "도장공사", "페인트": "도장공사",
    "수장": "수장공사", "내장": "수장공사",
    "단열": "단열공사", "단열재": "단열공사",
    "커튼월": "커튼월공사", "알루미늄패널": "커튼월공사"
}

def keyword_problem_generation_ui():
    st.subheader("🔍 키워드로 문제 생성")
    keyword = st.text_input("문제 생성을 원하는 키워드를 입력하세요")
    난이도 = st.selectbox("난이도 선택", ["하", "중", "상"], index=1)

    if st.button("문제 생성"):
        if keyword:
            with st.spinner("문제를 생성 중입니다..."):
                raw_text = generate_question_by_keyword(keyword)
            st.success("문제가 생성되었습니다.")
            st.text_area("생성된 문제 (원문)", value=raw_text, height=200)

            parsed = parse_gpt_problem(raw_text)

            if parsed["문제"] and len(parsed["선택지"]) == 4 and parsed["정답"]:
                st.session_state.generated_problem = {
                    "id": str(uuid.uuid4()),
                    "문제": parsed["문제"],
                    "선택지": parsed["선택지"],
                    "정답": parsed["정답"],
                    "해설": parsed["해설"],
                    "문제출처": "GPT 키워드 생성",
                    "문제형식": "객관식",
                    "키워드": keyword,
                    "난이도": 난이도
                }
            else:
                st.error("⚠️ 문제 파싱에 실패했습니다. 생성된 텍스트 형식을 확인해 주세요.")

    if "generated_problem" in st.session_state:
        if st.button("📁 문제 저장 (CSV)"):
            save_problem_to_csv(st.session_state.generated_problem)
            st.success("문제가 generated_problems.csv 파일에 저장되었습니다.")

    if os.path.exists("generated_problems.csv"):
        with open("generated_problems.csv", "rb") as f:
            st.download_button(
                label="📥 CSV 파일 다운로드",
                data=f,
                file_name="generated_problems.csv",
                mime="text/csv"
            )

    st.markdown("---")
    st.markdown("### 🔍 자동 키워드 추천")

    if st.button("📌 CSV 파일에서 키워드 추출하기"):
        try:
            df = pd.read_csv("generated_problems.csv")
            if not df.empty:
                keyword_candidates = extract_keywords_tfidf(df["문제"].tolist(), n_keywords=10)
                st.session_state.keyword_candidates = keyword_candidates
            else:
                st.warning("CSV 파일에 문제가 없습니다.")
        except Exception as e:
            st.error(f"키워드 추출 실패: {e}")

    if "keyword_candidates" in st.session_state:
        selected_keywords = st.multiselect("추천 키워드 중 선택", st.session_state.keyword_candidates)

        if st.button("선택한 키워드로 문제 생성"):
            for keyword in selected_keywords:
                with st.spinner(f"{keyword} 기반 문제 생성 중..."):
                    raw_text = generate_question_by_keyword(keyword)
                    parsed = parse_gpt_problem(raw_text)

                    if parsed["문제"] and len(parsed["선택지"]) == 4 and parsed["정답"]:

                        chapter = keyword_to_chapter.get(keyword, "총론")
                        problem_data = {
                            "id": str(uuid.uuid4()),
                            "문제": parsed["문제"],
                            "선택지": parsed["선택지"],
                            "정답": parsed["정답"],
                            "해설": parsed["해설"],
                            "문제출처": "GPT 키워드 생성",
                            "문제형식": "객관식",
                            "키워드": keyword,
                            "난이도": "중",
                            "챕터": chapter
                        }
                        save_problem_to_csv(problem_data)
                        st.success(f"✅ 키워드 [{keyword}] 기반 문제 저장 완료")
                    else:
                        st.warning(f"⚠️ [{keyword}] 문제 파싱 실패")

def render_problem_tab():
    st.subheader("문제풀이")
    col1, col2 = st.columns([2, 4])

    with col1:
        st.markdown("### 문제 출처 및 수 선택")
        selected_source = st.radio("문제 출처 선택", (
            "건축기사 기출문제", 
            "건축시공 기출문제", 
            "GPT 생성 문제 (CSV)"
        ))
        num_objective = st.number_input("객관식 문제 수", min_value=1, value=3, step=1)
        num_subjective = 0
        if selected_source == "건축시공 기출문제":
            num_subjective = st.number_input("주관식 문제 수", min_value=0, value=2, step=1)

        if st.button("문제 시작하기"):
            st.session_state.problem_list = []
            st.session_state.show_problems = True
            st.session_state.user_answers = {}
            st.session_state.show_results = {}

            if selected_source == "건축기사 기출문제":
                try:
                    df = pd.read_csv("456.csv")
                    if not df.empty:
                        sampled_df = df.sample(n=num_objective, random_state=42)
                        for prob in sampled_df.to_dict(orient='records'):
                            prob['id'] = str(uuid.uuid4())
                            prob['문제출처'] = '건축기사 기출문제'
                            prob['문제형식'] = '객관식'
                            prob['선택지'] = [prob.get(f'선택지{i+1}', '') for i in range(4)]
                            prob['정답'] = str(prob.get('정답', ''))
                            prob['해설'] = prob.get('해설', '')

                            saved = save_problem_to_db(prob)
                            st.session_state.problem_list.append(saved)

                        st.success(f"CSV에서 문제 {len(st.session_state.problem_list)}개 불러오기 완료!")
                    else:
                        st.warning("CSV 파일이 비어 있습니다.")
                except FileNotFoundError:
                    st.error("CSV 파일이 존재하지 않습니다.")
                except Exception as e:
                    st.error(f"문제 불러오기 오류: {e}")

            elif selected_source == "건축시공 기출문제":
                for _ in range(num_objective):
                    prob = load_problems_from_db("건축시공 기출문제", "객관식", 1)
                    if prob:
                        st.session_state.problem_list.extend(prob)
                for _ in range(num_subjective):
                    prob = load_problems_from_db("건축시공 기출문제", "주관식", 1)
                    if prob:
                        st.session_state.problem_list.extend(prob)

            elif selected_source == "GPT 생성 문제 (CSV)":
                try:
                    df = pd.read_csv("generated_problems.csv")
                    if not df.empty:
                        sampled_df = df.sample(n=min(num_objective, len(df)), random_state=42)
                        for prob in sampled_df.to_dict(orient='records'):
                            prob['id'] = str(uuid.uuid4())
                            prob['선택지'] = [prob.get(f'선택지{i+1}', '') for i in range(4)]
                            prob['문제출처'] = "GPT 키워드 생성"
                            prob['문제형식'] = "객관식"
                            prob['정답'] = str(prob.get('정답', ''))
                            prob['해설'] = prob.get('해설', '')

                            st.session_state.problem_list.append(prob)

                        st.success(f"GPT 생성 문제 {len(st.session_state.problem_list)}개 불러오기 완료!")
                    else:
                        st.warning("CSV 파일이 비어 있습니다.")
                except FileNotFoundError:
                    st.error("CSV 파일이 존재하지 않습니다.")
                except Exception as e:
                    st.error(f"문제 로딩 오류: {e}")

    with col2:
        if st.session_state.get("show_problems", False):
            st.markdown("### 📝 문제 풀이")
            for idx, prob in enumerate(st.session_state.problem_list):
                st.markdown(f"### 문제 {idx + 1}: {prob['문제']}")
                answer_key = f"answer_{idx}"
                if prob["문제형식"] == "객관식":
                    user_answer = st.radio("선택지", prob["선택지"], key=answer_key)
                else:
                    user_answer = st.text_area("답안을 입력하세요", key=answer_key)

                st.session_state.user_answers[prob['id']] = user_answer

            if st.button("채점하기"):
                st.session_state.show_results = {}
                for idx, prob in enumerate(st.session_state.problem_list):
                    user_answer = st.session_state.user_answers.get(prob['id'], "").strip()
                    correct_answer = str(prob["정답"]).strip()
                    is_correct = user_answer == correct_answer

                    record_attempt(
                        user_id=st.session_state.username,
                        problem_id=prob['id'],
                        user_answer=user_answer,
                        is_correct=is_correct
                    )

                    save_result_to_csv(
                        user_id=st.session_state.username,
                        question=prob["문제"],
                        selected=user_answer,
                        correct=correct_answer,
                        concept=prob.get("챕터", "기타"),
                        is_correct=is_correct,
                        solve_time=42  # 추후 수정 가능
                    )

                    st.session_state.show_results[prob['id']] = is_correct

                st.rerun()

        if st.session_state.get("show_results", False):
            st.markdown("### ✅ 채점 결과")
            correct_count = 0
            total = len(st.session_state.problem_list)

            for idx, prob in enumerate(st.session_state.problem_list):
                result = st.session_state.show_results.get(prob['id'], False)
                if result:
                    st.success(f"문제 {idx + 1}: 정답 🎉")
                    correct_count += 1
                else:
                    st.error(f"문제 {idx + 1}: 오답 ❌ (정답: {prob['정답']})")
                    with st.expander("해설 보기"):
                        st.info(prob.get("해설", "해설이 등록되지 않았습니다."))

                    feedback = st.text_area(f"문제 {idx + 1} 피드백 작성", key=f"feedback_{idx}")
                    if st.button(f"문제 {idx + 1} 피드백 저장", key=f"save_feedback_{idx}"):
                        if feedback.strip():
                            record_feedback(
                                user_id=st.session_state.username,
                                problem_id=prob['id'],
                                feedback_text=feedback
                            )
                            st.success("피드백이 저장되었습니다.")

            st.markdown(f"### 🎯 최종 정답률: **{correct_count} / {total}** ({(correct_count/total)*100:.2f}%)")