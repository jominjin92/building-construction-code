import streamlit as st
from db.lecture_material_db import init_lecture_materials_db, add_lecture_material, get_lecture_materials_by_week, delete_lecture_material

# DB 초기화
init_lecture_materials_db()

def render_lecture_material_tab():
    st.title('주차별 강의자료 관리')

    for week in range(1, 16):
        with st.expander(f"{week}주차 강의자료"):
            uploaded_files = st.file_uploader(
                f"{week}주차 자료 추가",
                accept_multiple_files=True,
                key=f"uploader_{week}"
            )

            if uploaded_files:
                for uploaded_file in uploaded_files:
                    add_lecture_material(week, uploaded_file.name)
                    st.success(f"'{uploaded_file.name}' 업로드 완료!")
                st.experimental_rerun()

            materials = get_lecture_materials_by_week(week)

            if materials:
                for material in materials:
                    material_id, filename, upload_time = material
                    col1, col2, col3 = st.columns([6, 3, 1])
                    with col1:
                        st.write(filename)
                    with col2:
                        st.write(f"업로드: {upload_time}")
                    with col3:
                        if st.button("삭제", key=f"delete_{week}_{material_id}"):
                            delete_lecture_material(material_id)
                            st.success(f"'{filename}' 삭제 완료!")
                            st.experimental_rerun()
            else:
                st.write("등록된 자료가 없습니다.")