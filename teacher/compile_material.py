import streamlit as st

from utils.llm_handlers import generate_reading_material_Gemini

from io import BytesIO
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import base64
from PyPDF2 import PdfWriter, PdfReader
import time



@st.fragment
def handle_uploaded_pdf_to_BytesIO(uploaded_file):
    """Convert an uploaded PDF file to BytesIO for processing"""
    if uploaded_file is not None:
        # Read bytes from the uploaded file
        pdf_bytes = uploaded_file.read()
        
        # Create a BytesIO object
        pdf_bytesio = BytesIO(pdf_bytes)
        
        # Reset the uploaded file's position for potential future reads
        uploaded_file.seek(0)
        
        return pdf_bytesio
    return None


@st.fragment
def markdown_to_pdf(markdown_text: str) -> bytes:
    """
    Convert Markdown content to PDF using a headless browser.

    This function converts the provided Markdown text into HTML, wraps it
    with basic styling, writes it to a temporary HTML file, and then loads
    that file in headless Chrome via Selenium to generate a PDF.

    Args:
        markdown_text (str): The markdown content to be converted.

    Returns:
        bytes: The generated PDF as bytes.
    """

    import os
    import markdown
    from tempfile import NamedTemporaryFile
    
    # Convert markdown to HTML body
    html_body = markdown.markdown(markdown_text)
    
    # Wrap HTML with a full document and basic CSS styling
    full_html = f"""
    <html>
      <head>
        <meta charset="utf-8">
        <title>Markdown to PDF</title>
        <style>
          body {{
            font-family: Arial, sans-serif;
            margin: 2em;
            line-height: 1.6;
          }}
          h1, h2, h3, h4, h5, h6 {{
            color: #333;
          }}
          pre {{
            background: #f4f4f4;
            padding: 1em;
            border-radius: 5px;
            overflow-x: auto;
          }}
          code {{
            background: #f4f4f4;
            padding: 0.2em 0.4em;
            border-radius: 3px;
          }}
        </style>
      </head>
      <body>
        {html_body}
      </body>
    </html>
    """
    
    # Write the HTML content to a temporary file
    with NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as tmp_file:
        tmp_file.write(full_html)
        tmp_file_path = tmp_file.name
        
    # Convert Windows path to a file URL
    file_url = "file:///" + tmp_file_path.replace("\\", "/")
    
    # Generate PDF bytes using the existing Selenium-based function
    pdf_bytes = process_url_to_pdf(file_url)
    pdf_buffer = BytesIO(pdf_bytes)
    # Clean up the temporary file
    os.remove(tmp_file_path)
    
    return pdf_buffer

@st.fragment
def process_url_to_pdf(url: str) -> bytes:
    """Convert webpage to PDF using Selenium and Chrome's PDF capabilities"""
    try:
        #st.write(f"Processing URL: {url}")
        
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")  # Important for Ploomber
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1200,1600")  # Portrait A4-like ratio
        
        # Create the driver
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            if not "file:" in url:
                st.write(f"Navigating to URL: {url}")
            driver.get(url)
            
            # Wait for the page to load completely, including math formulas
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Extra wait time for MathJax/LaTeX rendering
            st.write("Making sure to capture everything for you...")
            time.sleep(5)
            
            # Configure PDF options
            pdf_options = {
                "printBackground": True,
                "paperWidth": 8.27,  # A4 width in inches
                "paperHeight": 11.69,  # A4 height in inches
                "marginTop": 0.4,
                "marginBottom": 0.4,
                "marginLeft": 0.4,
                "marginRight": 0.4,
                "scale": 0.9
            }
            
            # Get PDF as base64
            st.write("Converting page to PDF...")
            result = driver.execute_cdp_cmd("Page.printToPDF", pdf_options)
            pdf_data = base64.b64decode(result['data'])
            
            st.write(f"PDF generated successfully ({len(pdf_data) / (1024 * 1024):.2f} MB)")
            return pdf_data
            
        finally:
            driver.quit()
            
    except Exception as e:
        st.error(f"Error converting webpage to PDF: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return bytes()

@st.fragment
def display_pdf_pages_advanced(pdf_bytes, width=100, height=500, zoom=1.0):
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


# @st.fragment
# def compile_source_material():   #download_and_summarize_urls():
#     """Streamlit function to download and process URLs or text"""
#     st.subheader(" :globe_with_meridians: Compile from web pages/text")
    
#     urls_col, grade_col, subject_col = st.columns([3,1,1]) 
#     option_map = {
#         0: ":material/http:",
#         1: ":material/picture_as_pdf:",
#     }
#     selection = urls_col.segmented_control(
#         "Source",
#         options=option_map.keys(),
#         format_func=lambda option: option_map[option],
#         selection_mode="single", 
#         default=0,
#     )
    
#     # Initialize variables for both input types
#     urls_input = ""
#     text_input = ""
#     pdf_bytesio=BytesIO()
#     # st.session_state.setdefault("pdf_bytesio", None)
#     if selection == 0:
#         urls_input = urls_col.text_area("Enter URLs (one per line)", key="url_txt")
#     elif selection == 1:
#         uploaded_pdf = urls_col.file_uploader("Upload a PDF file", type=["pdf"])
#         if uploaded_pdf:
#             pdf_bytesio = handle_uploaded_pdf_to_BytesIO(uploaded_pdf)
        
#     grade_level = grade_col.selectbox("Select grade level:", ("9th", "10th", "11th", "12th"))
#     subject = subject_col.selectbox("Select subject:", ("Biology", "Chemistry", "Physics", "PLTW Medical Interventions"))
#     final_no_pages=grade_col.number_input("Number of pages", min_value=1, max_value=5, value=1)
#     diff_level=subject_col.selectbox("Select difficulty level:", ("Easy", "Medium", "Advanced"), index=0)

#     use_as_question_source = st.toggle("Use content for question generation")

#     rdbtnL, rdbtnC, rdbtnR = st.columns([1,2,1]) 



#     if rdbtnC.button(":book: Generate Reading Material", type="primary"):
#         # Validate input based on selection
#         if (selection == 0 and not urls_input) or (selection == 1 and not pdf_bytesio) or not grade_level or not subject:
#             st.error("Please provide all required inputs (URLs/pdf, grade level, and subject).")
#             return
            
#         with st.status("Processing content and preparing reading material...", expanded=True) as compile_material:
#             try:
#                 combined_pdf = BytesIO()
                
#                 # Handle URL input
#                 if selection == 0:
#                     urls = [url.strip() for url in urls_input.splitlines() if url.strip()]
#                     url_pdfs = []
                    
#                     for urlX in urls:
#                         st.write(f"Processing URL: {urlX}")
#                         pdf_data = process_url_to_pdf(url=urlX)
#                         # Verify PDF has content
#                         if pdf_data and len(pdf_data) > 100:
#                             url_pdfs.append(pdf_data)
#                         else:
#                             st.warning(f"Failed to generate valid PDF for {urlX}")                   


#                     # Combine PDFs into a single file
#                     pdf_writer = PdfWriter()

#                     if not url_pdfs:
#                         st.error("No valid PDFs were generated from the provided URLs.")
#                         return

#                     st.write("Combining PDFs...")
#                     # Add pages from each PDF to the combined PDF
#                     for pdf_bytes in url_pdfs:
#                         # Convert bytes to BytesIO then to PdfReader
#                         pdf_reader = PdfReader(BytesIO(pdf_bytes))
#                         # Check if PDF has pages
#                         if len(pdf_reader.pages) > 0:
#                             # Add all pages from current PDF
#                             for page in pdf_reader.pages:
#                                 pdf_writer.add_page(page)
#                         else:
#                             st.warning("Skipping PDF with no pages")
                    
#                     # Check if the combined PDF has pages
#                     if len(pdf_writer.pages) == 0:
#                         st.error("No pages were added to the combined PDF. Check the source URLs.")
#                         return

#                     # Write combined PDF to BytesIO buffer
#                     pdf_writer.write(combined_pdf)
#                     combined_pdf.seek(0)
                
#                 # Handle text input
#                 elif selection == 1:
#                     st.write("Converting text to PDF...")
#                     combined_pdf = pdf_bytesio  
#                     #if st.session_state.pdf_bytesio is not None:
#             except Exception as e:
#                 st.error(f"Error processing content: {str(e)}")
#                 import traceback
#                 st.error(traceback.format_exc())
                
#         # Display the PDF and generate reading material
#         col_pdf, col_rd = st.columns(2)
#         with col_pdf:
#             st.write("### Combined PDF")
#             display_pdf_pages_advanced(combined_pdf, 95, 500, 1.0)
            
#         with col_rd:
#             st.write("Crafting reading material...")
#             reading_material = generate_reading_material_Gemini(combined_pdf, grade_level, subject, final_no_pages, diff_level)
#             # st.write("### Reading Material")
#             # st.markdown(
#             #     f"""
#             #     <div style='height: 500px; overflow-y: scroll; border: 1px solid #ccc; padding: 1rem; border-radius: 5px;'>
#             #         {reading_material}
                
#             #     """,
#             #     unsafe_allow_html=True
#             # )
            
#             if use_as_question_source:
#                 st.session_state['extracted_pdf'] = markdown_to_pdf(reading_material)
#                 st.success("Reading material converted to the PDF format and ready for question generation.")
                
#                 # Add download button for PDF
#                 download_col1, download_col2, download_col3 = st.columns([1,2,1])
#                 with download_col2:
#                     pdf_bytes = st.session_state['extracted_pdf'].getvalue()
#                     st.download_button(
#                         label="⬇️ Download Reading Material as PDF",
#                         data=pdf_bytes,
#                         file_name="reading_material.pdf",
#                         mime="application/pdf",
#                         use_container_width=True
#                     )
#             if "Error" in reading_material:
#                 st.error(reading_material)
#                 return

@st.fragment
def compile_source_material_v2():
    """Streamlit function with improved UI for compiling source material."""
    st.subheader(":material/note_stack_add: Compile Source Material", divider=True)
    st.write("Choose a source (Web URLs or PDF) and set parameters to generate reading material.")

    # st.divider() # Visually separates sections

    source_selection_col, generation_params_col= st.columns([1, 1],
                                                            vertical_alignment="bottom",
                                                            border=True) # Adjust column widths as needed
    
    with source_selection_col:
        # --- Section 1: Source Selection and Input ---
        st.subheader("1. Select and Provide Source", divider=True)
        cols_source_type = st.columns([2, 3]) # Give more space to the control

        option_map = {
            "Web URLs": ":material/http:",
            "PDF File": ":material/picture_as_pdf:",
        }
        # Use radio for clearer selection, place label above
        source_type = cols_source_type[0].radio(
            "Select Source Type:",
            options=option_map.keys(),
            # format_func=lambda option: option_map[option], # Keep icons if desired
            horizontal=True, # Makes radio buttons horizontal
            label_visibility="collapsed" # Hide redundant label if needed, title is above
        )

        # Initialize variables
        urls_input = ""
        uploaded_pdf_file = None
        source_data_valid = False

        # Conditional Input Area
        if source_type == "Web URLs":
            urls_input = st.text_area(
                "Enter URLs (one per line):",
                key="url_txt_v2",
                placeholder="https://example.com/page1\nhttps://anothersite.org/article",
                height=150,
                label_visibility="collapsed", # Hide label if using title above
            )
            if urls_input.strip():
                source_data_valid = True
        elif source_type == "PDF File":
            uploaded_pdf_file = st.file_uploader(
                "Upload a PDF file:",
                type=["pdf"],
                key="pdf_upload_v2",
                accept_multiple_files=False # Ensure only one file
            )
            if uploaded_pdf_file:
                source_data_valid = True


    with generation_params_col:
    
        #st.divider()

        # --- Section 2: Parameters ---
        st.subheader("2. Set Generation Parameters", divider=True)
        st.write(" ")
        use_as_question_source = st.toggle(
        ":material/quiz: Use generated content for question generation later?",
        value=False, # Default to off
        key="use_for_q_v2",
        help="If enabled, the generated reading material will be saved in PDF format for use in the question generation steps."
    )
        param_col1, param_col2 = st.columns(2)

        with param_col1:
            grade_level = st.selectbox(
                ":material/school: Grade Level:",
                ("9th", "10th", "11th", "12th"),
                key="grade_v2"
            )
            final_no_pages = st.number_input(
                ":material/description: Target Pages:",
                min_value=1, max_value=10, value=1, step=1, # Increased max slightly
                key="pages_v2",
                help="Approximate number of pages for the generated reading material."
            )

        with param_col2:
            subject = st.selectbox(
                ":material/science: Subject:",
                ("Biology", "Chemistry", "Physics", "PLTW Medical Interventions", "Other"), # Added 'Other'
                key="subject_v2"
            )
            diff_level = st.selectbox(
                ":material/signal_cellular_alt: Difficulty Level:",
                ("Easy", "Medium", "Advanced"),
                index=0, # Default to Easy
                key="difficulty_v2"
            )

    st.divider()

    # # --- Section 3: Options and Generation ---
    # st.markdown("##### 3. Configure Output and Generate")
    # use_as_question_source = st.toggle(
    #     ":material/quiz: Use generated content for question generation later?",
    #     value=False, # Default to off
    #     key="use_for_q_v2",
    #     help="If enabled, the generated reading material will be saved in PDF format for use in the question generation steps."
    # )

    # st.write("") # Add a little space before the button

    # Centered Button
    button_cols = st.columns([1, 2, 1]) # Adjust ratio as needed for centering
    generate_button_pressed = button_cols[1].button(
        ":book: Generate Reading Material",
        type="primary",
        use_container_width=True,
        key="generate_btn_v2"
    )

    # --- Processing Logic (Keep your original logic here) ---
    if generate_button_pressed:
        # 1. Validate Inputs
        if not source_data_valid:
            st.error("Please provide source content (URLs or a PDF file).")
            return
        if not grade_level or not subject:
            st.error("Please select a grade level and subject.")
            return

        # 2. Process Source (URL or PDF) -> combined_pdf (BytesIO)
        with st.status("Processing source content...", expanded=True) as status:
            combined_pdf = BytesIO()
            try:
                if source_type == "Web URLs":
                    urls = [url.strip() for url in urls_input.splitlines() if url.strip()]
                    if not urls:
                         st.error("No valid URLs entered.")
                         return # Exit early

                    status.update(label=f"Processing {len(urls)} URL(s)...")
                    url_pdfs = []
                    pdf_writer = PdfWriter()
                    for i, urlX in enumerate(urls):
                        st.write(f"Fetching and converting URL {i+1}/{len(urls)}: {urlX}")
                        pdf_data = process_url_to_pdf(url=urlX) # Your actual function
                        if pdf_data and len(pdf_data) > 100: # Basic check
                            try:
                                pdf_reader = PdfReader(BytesIO(pdf_data))
                                if len(pdf_reader.pages) > 0:
                                     url_pdfs.append(pdf_data)
                                     for page in pdf_reader.pages:
                                         pdf_writer.add_page(page)
                                else:
                                    st.warning(f"Skipping URL {urlX} - generated PDF has no pages.")
                            except Exception as read_err:
                                st.warning(f"Skipping URL {urlX} - error reading generated PDF: {read_err}")
                        else:
                            st.warning(f"Failed to generate a valid PDF for URL: {urlX}")

                    if not url_pdfs or len(pdf_writer.pages) == 0:
                        st.error("Could not generate valid content from the provided URLs.")
                        status.update(label="URL processing failed.", state="error")
                        return

                    status.update(label="Combining generated PDFs...")
                    pdf_writer.write(combined_pdf)
                    combined_pdf.seek(0)
                    st.write("PDFs combined successfully.")


                elif source_type == "PDF File":
                    status.update(label="Processing uploaded PDF...")
                    if uploaded_pdf_file:
                        # Ensure the file pointer is at the beginning for processing
                        uploaded_pdf_file.seek(0)
                        # Directly use the uploaded file's bytes
                        combined_pdf = BytesIO(uploaded_pdf_file.read())
                        combined_pdf.seek(0) # Reset pointer after reading
                        st.write("Uploaded PDF processed.")
                    else:
                        # This case should be caught by source_data_valid, but double-check
                        st.error("No PDF file was uploaded.")
                        status.update(label="PDF processing failed.", state="error")
                        return

            except Exception as e:
                st.error(f"Error during source processing: {str(e)}")
                import traceback
                st.error(traceback.format_exc())
                status.update(label="Processing error.", state="error")
                return

            status.update(label="Source processing complete.", state="complete", expanded=False)


        # 3. Generate Reading Material
        if combined_pdf.getbuffer().nbytes > 0: # Check if we have content
             st.markdown("---") # Separator before results
             results_col1, results_col2 = st.columns(2, border=True) # Adjust column widths as needed

             with results_col1:
                 st.subheader("Source Preview",divider=True)
                 st.write("Combined content from source(s):")
                 # Ensure the buffer is passed correctly
                 display_pdf_pages_advanced(combined_pdf, width=100, height=500, zoom=0.9) # Display in the column

             with results_col2:
                st.subheader("Generated Material",divider=True)
                with st.spinner("Generating reading material based on source..."):
                    try:
                        reading_material_container=st.empty() # Placeholder for generated content
                         # Pass the BytesIO object directly
                        combined_pdf.seek(0) # Ensure it's at the start before passing
                        reading_material = generate_reading_material_Gemini(
                            combined_pdf, grade_level, subject, final_no_pages, diff_level,
                            reading_material_container=reading_material_container # Pass the container for updates
                        ) # Your actual function

                        if "Error" in reading_material: # Check for explicit errors from the LLM call
                            reading_material_container.error(f"Failed to generate reading material: {reading_material}")
                        else:
                            reading_material_container.empty() # Clear the placeholder
                            reading_material_container.success("Reading material generated!")
                            # Display the generated markdown in a scrollable box
                            reading_material_container.markdown(
                                f"""
                                <div style='height: 450px; overflow-y: scroll; border: 1px solid #ccc; padding: 10px; border-radius: 5px; margin-top: 10px;'>
                                    {reading_material}
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                            # 4. Handle Post-Generation Options (PDF conversion/download)
                            if use_as_question_source:
                                with st.spinner("Converting reading material to PDF for question generation..."):
                                    try:
                                        reading_material_pdf_buffer = markdown_to_pdf(reading_material) # Your function
                                        reading_material_pdf_buffer.seek(0) # Reset buffer pointer
                                        # st.session_state['extracted_pdf_v2'] = reading_material_pdf_buffer # Use a distinct key
                                        st.session_state['extracted_pdf'] = reading_material_pdf_buffer #markdown_to_pdf(reading_material)
                                        
                                        # Offer download immediately
                                        st.download_button(
                                            label="⬇️ Download Reading Material (PDF)",
                                            data=st.session_state['extracted_pdf'], # Use the buffer directly
                                            file_name=f"{subject.lower().replace(' ', '_')}_reading_material.pdf",
                                            mime="application/pdf",
                                            key="download_reading_pdf_v2",
                                            use_container_width=True,
                                            help="Download the generated reading material in PDF format."
                                        )
                                        st.info("Reading material saved for question generation.")

                                    except Exception as pdf_conv_err:
                                         st.error(f"Could not convert reading material to PDF: {pdf_conv_err}")


                    except Exception as gen_err:
                        st.error(f"An error occurred during reading material generation: {gen_err}")
                        import traceback
                        st.error(traceback.format_exc())
        else:
            st.warning("No content was processed from the source. Cannot generate reading material.")



compile_source_material_v2()