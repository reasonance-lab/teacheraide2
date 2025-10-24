import asyncio
import streamlit as st

from io import BytesIO
from prompts.qti_prompts import create_complete_prompt #create_llm_prompt
from utils.llm_handlers import (
    generate_openai_response,
    generate_anthropic_response,
)

@st.fragment
def process_pdf_for_Claude(pdf_output: BytesIO) -> str:
    """Process PDF for Claude API, with size checks and compression if needed"""
    import base64
    try:
        # Reset buffer position
        pdf_output.seek(0)
        # Get the PDF content
        pdf_content = pdf_output.getvalue()
        # Check original size
        original_size_mb = len(pdf_content) / (1024 * 1024)
        if original_size_mb > 10:  # If larger than 10MB
            # st.warning(f"PDF size ({original_size_mb:.2f}MB) is large, compressing...")
            try:
                import fitz  # PyMuPDF
                # Create PDF document from bytes
                doc = fitz.open(stream=pdf_content, filetype="pdf")
                # Create new PDF with compression
                output = BytesIO()
                doc.save(output, 
                        garbage=4,     # Max garbage collection
                        deflate=True,  # Use deflate compression
                        ascii=False,   # Allow binary content
                        linear=False)  # Non-linear PDF to save space
                
                # Get compressed content
                pdf_content = output.getvalue()
                compressed_size_mb = len(pdf_content) / (1024 * 1024)
                # st.write(f"Compressed PDF size: {compressed_size_mb:.2f}MB")
                doc.close()             
            except Exception as e:
                st.warning(f"Compression failed: {str(e)}. Using original PDF.")
        
        # Convert to base64
        base_64_encoded_data = base64.b64encode(pdf_content)
        pdf_data = base_64_encoded_data.decode('utf-8')
        final_size_mb = len(pdf_data.encode('utf-8')) / (1024 * 1024)
        # st.write(f"Final PDF data size: {final_size_mb:.2f}MB")
        return pdf_data
        
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        return ""

@st.fragment
def generate_text_only_questions():
    """Render the Question Generation tab"""
    
    import xml.etree.ElementTree as ET
    from datetime import datetime
    from utils.yaml_converter import YAMLtoQTIConverter
    from utils.combined_questions import store_questions, create_package
    
    if 'extracted_pdf' not in st.session_state or st.session_state.get('extracted_pdf') is None:
        st.warning("⚠️ Please upload and process a PDF first")
        return

    st.subheader(":material/article: Generate Text-only Questions", divider=True)
    upload_content = [
        (0, "reading material and I want to generate questions based on the whole content", "rm_q"),
        (1, "collection of questions and I want to generate similar questions, by paraphrasing the questions", "siml_q"),
        (2, """collection of questions and I want to generate questions with completely different content, 
            but with the same topics, concepts, learning objectives and difficulty""", "diffr_q"),
        (3, "images and I want to generate specified type of question per image", "img_q"),
    ]
    content_type_col, assessment_type_col = st.columns([2, 1])
    content_type=content_type_col.selectbox("I uploaded...",
                            upload_content,
                            format_func=lambda x: x[1],help="Choose how to generate questions")
    
    assessment_type=assessment_type_col.selectbox("Assessment Type",["Practice/Diagnostic","Formative","Summative"])


    st.session_state.content_type=content_type[2]
    st.session_state.assessment_type=assessment_type
    gen_similar_questions=False
    if not (st.session_state.content_type=="rm_q"):
        gen_similar_questions=st.toggle("Generate same types and count of questions")
    
    
    with st.form("generate_questions"):
        instr_exp=st.expander("Provide instructions, question types and counts", expanded=False)
        if not gen_similar_questions:   
            with instr_exp: 
                special_instructions=st.text_area("Provide special instructions for all questions:")
                if special_instructions:
                    st.session_state.special_instructions=special_instructions
                else:
                    st.session_state.special_instructions="None"
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown("###### Selection Questions")
                    num_mcq = st.number_input("Multiple Choice (MCQ)", 
                                            min_value=0, value=0, step=1,
                                            help="Single correct answer from multiple options")
                    num_multi_answer = st.number_input("Multiple Response (MRQ)", 
                                                    min_value=0, value=0, step=1,
                                                    help="Multiple correct answers allowed")
                    num_true_false = st.number_input("True/False", 
                                                min_value=0, value=0, step=1,
                                                help="Binary choice questions")
                    num_order = st.number_input("Order", 
                                            min_value=0, value=0, step=1,
                                            help="Arrange items in sequence")
            
                with col2:
                    st.markdown("###### Text Entry Questions")
                    num_fill_blank = st.number_input("Fill in Blank", 
                                                min_value=0, value=0, step=1,
                                                help="Text entry with specific answer")
                    num_extended_text = st.number_input("Extended Text", 
                                                    min_value=0, value=0, step=1,
                                                    help="Essay or long form response")

                with col3:
                    st.markdown("###### Interactive Questions")
                    num_matching = st.number_input("Match", 
                                                min_value=0, value=0, step=1,
                                                help="Match items between two sets")    
        btnL,btnC, btnR = st.columns([1,2,1])
        with btnC:
            generate_clicked = st.form_submit_button(":page_facing_up: Generate Questions", 
                                            use_container_width=True, 
                                            type="primary") 

    if generate_clicked:
        total_questions=0
        with st.spinner("Preparing your questions...") :
            try:
                # Create initial dictionary based on generation mode
                if not gen_similar_questions:
                    num_questions_dict = {
                        'mcq': num_mcq,
                        'mrq': num_multi_answer,
                        'tf': num_true_false,
                        'match': num_matching,
                        'order': num_order,
                        'fib': num_fill_blank,
                        'essay': num_extended_text
                    }
                    # Remove zero-count question types
                    num_questions_dict = {k: v for k, v in num_questions_dict.items() if v > 0}
                    # Display selected questions only if we have them
                    if num_questions_dict:
                        with st.expander("Selected Questions", expanded=True):
                            st.html("<h4>Selected Questions:</h4> <hr/>")
                            active_questions = [(qtype, count) for qtype, count in num_questions_dict.items()]
                            total_questions = sum(count for _, count in active_questions)
                            
                            if active_questions:
                                num_cols = min(3, max(2, (len(active_questions) + 3) // 4))
                                cols = st.columns(num_cols)
                                for idx, (qtype, count) in enumerate(active_questions):
                                    col_idx = idx % num_cols
                                    cols[col_idx].write(f"- {count} {qtype.upper()} question(s)")
                                
                                st.write(f"**Total Questions:** {total_questions}")
                else:
                    # For similar questions, we don't need to show question counts
                    num_questions_dict = None
                    st.info("Question types and counts will be determined from the uploaded content")
                
                prompt = create_complete_prompt(st.session_state.special_instructions,
                                                st.session_state.content_type, 
                                                st.session_state.assessment_type, 
                                                num_questions_dict, 
                                                gen_similar_questions)

                # Create message placeholder for streaming output
                message_placeholder = st.empty()

                # Get YAML response from LLM
                if st.session_state.model_choice == "GPT-4o (OpenAI)" and st.session_state.user_openAIapi_key:
                    # Process PDF for OpenAI
                    pdf_content=process_pdf_for_Claude(st.session_state['extracted_pdf'])
                    # encoded_images = process_pdf_for_openai(pdf_content)   #st.session_state['extracted_pdf'])
                    if pdf_content: #if encoded_images:
                        yaml_response =asyncio.run(generate_openai_response(
                            prompt, total_questions,
                            st.session_state.user_openAIapi_key,
                            pdf_content,   #encoded_images,
                            message_placeholder,
                            model="o4-mini"
                        ))
                        # st.write("yaml response:")
                        # st.write(yaml_response)
                    else:
                        st.error("Failed to process PDF for OpenAI")
                        return
                
                elif st.session_state.model_choice == "Claude 3.7 Sonnet (Anthropic)" and st.session_state.user_anthropic_key:
                    pdf_content=process_pdf_for_Claude(st.session_state['extracted_pdf'])
                    yaml_response =generate_anthropic_response(total_questions,prompt=prompt, 
                                                               pdf_content=pdf_content,
                                                               api_key=st.session_state.user_anthropic_key)
                else:
                    st.error("Please configure API keys in the Settings tab")
                    return

                if yaml_response:
                    try:
                        # Initialize converter
                        converter = YAMLtoQTIConverter(templates_dir="templates")
                        # Process YAML response and convert to XML
                        xml_questions = converter.convert(yaml_response)
                        
                        if xml_questions:
                            ##Debug view with collapsible sections
                            # with st.expander("View Generated Questions", expanded=False):
                            #     # Show YAML
                            #     st.write("### YAML Format:")
                            #     st.code(yaml_response, language="yaml")
                                
                            #     # Show each question's XML with its own expander
                            #     st.write("### XML Format:")
                            #     for i, xml in enumerate(xml_questions, 1):
                            #         container = st.container()
                            #         with container:
                            #             st.subheader(f"Question {i}")
                            #             st.code(xml, language="xml")
                                        
                            #             # Parse XML to show question type
                            #             try:
                            #                 root = ET.fromstring(xml)
                            #                 # Updated XPath to handle various interaction types
                            #                 interactions = root.findall(".//{http://www.imsglobal.org/xsd/imsqti_v2p2}*")
                            #                 interaction_elem = next((elem for elem in interactions if 'Interaction' in elem.tag), None)
                            #                 if interaction_elem is not None:
                            #                     question_type = interaction_elem.tag.split('}')[-1]
                            #                     st.caption(f"Question Type: {question_type}")
                            #             except ET.ParseError:
                            #                 st.caption("Could not determine question type")
                            
                            # Store questions for later combining
                            store_questions(xml_questions, source_type="text")
                            
                            # Create QTI package for text-only download
                            text_package_data = create_package(
                                test_title="TeacherAIde Text Questions",
                                questions=None,  #xml_questions,
                                question_types='text'
                            )
                            
                            st.toast("✅ Questions generated successfully!")
                            with st.expander("Generation Details", expanded=False):
                                # Add info about review tab
                                st.info("📌 Your questions have been saved. Go to the 'Review & Download' tab to see your questions combined with any image questions.")

                                # Show summary
                                st.html("<h4>Question Summary:</h4> <hr/>")
                                question_types = {}
                                for xml in xml_questions:
                                    try:
                                        root = ET.fromstring(xml)
                                        # Updated interaction finding logic
                                        interactions = root.findall(".//{http://www.imsglobal.org/xsd/imsqti_v2p2}*")
                                        interaction_elem = next((elem for elem in interactions if 'Interaction' in elem.tag), None)
                                        if interaction_elem is not None:
                                            q_type = interaction_elem.tag.split('}')[-1]
                                            question_types[q_type] = question_types.get(q_type, 0) + 1
                                    except ET.ParseError:
                                        continue
                                
                                # Display summary in columns
                                if question_types:
                                    cols = st.columns(3)
                                    for idx, (qtype, count) in enumerate(question_types.items()):
                                        cols[idx % 3].metric(
                                            label=qtype.replace('Interaction', ''),
                                            value=count)
                                else:
                                    st.warning("No interaction types found in generated questions")
                                                            # Only show text-only download in this tab
                            dbtnL,dbtnC, dbtnR = st.columns([1,2,1])
                            with dbtnC:
                                st.download_button(
                                    label="⬇️ Download Text-Only Package",
                                    data=text_package_data,
                                    file_name=f"text_questions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                                    mime="application/zip",
                                    use_container_width=True, type="primary",)
                        else:
                            st.error("❌ No valid questions were generated")
                            
                    except Exception as e:
                        st.error(f"❌ Error processing questions: {str(e)}")
                        st.write("### Debug Information:")
                        st.code(yaml_response, language="yaml")
                        # Add stack trace for debugging
                        st.write("### Stack Trace:")
                        st.exception(e)
                else:
                    st.error("❌ No response received from LLM")
                        
            except Exception as e:
                st.error(f"Error during question generation: {str(e)}")

generate_text_only_questions()