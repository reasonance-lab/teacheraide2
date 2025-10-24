#myutils.py
import streamlit as st


def align_top_css():
    css = '''
        .stMainBlockContainer {
            margin-top:-80px;}
            
        [data-testid="stHeader"] {
            visibility:hidden;
            margin-top:-20px; }

        [data-testid="stToolbar"] {
            visibility:hidden; }

        [data-testid="stAppViewBlockContainer"] {
            margin-top:-80px; }
    '''
    st.markdown(f'<style>{css}</style>',unsafe_allow_html=True)