import base64
from io import BytesIO
# Third-party imports
import streamlit as st
from PyPDF2 import PdfReader, PdfWriter


def parse_page_numbers(page_numbers_str, num_pages):
    """Parse page numbers from string input"""
    pages = []
    tokens = page_numbers_str.split(',')
    for token in tokens:
        token = token.strip()
        if '-' in token:
            start, end = token.split('-')
            start = int(start) - 1
            end = int(end)
            pages.extend(range(start, end))
        else:
            page = int(token) - 1
            pages.append(page)
    return sorted(set([p for p in pages if 0 <= p < num_pages]))

def extract_pages(pdf_file, selected_pages):
    """Extract selected pages from PDF file"""
    pdf_reader = PdfReader(pdf_file)
    pdf_writer = PdfWriter()
    
    selected_indices = [i-1 for i in selected_pages]
    
    for page_num in selected_indices:
        page = pdf_reader.pages[page_num]
        pdf_writer.add_page(page)
    
    output = BytesIO()
    pdf_writer.write(output)
    output.seek(0)
    
    return output


def display_pdf_pages_advanced(pdf_bytes, width=95, height=500, zoom=1.0):
    """Display extracted PDF pages in Streamlit"""
    if not (pdf_bytes is None):
        base64_pdf = base64.b64encode(pdf_bytes.read()).decode('utf-8')
        pdf_display = f"""
        <div style="transform: scale({zoom}); 
                    transform-origin: top left; 
                    width: {width}%; 
                    height: {height}px;">
            <iframe
                src="data:application/pdf;base64,{base64_pdf}"
                width="100%"
                height="100%"
                type="application/pdf">
            </iframe>
        </div>
    """
        st.markdown(pdf_display, unsafe_allow_html=True)

st.subheader(":material/upload: Upload Source Material", divider=True)
col1, col2 = st.columns([2, 3], border=True)
if 'extracted_pdf' not in st.session_state or st.session_state.get('extracted_pdf') is None:
    st.session_state.setdefault("extracted_pdf",None)
# else:
#     st.write("extracted_pdf found")
with col1:
    
    # Extraction options
    pages_col1, pages_col2=st.columns([1,1])
    with pages_col1:
        option = st.selectbox(
            "Select pages:",
            ["All pages", "Custom selection"],
            help="Choose how to extract pages from your PDF"
        )
    with pages_col2:
        if option == "Custom selection":
            selected_pages_input = st.text_input(
                "Enter pages (e.g., 1,3,5-7):",
                help="Enter individual pages and/or ranges separated by commas"
            )
        else:
            selected_pages_input = None

    # File upload
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        help="Maximum file size: 200MB"
    )

    if uploaded_file is not None:
        pdf_reader = PdfReader(uploaded_file)
        num_pages = len(pdf_reader.pages)
        st.info(f"📄 PDF contains {num_pages} pages")

        # Page extraction
        if option == "All pages":
            selected_pages = list(range(1, num_pages + 1))
        elif selected_pages_input:
            selected_pages = parse_page_numbers(selected_pages_input, num_pages)
        else:
            selected_pages = []

        if selected_pages:
            extracted_pdf = extract_pages(uploaded_file, selected_pages)
            st.session_state['extracted_pdf'] = extracted_pdf
            st.session_state['num_pages'] = num_pages
           

with col2:
    # if st.button("List all keys in session state"):
    #     st.write(list(st.session_state.keys()))
    if st.session_state.get('extracted_pdf'):
        st.session_state['extracted_pdf'].seek(0)
        # with st.expander("st.session content"):
        #     st.write(st.session_state['extracted_pdf'])
        
        st.session_state['extracted_pdf'].seek(0)
        display_pdf_pages_advanced(st.session_state['extracted_pdf'], width=100, height=600, zoom=1.0)
    # else:
    #     st.write("st.session_state['extracted_pdf'] not found")

