import streamlit as st
import base64
import xml.etree.ElementTree as ET
from datetime import datetime
import time
from utils.yaml_converter import YAMLtoQTIConverter # Assuming these exist
from utils.combined_questions import store_questions, create_package # Assuming these exist
from openai import OpenAI # Moved import up
from utils.llm_handlers import get_config_value

# --- Helper function to load prompts ---
def load_prompts_from_xml(filepath):
    """Loads instruction prompts from an XML file."""
    from pathlib import Path
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        prompts = {}
        for prompt_elem in root.findall('prompt'):
            prompt_type = prompt_elem.get('type')
            prompt_text = prompt_elem.text.strip() if prompt_elem.text else ""
            if prompt_type and prompt_text:
                prompts[prompt_type] = prompt_text
        if not prompts:
            st.error(f"❌ No prompts found in {filepath}. Check XML structure.")
            return None
        # st.info(f"Successfully loaded prompts from: {filepath}") # Optional debug
        return prompts
    except FileNotFoundError:
        st.error(f"❌ Prompt file not found: {filepath}.")
        st.error(f"Current working directory: {Path.cwd()}")
        st.error(f"Script location (__file__): {__file__}")
        return None
    except ET.ParseError as e:
        st.error(f"❌ Error parsing {filepath}: {e}. Check XML syntax.")
        return None
    except Exception as e:
        st.error(f"❌ Error loading prompts from {filepath}: {e}")
        return None
# --- End Helper Function ---


@st.fragment
def generate_questions_with_images():
    """Generate QTI v2.2 questions based on uploaded images"""
    # Removed imports already at the top
    from pathlib import Path
    import re
    st.subheader(":frame_with_picture: Generate Image based Questions", divider=True)
    with st.container(border=True):
        sel_subj_col, dummy_col, num_quest_col = st.columns([1, 0.1, 2])
        # Step 0: User selects subject
        selected_subject = sel_subj_col.selectbox("Select subject:", ("Biology", "Chemistry", "Physics", "PLTW Medical Interventions"), key="img_subject")
        # Step 1: User selects number of questions
        num_questions = num_quest_col.slider("Number of questions to generate", 1, 10, 3)


    # Question type options
    question_types = ["Multiple choice", "True/False", "Fill in blank", "Matching"]

    # Step 2: Create file uploaders and question type selectors
    uploaded_images = []
    selected_types = []
    image_prompts = []
    assessment_title = ""
    # Create two columns for each question - one for upload, one for type selection
    with st.container(border=True):
        for i in range(num_questions):
            col1, col2 = st.columns([1, 1])
            with col1:
                uploaded_file = st.file_uploader(f"Upload image {i+1}", type=['jpg', 'jpeg', 'png'], key=f"image_{i}")
            with col2:
                # Enable selection only if file is uploaded
                is_disabled = uploaded_file is None
                question_type = st.selectbox(
                    f"Question type for image {i+1}",
                    question_types,
                    index=0,
                    key=f"type_{i}",
                    disabled=is_disabled
                )
                image_prompt_text = st.text_area(
                    f"Prompt/standard for image {i+1}",
                    key=f"prompt_{i}",
                    max_chars=500,
                    height=150,
                    disabled=is_disabled
                )

                if uploaded_file:
                    uploaded_images.append(uploaded_file)
                    selected_types.append(question_type)
                    image_prompts.append(image_prompt_text) # Store the text entered

            st.divider()

    # Filter out entries where no image was uploaded (important for zipping later)
    valid_entries = [(img, stype, iprompt) for img, stype, iprompt in zip(uploaded_images, selected_types, image_prompts) if img is not None]
    num_valid_uploads = len(valid_entries)


    # Step 3: Assessment information
    if num_valid_uploads > 0:
        with st.expander("Assessment Information", expanded=True):
            assessment_title = st.text_input("Assessment Title", value="TeacherAIde Image-based Assessment")
            api_key = st.session_state.get("user_openAIapi_key", None) # Use .get for safety

    # Step 4: Generate button
    gen_but_colL, gen_but_colC, gen_but_colR = st.columns([1, 3, 1])
    generate_clicked = gen_but_colC.button(":frame_with_picture: Generate Image Questions", type="primary", disabled=num_valid_uploads == 0)

    if generate_clicked and num_valid_uploads > 0 and api_key:
        # --- Load Prompts ---
        try:
            script_dir = Path(__file__).parent
            prompts_file_path = (script_dir.parent / "assets" / "prompts" / "image_quest_prompts.xml").resolve()
            # st.write(f"Attempting to load prompts from: {prompts_file_path}") # Debug
            prompts = load_prompts_from_xml(prompts_file_path)
        except Exception as e:
             st.error(f"Error determining prompts file path: {e}")
             prompts = None

        if not prompts:
            st.error("Could not load prompts. Aborting generation.")
            st.stop()
        # --- End Load Prompts ---

        with st.spinner("Generating questions from images..."):
            try:
                yaml_questions = []
                media_files = {}
                message_placeholder = st.empty()
                message_placeholder.text("Preparing to generate questions...")
                client = OpenAI(api_key=api_key)
                type_map = {
                    "Multiple choice": "mcq", "True/False": "tf",
                    "Fill in blank": "fib", "Matching": "match"
                }

                for i, (image, q_type, img_prompt) in enumerate(valid_entries, 1):
                    message_placeholder.text(f"Processing question {i} of {num_valid_uploads}...")
                                                            # Count number of questions by counting "- type:" occurrences
                    progress_cnt = min(i / num_valid_uploads, 1.0)
                    message_placeholder.progress(progress_cnt, f"Generating questions: {i}/{num_valid_uploads}")
                    mapped_type = type_map.get(q_type)
                    prompt_template = prompts.get(mapped_type)

                    if not mapped_type or not prompt_template:
                        st.warning(f"Skipping image {image.name}: No prompt found for type '{mapped_type}'.")
                        continue

                    # Prepare image data
                    image.seek(0)
                    encoded_image = base64.b64encode(image.read()).decode('utf-8')
                    image.seek(0)
                    media_files[image.name] = image.read() # Store raw bytes

                    # Format the instruction (variables should be in scope for f-string)
                    try:
                         # Pass necessary variables to format the template string
                         instruction = prompt_template.format(
                             i=i,
                             selected_subject=selected_subject,
                             # No need to pass image.name to the prompt template itself now
                             img_prompt=img_prompt
                         )
                    except KeyError as e:
                         st.error(f"Missing placeholder {e} in prompt template for type '{mapped_type}'. Check prompts.xml.")
                         continue
                    except Exception as e:
                         st.error(f"Error formatting prompt: {e}")
                         continue

                    model_name = get_config_value("OPENAI_REASON_MODEL", "gpt-4o")
                    # st.write(f"Using model: {model_name}") # Debug
                    # Make the API call
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": "You are a question generator outputting only valid YAML. Do not include ``` markers."},
                            {"role": "user", "content": [
                                {"type": "text", "text": instruction},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}}
                            ]}
                        ],
                        temperature=1
                    )

                    yaml_text = response.choices[0].message.content.strip()

                    # ---- START POST-PROCESSING ----
                    # Define the actual HTML img tag using the correct image name
                    # Ensure HTML characters within the alt text are properly escaped if needed,
                    # but for a simple description, it's often fine.
                    # Use double quotes for HTML attributes for consistency.
                    actual_image_html = f'<p><img src="media/{image.name}" alt="Question related image {i}" width="400"/></p>'

                    # Replace the placeholder in the YAML string.
                    # Need to be careful about quotes used in the YAML. The LLM might use single or double.
                    # Using regex for a more robust replacement of the value associated with question_image:
                    placeholder = "__IMAGE_HTML_PLACEHOLDER__"
                    # Escape the replacement HTML for safe insertion into a YAML string (simple escaping)
                    # YAML strings use ' or ". If HTML contains ', escape it if YAML uses '. If HTML contains ", escape it if YAML uses ".
                    # Let's assume YAML uses double quotes mostly. Escape double quotes in HTML.
                    # html_escaped_for_yaml = actual_image_html.replace('"', '\\"')

                    # # Regex to find `question_image:` followed by a quoted string and replace the string content
                    # # It handles potential variations in spacing and quote types.
                    # yaml_text_updated = re.sub(
                    #     r"(question_image:\s*)(['\"])"+placeholder+r"\2", # Match 'placeholder' or "placeholder"
                    #     rf'\1"{html_escaped_for_yaml}"', # Replace with "escaped_html"
                    #     yaml_text
                    # )

                    # # Fallback simple replace if regex didn't work (e.g., unexpected format)
                    # if placeholder in yaml_text and placeholder not in yaml_text_updated:
                    #      st.warning(f"Regex replacement failed for image {i}, trying simple replace.")
                    yaml_text_updated = yaml_text.replace(f"'{placeholder}'", f"'{actual_image_html}'")
                    yaml_text_updated = yaml_text_updated.replace(f'"{placeholder}"', f'"{actual_image_html}"')

                    # Optional: Check if replacement happened
                    if placeholder in yaml_text_updated:
                         st.warning(f"Placeholder '{placeholder}' still found in YAML for image {i} after replacement attempt. Check LLM output format.")
                         st.code(yaml_text, language='yaml') # Log original yaml

                    yaml_text = yaml_text_updated # Use the updated YAML
                    # ---- END POST-PROCESSING ----


                    # Clean potential markdown fences (though system prompt asks not to use them)
                    if yaml_text.startswith("```yaml"):
                        yaml_text = yaml_text.replace("```yaml", "").replace("```", "").strip()

                    yaml_questions.append(yaml_text)

                    # Show progress
                    current_output = "\n---\n".join(yaml_questions)
                    # message_placeholder.markdown(f"Generated {i} of {num_valid_uploads} questions:\n```yaml\n{current_output}\n```")


                # ... (rest of the code: combine YAML, convert, store, download button) ...
                # Make sure to use the `yaml_questions` list which now contains the *processed* YAML strings

                if not yaml_questions:
                    st.warning("⚠️ No questions were generated or processed successfully.")
                    st.stop()

                combined_yaml = "\n---\n".join(yaml_questions) # Use separator

                # Convert YAML to QTI XML
                try:
                    converter = YAMLtoQTIConverter(templates_dir="templates")
                    xml_questions = converter.convert(combined_yaml)

                    if xml_questions:
                         # ... (Display results, store, create package, download button code) ...
                         # (This part should now work correctly as xml_questions are based on processed YAML)

                        #  with st.expander("View Generated Questions", expanded=False):
                        #     st.write("### Processed YAML (Sent for Conversion):")
                        #     st.code(combined_yaml, language="yaml")

                        #     st.write("### Generated QTI XML:")
                        #     for idx, xml_content in enumerate(xml_questions, 1):
                        #         with st.container(border=True):
                        #             st.subheader(f"Question {idx}")
                        #             st.code(xml_content, language="xml")

                         store_questions(xml_questions, media_files, source_type="image")

                         image_package_data = create_package(
                            test_title=assessment_title,
                            questions=None,   # ,xml_questions
                            media_files=media_files,
                            question_types='image'
                         )
                         # ... (download button logic) ...
                         if image_package_data:
                             st.toast("✅ Questions generated successfully! ")
                             timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                             safe_title = "".join(c if c.isalnum() else "_" for c in assessment_title)
                             quiz_file_name = f"{safe_title}_image_{timestamp}.zip"

                             st.download_button(
                                 label="⬇️ Download Image Questions Only",
                                 data=image_package_data,
                                 file_name=quiz_file_name,
                                 mime="application/zip",
                                 use_container_width=True,
                                 key=f"download_image_{timestamp}" # Unique key for download
                             )
                             st.info("📌 Image questions saved. Review/combine in 'Review & Download'.")
                             # ... (summary) ...
                         else:
                             st.error("❌ Failed to create the download package.")
                    else:
                        st.error("❌ No valid QTI questions were generated after conversion.")
                        st.write("Processed YAML that failed conversion:")
                        st.code(combined_yaml, language="yaml")

                except Exception as e:
                    st.error(f"❌ Error converting YAML to QTI or creating package: {str(e)}")
                    st.write("Processed YAML that caused error:")
                    st.code(combined_yaml, language="yaml")
                    st.exception(e)

            except Exception as e:
                st.error(f"Error during question generation loop: {str(e)}")
                st.exception(e)

    elif generate_clicked and not api_key:
        st.error("🚫 Please enter your OpenAI API key in the settings.")
    elif generate_clicked and num_valid_uploads == 0:
        st.warning("⚠️ Please upload at least one image.")


generate_questions_with_images()