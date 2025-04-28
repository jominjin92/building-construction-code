import streamlit as st
import datetime

# session_state 초기화
def init_session():
    if 'lecture_files' not in st.session_state:
        st.session_state['lecture_files'] = {week: [] for week in range(1, 16)}

# 파일 업로드 핸들링 함수
def handle_upload(week, uploaded_files):
    for uploaded_file in uploaded_files:
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        st.session_state['lecture_files'][week].append({
            'filename': uploaded_file.name,
            'timestamp': timestamp
        })

# 파일 삭제 핸들링 함수
def handle_delete(week, index):
    if 0 <= index < len(st.session_state['lecture_files'][week]):
        del st.session_state['lecture_files'][week][index]

# 메인 프로그램
init_session()

# 왼쪽 사이드바 (분류)
with st.sidebar:
    st.title('분류')
    st.markdown('''
    - 강의자료 관리
    - 문제 관리
    - 학습성과 분석
    ''')

# 오른쪽 메인 화면
st.title('주차별 강의자료 관리')

for week in range(1, 16):
    with st.expander(f"{week}주차 강의자료"):
        uploaded_files = st.file_uploader(
            f"{week}주차 자료 추가",
            accept_multiple_files=True,
            key=f"uploader_{week}"
        )
        if uploaded_files:
            handle_upload(week, uploaded_files)

        # 업로드된 파일 목록 보여주기
        if st.session_state['lecture_files'][week]:
            for idx, file_info in enumerate(st.session_state['lecture_files'][week]):
                col1, col2, col3 = st.columns([6, 3, 1])
                with col1:
                    st.write(f"{file_info['filename']}")
                with col2:
                    st.write(f"업로드: {file_info['timestamp']}")
                with col3:
                    if st.button("삭제", key=f"delete_{week}_{idx}"):
                        handle_delete(week, idx)
                        st.experimental_rerun()
        else:
            st.write("등록된 자료가 없습니다.")