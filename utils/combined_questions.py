# Description: This file contains functions to store, combine, and review generated questions from text and image sources.
#name of the file: combined_questions.py
from typing import Any
import streamlit as st
from utils.yaml_converter import YAMLtoQTIConverter
import xml.etree.ElementTree as ET
import time
from datetime import datetime
import zipfile
import io
from utils.docx_converter import QTIToDocxConverter # Import the new converter


def store_questions(questions, media_files=None, source_type="text"):
    """
    Store generated questions in session state with proper organization
    
    Parameters:
    questions (list): List of XML question strings
    media_files (dict): Dictionary of media files {filename: file_content}
    source_type (str): Either "text" or "image" to indicate the source
    """
    # Initialize questions container if it doesn't exist or is None
    if "generated_questions" not in st.session_state or st.session_state.generated_questions is None:
        st.session_state.generated_questions = {
            "text": {"questions": [], "timestamp": None},
            "image": {"questions": [], "media_files": {}, "timestamp": None}
        }
    
    # Store questions with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if source_type == "text":
        st.session_state.generated_questions["text"] = {
            "questions": questions,
            "timestamp": timestamp
        }
    elif source_type == "image":
        st.session_state.generated_questions["image"] = {
            "questions": questions,
            "media_files": media_files or {},
            "timestamp": timestamp
        }

def get_question_count_summary():
    """
    Get a summary of question counts by type from all sources
    
    Returns:
    dict: Dictionary with question types as keys and counts as values
    """
    question_types = {}
    
    if "generated_questions" not in st.session_state:
        return question_types
    
    # Process all questions from both sources
    all_questions = []
    all_questions.extend(st.session_state.generated_questions.get("text", {}).get("questions", []))
    all_questions.extend(st.session_state.generated_questions.get("image", {}).get("questions", []))
    
    # Extract question types
    for xml in all_questions:
        try:
            root = ET.fromstring(xml)
            # Find interaction elements
            interactions = root.findall(".//{http://www.imsglobal.org/xsd/imsqti_v2p2}*")
            interaction_elem = next((elem for elem in interactions if 'Interaction' in elem.tag), None)
            if interaction_elem is not None:
                q_type = interaction_elem.tag.split('}')[-1]
                readable_type = q_type.replace('Interaction', '')
                question_types[readable_type] = question_types.get(readable_type, 0) + 1
        except ET.ParseError:
            continue
        except Exception:
            continue
    
    return question_types


def create_package(test_title="TeacherAIde Assessment", questions=None, media_files=None, question_types='all', templates_dir="templates"):
    """
    Create a QTI v2.2 package with questions and media files.
    
    This function can either use directly provided questions and media files,
    or pull from session state, or a combination of both.
    
    Parameters:
    test_title (str): Title for the assessment
    questions (list): Optional - List of XML question strings to include directly
    media_files (dict): Optional - Dictionary of media files {filename: file_content} to include directly
    question_types (str): Which types to include from session state ('text', 'image', or 'all')
    templates_dir (str): Directory containing QTI templates
    
    Returns:
    bytes: Package data or None if no questions available
    """
    # Initialize questions and media files
    final_questions = [] if questions is None else list(questions)
    final_media_files = {} if media_files is None else dict(media_files)
    
    # Get questions from session state if they exist
    if "generated_questions" in st.session_state:
        # Get text questions if requested
        if question_types in ['text', 'all'] and 'text' in st.session_state.generated_questions:
            text_questions = st.session_state.generated_questions['text'].get('questions', [])
            final_questions.extend(text_questions)
        
        # Get image questions and media files if requested
        if question_types in ['image', 'all'] and 'image' in st.session_state.generated_questions:
            image_questions = st.session_state.generated_questions['image'].get('questions', [])
            final_questions.extend(image_questions)

            # Get media files from session state
            session_media = st.session_state.generated_questions['image'].get('media_files', {})
            final_media_files.update(session_media)
        # else:
        #     st.warning("⚠️ No image questions found in memory")
    
    # If no questions available, return None
    if not final_questions:
        st.error("⚠️ No questions available to create a package")
        return None
    
    # Use the original converter to access templates and helper methods
    from utils.yaml_converter import YAMLtoQTIConverter
    converter = YAMLtoQTIConverter(templates_dir=templates_dir)
    
    # Create the package
    import zipfile
    from io import BytesIO
    import uuid
    import xml.etree.ElementTree as ET
    
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add manifest
        manifest_xml = converter.package_templates['manifest.xml'].format(
            manifest_id=f"MANIFEST-{uuid.uuid4()}",
            dependencies=converter._generate_dependencies(final_questions),
            resources=converter._generate_resources(final_questions)
        )
        zip_file.writestr('imsmanifest.xml', manifest_xml)
        
        # Add assessment test
        test_xml = converter.package_templates['assessment.xml'].format(
            test_id=f"test-{uuid.uuid4()}",
            test_title=test_title,
            item_refs=converter._generate_item_refs(final_questions)
        )
        zip_file.writestr('assessmentTest.xml', test_xml)
        
        # Add individual questions
        for question in final_questions:
            root = ET.fromstring(question)
            question_id = root.get('identifier')
            zip_file.writestr(f"{question_id}.xml", question)
        
        # Add media files if provided
        if final_media_files:
            # Ensure media directory exists in the zip
            zip_file.writestr('media/.placeholder', '')
            
            for filename, content in final_media_files.items():
                # Make sure the content is bytes, not string
                if isinstance(content, str):
                    content = content.encode('utf-8')
                
                # Store the media file
                try:
                    zip_file.writestr(f"media/{filename}", content)
                except Exception as e:
                    st.error(f"Error adding media file {filename}: {str(e)}")
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def display_mcq(root, ns, prompt, img_src, media_files):
    """Display Multiple Choice Question"""
    st.markdown(f"**Question:** {prompt}")
    
    # Display image if present
    if img_src and img_src.startswith("media/") and img_src in media_files:
        st.image(media_files[img_src], caption=f"Question Image: {img_src}")
    
    # Get correct answer
    correct_value = root.find(".//qti:correctResponse/qti:value", ns)
    correct_answer = correct_value.text if correct_value is not None else None
    
    # Display choices
    choices = root.findall(".//qti:simpleChoice", ns)
    for choice in choices:
        choice_id = choice.get("identifier")
        is_correct = (choice_id == correct_answer)
        
        # Format for choice text and potential images
        choice_text = "".join(choice.itertext()).strip()
        
        # Check if choice has an image
        choice_img = choice.find(".//qti:img", ns)
        choice_img_src = choice_img.get("src", "") if choice_img is not None else None
        
        col1, col2 = st.columns([1, 20])
        with col1:
            if is_correct:
                st.markdown("✅")
            else:
                st.markdown("⬜")
        with col2:
            st.markdown(f"**{choice_id}:** {choice_text}")
            if choice_img_src and choice_img_src.startswith("media/") and choice_img_src in media_files:
                st.image(media_files[choice_img_src], caption=f"Choice Image: {choice_img_src}")


def display_mrq(root, ns, prompt, img_src, media_files):
    """Display Multiple Response Question"""
    st.markdown(f"**Question:** {prompt}")
    
    # Display image if present
    if img_src and img_src.startswith("media/") and img_src in media_files:
        st.image(media_files[img_src], caption=f"Question Image: {img_src}")
    
    # Get correct answers
    correct_values = root.findall(".//qti:correctResponse/qti:value", ns)
    correct_answers = [value.text for value in correct_values if value.text]
    
    # Display choices
    choices = root.findall(".//qti:simpleChoice", ns)
    for choice in choices:
        choice_id = choice.get("identifier")
        is_correct = (choice_id in correct_answers)
        
        choice_text = "".join(choice.itertext()).strip()
        
        col1, col2 = st.columns([1, 20])
        with col1:
            if is_correct:
                st.markdown("✅")
            else:
                st.markdown("⬜")
        with col2:
            st.markdown(f"**{choice_id}:** {choice_text}")

def display_tf(root, ns, prompt):
    """Display True/False Question"""
    st.markdown(f"**Question:** {prompt}")
    
    # Get correct answer
    correct_value = root.find(".//qti:correctResponse/qti:value", ns)
    correct_answer = correct_value.text if correct_value is not None else None
    
    # Display options
    col1, col2 = st.columns([1, 20])
    with col1:
        if correct_answer == "true":
            st.markdown("✅")
        else:
            st.markdown("⬜")
    with col2:
        st.markdown("**True**")
    
    col1, col2 = st.columns([1, 20])
    with col1:
        if correct_answer == "false":
            st.markdown("✅")
        else:
            st.markdown("⬜")
    with col2:
        st.markdown("**False**")

def display_order(root, ns, prompt):
    """Display Order Question"""
    st.markdown(f"**Question:** {prompt}")
    
    # Get correct sequence
    correct_values = root.findall(".//qti:correctResponse/qti:value", ns)
    correct_sequence = [value.text for value in correct_values if value.text]
    
    # Get all choices
    choices = root.findall(".//qti:simpleChoice", ns)
    choice_map = {choice.get("identifier"): "".join(choice.itertext()).strip() for choice in choices}
    
    # Display correct sequence
    st.markdown("**Correct Order:**")
    for i, choice_id in enumerate(correct_sequence, 1):
        if choice_id in choice_map:
            st.code(f"{i}. {choice_map[choice_id]}", language="wolfram")
            #st.markdown(f"{i}. {choice_map[choice_id]}")


# def display_fib(root, ns, prompt):
#     """Display Fill in Blank Question with properly formatted blanks"""
#     try:
#         # Find the paragraph containing the question text
#         p_elem = root.find(".//qti:itemBody/qti:p", ns)
#         if p_elem is None:
#             st.markdown(f"**Prompt:** {prompt}")
#             return
        
#         # Get the XML as string
#         xml_str = ET.tostring(p_elem, encoding='unicode')
        
#         # Replace textEntryInteraction tags with blank placeholders
#         import re
#         processed_text = re.sub(r'<textEntryInteraction[^>]*>', ' <span style="display:inline-block;min-width:80px;border-bottom:2px solid #2e6fac;"></span> ', xml_str)
        
#         # Remove all remaining XML tags
#         processed_text = re.sub(r'<[^>]*>', '', processed_text)
        
#         # Display the text with formatted blanks
#         st.markdown("**Prompt with Blanks:**")
#         st.markdown(f"""
#         <div style="padding: 15px; background-color: #f8f9fa; border-radius: 5px; margin-bottom: 15px; line-height: 1.6;">
#             {processed_text}
#         </div>
#         """, unsafe_allow_html=True)
        
#         # Show correct answers
#         st.markdown("**Correct Answers:**")
        
#         # Find all response declarations
#         response_decls = root.findall(".//qti:responseDeclaration", ns)
        
#         for i, decl in enumerate(response_decls, 1):
#             if decl is None:
#                 continue
                
#             resp_id = decl.get("identifier", "")
#             if resp_id.startswith("RESPONSE"):
#                 # Extract blank number
#                 blank_num = resp_id.replace("RESPONSE", "")
#                 if not blank_num:
#                     blank_num = "1"  # Default to 1 if no number
                
#                 # Get all acceptable answers
#                 values = decl.findall(".//qti:value", ns)
#                 answers = []
#                 for val in values:
#                     if val is not None and val.text:
#                         answers.append(val.text)
                
#                 if answers:
#                     st.markdown(f"- **Blank {blank_num}:** {', '.join(answers)}")
    
#     except Exception as e:
#         # Fallback for any errors
#         st.warning(f"Error displaying fill-in-blank question: {str(e)}")
#         st.markdown(f"**Prompt:** {prompt}")

def display_fib(root, ns, prompt):
    """Display Fill in Blank Question with properly formatted blanks"""
    # Find the paragraph containing the text and interaction elements
    p_elem = root.find(".//qti:itemBody/qti:p", ns)
    if p_elem is None:
        st.markdown(f"**Question:** {prompt}")
        return
    
    # Get all the text content and interaction elements
    elements = []
    if p_elem.text:
        elements.append({"type": "text", "content": p_elem.text})
    
    for i, child in enumerate(p_elem):
        if child.tag.endswith('textEntryInteraction'):
            # Track the blank number
            blank_num = i + 1
            response_id = child.get("responseIdentifier", f"RESPONSE{blank_num}")
            expected_length = child.get("expectedLength", "10")
            
            # Add a blank placeholder
            elements.append({"type": "blank", "number": blank_num, "id": response_id, "length": expected_length})
        else:
            # Add other elements if any
            if child.text:
                elements.append({"type": "text", "content": child.text})
        
        # Add any tail text
        if child.tail:
            elements.append({"type": "text", "content": child.tail})
    
    # Display the text with styled blank spaces
    st.markdown("**Prompt with Blanks:**")
    
    # Combine all text elements, but render blanks as styled elements
    html_parts = []
    for element in elements:
        if element["type"] == "text":
            html_parts.append(element["content"])
        else:  # blank
            # Create a styled blank space with numbered label
            blank_width = min(max(int(element["length"]), 10), 30) # Scale reasonably
            html_parts.append(f'<span style="display:inline-flex;align-items:center;margin:0 4px;"><span style="display:inline-block;min-width:{blank_width*8}px;height:24px;border-bottom:2px solid #2e6fac;background:#f0f7ff;border-radius:2px;padding:0 8px;"></span></span>')
    
    # Join all parts and display as HTML
    full_html = ''.join(html_parts)
    st.markdown(f'<div style="margin-bottom:16px">{full_html}</div>', unsafe_allow_html=True)
    
    # Get and display correct answers
    st.markdown("**Correct Answers:**")
    response_decls = root.findall(".//qti:responseDeclaration", ns)
    
    for i, decl in enumerate(response_decls, 1):
        resp_id = decl.get("identifier")
        if resp_id.startswith("RESPONSE"):
            values = decl.findall(".//qti:value", ns)
            answers = [value.text for value in values if value.text]
            
            # Show blank number and acceptable answers with better formatting
            if answers:
                st.markdown(f'<div style="margin:4px 0"><span style="display:inline-block;font-weight:bold;min-width:80px;">Blank {i}:</span> {", ".join(answers)}</div>', unsafe_allow_html=True)

def display_essay(root, ns, prompt, question_index, tab_id="all"):
    """Display Essay Question with unique keys for text areas"""
    st.markdown(f"**Question:** {prompt}")
    
    # Get expected lines
    interaction = root.find(".//qti:extendedTextInteraction", ns)
    expected_lines = interaction.get("expectedLines", "5") if interaction is not None else "5"
    
    st.markdown(f"**Expected Answer Length:** {expected_lines} lines")
    
    # Create a truly unique key combining tab_id, question_index and identifier
    question_id = root.get('identifier', '')
    unique_key = f"essay_answer_{tab_id}_{question_index}_{question_id}"
    
    # Display empty text area as placeholder with the unique key
    st.text_area(
        "Answer Area (Preview Only)", 
        "", 
        height=int(expected_lines)*24, 
        disabled=True, 
        key=unique_key
    )


# def display_match(root, ns, prompt):
#     """Display Matching Question"""
#     st.markdown(f"**Prompt:** {prompt}")
    
#     # Get correct pairs
#     correct_values = root.findall(".//qti:correctResponse/qti:value", ns)
#     correct_pairs = []
#     for value in correct_values:
#         if value.text:
#             source, target = value.text.split()
#             correct_pairs.append((source, target))
    
#     # Get source and target choices
#     match_sets = root.findall(".//qti:simpleMatchSet", ns)
#     if len(match_sets) >= 2:
#         source_choices = match_sets[0].findall(".//qti:simpleAssociableChoice", ns)
#         target_choices = match_sets[1].findall(".//qti:simpleAssociableChoice", ns)
        
#         source_map = {choice.get("identifier"): "".join(choice.itertext()).strip() for choice in source_choices}
#         target_map = {choice.get("identifier"): "".join(choice.itertext()).strip() for choice in target_choices}
        
#         # Display matching pairs
#         st.markdown("**Matching Pairs:**")
#         for source_id, target_id in correct_pairs:
#             if source_id in source_map and target_id in target_map:
#                 col1, col2, col3 = st.columns([1, 0.1, 1])
#                 with col1:
#                     st.success(source_map[source_id])
#                 with col2:
#                     st.write("→")  
#                 with col3:
#                     st.info(target_map[target_id])

# def display_match(root, ns, prompt):
#     """Display Matching Question"""
#     st.markdown(f"**Prompt:** {prompt}")
    
#     # Get correct pairs
#     correct_values = root.findall(".//qti:correctResponse/qti:value", ns)
#     correct_pairs = []
#     for value in correct_values:
#         if value.text:
#             parts = value.text.strip().split()
#             if len(parts) >= 2:
#                 source, target = parts[0], parts[1]
#                 correct_pairs.append((source, target))
    
#     # Get source and target choices
#     match_sets = root.findall(".//qti:simpleMatchSet", ns)
#     if len(match_sets) >= 2:
#         source_choices = match_sets[0].findall(".//qti:simpleAssociableChoice", ns)
#         target_choices = match_sets[1].findall(".//qti:simpleAssociableChoice", ns)
        
#         # Extract text content properly from the XML elements
#         source_map = {}
#         for choice in source_choices:
#             identifier = choice.get("identifier")
#             # Get the text content, handling possible nested elements
#             text = ''.join(choice.itertext()).strip()
#             source_map[identifier] = text
        
#         target_map = {}
#         for choice in target_choices:
#             identifier = choice.get("identifier")
#             # Get the text content, handling possible nested elements
#             text = ''.join(choice.itertext()).strip()
#             target_map[identifier] = text
        
#         # Display matching pairs
#         st.markdown("**Matching Pairs:**")
#         for source_id, target_id in correct_pairs:
#             if source_id in source_map and target_id in target_map:
#                 col1, col2, col3 = st.columns([1, 0.1, 1])
#                 with col1:
#                     st.success(source_map[source_id])
#                 with col2:
#                     st.write("→")  
#                 with col3:
#                     st.info(target_map[target_id])
#             else:
#                 st.warning(f"Could not find match for {source_id} → {target_id}")

# def display_match(root, ns, prompt):
#     """Display Matching Question"""
#     st.markdown(f"**Prompt:** {prompt}")
    
#     # Get all choices from both sets
#     match_sets = root.findall(".//qti:simpleMatchSet", ns)
#     if len(match_sets) >= 2:
#         all_choices = []
        
#         # Extract all choices from both match sets
#         for match_set in match_sets:
#             choices = match_set.findall(".//qti:simpleAssociableChoice", ns)
#             for choice in choices:
#                 identifier = choice.get("identifier")
#                 text = ''.join(choice.itertext()).strip()
#                 all_choices.append((identifier, text))
        
#         # Separate into source and target choices based on identifier pattern
#         source_choices = [(id, text) for id, text in all_choices if id.startswith('S')]
#         target_choices = [(id, text) for id, text in all_choices if id.startswith('T')]
        
#         # Create maps for lookup
#         source_map = {id: text for id, text in source_choices}
#         target_map = {id: text for id, text in target_choices}
        
#         # Get correct pairs
#         correct_values = root.findall(".//qti:correctResponse/qti:value", ns)
#         correct_pairs = []
#         for value in correct_values:
#             if value.text:
#                 parts = value.text.strip().split()
#                 if len(parts) >= 2:
#                     source, target = parts[0], parts[1]
#                     correct_pairs.append((source, target))
        
#         # If no correct pairs found in XML, create logical pairs
#         if not correct_pairs and source_choices and target_choices:
#             # Create pairs based on similar indices if possible
#             if len(source_choices) <= len(target_choices):
#                 for i in range(len(source_choices)):
#                     correct_pairs.append((source_choices[i][0], target_choices[i][0]))
        
#         # # Display all source choices
#         # st.markdown("**Source Choices:**")
#         # for id, text in source_choices:
#         #     st.info(f"{id}: {text}")
        
#         # # Display all target choices
#         # st.markdown("**Target Choices:**")
#         # for id, text in target_choices:
#         #     st.success(f"{id}: {text}")
        
#         # Display matching pairs if available
#         if correct_pairs:
#             st.markdown("**Correct Matching Pairs:**")
#             for source_id, target_id in correct_pairs:
#                 if source_id in source_map and target_id in target_map:
#                     col1, col2, col3 = st.columns([1, 0.1, 1])
#                     with col1:
#                         st.info(f"{source_id}: {source_map[source_id]}")
#                     with col2:
#                         st.write("→")  
#                     with col3:
#                         st.success(f"{target_id}: {target_map[target_id]}")
#                 else:
#                     st.warning(f"Could not find match for {source_id} → {target_id}")
#         else:
#             st.warning("No matching pairs found in the XML. Please check the correctResponse section.")

def display_match(root, ns, prompt):
    """Display Matching Question"""
    st.markdown(f"**Question:** {prompt}")
    
    # Get all choices from both sets
    match_sets = root.findall(".//qti:simpleMatchSet", ns)
    if len(match_sets) >= 2:
        all_choices = []
        
        # Extract all choices from both match sets
        for i, match_set in enumerate(match_sets):
            choices = match_set.findall(".//qti:simpleAssociableChoice", ns)
            for choice in choices:
                identifier = choice.get("identifier")
                text = ''.join(choice.itertext()).strip()
                all_choices.append((identifier, text, i))  # Add set index
        
        # Separate into source and target choices based on which set they belong to
        source_choices = [(id, text) for id, text, idx in all_choices if idx == 0]
        target_choices = [(id, text) for id, text, idx in all_choices if idx == 1]
        
        # Create maps for lookup
        source_map = {id: text for id, text in source_choices}
        target_map = {id: text for id, text in target_choices}
        
        # Get correct pairs
        correct_values = root.findall(".//qti:correctResponse/qti:value", ns)
        correct_pairs = []
        for value in correct_values:
            if value.text:
                parts = value.text.strip().split()
                if len(parts) >= 2:
                    source, target = parts[0], parts[1]
                    correct_pairs.append((source, target))
        
        # If no correct pairs found in XML, create logical pairs
        if not correct_pairs and source_choices and target_choices:
            # Create pairs based on similar indices if possible
            if len(source_choices) <= len(target_choices):
                for i in range(len(source_choices)):
                    correct_pairs.append((source_choices[i][0], target_choices[i][0]))
        
        # Display matching pairs if available
        if correct_pairs:
            st.markdown("**Correct Matching Pairs:**")
            for source_id, target_id in correct_pairs:
                if source_id in source_map and target_id in target_map:
                    col1, col2, col3 = st.columns([1, 0.1, 1])
                    with col1:
                        st.info(f"{source_id}: {source_map[source_id]}")
                    with col2:
                        st.write("→")  
                    with col3:
                        st.success(f"{target_id}: {target_map[target_id]}")
                else:
                    st.warning(f"Could not find match for {source_id} → {target_id}")
        else:
            st.warning("No matching pairs found in the XML. Please check the correctResponse section.")


def display_questions(questions, media_files, tab_id="all"):
    """Display questions in a user-friendly format
    
    Parameters:
    questions - list of XML question strings
    media_files - dictionary of media files
    tab_id - identifier for which tab is displaying the questions ('all', 'text', 'image')
    """
    for i, xml in enumerate(questions, 1):
        try:
            # Parse the XML
            root = ET.fromstring(xml)
            ns = {"qti": "http://www.imsglobal.org/xsd/imsqti_v2p2"}
            
            # Get question identifier and title
            identifier = root.get('identifier', f'Question_{i}')
            title = root.get('title', f'Question {i}')
            
            # Find question type
            interaction_elems = root.findall(".//qti:*", ns)
            interaction_elem = next((elem for elem in interaction_elems if 'Interaction' in elem.tag), None)
            
            if interaction_elem is None:
                continue
                
            q_type = interaction_elem.tag.split('}')[-1]
            readable_type = q_type.replace('Interaction', '')
            
            # Find prompt
            prompt_elem = root.find(".//qti:prompt", ns)
            prompt = prompt_elem.text if prompt_elem is not None and prompt_elem.text else ""
            
            # Check for images
            img_elem = root.find(".//qti:img", ns)
            img_src = None
            if img_elem is not None:
                img_src = img_elem.get("src", "")
            
            # Create a container for the question
            with st.container(border=True):
                # Question header with edit button
                col1, col2 = st.columns([4, 1])
                col1.markdown(f"###### {title}", unsafe_allow_html=True)
                col1.caption(f"Type: {readable_type} | ID: {identifier}")
                
                # Handle question display based on type
                if "choiceInteraction" in q_type and "multiple" not in root.find(".//qti:responseDeclaration", ns).get("cardinality", ""):
                    # MCQ (Single choice)
                    display_mcq(root, ns, prompt, img_src, media_files)
                elif "choiceInteraction" in q_type and "multiple" in root.find(".//qti:responseDeclaration", ns).get("cardinality", ""):
                    # MRQ (Multiple choice)
                    display_mrq(root, ns, prompt, img_src, media_files)
                elif "orderInteraction" in q_type:
                    # Order
                    display_order(root, ns, prompt)
                elif "textEntryInteraction" in q_type:
                    # Fill in Blank
                    display_fib(root, ns, prompt)
                elif "extendedTextInteraction" in q_type:
                    # Essay - pass both question index and tab context for unique key
                    display_essay(root, ns, prompt, i, tab_id)
                elif "matchInteraction" in q_type:
                    # Match
                    display_match(root, ns, prompt)
                else:
                    # Default fallback for other question types
                    st.markdown(f"**Question:** {prompt}")
                    if img_src and img_src.startswith("media/") and img_src in media_files:
                        st.image(media_files[img_src], caption=f"Question Image: {img_src}")
                    
                # Show raw XML in expandable section
                # with st.expander("Show XML", expanded=False):
                #     st.code(xml, language="xml")
        except ET.ParseError:
            st.error(f"Error parsing question XML for question {i}")
        except Exception as e:
            st.error(f"Error displaying question {i}: {str(e)}")

def render_review_tab():
    """Render the Review & Download tab with combined questions and user-friendly display"""
    st.subheader(":material/download: Review & Download Questions", divider=True)
    refresh_col, cancel_col = st.columns([1, 1])

    refresh_col.button(":material/refresh: Refresh Questions", type="secondary")
    
    # Check if we have any questions - improved null check
    if not st.session_state.get("generated_questions"):
        st.warning("⚠️ No questions generated yet")
        return
        
    # If user clicks cancel button
    if cancel_col.button(":material/delete_forever: Clear Questions", type="primary"):
        st.session_state.generated_questions = None
        st.rerun()

    # Get question sources - safely access nested dictionaries
    text_questions = []
    image_questions = []
    media_files = {}
    text_timestamp = None
    image_timestamp = None
    
    # Use safe dictionary access via get() to avoid None errors
    text_data = st.session_state.generated_questions.get("text", {})
    if text_data:
        text_questions = text_data.get("questions", [])
        text_timestamp = text_data.get("timestamp")
    
    image_data = st.session_state.generated_questions.get("image", {})
    if image_data:
        image_questions = image_data.get("questions", [])
        media_files = image_data.get("media_files", {})
        image_timestamp = image_data.get("timestamp")
    
    # If no questions at all, show warning
    if not text_questions and not image_questions:
        st.warning("⚠️ No questions generated yet")
        return
    
    # Display summary metrics
    with st.container(border=True):
        st.markdown("##### Question Summary")
        question_types = get_question_count_summary()
        
        if question_types:
            cols = st.columns(min(len(question_types), 4))
            for idx, (qtype, count) in enumerate(question_types.items()):
                cols[idx % len(cols)].metric(
                    label=qtype,
                    value=count
                )
    
    with st.container(border=True):
    # Combined assessment section
        st.markdown("### Combined Assessment")
        assessment_title = st.text_input("Assessment Title", value="TeacherAIde Combined Assessment", 
                                        help="Customize the title of your assessment package")
    
    # Create package
    package_data = create_package(test_title=assessment_title, question_types='all')
    
    if package_data:
        # Show assessment summary
        has_text = len(text_questions) > 0
        has_images = len(image_questions) > 0
        
        if has_text and has_images:
            st.success(f"✅ Combined assessment with {len(text_questions)} text questions and {len(image_questions)} image questions")
        elif has_text:
            st.success(f"✅ Assessment with {len(text_questions)} text-only questions")
        else:
            st.success(f"✅ Assessment with {len(image_questions)} image-based questions")
        
        # Download button
        st.download_button(
            label="⬇️ Download Assessment Package",
            data=package_data,
            file_name=f"{assessment_title.replace(' ', '_')}.zip",
            mime="application/zip",
            use_container_width=True,
            key="download_qti_zip" # Added key for uniqueness
        )

        # --- START: New Code for DOCX Download ---
        try:
            # Combine all questions and media files for DOCX generation
            all_questions_for_docx = text_questions + image_questions
            if all_questions_for_docx:
                st.write("---") # Visual separator
                st.markdown("##### Download as Word Document")
                docx_converter = QTIToDocxConverter(
                    questions_xml=all_questions_for_docx,
                    media_files=media_files,
                    title=assessment_title
                )
                docx_bytes = docx_converter.generate_docx_bytes()
                st.download_button(
                    label="📄 Download Quiz Paper (.docx)",
                    data=docx_bytes,
                    file_name=f"{assessment_title.replace(' ', '_')}_QuizPaper.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    key="download_docx" # Added key for uniqueness
                )
            else:
                # Optionally show a disabled button if no questions
                # st.button("📄 Download Quiz Paper (.docx)", disabled=True, use_container_width=True)
                pass # Or just don't show the button

        except Exception as e:
            st.error(f"Error generating Word document: {e}")
        # --- END: New Code for DOCX Download ---

        # Show package contents
        with st.container():
            st.subheader("Assessment Contents")
            st.write(f"**Text Questions:** {len(text_questions)}")
            st.write(f"**Image Questions:** {len(image_questions)}")
            st.write(f"**Total Questions:** {len(text_questions) + len(image_questions)}")
            
            if text_timestamp:
                st.write(f"**Text Questions Generated:** {text_timestamp}")
            if image_timestamp:
                st.write(f"**Image Questions Generated:** {image_timestamp}")
                
            if media_files:
                st.write(f"**Media Files:** {len(media_files)}")
                with st.expander("Media File Names", expanded=False):
                    for filename in media_files:
                        st.write(f"- {filename}")
    else:
        st.warning("⚠️ No questions available to combine")
    
    # Create display tabs
    all_questions = text_questions + image_questions
    
    # Create tabs based on available question types
    if text_questions and image_questions:
        tab1, tab2, tab3 = st.tabs(["All Questions", "Text-Only Questions", "Image Questions"])
        
        with tab1:
            st.markdown("#### All Questions", unsafe_allow_html=True)
            display_questions(all_questions, media_files, tab_id="all")
            
        with tab2:
            st.markdown("#### Text-Only Questions", unsafe_allow_html=True)
            st.success(f"✅ {len(text_questions)} text-based questions available")
            if text_timestamp:
                st.write(f"Generated: {text_timestamp}")
            display_questions(text_questions, {}, tab_id="text")
            
        with tab3:
            st.markdown("#### Image-Based Questions", unsafe_allow_html=True)
            st.success(f"✅ {len(image_questions)} image-based questions available")
            if image_timestamp:
                st.write(f"Generated: {image_timestamp}")
            display_questions(image_questions, media_files, tab_id="image")
            
    elif text_questions:
        tab1, tab2 = st.tabs(["All Questions", "Text-Only Questions"])
        
        with tab1:
            st.markdown("#### All Questions", unsafe_allow_html=True)
            display_questions(text_questions, {}, tab_id="all")
            
        with tab2:
            st.markdown("#### Text-Only Questions", unsafe_allow_html=True)
            st.success(f"✅ {len(text_questions)} text-based questions available")
            if text_timestamp:
                st.write(f"Generated: {text_timestamp}")
            display_questions(text_questions, {}, tab_id="text")
            
    elif image_questions:
        tab1, tab2 = st.tabs(["All Questions", "Image Questions"])
        
        with tab1:
            st.markdown("#### All Questions", unsafe_allow_html=True)
            display_questions(image_questions, media_files, tab_id="all")
            
        with tab2:
            st.markdown("#### Image-Based Questions", unsafe_allow_html=True)
            st.success(f"✅ {len(image_questions)} image-based questions available")
            if image_timestamp:
                st.write(f"Generated: {image_timestamp}")
            display_questions(image_questions, media_files, tab_id="image")
    else:
        st.container()
        st.markdown("#### All Questions", unsafe_allow_html=True)
        display_questions(all_questions, media_files, tab_id="all")

# def render_review_tab():
#     """Render the Review & Download tab with combined questions and user-friendly display"""
#     st.markdown("### 📊 Review & Download Questions")
#     refresh_col, cancel_col = st.columns([1, 1])

#     refresh_col.button(":material/refresh: Refresh Questions", type="secondary")
    
#     # Check if we have any questions
#     if "generated_questions" not in st.session_state:
#         st.warning("⚠️ No questions generated yet")
#         return
#     else:
#         if cancel_col.button(":material/delete_forever: Clear Questions", type="primary"):
#             st.session_state.generated_questions = None
#             st.rerun()
            
#         # # Get question sources
#         # text_questions = st.session_state.generated_questions.get("text", {}).get("questions", [])
#         # image_questions = st.session_state.generated_questions.get("image", {}).get("questions", [])
#         # media_files = st.session_state.generated_questions.get("image", {}).get("media_files", {})
#         # text_timestamp = st.session_state.generated_questions.get("text", {}).get("timestamp")
#         # image_timestamp = st.session_state.generated_questions.get("image", {}).get("timestamp")
        
#         # Get question sources - safely access nested dictionaries
#         text_questions = []
#         image_questions = []
#         media_files = {}
#         text_timestamp = None
#         image_timestamp = None

#         # Safely get text questions
#         if "text" in st.session_state.generated_questions:
#             text_data = st.session_state.generated_questions["text"]
#             if isinstance(text_data, dict):
#                 text_questions = text_data.get("questions", [])
#                 text_timestamp = text_data.get("timestamp")
        
#         # Safely get image questions
#         if "image" in st.session_state.generated_questions:
#             image_data = st.session_state.generated_questions["image"]
#             if isinstance(image_data, dict):
#                 image_questions = image_data.get("questions", [])
#                 media_files = image_data.get("media_files", {})
#                 image_timestamp = image_data.get("timestamp")


#         # If no questions at all, show warning
#         if not text_questions and not image_questions:
#             st.warning("⚠️ No questions generated yet")
#             return
        
#         # Display summary metrics
#         st.markdown("#### Question Summary")
#         question_types = get_question_count_summary()
        
#         if question_types:
#             cols = st.columns(min(len(question_types), 4))
#             for idx, (qtype, count) in enumerate(question_types.items()):
#                 cols[idx % len(cols)].metric(
#                     label=qtype,
#                     value=count
#                 )
        
#         # Combined assessment section - always first and most prominent
#         st.markdown("### Combined Assessment")
#         assessment_title = st.text_input("Assessment Title", value="TeacherAId Combined Assessment", 
#                                         help="Customize the title of your assessment package")
        
#         # Always create a fresh combined package to ensure it's up to date
#         package_data = create_package(test_title=assessment_title, question_types='all')
        
#         if package_data:
#             # Show summary of combined questions
#             has_text = len(text_questions) > 0
#             has_images = len(image_questions) > 0
#             has_both = has_text and has_images
            
#             if has_both:
#                 st.success(f"✅ Combined assessment with {len(text_questions)} text questions and {len(image_questions)} image questions")
#             elif has_text:
#                 st.success(f"✅ Assessment with {len(text_questions)} text-only questions")
#             else:
#                 st.success(f"✅ Assessment with {len(image_questions)} image-based questions")
            
#             # Download button for combined package
#             st.download_button(
#                 label="⬇️ Download Assessment Package",
#                 data=package_data,
#                 file_name=f"{assessment_title.replace(' ', '_')}.zip",
#                 mime="application/zip",
#                 use_container_width=True
#             )
            
#             # Show a preview of what's included
#             with st.container():
#                 st.subheader("Assessment Contents")
#                 st.write(f"**Text Questions:** {len(text_questions)}")
#                 st.write(f"**Image Questions:** {len(image_questions)}")
#                 st.write(f"**Total Questions:** {len(text_questions) + len(image_questions)}")
                
#                 if text_timestamp:
#                     st.write(f"**Text Questions Generated:** {text_timestamp}")
#                 if image_timestamp:
#                     st.write(f"**Image Questions Generated:** {image_timestamp}")
                    
#                 if media_files:
#                     st.write(f"**Media Files:** {len(media_files)}")
#                     with st.expander("Media File Names", expanded=False):
#                         for filename in media_files:
#                             st.write(f"- {filename}")
#         else:
#             st.warning("⚠️ No questions available to combine")
        
#         # Create tabs for the individual question types
#         tabs = []
#         if text_questions and image_questions:
#             questions_tab, text_tab, image_tab = st.tabs(["All Questions", "Text-Only Questions", "Image Questions"])
#             tabs = [questions_tab, text_tab, image_tab]
#         elif text_questions:
#             questions_tab, text_tab = st.tabs(["All Questions", "Text-Only Questions"])
#             tabs = [questions_tab, text_tab]
#         elif image_questions:
#             questions_tab, image_tab = st.tabs(["All Questions", "Image Questions"])
#             tabs = [questions_tab, image_tab]
#         else:
#             questions_tab = st.container()
#             tabs = [questions_tab]
        
#         # All questions tab
#         with tabs[0]:
#             st.subheader("All Questions")
#             display_questions(text_questions + image_questions, media_files)
        
#         # Text-only questions tab
#         if len(tabs) > 1 and text_questions:
#             with tabs[1]:
#                 st.subheader("Text-Only Questions")
#                 if text_questions:
#                     st.success(f"✅ {len(text_questions)} text-based questions available")
#                     st.write(f"Generated: {text_timestamp}")
#                     display_questions(text_questions, {})
#                 else:
#                     st.info("No text-based questions generated yet")
        
#         # Image-based questions tab
#         if len(tabs) > 1 and image_questions:
#             with tabs[-1]:
#                 st.subheader("Image-Based Questions")
#                 if image_questions:
#                     st.success(f"✅ {len(image_questions)} image-based questions available")
#                     st.write(f"Generated: {image_timestamp}")
#                     display_questions(image_questions, media_files)
#                 else:
#                     st.info("No image-based questions generated yet")


# def render_review_tab():
#     """Render the Review & Download tab with combined questions"""
#     st.markdown("### 📊 Review & Download Questions")
#     refresh_col, cancel_col = st.columns([1, 1])

#     refresh_col.button(":material/refresh: Refresh Questions", type="secondary",)


    
#     # Check if we have any questions
#     if "generated_questions" not in st.session_state:
#         st.warning("⚠️ No questions generated yet")
#         st.stop
#     else:
#         if cancel_col.button(":material/delete_forever: Clear Questions", type="primary"):
#             st.session_state.generated_questions = None
#             st.stop
#         # Get question sources
#         text_questions = st.session_state.generated_questions.get("text", {}).get("questions", [])
#         image_questions = st.session_state.generated_questions.get("image", {}).get("questions", [])
#         media_files = st.session_state.generated_questions.get("image", {}).get("media_files", {})
#         text_timestamp = st.session_state.generated_questions.get("text", {}).get("timestamp")
#         image_timestamp = st.session_state.generated_questions.get("image", {}).get("timestamp")
        
#         # If no questions at all, show warning
#         if not text_questions and not image_questions:
#             st.warning("⚠️ No questions generated yet")
#             return
        
#         # Display summary metrics
#         st.markdown("#### Question Summary")
#         question_types = get_question_count_summary()
        
#         if question_types:
#             cols = st.columns(min(len(question_types), 4))
#             for idx, (qtype, count) in enumerate(question_types.items()):
#                 cols[idx % len(cols)].metric(
#                     label=qtype,
#                     value=count
#                 )
        
#         # Combined assessment section - always first and most prominent
#         st.markdown("### Combined Assessment")
#         assessment_title = st.text_input("Assessment Title", value="TeacherAId Combined Assessment", 
#                                         help="Customize the title of your assessment package")
        
#         # Always create a fresh combined package to ensure it's up to date
#         package_data = create_package(test_title=assessment_title, question_types='all')
        
#         if package_data:
#             # Show summary of combined questions
#             has_text = len(text_questions) > 0
#             has_images = len(image_questions) > 0
#             has_both = has_text and has_images
            
#             if has_both:
#                 st.success(f"✅ Combined assessment with {len(text_questions)} text questions and {len(image_questions)} image questions")
#             elif has_text:
#                 st.success(f"✅ Assessment with {len(text_questions)} text-only questions")
#             else:
#                 st.success(f"✅ Assessment with {len(image_questions)} image-based questions")
            
#             # Download button for combined package
#             st.download_button(
#                 label="⬇️ Download Assessment Package",
#                 data=package_data,
#                 file_name=f"{assessment_title.replace(' ', '_')}.zip",
#                 mime="application/zip",
#                 use_container_width=True
#             )
            
#             # Show a preview of what's included
#             with st.container():
#                 st.subheader("Assessment Contents")
#                 st.write(f"**Text Questions:** {len(text_questions)}")
#                 st.write(f"**Image Questions:** {len(image_questions)}")
#                 st.write(f"**Total Questions:** {len(text_questions) + len(image_questions)}")
                
#                 if text_timestamp:
#                     st.write(f"**Text Questions Generated:** {text_timestamp}")
#                 if image_timestamp:
#                     st.write(f"**Image Questions Generated:** {image_timestamp}")
                    
#                 if media_files:
#                     st.write(f"**Media Files:** {len(media_files)}")
#                     with st.expander("Media File Names", expanded=False):
#                         for filename in media_files:
#                             st.write(f"- {filename}")
#         else:
#             st.warning("⚠️ No questions available to combine")
        
#         # Create tabs for the individual question types
#         tabs = []
#         if text_questions and image_questions:
#             questions_tab, text_tab, image_tab = st.tabs(["All Questions", "Text-Only Questions", "Image Questions"])
#             tabs = [questions_tab, text_tab, image_tab]
#         elif text_questions:
#             questions_tab, text_tab = st.tabs(["All Questions", "Text-Only Questions"])
#             tabs = [questions_tab, text_tab]
#         elif image_questions:
#             questions_tab, image_tab = st.tabs(["All Questions", "Image Questions"])
#             tabs = [questions_tab, image_tab]
#         else:
#             questions_tab = st.container()
#             tabs = [questions_tab]
        
#         # All questions tab
#         with tabs[0]:
#             st.subheader("All Questions")
            
#             # Text questions section
#             if text_questions:
#                 st.write(f"### Text Questions ({len(text_questions)})")
#                 st.write(f"Generated: {text_timestamp}")
                
#                 for i, xml in enumerate(text_questions, 1):
#                     with st.container(border=True):
#                         st.subheader(f"Text Question {i}")
                        
#                         # Extract and display question content from XML
#                         try:
#                             root = ET.fromstring(xml)
                            
#                             # Find prompt
#                             prompt_elem = root.find(".//{http://www.imsglobal.org/xsd/imsqti_v2p2}prompt")
#                             if prompt_elem is not None and prompt_elem.text:
#                                 st.markdown(f"**Prompt:** {prompt_elem.text}")
                            
#                             # Find interaction type
#                             interactions = root.findall(".//{http://www.imsglobal.org/xsd/imsqti_v2p2}*")
#                             interaction_elem = next((elem for elem in interactions if 'Interaction' in elem.tag), None)
#                             if interaction_elem is not None:
#                                 q_type = interaction_elem.tag.split('}')[-1]
#                                 st.caption(f"Type: {q_type.replace('Interaction', '')}")
                            
#                         except ET.ParseError:
#                             st.write("Error parsing question XML")
                        
#                         with st.expander("Show XML", expanded=False):
#                             st.code(xml, language="xml")
            
#             # Image questions section
#             if image_questions:
#                 st.write(f"### Image Questions ({len(image_questions)})")
#                 st.write(f"Generated: {image_timestamp}")
                
#                 for i, xml in enumerate(image_questions, 1):
#                     with st.container(border=True):
#                         st.subheader(f"Image Question {i}")
                        
#                         # Extract and display question content from XML
#                         try:
#                             root = ET.fromstring(xml)
                            
#                             # Find image if present
#                             img_elem = root.find(".//{http://www.imsglobal.org/xsd/imsqti_v2p2}img")
#                             if img_elem is not None:
#                                 src = img_elem.get("src", "")
#                                 if src.startswith("media/"):
#                                     st.write(f"**Image:** {src}")
                            
#                             # Find prompt
#                             prompt_elem = root.find(".//{http://www.imsglobal.org/xsd/imsqti_v2p2}prompt")
#                             if prompt_elem is not None and prompt_elem.text:
#                                 st.markdown(f"**Prompt:** {prompt_elem.text}")
                            
#                             # Find interaction type
#                             interactions = root.findall(".//{http://www.imsglobal.org/xsd/imsqti_v2p2}*")
#                             interaction_elem = next((elem for elem in interactions if 'Interaction' in elem.tag), None)
#                             if interaction_elem is not None:
#                                 q_type = interaction_elem.tag.split('}')[-1]
#                                 st.caption(f"Type: {q_type.replace('Interaction', '')}")
                            
#                         except ET.ParseError:
#                             st.write("Error parsing question XML")
                        
#                         with st.expander("Show XML", expanded=False):
#                             st.code(xml, language="xml")
        
#         # Text-only questions tab
#         if len(tabs) > 1 and text_questions:
#             with tabs[1]:
#                 st.subheader("Text-Only Questions")
#                 if text_questions:
#                     st.success(f"✅ {len(text_questions)} text-based questions available")
#                     st.write(f"Generated: {text_timestamp}")
                    
#                     for i, xml in enumerate(text_questions, 1):
#                         with st.container(border=True):
#                             st.subheader(f"Question {i}")
                            
#                             # Extract and display question content from XML
#                             try:
#                                 root = ET.fromstring(xml)
                                
#                                 # Find prompt
#                                 prompt_elem = root.find(".//{http://www.imsglobal.org/xsd/imsqti_v2p2}prompt")
#                                 if prompt_elem is not None and prompt_elem.text:
#                                     st.markdown(f"**Prompt:** {prompt_elem.text}")
                                
#                                 # Find interaction type
#                                 interactions = root.findall(".//{http://www.imsglobal.org/xsd/imsqti_v2p2}*")
#                                 interaction_elem = next((elem for elem in interactions if 'Interaction' in elem.tag), None)
#                                 if interaction_elem is not None:
#                                     q_type = interaction_elem.tag.split('}')[-1]
#                                     st.caption(f"Type: {q_type.replace('Interaction', '')}")
                                
#                             except ET.ParseError:
#                                 st.write("Error parsing question XML")
                            
#                             with st.expander("Show XML", expanded=False):
#                                 st.code(xml, language="xml")
#                 else:
#                     st.info("No text-based questions generated yet")
        
#         # Image-based questions tab
#         if len(tabs) > 1 and image_questions:
#             with tabs[-1]:
#                 st.subheader("Image-Based Questions")
#                 if image_questions:
#                     st.success(f"✅ {len(image_questions)} image-based questions available")
#                     st.write(f"Generated: {image_timestamp}")
                    
#                     for i, xml in enumerate(image_questions, 1):
#                         with st.container(border=True):
#                             st.subheader(f"Question {i}")
                            
#                             # Extract and display question content from XML
#                             try:
#                                 root = ET.fromstring(xml)
                                
#                                 # Find image if present
#                                 img_elem = root.find(".//{http://www.imsglobal.org/xsd/imsqti_v2p2}img")
#                                 if img_elem is not None:
#                                     src = img_elem.get("src", "")
#                                     if src.startswith("media/"):
#                                         st.write(f"**Image:** {src}")
                                
#                                 # Find prompt
#                                 prompt_elem = root.find(".//{http://www.imsglobal.org/xsd/imsqti_v2p2}prompt")
#                                 if prompt_elem is not None and prompt_elem.text:
#                                     st.markdown(f"**Prompt:** {prompt_elem.text}")
                                
#                                 # Find interaction type
#                                 interactions = root.findall(".//{http://www.imsglobal.org/xsd/imsqti_v2p2}*")
#                                 interaction_elem = next((elem for elem in interactions if 'Interaction' in elem.tag), None)
#                                 if interaction_elem is not None:
#                                     q_type = interaction_elem.tag.split('}')[-1]
#                                     st.caption(f"Type: {q_type.replace('Interaction', '')}")
                                
#                             except ET.ParseError:
#                                 st.write("Error parsing question XML")
                            
#                             with st.expander("Show XML", expanded=False):
#                                 st.code(xml, language="xml")
#                 else:
#                     st.info("No image-based questions generated yet")
