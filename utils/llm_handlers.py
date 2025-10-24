from openai import OpenAI, AsyncOpenAI
from anthropic import Anthropic
import base64
from typing import Optional, Any
import  yaml, os, asyncio
from PIL import Image
from io import BytesIO
import fitz, re
import streamlit as st
from google import genai
from google.genai import types
from prompts.qti_prompts import PromptPrefixGenerator

import uuid


try:
    from streamlit.errors import StreamlitAPIException
except Exception:  # pragma: no cover - streamlit not always available
    StreamlitAPIException = Exception  # type: ignore


def get_config_value(key: str, default: Optional[Any] = None) -> Optional[Any]:
    """Safely retrieve configuration values from the environment or Streamlit secrets."""
    env_value = os.environ.get(key)
    if env_value is not None:
        return env_value

    try:
        secrets = st.secrets  # May raise when secrets are not configured
    except StreamlitAPIException:
        return default
    except Exception:
        return default

    if not secrets:
        return default

    try:
        return secrets.get(key, default)
    except Exception:
        return default


def generate_valid_filename(original_filename: str = None) -> str:
    """Generate a valid filename for Gemini API that only contains allowed characters."""
    # Create a base name using uuid
    base_name = str(uuid.uuid4())[:8].lower()
    
    # Get extension if exists, ensure it's lowercase and alphanumeric
    if original_filename and '.' in original_filename:
        ext = original_filename.split('.')[-1].lower()
        # Remove any non-alphanumeric characters from extension
        ext = re.sub(r'[^a-z0-9]', '', ext)
        if ext:
            return f"file-{base_name}-{ext}"
    
    # Return just the base name if no valid extension
    return f"file-{base_name}"

def sanitize_file(file_obj, valid_name):
    import io
    """Wrap the file content in a BytesIO object and set a valid name."""
    file_obj.seek(0)  # Ensure we're at the start
    content = file_obj.read()
    new_file_obj = io.BytesIO(content)
    new_file_obj.name = valid_name
    file_obj.seek(0)
    return new_file_obj

def get_pdf_for_gemini(pdf_data: bytes) -> str:
    import pathlib

# @st.fragment
# def generate_reading_material_Gemini_old(pdf_material, grade_level, subject):
#     """Uploads files to Gemini and transcribes medical reports."""
#     # client = genai.Client(api_key=api_key_gemini)
#     # uploaded_files = []
    
#     # Upload each file if it exists
#     # for i, file in enumerate([path1, path2, path3], 1):
#     #     if file is not None:
#     #         # Generate valid filename
#     #         valid_name = generate_valid_filename(
#     #             file.name if hasattr(file, 'name') else None
#     #         )
            
#     #         config = {
#     #             "mime_type": mime_type,
#     #             "name": valid_name
#     #         }
            
#     #         # Sanitize the file object so its name attribute is valid
#     #         # file_to_upload = sanitize_file(file, valid_name)
#     #         # st.image(file)
#     #         try:
#     #             # st.write("Valid name:", valid_name)

#     #             # debug_bytes = file_to_upload.read(20)
#     #             # st.write("First 20 bytes:", repr(debug_bytes))
#     #             # file_to_upload.seek(0)

#     #             uploaded_file = client.files.upload(path=file, config=config)
#     #             # st.text("File type uploaded_file: " + str(type(uploaded_file)))
#     #             # file_to_upload.seek(0)
#     #             uploaded_files.append(uploaded_file)
#     #         except Exception as e:
#     #             # st.write(CreateFileRequest.file.name)
#     #             st.error(f"Fayl {i} yüklənməsində xəta: {str(e)}")
#     #             st.stop()
                
#     gemini_model="gemini-2.0-flash-exp"
#     api_key_gemini=os.environ["GEMINI_API_KEY"]
#     client = genai.Client(api_key=api_key_gemini)
#     # Skip processing if no files were uploaded
#     # if not uploaded_files:
#     #     raise ValueError("Analiz üçün heç bir fayl təqdim edilməyib")
#     import tempfile
#     # If pdf_material is a BytesIO object, write it to a temporary file
#     if isinstance(pdf_material, BytesIO):
#         with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
#             tmp_file.write(pdf_material.getvalue())
#             tmp_file_path = tmp_file.name
#     else:
#         tmp_file_path = pdf_material  # Assume it's already a valid path
    
#     sample_doc = client.files.upload(
#         path=tmp_file_path,
#         config=dict(mime_type='application/pdf')
#     )
    
#     # Clean up temporary file if it was created
#     if isinstance(pdf_material, BytesIO):
#         os.remove(tmp_file_path)

#     # Create the model config
#     config_types = types.GenerateContentConfig(
#         system_instruction="""You are a useful and very skilled OCR reader who transcribes
#         provided pdf file into text format. Then you will generate a textbook format chapter based on the content of the pdf file.""",
#         temperature=1,
#         top_p=0.95,
#         top_k=40,
#         max_output_tokens=8192,
#         response_mime_type="text/plain",
#         safety_settings=[types.SafetySetting(
#                 category="HARM_CATEGORY_HATE_SPEECH",
#                 threshold="BLOCK_ONLY_HIGH",
#             )
#         ]
#     )
  
#     # Prepare the contents list with the prompt and files
#     user_prompt =f"""Perform OCR on the attached PDF file and transcribe the content into text format.
#         Then convert the text into a textbook format chapter based on the content of the PDF file.
#         Describe images you see in square brackets like [image1:description1], [image2:description2], etc.
#         The target audience for the textbook is students in {grade_level} studying {subject}."""
  
    

#     # sample_doc = client.files.upload(
#     # # You can pass a path or a file-like object here
#     # path=pdf_material, 
#     # config=dict(mime_type='application/pdf'))


#     # Generate content with uploaded files
#     gemini_response = client.models.generate_content(
#         model=gemini_model,
#         contents= [
#             {"parts": [{"data": sample_doc.name}]},
#             {"parts": [{"data": user_prompt}]}
#         ],
#         config=config_types,
#     )

#     return gemini_response

# #MAIN WORKING ONE
# @st.fragment
# def generate_reading_material_Gemini(pdf_material, grade_level, subject, target_no_pages, difficulty_level):
#     """Uploads a PDF to Gemini and generates reading material."""
#     import os

#     gemini_model = os.environ["GEMINI_MODEL"] #"gemini-2.0-flash"
#     api_key_gemini = os.environ["GEMINI_API_KEY"]
#     client = genai.Client(api_key=api_key_gemini)

#     # Read PDF bytes from the BytesIO object or a file path
#     if isinstance(pdf_material, BytesIO):
#         pdf_bytes = pdf_material.getvalue()
#     else:
#         with open(pdf_material, "rb") as f:
#             pdf_bytes = f.read()

#     # Create the model config
#     config_types = types.GenerateContentConfig(
#         system_instruction=f"""You are a useful and very skilled OCR reader who transcribes
# provided pdf file into text format. Also, you are a teacher in {subject} in {grade_level} grade of high school.
# You will generate a textbook format chapter based on the content of the pdf file you transcibe.""",
#         temperature=1,
#         top_p=0.95,
#         top_k=40,
#         max_output_tokens=8192,
#         response_mime_type="text/plain",
#         safety_settings=[types.SafetySetting(
#             category="HARM_CATEGORY_HATE_SPEECH",
#             threshold="BLOCK_ONLY_HIGH",
#         )]
#     )

#     # Prepare the prompt as text     E.g. instead of "\(\frac{'m_1g'}\)' write "(\frac{'m_1g'})
#     user_prompt = f"""Perform OCR on the attached PDF file and transcribe the content into text format.
#     Describe images you see in square brackets like [image1:description1], [image2:description2], etc to use them as part of the source material to craft your final output.
#     Then convert the text into a textbook format chapter based on the content of the PDF file.
#     Use real life examples to explain concepts. Use analogies to explain difficult concepts.
#     Encode ALL LaTeX or other math equations, special formulas, chemical formulas in RENDERABLE STANDARD LaTeX FORMAT.
#     IN LaTex format, DO NOT put forward slashes before the first and last parenthesises. 
#     IN YOUR OUTPUT REDRAW THE IMAGES YOU SEE IN THE MATERIAL.
#     The target audience for the textbook is students in {grade_level} studying {subject}. 
#     LIMIT YOUR RESPONSE TO {target_no_pages} and the DIFFICULTY LEVEL SHOULD BE {difficulty_level}. 
#     DO NOT REITERATE MY INSTRUCTIONS, JUST FOLLOW THEM STRICTLY."""

#     # Generate content with the PDF as a bytes part and the prompt as text
#     gemini_response = client.models.generate_content(
#         model=gemini_model,
#         contents=[
#             types.Part.from_bytes(
#                 data=pdf_bytes,
#                 mime_type='application/pdf'
#             ),
#             user_prompt
#         ],
#         config=config_types,
#     )

#     return gemini_response.text


@st.fragment
def generate_reading_material_Gemini(pdf_material, grade_level, subject, target_no_pages, difficulty_level,reading_material_container):
    """Uploads a PDF to Gemini and generates reading material with images."""
    import os
    import mimetypes
    from pathlib import Path
    from io import BytesIO
    import base64
    
    # Initialize session state for storing content
    if 'pdf_bytes' not in st.session_state:
        st.session_state.pdf_bytes = None
    
    if 'markdown_content' not in st.session_state:
        st.session_state.markdown_content = ""
    
    def ensure_image_directory():
        """Create images directory if it doesn't exist"""
        image_dir = Path("images")
        image_dir.mkdir(exist_ok=True)
        return image_dir
    
    def image_to_base64(image_path):
        """Convert image to base64 string"""
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    
    # Setup API client
    api_key_gemini=""
    image_gen_model=""
    text_model=""
    try:
        api_key_gemini = get_config_value("GEMINI_API_KEY")
        image_gen_model = get_config_value("GEMINI_IMAGE_MODEL", "gemini-2.0-flash-exp-image-generation")
        text_model = get_config_value("GEMINI_MODEL", "gemini-2.0-flash")  # Text-only model for initial analysis
    except Exception as e:
        reading_material_container.error(f"Unexpected error loading variables. Try again or contact support.")
        st.stop()
        return

    if not api_key_gemini:
        reading_material_container.error("Gemini API key not configured. Please set GEMINI_API_KEY in your environment or Streamlit secrets.")
        st.stop()
        return

    gemini_client = genai.Client(api_key=api_key_gemini)
    # Read PDF bytes from the BytesIO object or a file path
    if isinstance(pdf_material, BytesIO):
        pdf_bytes = pdf_material.getvalue()
    else:
        with open(pdf_material, "rb") as f:
            pdf_bytes = f.read()
    
    # Ensure image directory exists
    image_dir = ensure_image_directory()
    
    # Create containers for display
    # status = st.empty()
    # output_container = st.container()

    reading_material_container.info("Analyzing PDF and extracting content. Please wait...")
    
    # First, analyze the PDF using the text model (with system instruction support)
    config_types = types.GenerateContentConfig(
        system_instruction=f"""You are a useful and very skilled OCR reader who transcribes
provided pdf file into text format. Also, you are a teacher in {subject} in {grade_level} grade of high school.
You will generate a textbook format chapter based on the content of the pdf file you transcribe.""",
        temperature=1,
        top_p=0.95,
        top_k=40,
        max_output_tokens=8192,
        response_mime_type="text/plain",
        safety_settings=[types.SafetySetting(
            category="HARM_CATEGORY_HATE_SPEECH",
            threshold="BLOCK_ONLY_HIGH",
        )]
    )
    
    # Prepare the prompt for PDF analysis
    analysis_prompt = f"""Perform OCR on the attached PDF file and transcribe the content into text format.
    Describe images you see in square brackets like [image1:description1], [image2:description2], etc.
    Extract the main educational concepts that will need illustration later."""
    
    try:
        # First, analyze the PDF content using the text model
        pdf_analysis = gemini_client.models.generate_content(
            model=text_model,
            contents=[
                types.Part.from_bytes(
                    data=pdf_bytes,
                    mime_type='application/pdf'
                ),
                analysis_prompt
            ],
            config=config_types,
        )
        
        extracted_content = pdf_analysis.text
        
        # Create a list of key concepts for illustration
        reading_material_container.info("Generating illustrated educational material...")
        
        # Now use the image generation model to create the educational content with images
        markdown_text = ""
        image_counter = 0
        
        # Create content generation config for the image model
        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
            response_modalities=["image", "text"],
            safety_settings=[
                types.SafetySetting(
                    category="HARM_CATEGORY_HATE_SPEECH",
                    threshold="BLOCK_ONLY_HIGH",
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_CIVIC_INTEGRITY",
                    threshold="BLOCK_ONLY_HIGH",
                )
            ],
            response_mime_type="text/plain",
        )
        
        # Create the prompt for the image generation model
        image_gen_prompt = f"""Create an illustrated textbook chapter based on this content:
        
        {extracted_content}
        
        Format this as a textbook chapter for {grade_level} students studying {subject}.
        The difficulty level should be {difficulty_level}.
        Limit your response to about {target_no_pages} pages.
        
        For each major concept, generate an appropriate educational illustration.
        Use real-life examples and analogies to explain difficult concepts.
        Format all math equations, chemical formulas, and special notations in proper LaTeX.
        """
        
        # Process the stream of generated content with the image model
        content_stream = gemini_client.models.generate_content_stream(
            model=image_gen_model,
            contents=[types.Content(
                role="user",
                parts=[types.Part.from_text(text=image_gen_prompt)]
            )],
            config=generate_content_config,
        )
        
        # Process the stream of generated content
        for chunk in content_stream:
            if not chunk.candidates or not chunk.candidates[0].content or not chunk.candidates[0].content.parts:
                continue
            
            # Handle image content
            part = chunk.candidates[0].content.parts[0]
            if hasattr(part, 'inline_data') and part.inline_data:
                image_counter += 1
                inline_data = part.inline_data
                mime_type = inline_data.mime_type
                file_extension = mimetypes.guess_extension(mime_type) or '.jpg'
                
                # Save the image file
                file_name = f"image{image_counter}{file_extension}"
                file_path = str(image_dir / file_name)
                
                with open(file_path, "wb") as f:
                    f.write(inline_data.data)
                
                # Generate base64 version of the image for markdown
                img_base64 = image_to_base64(file_path)
                
                # Add image to markdown as embedded base64 for PDF
                markdown_text += f"\n\n![Image {image_counter}](data:{mime_type};base64,{img_base64})\n\n"
                
                # Display in Streamlit with scrollable container
                # with output_container:
                reading_material_container.markdown(f"""
                    <style>.scrollable-container {"""max-height: 500px;overflow-y: auto;"""}</style>
                    <div class="scrollable-container">
                     {reading_material_container.image(file_path, caption=f"Generated Image {image_counter}")}       
                    </div>
                """, unsafe_allow_html=True)
                reading_material_container.info(f"Generated image {image_counter}...")
            # Handle text content with scrollable container
            elif hasattr(chunk, 'text') and chunk.text:
                text = chunk.text
                markdown_text += text
                # with output_container:
                reading_material_container.markdown(f"""
                    <style>
                            {"""
                            max-height: 400px;
                            overflow-y: auto;
                        """}
                    </style> {text}
                """, unsafe_allow_html=True)
                # reading_material_container.write(text)
        
        # Update session state with generated content
        st.session_state.markdown_content = markdown_text
        
        return markdown_text
    
    except Exception as e:
        reading_material_container.error(f"Error generating content: {str(e)}")
        return f"An error occurred: {str(e)}"


def ensure_image_directory():
    """Create images directory if it doesn't exist"""
    from pathlib import Path
    image_dir = Path("images")
    image_dir.mkdir(exist_ok=True)
    return image_dir

def image_to_base64(image_path):
    """Convert image to base64 string"""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

def generate_streamlit():
    """
    Streamlit adaptation of the generate() function for creating stories with images
    and saving them as a PDF
    """
    import mimetypes
    # Set default prompt or let user customize
    default_prompt = "Generate a story about a cute baby turtle in a 3d digital art style. For each scene, generate an image."
    prompt = st.text_area("Enter your prompt:", default_prompt, height=100)
    
    # Initialize session state for storing content
    if 'pdf_bytes' not in st.session_state:
        st.session_state.pdf_bytes = None
    
    if 'markdown_content' not in st.session_state:
        st.session_state.markdown_content = ""
    
    api_key_gemini = get_config_value("GEMINI_API_KEY")
    if not api_key_gemini:
        st.error("Gemini API key not configured. Please set GEMINI_API_KEY in your environment or Streamlit secrets.")
        st.stop()
        return

    client = genai.Client(api_key=api_key_gemini)
    model = get_config_value("GEMINI_IMAGE_MODEL", "gemini-2.0-flash-exp-image-generation")
    
    # Ensure image directory exists
    image_dir = ensure_image_directory()
    
    # Create containers for display
    status = st.empty()
    output_container = st.container()
    
    status.info("Generating content. Please wait...")
    
    # Initialize counters and content storage
    cnt = 0
    markdown_text = ""
    
    # Create content generation request
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)],
        ),
    ]
    
    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        top_p=0.95,
        top_k=40,
        max_output_tokens=8192,
        response_modalities=["image", "text"],
        safety_settings=[
            types.SafetySetting(
                category="HARM_CATEGORY_CIVIC_INTEGRITY",
                threshold="OFF",
            ),
        ],
        response_mime_type="text/plain",
    )
    
    # Process the stream of generated content
    try:
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if not chunk.candidates or not chunk.candidates[0].content or not chunk.candidates[0].content.parts:
                continue
            
            # Handle image content
            if chunk.candidates[0].content.parts[0].inline_data:
                cnt += 1
                inline_data = chunk.candidates[0].content.parts[0].inline_data
                mime_type = inline_data.mime_type
                file_extension = mimetypes.guess_extension(mime_type) or '.jpg'
                
                # Save the image file
                file_name = f"image{cnt}{file_extension}"
                file_path = str(image_dir / file_name)
                
                with open(file_path, "wb") as f:
                    f.write(inline_data.data)
                
                # Generate base64 version of the image for markdown
                img_base64 = image_to_base64(file_path)
                
                # Add image to markdown as embedded base64 for PDF
                markdown_text += f"\n\n![Image {cnt}](data:{mime_type};base64,{img_base64})\n\n"
                
                # Display in Streamlit
                with output_container:
                    st.image(file_path, caption=f"Generated Image {cnt}")
                
                status.info(f"Generated image {cnt}...")
                
            # Handle text content
            else:
                text = chunk.text
                if text:
                    markdown_text += text
                    with output_container:
                        st.write(text)
        
        # Update session state with generated content
        st.session_state.markdown_content = markdown_text
        # Clear status when complete
        status.empty()
    except Exception as e:
        st.error(f"Error generating content: {str(e)}")


def get_size_mb(data: str) -> float:
    """Get size of string data in MB"""
    return len(data.encode('utf-8')) / (1024 * 1024)

def compress_pdf_data(pdf_data: str, max_size_mb: int = 2) -> str:
    """Compress PDF data while maintaining readability"""
    try:
        st.write(f"Original PDF size: {get_size_mb(pdf_data):.2f} MB")
        
        # Decode base64 PDF data
        pdf_bytes = base64.b64decode(pdf_data)
        pdf_stream = BytesIO(pdf_bytes)
        
        st.write(f"Decoded PDF stream size: {len(pdf_bytes) / (1024 * 1024):.2f} MB")
        
        # Open PDF with PyMuPDF
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        st.write(f"PDF pages: {doc.page_count}")
        
        # Create new PDF for compressed output
        out_stream = BytesIO()
        out_doc = fitz.open()
        
        # Determine compression ratio based on size
        scale = 1.0
        if get_size_mb(pdf_data) > max_size_mb:
            scale = 0.5  # Reduce quality for large PDFs
            
        st.write(f"Using scale factor: {scale}")
        
        # Process only first few pages if document is too large
        max_pages = min(doc.page_count, 5)  # Limit to 5 pages
        status_text = st.empty()
        status_text.write(f"Processing {max_pages} pages")
        
        progress_bar = st.progress(0)
        for page_num in range(max_pages):
            page = doc[page_num]
            # Convert page to lower resolution image
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
            new_page = out_doc.new_page(width=pix.width, height=pix.height)
            new_page.insert_image(new_page.rect, stream=pix.tobytes())
            progress = (page_num + 1) / max_pages
            progress_bar.progress(progress)
            status_text.write(f"Processed page {page_num + 1}/{max_pages}")
            
        # Save with maximum compression
        out_stream = BytesIO()
        out_doc.save(out_stream, 
                    garbage=4,     # Maximum garbage collection
                    deflate=True,  # Use deflate compression
                    ascii=False,   # Allow binary content
                    linear=False)  # Non-linear PDF to save space
        
        # Clean up
        out_doc.close()
        doc.close()
        
        # Convert back to base64
        compressed_data = base64.b64encode(out_stream.getvalue()).decode('utf-8')
        st.write(f"Compressed PDF size: {get_size_mb(compressed_data):.2f} MB")
        
        return compressed_data
        
    except Exception as e:
        st.error(f"PDF compression error: {str(e)}")
        raise

def split_prompt_into_chunks(prompt: str, max_length: int = 4000) -> list:
    """Split prompt into manageable chunks"""
    chunks = []
    current_chunk = []
    current_length = 0
    
    # Split by sentences to maintain context
    sentences = re.split(r'(?<=[.!?])\s+', prompt)
    
    for sentence in sentences:
        sentence_length = len(sentence)
        if current_length + sentence_length > max_length:
            if current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_length
            else:
                # If single sentence is too long, split by words
                words = sentence.split()
                while words:
                    chunk = []
                    chunk_length = 0
                    while words and chunk_length + len(words[0]) + 1 <= max_length:
                        word = words.pop(0)
                        chunk.append(word)
                        chunk_length += len(word) + 1
                    chunks.append(' '.join(chunk))
        else:
            current_chunk.append(sentence)
            current_length += sentence_length + 1
            
    if current_chunk:
        chunks.append(' '.join(current_chunk))
        
    return chunks

def compress_image(image_str: str, max_size_kb: int = 500) -> str:
    """Compress base64 encoded image if it's too large"""
    try:
        # Decode base64 image
        img_data = base64.b64decode(image_str)
        img = Image.open(BytesIO(img_data))
        
        # Calculate current size in KB
        current_size = len(img_data) / 1024
        
        if current_size > max_size_kb:
            # Calculate compression ratio
            ratio = (max_size_kb / current_size) ** 0.5
            
            # Resize image maintaining aspect ratio
            new_size = tuple(int(dim * ratio) for dim in img.size)
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Save compressed image
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=85, optimize=True)
            compressed_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return compressed_str
            
        return image_str
        
    except Exception as e:
        raise Exception(f"Error compressing image: {str(e)}")
    
def fix_yaml_format(yaml_str: str) -> str:
    """Fix common YAML formatting issues"""
    # Remove any markdown code block markers
    yaml_str = yaml_str.replace('```yaml', '').replace('```', '')
    
    # Remove any explanatory text before the YAML content
    if not yaml_str.strip().startswith('- type:'):
        parts = yaml_str.split('---\n')
        yaml_str = parts[-1].strip()
    
    # Ensure proper list formatting
    if not yaml_str.startswith('- '):
        yaml_str = '- ' + yaml_str
    
    return yaml_str

def validate_yaml_response(yaml_str: str, chunk_size: int = 50000) -> bool:
    """Validate that YAML response meets specific structure and content requirements."""
    try:
        # Handle large YAML strings in chunks
        if len(yaml_str) > chunk_size:
            chunks = [yaml_str[i:i+chunk_size] for i in range(0, len(yaml_str), chunk_size)]
            return all(validate_yaml_response(chunk, chunk_size) for chunk in chunks)

        # Parse YAML with safe_load
        questions = yaml.safe_load(yaml_str)
        if not isinstance(questions, list):
            return False
            
        # Validate each question
        for q in questions:
            if not isinstance(q, dict):
                return False
            
            # Required base fields
            if not {'type', 'identifier', 'title', 'prompt'}.issubset(q.keys()):
                return False
            
            # Validate by question type
            type_validators = {
                'mcq': lambda x: validate_mcq(x),
                'mrq': lambda x: validate_mrq(x),
                'tf': lambda x: validate_tf(x),
                'match': lambda x: validate_match(x),
                'fib': lambda x: validate_fib(x),
                'highlight_text': lambda x: validate_highlight_text(x),
                'numeric': lambda x: validate_numeric(x),
                'order': lambda x: validate_order(x),
                'essay': lambda x: validate_essay(x),
                'upload': lambda x: validate_upload(x),
                'label_image': lambda x: validate_label_image(x),
                'highlight_image': lambda x: validate_highlight_image(x)
            }
            
            if q['type'] not in type_validators or not type_validators[q['type']](q):
                return False
                
        return True
        
    except yaml.YAMLError:
        return False
    except Exception:
        return False

def validate_mcq(q: dict) -> bool:
    return (isinstance(q.get('choices'), list) and 
            any(choice.get('correct', False) for choice in q['choices']) and 
            isinstance(q.get('shuffle', True), bool))

def validate_mrq(q: dict) -> bool:
    return validate_mcq(q)  # Same validation rules as MCQ

def validate_tf(q: dict) -> bool:
    return isinstance(q.get('correct'), bool)

def validate_match(q: dict) -> bool:
    match_sets = q.get('matchSets', {})
    return (isinstance(match_sets, dict) and
            all(isinstance(match_sets.get(key, []), list) for key in ['source', 'target']) and
            isinstance(q.get('correctPairs'), list) and
            isinstance(q.get('shuffle', True), bool))

def validate_fib(q: dict) -> bool:
    return (('correctAnswer' in q or isinstance(q.get('correctAnswers'), list)) and
            isinstance(q.get('expectedLength', 10), int))

def validate_numeric(q: dict) -> bool:
    return (('correctAnswer' in q or 'correctResponse' in q) and
            isinstance(q.get('tolerance', 0), (int, float)) and
            isinstance(q.get('expectedLength', 10), int))

def validate_order(q: dict) -> bool:
    return (isinstance(q.get('choices'), list) and
            isinstance(q.get('correctSequence'), list) and
            isinstance(q.get('shuffle', True), bool))

def validate_essay(q: dict) -> bool:
    return all(isinstance(q.get(field, 0), int) for field in ['expectedLength', 'expectedLines'])


def validate_highlight_text(q: dict) -> bool:
    return (isinstance(q.get('text'), list) and
            isinstance(q.get('correctHighlights'), list) and
            isinstance(q.get('maxSelections', 0), int))


def validate_upload(q: dict) -> bool:
    return (isinstance(q.get('maxSize', 0), int) and
            (not q.get('allowedTypes') or isinstance(q.get('allowedTypes'), list)))

def validate_label_image(q: dict) -> bool:
    return (isinstance(q.get('correctPairs'), list) and
            isinstance(q.get('image'), str) and
            isinstance(q.get('labels'), list) and
            isinstance(q.get('targets'), list))

def validate_highlight_image(q: dict) -> bool:
    return (isinstance(q.get('image'), str) and
            isinstance(q.get('hotspots'), list) and
            isinstance(q.get('correctHotspots'), list))

 
async def generate_openai_response(prompt: str, total_questions:int, api_key: str, pdf_content, #encoded_images: List[str], 
                           message_placeholder, model: str = "o4-mini") -> Optional[str]:
    """Generate YAML formatted response using OpenAI API with streaming output"""
    try:
        # Initialize the OpenAI client
        client = AsyncOpenAI(api_key=api_key)
        # Prepare the messages with both text prompt and PDF images
        model = get_config_value("OPENAI_REASON_MODEL", model)

        system_prompt = PromptPrefixGenerator.get_system_prompt()
        # messages = [{"role": "system","content": system_prompt},
        #     {"role": "user","content": [{
        #             "type": "file",
        #             "file": {"filename": "teacheraide.pdf",
        #                 "file_data": f"data:application/pdf;base64,{pdf_content}",}
        #         },
        #         {"type": "text", "text": prompt}
        #         ]}]
        input_text = [
             {"role": "user", "content": [{"type": "input_text","text": prompt}, 
                                          {"type": "input_file","filename": "teacheraide.pdf",
                                           "file_data": f"data:application/pdf;base64,{pdf_content}"}]},
                    ]
        # Add encoded images to the messages
        # for img_str in encoded_images:
        #     messages[1]["content"].append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_str}" } })

        # Initialize response collection
        full_response = []
        displayed_response = ""
        questions_count = 0
        # Call the OpenAI API with streaming

        #stream = client.chat.completions.create(model=model, messages=messages,  max_completion_tokens=16384,  stream=True, store=True)
        # Process the stream
        # current_chunk = ""
        # for chunk in stream:
        #     if chunk.choices[0].delta.content is not None:
        #         text_chunk = chunk.choices[0].delta.content
        #         full_response.append(text_chunk)
        #         displayed_response += text_chunk
                
        #         # Count number of questions by counting "- type:" occurrences
        #         questions_count = displayed_response.count("- type:")
        #         progress_cnt = min(questions_count / total_questions, 1.0)
                
        #         # Update the progress bar and displayed response
        #         message_placeholder.progress(progress_cnt, f" Generating questions: {questions_count}/{total_questions}")
        #         # message_placeholder.code(displayed_response, language="yaml")

        stream = await client.responses.create(model=model,reasoning={"effort": "high"}, 
                                         instructions=system_prompt, input=input_text, max_output_tokens=16384,  
                                         stream=True, store=True)
        async for event in stream:
        # st.write(event)
            # if event.type =="response.created":
            #     st.write('Response created')
            # elif event.type == "response.in_progress":
            #     st.write('Response in_progress')
            # elif event.type == "response.output_item.added":
            #     st.write('Response output item added')
            # elif event.type == "response.content_part.added":
            #     st.write('Response content_part added')
            # elif 
            if event.type =="response.output_text.delta":
                displayed_response += event.delta 
                questions_count = displayed_response.count("- type:")
                progress_cnt = min(questions_count / total_questions, 1.0)
                message_placeholder.progress(progress_cnt, f" Generating questions: {questions_count}/{total_questions}")
                full_response.append(event.delta)   
            elif event.type == "response.completed":
                yaml_response = "".join(full_response).strip()

        # Clear progress bar when complete
        # message_placeholder.empty()
        # yaml_response = "".join(full_response).strip()
        return yaml_response
    except Exception as e:
        raise Exception(f"OpenAI API error: {str(e)}")

def anthropic_count_tokens(prompt: str, pdf_content: str, api_key: str,model: str = "claude-3-7-sonnet-latest") -> Optional[str]:
    resolved_api_key = api_key or get_config_value("CLAUDE_API_KEY")
    if not resolved_api_key:
        raise ValueError("Anthropic API key not configured.")

    client = Anthropic(api_key=resolved_api_key)
    resolved_model = get_config_value("ANTHROPIC_REASON_MODEL", model)
    response = client.beta.messages.count_tokens(
        betas=["token-counting-2024-11-01", "pdfs-2024-09-25"],
        model=resolved_model,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_content
                    }
                },
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }]
    )
    return response.model_dump_json()

def generate_anthropic_response(prompt: str, pdf_content: str, api_key: str,
                              model: str = "claude-3-7-sonnet-latest") -> Optional[str]:
    """Generate YAML formatted response using Anthropic API"""
    try:
        debug_container = st.expander("Debug Information", expanded=True)
        with debug_container:
            st.write("=== Starting Anthropic API Request ===")
            resolved_api_key = api_key or get_config_value("CLAUDE_API_KEY")
            if not resolved_api_key:
                st.error("Anthropic API key not configured. Please set CLAUDE_API_KEY in your environment or Streamlit secrets.")
                return None
            # Initialize the Anthropic client
            client = Anthropic(api_key=resolved_api_key)

            from prompts.qti_prompts import PromptPrefixGenerator
            system_prompt = PromptPrefixGenerator.get_system_prompt()

            system_message=[{"type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"}}]
            # Create message
            message = [{"role": "user",
                "content": [{"type": "document",
                             "source": {"type": "base64","media_type": "application/pdf","data": pdf_content}, 
                             "cache_control": {"type": "ephemeral"} },
                    {"type": "text", "text": prompt, "cache_control": {"type": "ephemeral"}} ] 
            }]
            
            st.write("Making API call to Anthropic...")
            st.text_area("System Prompt:", system_prompt, height=200)
            st.text_area("Prompt:", prompt, height=200)
            # Make the API call
            resolved_model = get_config_value("ANTHROPIC_REASON_MODEL", model)
            response = client.messages.create(
                system=system_message,
                model=resolved_model,
                max_tokens=8192,
                messages=message,
                temperature=0.7
            )
            
            # Get the raw response
            raw_response = response.content[0].text.strip()
            
            # Display raw response
            st.write("\n=== Raw Response ===")
            st.code(raw_response, language="yaml")
            
            # Validate the raw response first
            # try:
            #     parsed_yaml = yaml.safe_load(raw_response)
            #     st.success("✓ Valid YAML structure received")
                
            #     # Basic validation of content
            #     if isinstance(parsed_yaml, list):
            #         valid = True
            #         for item in parsed_yaml:
            #             if not all(key in item for key in ['type', 'identifier', 'title', 'prompt']):
            #                 valid = False
            #                 missing = set(['type', 'identifier', 'title', 'prompt']) - set(item.keys())
            #                 st.error(f"Missing required fields: {missing}")
            #                 break
                    
            #         if valid:
            #             st.success("✓ All required fields present")
            #             return raw_response  # Return the raw response as it's already valid
            #         else:
            #             raise ValueError("Missing required fields in YAML structure")
            #     else:
            #         raise ValueError("YAML must be a list of questions")
                
            # except yaml.YAMLError as e:
            #     st.error(f"Invalid YAML received: {str(e)}")
            #     raise
            # except Exception as e:
            #     st.error(f"Validation error: {str(e)}")
            #     raise
            return raw_response
    except Exception as e:
        st.error(f"Anthropic API error: {str(e)}")
        raise

def process_pdf_for_llm(pdf_data: bytes) -> str:
    """Process PDF data for LLM consumption"""
    return base64.b64encode(pdf_data).decode('utf-8')


# def generate_hlt_lesson_prep_openai_streaming(
#         prompt: str, aimed_output: str, source_content: str, 
#         api_key: str, encoded_images: List[str], 
#         model: str = "gpt-4o"):
#     """Generate content using OpenAI API with streaming output to text area."""
#     try:
#         client = OpenAI(api_key=api_key)

#         messages = [
#             {"role": "system", "content": f"You are an educator generating {aimed_output} based on the provided {source_content}."},
#             {"role": "user", "content": [{"type": "text", "text": prompt}]}
#         ]
#         model = os.environ.get("OPENAI_MODEL", st.secrets.get("OPENAI_MODEL"))

#         for img_str in encoded_images:
#             messages[1]["content"].append({
#                 "type": "image_url",
#                 "image_url": {"url": f"data:image/jpeg;base64,{img_str}"}
#             })

#         response_content = ""
#         stream = client.chat.completions.create(
#             model=model,
#             messages=messages,
#             temperature=0.7,
#             max_tokens=16384,
#             stream=True
#         )

#         # Create a new placeholder for streaming updates
#         stream_placeholder = st.empty()

#         for chunk in stream:
#             if chunk.choices[0].delta.content:
#                 response_content += chunk.choices[0].delta.content
#                 # Update the streaming content
#                 stream_placeholder.text_area(
#                     f"Generated {aimed_output}:",
#                     value=response_content,
#                     height=400
#                 )

#         return response_content

#     except Exception as e:
#         st.error(f"OpenAI API error: {str(e)}")
#         return None



def generate_hlt_lesson_prep_openai_streaming(
        prompt: str, aimed_output: str, source_content, pdf_content, 
        api_key: str, model: str = "o4-mini"):
    """Generate content using OpenAI API with streaming output to text area."""
    try:
        client = OpenAI(api_key=api_key)
        model = get_config_value("OPENAI_REASON_MODEL", model)
        messages = [
            {"role": "system", "content": f"You are an educator generating {aimed_output} based on the provided {source_content}."},
            {"role": "user","content": [{
                    "type": "file",
                    "file": {"filename": "teacheraide.pdf",
                        "file_data": f"data:application/pdf;base64,{pdf_content}",}
                },
                {"type": "text", "text": prompt}
                ]}
        ]


        response_content = ""
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            max_completion_tokens=16384,
            stream=True,
            store=True
        )

        # Create a new placeholder for streaming updates
        stream_placeholder = st.empty()

        for chunk in stream:
            if chunk.choices[0].delta.content:
                response_content += chunk.choices[0].delta.content
                # Update the streaming content
                stream_placeholder.text_area(
                    f"Generated {aimed_output}:",
                    value=response_content,
                    height=400
                )

        return response_content

    except Exception as e:
        st.error(f"OpenAI API error: {str(e)}")
        return None




def generate_hlt_lesson_prep_anthropic_streaming(prompt: str, aimed_output: str, source_content: str, 
        api_key: str, pdf_content: str, 
        model: str = "claude-3-7-sonnet-latest"):
    """Generate content using Anthropic API with streaming output to text area."""
    try:
        # Initialize the Anthropic client
        resolved_api_key = api_key or get_config_value("CLAUDE_API_KEY")
        if not resolved_api_key:
            st.error("Anthropic API key not configured. Please set CLAUDE_API_KEY in your environment or Streamlit secrets.")
            return None

        client = Anthropic(
            api_key=resolved_api_key,
            default_headers={"anthropic-beta": "pdfs-2024-09-25,prompt-caching-2024-07-31"}
        )

        # Create a new placeholder for streaming updates
        stream_placeholder = st.empty()
        response_content = ""

        # Make the API call with system message and correct format
        resolved_model = get_config_value("ANTHROPIC_REASON_MODEL", model)
        with client.messages.stream(
            model=resolved_model,
            system=f"You are an educator generating {aimed_output} based on the provided {source_content}. Be thorough and specific in your response.",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_content
                        },
                        "cache_control": {
                            "type": "ephemeral"
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }],
            max_tokens=8192,
            temperature=0.7
        ) as stream:
            for text in stream.text_stream:
                response_content += text
                # Update the streaming content
                stream_placeholder.text_area(
                    f"Generated {aimed_output}:", 
                    value=response_content,
                    height=400
                )

        return response_content
    except Exception as e:
        st.error(f"Anthropic API error: {str(e)}")
        raise
# Function to handle the Streamlit page for lesson prep



def generate_reading_material_anthropic(pdfs_array, grade_level, subject, api_key: str, model_name: str = "claude-3-7-sonnet-latest"):
    """Processes raw text information with Claude to create a comprehensive reading material.

    Args:
        raw_info (str): The raw text content extracted from web pages.
        grade_level (str): The target grade level for the reading material.
        subject (str): The subject of the reading material.

    Returns:
        str: The generated reading material in HTML format.
    """
    prompt = f"""Read the attached pdf files and craft a comprehensive and cohesive reading material in a narrative format based on the provided content. 
    The reading material should be suitable for students in a {grade_level} in {subject}. 
    Make sure to include relevant images as HTML image tags within the reading material.
    Prioritize creating easy to understand sentences and use bullets and numbers for organization if needed.
    """
    resolved_api_key = api_key or get_config_value("CLAUDE_API_KEY")
    if not resolved_api_key:
        return "Error during LLM processing: Anthropic API key not configured."

    client = Anthropic(api_key=resolved_api_key)
    resolved_model = get_config_value("ANTHROPIC_REASON_MODEL", model_name)
    messages = [{"role": "user", "content": prompt}]

    try:
      response = client.messages.create(
          model=resolved_model,
          max_tokens=8192,
          messages=messages,
      )
      reading_material = response.content[0].text.strip()
      return reading_material
    except Exception as e:
         return f"Error during LLM processing: {e}"
    

def generate_reading_material_from_pdf_anthropic(combined_pdf_content, grade_level, subject, api_key):
    """Generate reading material using Anthropic API with images"""
    resolved_api_key = api_key or get_config_value("CLAUDE_API_KEY")
    if not resolved_api_key:
        raise ValueError("Anthropic API key not configured.")

    client = Anthropic(api_key=resolved_api_key)
    prompt = f"""Output verbatim the whole text from the PDF."

#     Using ONLY the information from the provided PDF, create an engaging textbook chapter that teaches through conversation and discovery:
# 1. STRUCTURE & NARRATIVE FLOW
# Opening:
# - Begin with an engaging "big picture" question or scenario
# - Provide clear, relatable definition of main concept
# - Set up chapter's learning journey

# Content Flow:
# - Progress logically from fundamentals to advanced topics
# - Use consistent narrative transitions:
#   * "Let's explore..."
#   * "Now that we understand X, let's discover..."
#   * "You might be wondering..."
#   * "Here's where it gets interesting..."
# - Break down complex topics into clear steps
# - Maintain source material's depth and scope

# 2. MAKING CONCEPTS RELATABLE
# Analogies:
# - Start each major concept with a familiar comparison:
#   * Compare scientific structures to everyday objects
#   * Relate processes to common experiences
#   * Link abstract concepts to tangible examples
# - Explain why each analogy works
# - Note any limitations of the comparison

# Real-World Connections:
# - Connect concepts to daily life applications
# - Use age-appropriate examples for {grade_level}
# - Include "Did you know?" segments for interesting facts

# 3. ENGAGEMENT ELEMENTS
# Interactive Components:
# - Add "Think About It" boxes for reflection
# - Include "Try This" mini-activities
# - Pose guiding questions throughout
# - Address common misconceptions directly

# Practice & Understanding:
# - Provide worked examples with clear steps
# - Include guided practice problems
# - Add "Check Your Understanding" sections
# - Use mixed difficulty levels for problems

# 4. TECHNICAL ACCURACY WITH ACCESSIBILITY
# Content Presentation:
# - Maintain scientific accuracy from source
# - Break down equations step-by-step
# - Define all terms in clear language
# - Use proper notation consistently
# - Include numerical examples

# Visual Elements:
# - Describe diagrams clearly using <image: detailed description>
# - Reference visuals in the text
# - Explain what to observe in each visual

# 5. FORMATTING & STRUCTURE
# Organization:
# - Use clear hierarchy (Chapter X, Section X.X)
# - Include concept boxes and summaries
# - Number all procedures and steps
# - Add margin notes for key points

# Each Section Should Include:
# - Opening question or scenario
# - Clear explanation with analogies
# - Worked examples
# - Practice problems
# - Summary points

# Voice and Tone:
# - Write like an enthusiastic, knowledgeable teacher
# - Use conversational but educational language
# - Guide reader through discoveries
# - Encourage curiosity and questions

# Target Audience: {grade_level} {subject} students
# Length: Maintain proportional to source material length

# Note: All content must come from the provided PDF. Focus on making complex concepts accessible through clear explanation, relatable analogies, and guided discovery.
# """

    message_content = [
        {"type": "text", "text": prompt},
    ]
    
    #for idx, each_pdf in enumerate(pdfs_array):
    message_content.extend([
            {"type": "document", "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": combined_pdf_content
            },  } #"cache_control": {"type": "ephemeral"}
        ])
    
    try:
        model_name = get_config_value("ANTHROPIC_REASON_MODEL", "claude-3-7-sonnet-latest")
        response = client.messages.create(
            model=model_name,
            max_tokens=8192,
            messages=[{"role": "user", "content": message_content}]
        )
        return response.content[0].text
    except Exception as e:
        return f"Error during LLM processing: {str(e)}"


# def generate_anthropic_response(prompt: str, api_key: str, pdf_data: str, model: str = "claude-3-5-sonnet-20241022") -> Optional[str]:
#     """Generate YAML formatted response using Anthropic API"""
#     try:
#         # Initialize the Anthropic client
#         client = Anthropic(api_key=api_key)
#         # Prepare messages with the PDF document and text prompt
#         messages = [{"role": "user","content": [{"type": "document","source": {"type": "base64","media_type": "application/pdf","data": pdf_data}, "cache_control": {"type": "ephemeral"}}, 
#                                                 {"type": "text","text": prompt}]}]

#         # Call the Anthropic API
#         response = client.beta.messages.create(model=model, max_tokens=8192, betas=["pdfs-2024-09-25"], temperature=0.7,messages=messages)
#         yaml_response = response.content[0].text.strip()
#         # Fix and validate YAML format
#         yaml_response = fix_yaml_format(yaml_response)
    
#         if not validate_yaml_response(yaml_response):
#             raise ValueError("Generated YAML does not meet requirements")

#         return yaml_response

#     except Exception as e:
#         raise Exception(f"Anthropic API error: {str(e)}")


# def validate_question_yaml(question: dict) -> bool:
#     """Validate individual question structure"""
#     required_fields = {'type', 'identifier', 'prompt'}
#     if not all(field in question for field in required_fields):
#         return False
        
#     # Type-specific validation
#     if question['type'] == 'mcq':
#         if 'choices' not in question:
#             return False
#         choices = question['choices']
#         if not isinstance(choices, list) or len(choices) < 2:
#             return False
#         if not any(c.get('correct', False) for c in choices):
#             return False
            
#     elif question['type'] == 'mrq':
#         if 'choices' not in question:
#             return False
#         choices = question['choices']
#         if not isinstance(choices, list) or len(choices) < 2:
#             return False
            
#     elif question['type'] == 'tf':
#         if 'correctResponse' not in question:
#             return False
            
#     return True

# def generate_openai_response(prompt: str, api_key: str, encoded_images: List[str], message_placeholder, model: str = "gpt-4o") -> Optional[str]:
#     """Generate response using OpenAI API with streaming output"""
#     try:
#         # Initialize the OpenAI client with the provided API key
#         client = OpenAI(api_key=api_key)

#         # Prepare the messages with both the text prompt and embedded images
#         messages = [
#             {
#                 "role": "system",
#                 "content": "You are a question generator that outputs only valid YAML format. Do not include (```yaml) and (```) on first and last lines, respectively!" #"content": "You are a question generator that outputs only valid QTI 2.2 XML format. Do not add ``` or ```xml in the output!"
#             },
#             {
#                 "role": "user",
#                 "content": [
#                     {"type": "text", "text": prompt}
#                 ]
#             }
#         ]

#         # Add the encoded images to the messages
#         for img_str in encoded_images:
#             messages[1]["content"].append({
#                 "type": "image_url",
#                 "image_url": {
#                     "url": f"data:image/jpeg;base64,{img_str}"
#                 }
#             })

#         # Initialize response collection
#         full_response = []
#         displayed_response = ""

#         # Call the OpenAI API with streaming
#         stream = client.chat.completions.create(
#             model=model,
#             messages=messages,
#             temperature=0.7,
#             max_tokens=16384,
#             stream=True
#         )

#         # Process the stream
#         for chunk in stream:
#             if chunk.choices[0].delta.content is not None:
#                 text_chunk = chunk.choices[0].delta.content
#                 full_response.append(text_chunk)
#                 displayed_response += text_chunk
#                 # Update the placeholder with the current response
#                 message_placeholder.markdown(f"Generating YAML:\n```yaml\n{displayed_response}\n```")

#         # Return the complete response
#         questions_xml = "".join(full_response).strip()
#         return questions_xml

#     except Exception as e:
#         raise Exception(f"OpenAI API error: {str(e)}")


# def generate_anthropic_response(prompt: str, api_key: str, pdf_data: str, model: str = "claude-3-5-sonnet-20241022") -> Optional[str]:
#     """Generate response using Anthropic API"""
#     try:
#         # Initialize the Anthropic client with the provided API key
#         client = Anthropic(api_key=api_key)
#         # Prepare the messages with the embedded PDF document and text prompt
#         messages = [{
#             "role": "user",
#             "content": [
#                 {
#                     "type": "document",
#                     "source": {
#                         "type": "base64",
#                         "media_type": "application/pdf",
#                         "data": pdf_data
#                     }
#                 },
#                 {
#                     "type": "text",
#                     "text": prompt
#                 }
#             ]
#         }]

#         # Call the Anthropic API
#         message = client.beta.messages.create(
#             model=model,
#             max_tokens=16384,
#             temperature=0.7,
#             messages=messages
#         )
#         return message.content

#     except Exception as e:
#         raise Exception(f"Anthropic API error: {str(e)}")


