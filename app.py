import streamlit as st
import core
import os

# Initialize session state for current student ID
if 'current_student_id' not in st.session_state:
    st.session_state.current_student_id = None

def main():
    st.title("UFT-BILSEM Öğrenci Yönetim Sistemi")
    
    # Sidebar for navigation
    st.sidebar.title("Menü")
    page = st.sidebar.selectbox("Sayfa Seçin", ["Öğrenci Listele", "Yeni Öğrenci Ekle", "Öğrenci Ara"])
    
    if page == "Öğrenci Listele":
        list_students()
    elif page == "Yeni Öğrenci Ekle":
        add_student()
    elif page == "Öğrenci Ara":
        search_student()

def list_students():
    st.header("Öğrenci Listesi")
    students = core.load_all()
    
    if not students:
        st.info("Henüz öğrenci kaydı bulunmuyor.")
        return
    
    for student in students:
        with st.expander(f"{student.get('name', 'İsimsiz')} - {student.get('class_name', '')}"):
            st.write(f"**ID:** {student.get('id', '')}")
            st.write(f"**Sınıf:** {student.get('class_name', '')}")
            st.write(f"**Kayıt Tarihi:** {student.get('last_updated', '')}")
            
            # Show grades
            grades = student.get('grades', [])
            if grades:
                st.subheader("Notlar")
                for grade in grades:
                    st.write(f"- {grade.get('subject', '')}: {grade.get('score', '')}")
            else:
                st.write("Not kaydı yok")
            
            # Show homeworks
            homeworks = student.get('homeworks', [])
            if homeworks:
                st.subheader("Ödevler")
                for hw in homeworks:
                    st.write(f"- {hw.get('title', '')} ({hw.get('subject', '')}) - Durum: {hw.get('status', '')}")
            else:
                st.write("Ödev kaydı yok")
            
            # Action buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"Bu Öğrenciyi Seç", key=f"select_{student['id']}"):
                    st.session_state.current_student_id = student['id']
                    st.rerun()
            with col2:
                if st.button(f"Sil", key=f"delete_{student['id']}"):
                    if core.delete_student(student['id']):
                        st.success("Öğrenci silindi!")
                        st.rerun()
                    else:
                        st.error("Silme işlemi başarısız!")

def add_student():
    st.header("Yeni Öğrenci Ekle")
    
    with st.form("new_student_form"):
        name = st.text_input("Öğrenci Adı")
        class_name = st.text_input("Sınıf")
        
        submitted = st.form_submit_button("Öğrenci Ekle")
        if submitted:
            if not name:
                st.error("Öğrenci adı zorunludur!")
                return
            
            # Create new student
            student = core.new_student()
            student['name'] = name
            student['class_name'] = class_name
            
            # Save student
            if core.save(student):
                st.success(f"Öğrenci başarıyla eklendi! ID: {student['id']}")
                # Clear form
                st.rerun()
            else:
                st.error("Öğrenci eklenirken bir hata oluştu!")

def search_student():
    st.header("Öğrenci Ara")
    search_term = st.text_input("Öğrenci adı veya sınıf için ara")
    
    if search_term:
        students = core.load_all()
        filtered = [
            s for s in students 
            if search_term.lower() in s.get('name', '').lower() 
            or search_term.lower() in s.get('class_name', '').lower()
        ]
        
        if not filtered:
            st.info("Arama kriterinize uygun öğrenci bulunamadı.")
            return
        
        st.write(f"{len(filtered)} öğrenci bulundu:")
        for student in filtered:
            with st.expander(f"{student.get('name', 'İsimsiz')} - {student.get('class_name', '')}"):
                st.write(f"**ID:** {student.get('id', '')}")
                st.write(f"**Sınıf:** {student.get('class_name', '')}")
                st.write(f"**Kayıt Tarihi:** {student.get('last_updated', '')}")
                
                if st.button(f"Bu Öğrenciyi Seç", key=f"select_search_{student['id']}"):
                    st.session_state.current_student_id = student['id']
                    st.rerun()

if __name__ == "__main__":
    main()