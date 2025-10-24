import streamlit as st
from utils.myutils import align_top_css
from utils.llm_handlers import get_config_value

st.set_page_config(page_title="Teacheraide", page_icon=None, layout="wide")

align_top_css()

def display_blank():
    logout_all()
    # st.error("Sizin güvənli oturum müddətiniz bitmişdir. Xahiş edirik əsas səhifədən yenidən daxil olun: https://medaid.az")

def logout_all():
    if "authenticated" in st.session_state:
        st.session_state["authenticated"] = False
        st.session_state["user"] = None
        st.session_state.clear()


def start_app_for_teacher():
    openai_api_key = get_config_value("OPENAI_API_KEY")
    st.session_state.setdefault("user_openAIapi_key", openai_api_key)
    st.session_state.setdefault("model_choice", "GPT-4o (OpenAI)")
    logout_page_teacher = st.Page(logout_all, title="Log out", icon=":material/logout:")
    compile_material_page=st.Page("teacher/compile_material.py", title="Compile source material", icon=":material/note_stack_add:", default=True)
    upload_material_page = st.Page("teacher/upload_material.py", title="Upload source material", icon=":material/upload:")
    text_questions_page = st.Page("teacher/text_questions.py", title="Text-only questions", icon=":material/article:")
    image_questions_page = st.Page("teacher/image_questions.py", title="Image based questions", icon=":material/format_image_right:")
    review_download_page = st.Page("teacher/review_download.py", title="Review and download assessment", icon=":material/download:")
    lesson_prep_page=st.Page("teacher/lesson_prep.py", title="Generate lesson prep", icon=":material/fact_check:")
    # msg_outbox = st.Page("user/outbox.py", title="Gedən mesajlar", icon=":material/outbox:")
    # passwd_page= st.Page("user/mexfi.py", title="Şifrənizi dəyişdirin", icon=":material/password:")
    
    # f'<a href="agreement.html">İstifadəçi Razılaşması və Məsuliyyətin İstisnası</a>'
    # agreement=f"medaid.az xidmlərindən istifadə edərək {agreement_link}nı qəbul etmiş olursunuz."

    # if st.session_state.authenticated:
    menu_divider = "_______________________"
    pg = st.navigation(
        {   f"       Welcome": [],
            "Follow the order":[compile_material_page, upload_material_page, text_questions_page, 
                    image_questions_page,review_download_page, lesson_prep_page, ],
            "": [],
            "": [],
            "": [],
            f"{menu_divider}":[logout_page_teacher],
            
             
        }
    )
    # else:
    #     pg = st.navigation([display_blank])
    pg.run()

def start_app_for_doctor():
    
    logout_page_doc = st.Page(logout_all, title="Log out", icon=":material/logout:")

    public_doc_profile = st.Page("doctor/public_profile.py", title="Həkim Profili", icon=":material/badge:")
    edit_doc_profile = st.Page("doctor/save_profile.py", title="Həkim Profili Redaktə", icon=":material/badge:")
    ai_assist_page=st.Page("doctor/ai_assistant.py", title="Asistentiniz", icon=":material/badge:")
    patient_questions_page=st.Page("doctor/patient_quest.py", title="Suallar", icon=":material/badge:")
    logout_page_doc=st.Page("doctor/patient_quest.py", title="Çıxış", icon=":material/badge:")
    if st.session_state.authenticated:        
        pg = st.navigation(
            {
                f"Xoş gəldiniz {st.session_state['user']['name']}": [],
                "Profil əməliyyatları": [public_doc_profile, edit_doc_profile],
                "Ofis": [ai_assist_page, patient_questions_page],
                "Çıxış": [logout_page_doc],
                "medaid.az xidmlərindən istifadə edərək 'İstifadə qayda və şərtləri'ni qəbul etmiş olursunuz." :[],
                })
    else:
        pg = st.navigation([display_blank])

    pg.run()

def main():
    start_app_for_teacher()
    # from app_utils.fcrypto import user_exists 
    # from app_utils.token_validator import JWTValidator
    # # Initialize session state
    # if "authenticated" not in st.session_state:
    #     st.session_state.authenticated = False
    # if "user_type" not in st.session_state:
    #     st.session_state.user_type = None

    # validator = JWTValidator()

    # if not st.session_state["authenticated"]:
    #     user_info = validator.check_token_in_params()

    #     if not user_info:
    #         display_blank()
    #         st.stop()
        
    #     # Check if user exists with get() method (safer as it can provide a default value None if the key doesn't exist):
    #     user_status = user_exists(user_info.get('email'), "check")
        
    #     if user_status['exists'] == False:
    #         # New user - show agreement
    #         # if check_and_handle_agreement(is_new_user=True):
    #         st.session_state.authenticated = True
    #         st.session_state.user_type = 'patient'
    #         start_app_for_patient()
    #         # else:
    #             # st.stop()
    #     else:
    #         # Existing user - route based on type
    #         st.session_state.authenticated = True
    #         st.session_state.user_type = user_status['type']        
    #         # # Check if they need to accept updated agreement
    #         # if not check_and_handle_agreement(is_new_user=False):
    #         #     st.stop()  # Wait for agreement acceptance
    #         if user_status['type'] == 'patient':
    #             start_app_for_patient()
    #         elif user_status['type'] == 'physician':
    #             start_app_for_doctor()
    #         else:
    #             st.error("Invalid user type")
    #             #st.stop()
    # else:
    #     # Already authenticated in this session - still check for agreement updates
    #     # if not check_and_handle_agreement(is_new_user=False):
    #     #     st.stop()  # Wait for agreement acceptance
    #     # Proceed with appropriate app    
    #     if st.session_state.user_type == 'patient':
    #         start_app_for_patient()
    #     elif st.session_state.user_type == 'physician':
    #         start_app_for_doctor()

if __name__ == "__main__":
    main()