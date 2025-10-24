#description: This file converts YAML formatted questions to QTI 2.2 XML format. The file supports multiple question types including Multiple Choice, True/False, Fill in the Blank, Matching, Ordering, and Essay questions. The app also allows you to download the QTI package containing all questions in a single ZIP file.
# file name: yaml_converter.py

from pathlib import Path
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET
from xml.dom import minidom
import yaml
import streamlit as st
from dataclasses import dataclass

@dataclass
class QuestionTemplate:
    """Template metadata for question types"""
    type: str
    xml_content: str

class YAMLtoQTIConverter:
    """Convert YAML formatted questions to QTI 2.2 XML"""
    def __init__(self, templates_dir: str = "templates"):
        """Initialize converter with templates"""
        self.ns = "http://www.imsglobal.org/xsd/imsqti_v2p2"
        self.templates_dir = Path(templates_dir)
        self.question_types_dir = self.templates_dir / "question_types"
        self.package_dir = self.templates_dir / "package"
        
        # Load metadata from YAML file
        metadata_path = self.templates_dir / "metadata.yaml"
        with open(metadata_path, 'r', encoding='utf-8') as f:
            self.metadata = yaml.safe_load(f)
            
        self.templates = self._load_templates()
        self.package_templates = self._load_package_templates()
        ET.register_namespace('', self.ns)

    def _load_templates(self) -> Dict[str, QuestionTemplate]:
        """Load question type templates"""
        templates = {}
        template_files = {
            'fib': 'fib.xml',
            'mcq': 'mcq.xml',
            'mrq': 'mrq.xml',
            'tf': 'tf.xml',
            'match': 'match.xml',
            'order': 'order.xml',
            'essay': 'essay.xml'
            # 'upload': 'upload.xml',
            # 'label_image': 'label_image.xml',
            # 'highlight_text': 'highlight_text.xml',
            # 'highlight_image': 'highlight_image.xml',
            # 'numeric': 'numeric.xml'
        }
        
        for qtype, filename in template_files.items():
            template_path = self.question_types_dir / filename
            if template_path.exists():
                with open(template_path, 'r', encoding='utf-8') as f:
                    templates[qtype] = QuestionTemplate(
                        type=qtype,
                        xml_content=f.read()
                    )
            else:
                st.warning(f"Template file {filename} not found in {self.question_types_dir}")
        
        return templates
    
    def _load_package_templates(self) -> Dict[str, str]:
        """Load package-level templates"""
        package_templates = {}
        template_files = ['manifest.xml', 'assessment.xml']
        
        for filename in template_files:
            template_path = self.package_dir / filename
            if template_path.exists():
                with open(template_path, 'r', encoding='utf-8') as f:
                    package_templates[filename] = f.read()
            else:
                st.warning(f"Package template {filename} not found in {self.package_dir}")
        
        return package_templates
    
    def create_qti_package(self, questions: List[str], test_title: str) -> bytes:
        """Create complete QTI package"""
        import zipfile
        from io import BytesIO
        import uuid
        
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add manifest
            manifest_xml = self.package_templates['manifest.xml'].format(
                manifest_id=f"MANIFEST-{uuid.uuid4()}",
                dependencies=self._generate_dependencies(questions),
                resources=self._generate_resources(questions)
            )
            zip_file.writestr('imsmanifest.xml', manifest_xml)
            
            # Add assessment test
            test_xml = self.package_templates['assessment.xml'].format(
                test_id=f"test-{uuid.uuid4()}",
                test_title=test_title,
                item_refs=self._generate_item_refs(questions)
            )
            zip_file.writestr('assessmentTest.xml', test_xml)
            
            # Add individual questions
            for question in questions:
                root = ET.fromstring(question)
                question_id = root.get('identifier')
                zip_file.writestr(f"{question_id}.xml", question)
        
        zip_buffer.seek(0)
        return zip_buffer.getvalue()
    
    def _generate_dependencies(self, questions: List[str]) -> str:
        """Generate dependency references for manifest"""
        dependencies = []
        for question in questions:
            root = ET.fromstring(question)
            identifier = root.get('identifier')
            dependencies.append(f'<dependency identifierref="{identifier}"/>')
        return '\n            '.join(dependencies)

    def _generate_resources(self, questions: List[str]) -> str:
        """Generate resource items for manifest"""
        resources = []
        for question in questions:
            root = ET.fromstring(question)
            identifier = root.get('identifier')
            resources.append(f'''
            <resource identifier="{identifier}" type="imsqti_item_xmlv2p2" href="{identifier}.xml">
                <file href="{identifier}.xml"/>
            </resource>''')
        return '\n'.join(resources)

    def _generate_item_refs(self, questions: List[str]) -> str:
        """Generate item references for assessment test"""
        refs = []
        for question in questions:
            root = ET.fromstring(question)
            identifier = root.get('identifier')
            refs.append(f'<assessmentItemRef identifier="{identifier}" href="{identifier}.xml"/>')
        return '\n            '.join(refs)

    def validate_question(self, question: Dict, question_type: str) -> bool:
        """Validate question format"""
        if not question_type:
            raise ValueError("Missing question type")
                
        if question_type not in self.templates:
            raise ValueError(f"Unsupported question type: {question_type}")
                
        # Basic validation for all questions
        if not self._validate_common(question):
            return False
        
        # Type-specific validation
        if question_type == 'fib':
            return self._validate_fib(question)
        elif question_type in ['mcq', 'mrq']:
            return self._validate_choices(question, question_type)
        elif question_type == 'tf':
            return self._validate_tf(question)
        elif question_type == 'match':
            return self._validate_match(question)
        elif question_type == 'order':
            return self._validate_order(question)
        elif question_type == 'essay':
            return self._validate_essay(question)
        # elif question_type == 'upload':
        #     return self._validate_upload(question)
        # elif question_type == 'label_image':
        #     return self._validate_label_image(question)
        # elif question_type == 'highlight_text':
        #     return self._validate_highlight_text(question)
        # elif question_type == 'numeric':
        #     return self._validate_numeric(question)
        
        return True

    def _fix_yaml_apostrophes(self, yaml_str: str) -> str:
        """
        Fix YAML strings containing apostrophes by properly quoting them
        """
        import re
        
        # Process the YAML line by line
        lines = yaml_str.split('\n')
        result = []
        
        for line in lines:
            # Check if the line contains an apostrophe within a string that might cause parsing issues
            if ":" in line and "'" in line.split(":", 1)[1]:
                # Split the line into key and value
                key_part, value_part = line.split(":", 1)
                
                # If the value has apostrophes and is not already properly quoted with double quotes
                if "'" in value_part and not (value_part.strip().startswith('"') and value_part.strip().endswith('"')):
                    # Properly quote the value with double quotes, escaping any existing double quotes
                    value_part = value_part.strip()
                    if value_part.startswith("'") and value_part.endswith("'"):
                        # Already single quoted, replace with double quotes
                        value_part = '"' + value_part[1:-1].replace('"', '\\"') + '"'
                    else:
                        # Not quoted, add double quotes
                        #value_part = f' "{value_part.replace('"', '\\"')}"'
                        escaped_value = value_part.replace('"', '\\"')
                        value_part = f' "{escaped_value}"'
                    # Reconstruct the line
                    line = f"{key_part}:{value_part}"
            
            result.append(line)
        
        return '\n'.join(result)

    def _escape_xml_chars(self, text: str) -> str:
        """Escape special XML characters in text content"""
        if not isinstance(text, str):
            text = str(text)
        
        # Replace XML special characters with their entities
        replacements = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&apos;'
        }
        
        for char, entity in replacements.items():
            text = text.replace(char, entity)
        
        return text

    def _preprocess_fib_answers(self, questions: List[Dict]) -> List[Dict]:
        """
        Restructure FIB questions' correctAnswers to match the expected format.
        This converts multiple single-item answer sets into one multi-item answer set.
        """
        for question in questions:
            if question.get('type') == 'fib':
                # Count blanks in prompt
                num_blanks = question['prompt'].count('_')
                
                # Check if correctAnswers structure needs to be fixed
                answers = question.get('correctAnswers', [])
                
                # If we have more answer sets than blanks AND
                # each answer set has only one item, restructure
                if len(answers) > num_blanks and all(len(ans) == 1 for ans in answers):
                    # Restructure to one answer set with multiple items
                    restructured_answers = []
                    
                    # Group answers by position (assumes answers for first blank come first, etc.)
                    for i in range(num_blanks):
                        # Calculate how many answers belong to this blank
                        answers_per_blank = len(answers) // num_blanks
                        
                        # Create a new answer set with all alternatives for this blank
                        start_idx = i * answers_per_blank
                        end_idx = start_idx + answers_per_blank
                        new_answer_set = [item for sublist in answers[start_idx:end_idx] for item in sublist]
                        
                        restructured_answers.append(new_answer_set)
                    
                    # Replace the original answers with restructured ones
                    question['correctAnswers'] = restructured_answers
                    
        return questions

    def convert(self, yaml_str: str) -> List[str]:
        """Convert YAML string to list of QTI XML strings using custom parsing"""
        try:
            # Custom YAML parsing to handle LaTeX and other special characters
            questions = self._custom_yaml_parse(yaml_str)
            
            xml_questions = []
            for question in questions:
                try:
                    qtype = question.get('type')
                    if not qtype:
                        raise ValueError("Question missing type field")
                        
                    # Get template and format XML
                    template = self.templates.get(qtype)
                    if not template:
                        raise ValueError(f"Template not found for type: {qtype}")
                        
                    xml = self._format_question(question, template)
                    xml_questions.append(self._prettify(xml))
                    
                except Exception as e:
                    st.error(f"Error converting question {question.get('identifier', 'unknown')}: {str(e)}")
                    continue
                    
            return xml_questions
            
        except Exception as e:
            raise ValueError(f"Invalid YAML format: {str(e)}")

#commented on 3-18-2025
    # def _custom_yaml_parse(self, yaml_str: str) -> List[Dict]:
    #     """Parse YAML content manually to handle LaTeX, HTML, and nested structures"""
    #     import re
        
    #     # Split into individual questions
    #     question_blocks = re.split(r'(?=^- type:)', yaml_str, flags=re.MULTILINE)
    #     questions = []
        
    #     for block in question_blocks:
    #         if not block.strip():
    #             continue
                
    #         # Process each question
    #         question_dict = {}
    #         lines = block.strip().split('\n')
            
    #         # Process header line (- type: xxx)
    #         if lines[0].startswith('- type:'):
    #             question_dict['type'] = lines[0].split(':', 1)[1].strip().strip('"\'')
            
    #         # Process remaining fields
    #         i = 1
    #         in_choices = False
    #         choices = []
    #         current_choice = None
            
    #         # Add these variables at the beginning of the function with the other special section flags
    #         # For FIB questions
    #         in_fib_answers = False
    #         fib_answers = []
    #         current_fib_answer = None

    #         # For match-type questions
    #         in_match_sets = False
    #         match_sets = {'source': [], 'target': []}
    #         in_source = False
    #         in_target = False
    #         current_match_item = None
            
    #         # For correctPairs in match questions
    #         in_correct_pairs = False
    #         correct_pairs = []
    #         current_pair = []
            
    #         # For order type questions
    #         in_correct_sequence = False
    #         correct_sequence = []
            
    #         while i < len(lines):
    #             line = lines[i].rstrip()
                
    #             # Skip empty lines
    #             if not line.strip():
    #                 i += 1
    #                 continue

    #             # Handle match-type questions specifically
    #             if question_dict.get('type') == 'match':
    #                 # Detect matchSets section
    #                 if line.strip() == 'matchSets:':
    #                     in_match_sets = True
    #                     i += 1
    #                     continue
                    
    #                 # Process matchSets subsections
    #                 if in_match_sets:
    #                     # Detect source section
    #                     if line.strip() == 'source:':
    #                         # If we're transitioning from target to source, save any pending target item
    #                         if in_target and current_match_item:
    #                             match_sets['target'].append(current_match_item)
    #                             current_match_item = None
                                
    #                         in_source = True
    #                         in_target = False
    #                         i += 1
    #                         continue
                        
    #                     # Detect target section
    #                     elif line.strip() == 'target:':
    #                         # If we're transitioning from source to target, save any pending source item
    #                         if in_source and current_match_item:
    #                             match_sets['source'].append(current_match_item)
    #                             current_match_item = None
                                
    #                         in_source = False
    #                         in_target = True
    #                         i += 1
    #                         continue
                        
    #                     # Process items in source or target
    #                     elif (in_source or in_target) and line.strip().startswith('- identifier:'):
    #                         # Store previous item if exists
    #                         if current_match_item:
    #                             if in_source:
    #                                 match_sets['source'].append(current_match_item)
    #                             else:
    #                                 match_sets['target'].append(current_match_item)
                            
    #                         # Start new item
    #                         current_match_item = {'identifier': line.strip()[13:].strip().strip('"\'') }
                        
    #                     # Process item fields
    #                     elif current_match_item and ':' in line and (in_source or in_target):
    #                         field, value = line.strip().split(':', 1)
    #                         field = field.strip()
    #                         value = value.strip().strip('"\'')
                            
    #                         # Special handling for number fields
    #                         if field == 'matchMax':
    #                             try:
    #                                 value = int(value)
    #                             except ValueError:
    #                                 pass
                            
    #                         current_match_item[field] = value
                        
    #                     # Exit matchSets when we hit a new top-level field (not indented)
    #                     elif not line.startswith(' '):
    #                         # Add the last item
    #                         if current_match_item:
    #                             if in_source:
    #                                 match_sets['source'].append(current_match_item)
    #                             else:
    #                                 match_sets['target'].append(current_match_item)
    #                             current_match_item = None
                            
    #                         # Store the full matchSets in the question dict
    #                         question_dict['matchSets'] = match_sets
    #                         in_match_sets = False
    #                         in_source = False
    #                         in_target = False
    #                         continue  # Process this line as a regular field
                    
    #                 # Detect correctPairs section
    #                 elif line.strip() == 'correctPairs:':
    #                     in_correct_pairs = True
    #                     i += 1
    #                     continue
                    
    #                 # Process correctPairs items
    #                 elif in_correct_pairs:
    #                     if line.strip().startswith('- - '):
    #                         # Start a new pair
    #                         current_pair = [line.strip()[4:].strip().strip('"\'')]
    #                     elif line.strip().startswith('  - ') and current_pair:
    #                         # Complete the pair and add it
    #                         current_pair.append(line.strip()[4:].strip().strip('"\''))
    #                         correct_pairs.append(current_pair)
    #                         current_pair = []
    #                     # Exit correctPairs when we hit a non-indented line
    #                     elif not line.startswith(' '):
    #                         question_dict['correctPairs'] = correct_pairs
    #                         in_correct_pairs = False
    #                         continue  # Process this line as a regular field
                
    #             # Handle FIB-type questions specifically
    #             elif question_dict.get('type') == 'fib':
    #                 # Detect correctAnswers section
    #                 if line.strip() == 'correctAnswers:':
    #                     in_fib_answers = True
    #                     fib_answers = []
    #                     current_fib_answer = None
    #                     i += 1
    #                     continue
                    
    #                 # Process correctAnswers items
    #                 elif in_fib_answers:
    #                     if line.strip().startswith('- - '):
    #                         # Start a new answer group
    #                         if current_fib_answer:
    #                             fib_answers.append(current_fib_answer)
    #                         current_fib_answer = [line.strip()[4:].strip().strip('"\'')]
    #                     elif line.strip().startswith('  - ') and current_fib_answer is not None:
    #                         # Add alternative to current answer group
    #                         current_fib_answer.append(line.strip()[4:].strip().strip('"\''))
    #                     # Exit correctAnswers when we hit a non-indented line
    #                     elif not line.startswith(' '):
    #                         if current_fib_answer:
    #                             fib_answers.append(current_fib_answer)
    #                         question_dict['correctAnswers'] = fib_answers
    #                         in_fib_answers = False
    #                         current_fib_answer = None
    #                         continue  # Process this line as a regular field



    #             # Handle order-type questions specifically
    #             elif question_dict.get('type') == 'order':
    #                 # Detect correctSequence section
    #                 if line.strip() == 'correctSequence:':
    #                     in_correct_sequence = True
    #                     i += 1
    #                     continue
                    
    #                 # Process correctSequence items
    #                 elif in_correct_sequence:
    #                     if line.strip().startswith('- '):
    #                         # Add item to sequence
    #                         item = line.strip()[2:].strip().strip('"\'')
    #                         correct_sequence.append(item)
                        
    #                     # Exit correctSequence when we hit a non-indented line
    #                     elif not line.startswith(' '):
    #                         question_dict['correctSequence'] = correct_sequence
    #                         in_correct_sequence = False
    #                         continue  # Process this line as a regular field
                
    #             # Handle regular choices section (for mcq, mrq, etc.)
    #             if line.strip() == 'choices:':
    #                 in_choices = True
    #                 i += 1
    #                 continue
                    
    #             # Process choice items
    #             if in_choices:
    #                 # New choice starts with "- identifier:"
    #                 if line.strip().startswith('- identifier:'):
    #                     # Store previous choice if exists
    #                     if current_choice:
    #                         choices.append(current_choice)
                        
    #                     # Start new choice
    #                     current_choice = {'identifier': line.strip()[13:].strip().strip('"\'') }
                        
    #                 # Process choice fields (text, correct)
    #                 elif current_choice and ':' in line:
    #                     field, value = line.strip().split(':', 1)
    #                     field = field.strip()
    #                     value = value.strip().strip('"\'')
                        
    #                     # Special handling for text field which might have LaTeX
    #                     if field == 'text':
    #                         # If value starts with triple quotes, extract until end triple quotes
    #                         if value.startswith('"""') or value.startswith("'''"):
    #                             quote_type = value[:3]
    #                             if quote_type in value[3:]:
    #                                 # Single line with triple quotes
    #                                 end_quote = value.rindex(quote_type)
    #                                 value = value[3:end_quote]
    #                             else:
    #                                 # Multi-line triple quoted string
    #                                 text_parts = [value[3:]]
    #                                 j = i + 1
    #                                 while j < len(lines):
    #                                     if quote_type in lines[j]:
    #                                         end_quote = lines[j].rindex(quote_type)
    #                                         text_parts.append(lines[j][:end_quote])
    #                                         i = j
    #                                         break
    #                                     else:
    #                                         text_parts.append(lines[j])
    #                                     j += 1
    #                                 value = ' '.join(text_parts)
                            
    #                         current_choice[field] = value
    #                     elif field == 'correct':
    #                         current_choice[field] = value.lower() == 'true'
    #                     else:
    #                         current_choice[field] = value
                    
    #                 # Check if choices section ends
    #                 elif not line.startswith(' '):
    #                     # Add the current choice and end choices section
    #                     if current_choice:
    #                         choices.append(current_choice)
    #                         current_choice = None
                        
    #                     question_dict['choices'] = choices
    #                     in_choices = False
    #                     continue  # Process this line again as a regular field
                
    #             # Process regular fields
    #             if ':' in line and not in_choices and not in_match_sets and not in_correct_pairs and not in_correct_sequence:
    #                 key, value = line.split(':', 1)
    #                 key = key.strip()
    #                 value = value.strip()
                    
    #                 # Strip quotes if present
    #                 if (value.startswith('"') and value.endswith('"')) or \
    #                 (value.startswith("'") and value.endswith("'")):
    #                     value = value[1:-1]
    #                 elif (value.startswith('"""') and value.endswith('"""')) or \
    #                     (value.startswith("'''") and value.endswith("'''")):
    #                     value = value[3:-3]
                    
    #                 # Convert boolean values
    #                 if value.lower() == 'true':
    #                     value = True
    #                 elif value.lower() == 'false':
    #                     value = False
                    
    #                 question_dict[key] = value
                
    #             i += 1
            
    #         # Don't forget to add the last choice if still in choices section
    #         if in_choices and current_choice:
    #             choices.append(current_choice)
    #             question_dict['choices'] = choices
            
    #         # Handle final items for match questions
    #         if question_dict.get('type') == 'match':
    #             # Add the last match item if we're still in matchSets
    #             if in_match_sets and current_match_item:
    #                 if in_source:
    #                     match_sets['source'].append(current_match_item)
    #                 elif in_target:
    #                     match_sets['target'].append(current_match_item)
    #                 question_dict['matchSets'] = match_sets
                
    #             # Make sure we store correctPairs if we're at the end of the block
    #             if in_correct_pairs:
    #                 question_dict['correctPairs'] = correct_pairs
                
    #             # Generate default correctPairs if not present
    #             if 'matchSets' in question_dict and 'correctPairs' not in question_dict:
    #                 # Create default pairs by matching source with target by index order
    #                 # Only if both source and target exist with items
    #                 if ('source' in question_dict['matchSets'] and 
    #                     'target' in question_dict['matchSets'] and
    #                     question_dict['matchSets']['source'] and 
    #                     question_dict['matchSets']['target']):
                        
    #                     generated_pairs = []
    #                     source_choices = question_dict['matchSets']['source']
    #                     target_choices = question_dict['matchSets']['target']
                        
    #                     # Match up to the minimum number of choices available in either set
    #                     pair_count = min(len(source_choices), len(target_choices))
    #                     for i in range(pair_count):
    #                         source_id = source_choices[i].get('identifier')
    #                         target_id = target_choices[i].get('identifier')
    #                         if source_id and target_id:
    #                             generated_pairs.append([source_id, target_id])
                        
    #                     question_dict['correctPairs'] = generated_pairs
            
    #         # Handle final items for order questions
    #         if question_dict.get('type') == 'order' and in_correct_sequence:
    #             question_dict['correctSequence'] = correct_sequence
            
    #         # Handle final items for FIB questions
    #         if question_dict.get('type') == 'fib' and in_fib_answers and current_fib_answer:
    #             fib_answers.append(current_fib_answer)
    #             question_dict['correctAnswers'] = fib_answers

    #         questions.append(question_dict)
        
    #     return questions
   

#    #commented of 24 april 2025
    def _custom_yaml_parse(self, yaml_str: str) -> List[Dict]:
        """Parse YAML content manually to handle LaTeX, HTML, and nested structures"""
        import re
        
        # Split into individual questions
        question_blocks = re.split(r'(?=^- type:)', yaml_str, flags=re.MULTILINE)
        questions = []
        
        for block in question_blocks:
            if not block.strip():
                continue
                
            # Process each question
            question_dict = {}
            lines = block.strip().split('\n')
            
            # Process header line (- type: xxx)
            if lines[0].startswith('- type:'):
                question_dict['type'] = lines[0].split(':', 1)[1].strip().strip('"\'')
            
            # Process remaining fields
            i = 1
            in_choices = False
            choices = []
            current_choice = None
            
            # Add these variables at the beginning of the function with the other special section flags
            # For FIB questions
            in_fib_answers = False
            fib_answers = []
            current_fib_answer = None

            # For match-type questions
            in_match_sets = False
            match_sets = {'source': [], 'target': []}
            in_source = False
            in_target = False
            current_match_item = None
            
            # For correctPairs in match questions
            in_correct_pairs = False
            correct_pairs = []
            current_pair = []
            
            # For order type questions
            in_correct_sequence = False
            correct_sequence = []
            
            while i < len(lines):
                line = lines[i].rstrip()
                
                # Skip empty lines
                if not line.strip():
                    i += 1
                    continue

                # Handle match-type questions specifically
                if question_dict.get('type') == 'match':
                    # Detect matchSets section
                    if line.strip() == 'matchSets:':
                        in_match_sets = True
                        i += 1
                        continue
                    
                    # Process matchSets subsections
                    if in_match_sets:
                        # Detect source section
                        if line.strip() == 'source:':
                            # If we're transitioning from target to source, save any pending target item
                            if in_target and current_match_item:
                                match_sets['target'].append(current_match_item)
                                current_match_item = None
                                
                            in_source = True
                            in_target = False
                            i += 1
                            continue
                        
                        # Detect target section
                        elif line.strip() == 'target:':
                            # If we're transitioning from source to target, save any pending source item
                            if in_source and current_match_item:
                                match_sets['source'].append(current_match_item)
                                current_match_item = None
                                
                            in_source = False
                            in_target = True
                            i += 1
                            continue
                        
                        # Process items in source or target
                        elif (in_source or in_target) and line.strip().startswith('- identifier:'):
                            # Store previous item if exists
                            if current_match_item:
                                if in_source:
                                    match_sets['source'].append(current_match_item)
                                else:
                                    match_sets['target'].append(current_match_item)
                            
                            # Start new item
                            current_match_item = {'identifier': line.strip()[13:].strip().strip('"\'') }
                        
                        # Process item fields
                        elif current_match_item and ':' in line and (in_source or in_target):
                            field, value = line.strip().split(':', 1)
                            field = field.strip()
                            value = value.strip().strip('"\'')
                            
                            # Special handling for number fields
                            if field == 'matchMax':
                                try:
                                    value = int(value)
                                except ValueError:
                                    pass
                            
                            current_match_item[field] = value
                        
                        # Exit matchSets when we hit a new top-level field (not indented)
                        elif not line.startswith(' '):
                            # Add the last item
                            if current_match_item:
                                if in_source:
                                    match_sets['source'].append(current_match_item)
                                else:
                                    match_sets['target'].append(current_match_item)
                                current_match_item = None
                            
                            # Store the full matchSets in the question dict
                            question_dict['matchSets'] = match_sets
                            in_match_sets = False
                            in_source = False
                            in_target = False
                            continue  # Process this line as a regular field
                    
                    # Detect correctPairs section
                    elif line.strip() == 'correctPairs:':
                        in_correct_pairs = True
                        i += 1
                        continue
                    
                    # Process correctPairs items
                    elif in_correct_pairs:
                        if line.strip().startswith('- - '):
                            # Start a new pair
                            current_pair = [line.strip()[4:].strip().strip('"\'')]
                        elif line.strip().startswith('  - ') and current_pair:
                            # Complete the pair and add it
                            current_pair.append(line.strip()[4:].strip().strip('"\''))
                            correct_pairs.append(current_pair)
                            current_pair = []
                        # Exit correctPairs when we hit a non-indented line
                        elif not line.startswith(' '):
                            question_dict['correctPairs'] = correct_pairs
                            in_correct_pairs = False
                            continue  # Process this line as a regular field
                
                # Handle FIB-type questions specifically
                elif question_dict.get('type') == 'fib':
                    # Detect correctAnswers section
                    if line.strip() == 'correctAnswers:':
                        in_fib_answers = True
                        fib_answers = []
                        current_fib_answer = []  # Initialize as empty list instead of None
                        i += 1
                        continue
                    
                    # Process correctAnswers items
                    elif in_fib_answers:
                        # Handle a standalone "- -" that introduces a new answer group but doesn't contain an answer
                        if line.strip() == '- -':
                            # If we have answers for the current blank, add them to the list and start a new group
                            if current_fib_answer:
                                fib_answers.append(current_fib_answer)
                                current_fib_answer = []
                            i += 1
                            continue
                        
                        # Handle "- - answer" format (first answer on same line as group marker)
                        elif line.strip().startswith('- - ') and len(line.strip()) > 4:
                            # If we have answers for the current blank, add them to the list
                            if current_fib_answer:
                                fib_answers.append(current_fib_answer)
                            
                            # Start a new answer group with this answer
                            answer = line.strip()[4:].strip().strip('"\'')
                            current_fib_answer = [answer]
                        
                        # Handle individual answers with "  - answer" format
                        elif line.strip().startswith('  - '):
                            # Extract the answer and add it to the current group
                            answer = line.strip()[4:].strip().strip('"\'')
                            current_fib_answer.append(answer)
                        
                        # Exit correctAnswers when we hit a non-indented line
                        elif not line.startswith(' '):
                            # Add the last answer group if it exists
                            if current_fib_answer:
                                fib_answers.append(current_fib_answer)
                            
                            question_dict['correctAnswers'] = fib_answers
                            in_fib_answers = False
                            current_fib_answer = []
                            continue  # Process this line as a regular field

                # Handle order-type questions specifically
                elif question_dict.get('type') == 'order':
                    # Detect correctSequence section
                    if line.strip() == 'correctSequence:':
                        in_correct_sequence = True
                        i += 1
                        continue
                    
                    # Process correctSequence items
                    elif in_correct_sequence:
                        if line.strip().startswith('- '):
                            # Add item to sequence
                            item = line.strip()[2:].strip().strip('"\'')
                            correct_sequence.append(item)
                        
                        # Exit correctSequence when we hit a non-indented line
                        elif not line.startswith(' '):
                            question_dict['correctSequence'] = correct_sequence
                            in_correct_sequence = False
                            continue  # Process this line as a regular field
                
                # Handle regular choices section (for mcq, mrq, etc.)
                if line.strip() == 'choices:':
                    in_choices = True
                    i += 1
                    continue
                    
                # Process choice items
                if in_choices:
                    # New choice starts with "- identifier:"
                    if line.strip().startswith('- identifier:'):
                        # Store previous choice if exists
                        if current_choice:
                            choices.append(current_choice)
                        
                        # Start new choice
                        current_choice = {'identifier': line.strip()[13:].strip().strip('"\'') }
                        
                    # Process choice fields (text, correct)
                    elif current_choice and ':' in line:
                        field, value = line.strip().split(':', 1)
                        field = field.strip()
                        value = value.strip().strip('"\'')
                        
                        # Special handling for text field which might have LaTeX
                        if field == 'text':
                            # If value starts with triple quotes, extract until end triple quotes
                            if value.startswith('"""') or value.startswith("'''"):
                                quote_type = value[:3]
                                if quote_type in value[3:]:
                                    # Single line with triple quotes
                                    end_quote = value.rindex(quote_type)
                                    value = value[3:end_quote]
                                else:
                                    # Multi-line triple quoted string
                                    text_parts = [value[3:]]
                                    j = i + 1
                                    while j < len(lines):
                                        if quote_type in lines[j]:
                                            end_quote = lines[j].rindex(quote_type)
                                            text_parts.append(lines[j][:end_quote])
                                            i = j
                                            break
                                        else:
                                            text_parts.append(lines[j])
                                        j += 1
                                    value = ' '.join(text_parts)
                            
                            current_choice[field] = value
                        elif field == 'correct':
                            current_choice[field] = value.lower() == 'true'
                        else:
                            current_choice[field] = value
                    
                    # Check if choices section ends
                    elif not line.startswith(' '):
                        # Add the current choice and end choices section
                        if current_choice:
                            choices.append(current_choice)
                            current_choice = None
                        
                        question_dict['choices'] = choices
                        in_choices = False
                        continue  # Process this line again as a regular field
                
                # Process regular fields
                if ':' in line and not in_choices and not in_match_sets and not in_correct_pairs and not in_correct_sequence and not in_fib_answers:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Strip quotes if present
                    if (value.startswith('"') and value.endswith('"')) or \
                    (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    elif (value.startswith('"""') and value.endswith('"""')) or \
                        (value.startswith("'''") and value.endswith("'''")):
                        value = value[3:-3]
                    
                    # Convert boolean values
                    if value.lower() == 'true':
                        value = True
                    elif value.lower() == 'false':
                        value = False
                    
                    question_dict[key] = value
                
                i += 1
            
            # Don't forget to add the last choice if still in choices section
            if in_choices and current_choice:
                choices.append(current_choice)
                question_dict['choices'] = choices
            
            # Handle final items for match questions
            if question_dict.get('type') == 'match':
                # Add the last match item if we're still in matchSets
                if in_match_sets and current_match_item:
                    if in_source:
                        match_sets['source'].append(current_match_item)
                    elif in_target:
                        match_sets['target'].append(current_match_item)
                    question_dict['matchSets'] = match_sets
                
                # Make sure we store correctPairs if we're at the end of the block
                if in_correct_pairs:
                    question_dict['correctPairs'] = correct_pairs
                
                # Generate default correctPairs if not present
                if 'matchSets' in question_dict and 'correctPairs' not in question_dict:
                    # Create default pairs by matching source with target by index order
                    # Only if both source and target exist with items
                    if ('source' in question_dict['matchSets'] and 
                        'target' in question_dict['matchSets'] and
                        question_dict['matchSets']['source'] and 
                        question_dict['matchSets']['target']):
                        
                        generated_pairs = []
                        source_choices = question_dict['matchSets']['source']
                        target_choices = question_dict['matchSets']['target']
                        
                        # Match up to the minimum number of choices available in either set
                        pair_count = min(len(source_choices), len(target_choices))
                        for i in range(pair_count):
                            source_id = source_choices[i].get('identifier')
                            target_id = target_choices[i].get('identifier')
                            if source_id and target_id:
                                generated_pairs.append([source_id, target_id])
                        
                        question_dict['correctPairs'] = generated_pairs
            
            # Handle final items for order questions
            if question_dict.get('type') == 'order' and in_correct_sequence:
                question_dict['correctSequence'] = correct_sequence
            
            # Handle final items for FIB questions
            if question_dict.get('type') == 'fib' and in_fib_answers and current_fib_answer:
                fib_answers.append(current_fib_answer)
                question_dict['correctAnswers'] = fib_answers

            questions.append(question_dict)
        
        return questions

 
###PRODUCES ERRORS WHEN PARSING FIB QUESTIONS. COMMENTED ON APRIL 27, 2025
    # def _custom_yaml_parse(self, yaml_str: str) -> List[Dict]:
    #     """Parse YAML content manually to handle LaTeX, HTML, and nested structures"""
    #     import re # Already imported

    #     # --- Helper function to handle potentially multi-line text extraction ---
    #     def extract_text_value(lines: List[str], current_index: int) -> tuple[str, int]:
    #         """
    #         Extracts a text value, handling single-line, quoted, and multi-line triple-quoted strings.

    #         Args:
    #             lines: The list of all lines in the current block.
    #             current_index: The index of the line containing the field key and start of the value.

    #         Returns:
    #             A tuple containing:
    #                 - The extracted and processed string value.
    #                 - The updated line index (pointing to the line *after* the processed value).
    #         """
    #         line = lines[current_index].rstrip()
    #         try:
    #             # Split only on the first colon
    #             _, value = line.split(':', 1)
    #         except ValueError:
    #             # Line doesn't contain ':', might be part of a multi-line structure handled elsewhere
    #             # or an invalid line for simple key-value. Return empty string and advance one line.
    #             # Or perhaps raise an error? For now, just returning empty.
    #             return "", current_index + 1

    #         value = value.strip()

    #         # 1. Handle multi-line triple-quoted strings
    #         if value.startswith('"""') or value.startswith("'''"):
    #             quote_type = value[:3]
    #             # Check if ends on the same line
    #             if len(value) > 5 and value.endswith(quote_type): # value[3:-3] needs at least 6 chars
    #                 return value[3:-3], current_index + 1
    #             else:
    #                 # Multi-line case
    #                 text_parts = [value[3:]] # Start with the part on the first line
    #                 j = current_index + 1
    #                 while j < len(lines):
    #                     line_part = lines[j].rstrip() # Don't strip leading whitespace, preserve indentation
    #                     if quote_type in line_part:
    #                         end_quote_index = line_part.rindex(quote_type)
    #                         text_parts.append(line_part[:end_quote_index])
    #                         # IMPORTANT: Join with newline to preserve LaTeX structure better than space
    #                         return '\n'.join(text_parts), j + 1
    #                     else:
    #                         text_parts.append(line_part)
    #                     j += 1
    #                 # If loop finishes without finding end quotes, it's malformed YAML.
    #                 # Return what we have, joined by newline.
    #                 return '\n'.join(text_parts), j # j will be len(lines)

    #         # 2. Handle single/double quoted strings
    #         elif (value.startswith('"') and value.endswith('"')) or \
    #             (value.startswith("'") and value.endswith("'")):
    #             # Strip only one layer of quotes
    #             return value[1:-1], current_index + 1

    #         # 3. Handle unquoted values (including potential booleans/numbers later)
    #         else:
    #             # Return the raw stripped value for further processing (bool, int etc)
    #             return value, current_index + 1
    #     # --- End Helper Function ---


    #     # Split into individual questions
    #     # Use positive lookahead to keep the delimiter pattern
    #     question_blocks = re.split(r'(?=^- type:)', yaml_str.strip(), flags=re.MULTILINE)
    #     questions = []

    #     for block in question_blocks:
    #         if not block.strip():
    #             continue

    #         # Process each question
    #         question_dict: Dict[str, Any] = {} # Use Any for flexibility
    #         lines = block.strip().split('\n')

    #         # Process header line (- type: xxx)
    #         if lines[0].startswith('- type:'):
    #             try:
    #                 question_dict['type'] = lines[0].split(':', 1)[1].strip().strip('"\'')
    #             except IndexError:
    #                 # Handle case where line is just "- type:"
    #                 question_dict['type'] = '' # Or raise error?

    #         # Process remaining fields
    #         i = 1
    #         in_choices = False
    #         choices = []
    #         current_choice = None

    #         in_fib_answers = False
    #         fib_answers = []
    #         current_fib_answer = [] # Initialize as list

    #         in_match_sets = False
    #         match_sets = {'source': [], 'target': []}
    #         in_source = False
    #         in_target = False
    #         current_match_item = None

    #         in_correct_pairs = False
    #         correct_pairs = []
    #         current_pair = []

    #         in_correct_sequence = False
    #         correct_sequence = []

    #         while i < len(lines):
    #             line = lines[i].rstrip() # Use rstrip initially

    #             # Skip empty lines or pure comment lines
    #             if not line.strip() or line.strip().startswith('#'):
    #                 i += 1
    #                 continue

    #             # Get indentation level
    #             indentation = len(line) - len(line.lstrip(' '))

    #             # --- State Management based on indentation and keywords ---
    #             # Exit nested structures if indentation decreases significantly
    #             if indentation == 0: # Top level field processing
    #                 # Ensure we clean up any open nested structures before processing
    #                 if in_choices:
    #                     if current_choice: choices.append(current_choice)
    #                     question_dict['choices'] = choices
    #                     in_choices, current_choice = False, None
    #                 if in_match_sets:
    #                     if current_match_item:
    #                         target_key = 'source' if in_source else 'target'
    #                         match_sets[target_key].append(current_match_item)
    #                     question_dict['matchSets'] = match_sets
    #                     in_match_sets, in_source, in_target, current_match_item = False, False, False, None
    #                 if in_correct_pairs:
    #                     question_dict['correctPairs'] = correct_pairs
    #                     in_correct_pairs, current_pair = False, []
    #                 if in_correct_sequence:
    #                     question_dict['correctSequence'] = correct_sequence
    #                     in_correct_sequence = False
    #                 if in_fib_answers:
    #                     if current_fib_answer: fib_answers.append(current_fib_answer)
    #                     question_dict['correctAnswers'] = fib_answers
    #                     in_fib_answers, current_fib_answer = False, []

    #             # --- Section Detection ---
    #             # Using strip() for keyword detection but process the original 'line'

    #             # Check for top-level keywords FIRST before checking indentation-based state exits
    #             # This prevents prematurely exiting a section if a keyword is at indentation 0
    #             line_stripped = line.strip()
    #             is_new_section_keyword = False # Flag to prevent processing as regular field

    #             if line_stripped == 'choices:':
    #                 in_choices = True
    #                 is_new_section_keyword = True
    #                 i += 1; continue # Move to next line
    #             elif line_stripped == 'matchSets:':
    #                 in_match_sets = True
    #                 is_new_section_keyword = True
    #                 i += 1; continue
    #             elif line_stripped == 'correctPairs:':
    #                 in_correct_pairs = True
    #                 is_new_section_keyword = True
    #                 i += 1; continue
    #             elif line_stripped == 'correctSequence:':
    #                 in_correct_sequence = True
    #                 is_new_section_keyword = True
    #                 i += 1; continue
    #             elif line_stripped == 'correctAnswers:':
    #                 in_fib_answers = True
    #                 current_fib_answer = [] # Reset for this section
    #                 is_new_section_keyword = True
    #                 i += 1; continue

    #             # --- Processing within Sections ---
    #             if in_choices:
    #                 # New choice starts with "- identifier:" (usually indented)
    #                 if line_stripped.startswith('- identifier:'):
    #                     if current_choice: choices.append(current_choice)
    #                     current_choice = {'identifier': line_stripped[len('- identifier:'):].strip().strip('"\'') }
    #                     i += 1; continue
    #                 # Process choice fields (indented under identifier)
    #                 elif current_choice and ':' in line_stripped and indentation > 2: # Check indentation
    #                     field_key = line_stripped.split(':', 1)[0].strip()
    #                     # *** REFINED LATEX HANDLING FOR CHOICE TEXT ***
    #                     if field_key == 'text':
    #                         value, i = extract_text_value(lines, i) # Use helper
    #                         current_choice[field_key] = value
    #                         continue # extract_text_value updated 'i'
    #                     elif field_key == 'correct':
    #                         value_str, i = extract_text_value(lines, i)
    #                         current_choice[field_key] = value_str.lower() == 'true'
    #                         continue
    #                     else: # Handle other potential fields like 'feedback'
    #                         value_str, i = extract_text_value(lines, i)
    #                         current_choice[field_key] = value_str
    #                         continue
    #                 # If line is not a new identifier or field, it might be end of choices
    #                 # Handled by the indentation check at the start of the loop

    #             elif in_match_sets:
    #                 # Detect source/target sections (usually indented)
    #                 if line_stripped == 'source:':
    #                     if in_target and current_match_item: match_sets['target'].append(current_match_item)
    #                     in_source, in_target, current_match_item = True, False, None
    #                     i += 1; continue
    #                 elif line_stripped == 'target:':
    #                     if in_source and current_match_item: match_sets['source'].append(current_match_item)
    #                     in_source, in_target, current_match_item = False, True, None
    #                     i += 1; continue

    #                 # Process items within source or target
    #                 if (in_source or in_target):
    #                     if line_stripped.startswith('- identifier:'):
    #                         if current_match_item:
    #                             target_key = 'source' if in_source else 'target'
    #                             match_sets[target_key].append(current_match_item)
    #                         current_match_item = {'identifier': line_stripped[len('- identifier:'):].strip().strip('"\'')}
    #                         i += 1; continue
    #                     # Process item fields (indented under identifier)
    #                     elif current_match_item and ':' in line_stripped and indentation > 4: # Check indentation
    #                         field_key = line_stripped.split(':', 1)[0].strip()
    #                         # *** REFINED LATEX HANDLING FOR MATCH TEXT ***
    #                         if field_key == 'text':
    #                             value, i = extract_text_value(lines, i) # Use helper
    #                             current_match_item[field_key] = value
    #                             continue # extract_text_value updated 'i'
    #                         elif field_key == 'matchMax':
    #                             value_str, i = extract_text_value(lines, i)
    #                             try: current_match_item[field_key] = int(value_str)
    #                             except ValueError: current_match_item[field_key] = value_str # Store as string if not int
    #                             continue
    #                         else: # Handle other potential fields
    #                             value_str, i = extract_text_value(lines, i)
    #                             current_match_item[field_key] = value_str
    #                             continue
    #                 # If line is not source/target/identifier/field, might be end of matchSets
    #                 # Handled by the indentation check at the start of the loop

    #             elif in_correct_pairs:
    #                 if line_stripped.startswith('- - '): # Start of a pair item
    #                     if current_pair: # Should not happen if format is correct, but safeguard
    #                         correct_pairs.append(current_pair)
    #                     current_pair = [line_stripped[len('- - '):].strip().strip('"\'')]
    #                 elif line_stripped.startswith('- ') and len(current_pair) == 1 and indentation > 1: # Second item of pair, indented
    #                     current_pair.append(line_stripped[len('- '):].strip().strip('"\''))
    #                     correct_pairs.append(current_pair)
    #                     current_pair = [] # Reset for next pair
    #                 # End of section handled by indentation check
    #                 i += 1; continue # Move to next line regardless

    #             elif in_correct_sequence:
    #                 if line_stripped.startswith('- '):
    #                     correct_sequence.append(line_stripped[len('- '):].strip().strip('"\''))
    #                 # End of section handled by indentation check
    #                 i += 1; continue # Move to next line

    #             elif in_fib_answers:
    #                 # Allow blank answers defined only by '- -'
    #                 if line_stripped == '- -':
    #                     if current_fib_answer is not None: # Check if it's not the very first group marker
    #                         fib_answers.append(current_fib_answer)
    #                     current_fib_answer = [] # Start new empty group
    #                     i += 1; continue
    #                 # Start new group with first answer on same line
    #                 elif line_stripped.startswith('- - '):
    #                     if current_fib_answer is not None: # Check if it's not the very first item
    #                         fib_answers.append(current_fib_answer)
    #                     current_fib_answer = [line_stripped[len('- - '):].strip().strip('"\'')]
    #                     i += 1; continue
    #                 # Add answer to current group (indented)
    #                 elif line_stripped.startswith('- ') and indentation > 1: # Indented answer
    #                     if current_fib_answer is not None:
    #                         current_fib_answer.append(line_stripped[len('- '):].strip().strip('"\''))
    #                     else:
    #                         # Error: answer found before a group marker ('- -')
    #                         pass # Or log a warning
    #                     i += 1; continue
    #                 # End of section handled by indentation check


    #             # --- Process Regular Top-Level Fields ---
    #             # Ensure we are not inside any section and it's not a section keyword line
    #             if not any([in_choices, in_match_sets, in_correct_pairs, in_correct_sequence, in_fib_answers]) \
    #             and not is_new_section_keyword and ':' in line:

    #                 key = line.split(':', 1)[0].strip()
    #                 # *** REFINED LATEX HANDLING FOR REGULAR FIELDS (like 'question') ***
    #                 value_str, i = extract_text_value(lines, i) # Use helper

    #                 # Post-process value if it's not potentially LaTeX heavy (like 'question', 'explanation')
    #                 # Keep raw string for text fields, attempt conversion for others
    #                 if key not in ['question', 'explanation', 'text']: # Add other text fields if needed
    #                     if value_str.lower() == 'true':
    #                         value = True
    #                     elif value_str.lower() == 'false':
    #                         value = False
    #                     else:
    #                         # Try converting to number, otherwise keep as string
    #                         try:
    #                             value = int(value_str) # Or float(value_str) if needed
    #                         except ValueError:
    #                             value = value_str # Keep as string
    #                 else:
    #                     # For text fields possibly containing LaTeX, keep the raw extracted string
    #                     value = value_str

    #                 question_dict[key] = value
    #                 continue # extract_text_value updated 'i'

    #             # If we reach here, the line wasn't processed; advance index if not done by helpers
    #             # (This case should be rare if logic is correct)
    #             i += 1
    #         # --- End While Loop ---


    #         # --- Final Cleanup After Processing All Lines ---
    #         # Add any remaining items from sections that might end at EOF
    #         if in_choices and current_choice:
    #             choices.append(current_choice)
    #             question_dict['choices'] = choices
    #         if in_match_sets and current_match_item:
    #             target_key = 'source' if in_source else 'target'
    #             match_sets[target_key].append(current_match_item)
    #             question_dict['matchSets'] = match_sets
    #         if in_correct_pairs: # Should be complete, but just in case
    #             question_dict['correctPairs'] = correct_pairs
    #         if in_correct_sequence:
    #             question_dict['correctSequence'] = correct_sequence
    #         if in_fib_answers and current_fib_answer is not None: # Check needed if block ends during FIB
    #             fib_answers.append(current_fib_answer)
    #             question_dict['correctAnswers'] = fib_answers

    #         # --- Post-Processing (e.g., Default correctPairs generation) ---
    #         if question_dict.get('type') == 'match' and 'matchSets' in question_dict and 'correctPairs' not in question_dict:
    #             # (Keep existing logic for generating default pairs)
    #             if ('source' in question_dict['matchSets'] and
    #                 'target' in question_dict['matchSets'] and
    #                 question_dict['matchSets']['source'] and
    #                 question_dict['matchSets']['target']):

    #                 generated_pairs = []
    #                 source_choices = question_dict['matchSets']['source']
    #                 target_choices = question_dict['matchSets']['target']
    #                 pair_count = min(len(source_choices), len(target_choices))
    #                 for idx in range(pair_count):
    #                     source_id = source_choices[idx].get('identifier')
    #                     target_id = target_choices[idx].get('identifier')
    #                     if source_id and target_id:
    #                         generated_pairs.append([source_id, target_id])
    #                 question_dict['correctPairs'] = generated_pairs

    #         # Add the processed question dictionary to the list
    #         if question_dict: # Ensure we don't add empty dicts if block was empty/invalid
    #             questions.append(question_dict)

    #     return questions


    def _format_question(self, question: Dict, template: QuestionTemplate) -> str:
            """Format question using appropriate template"""
            try:
                if template.type == 'fib':
                    return self._format_fib(question, template.xml_content)
                elif template.type == 'mcq':
                    return self._format_mcq(question, template.xml_content)
                elif template.type == 'mrq':
                    return self._format_mrq(question, template.xml_content)
                elif template.type == 'tf':
                    return self._format_tf(question, template.xml_content)
                elif template.type == 'match':
                    return self._format_match(question, template.xml_content)
                elif template.type == 'order':
                    return self._format_order(question, template.xml_content)
                elif template.type == 'essay':
                    return self._format_essay(question, template.xml_content)
                # elif template.type == 'upload':
                #     return self._format_upload(question, template.xml_content)
                # elif template.type == 'label_image':
                #     return self._format_label_image(question, template.xml_content)
                # elif template.type == 'highlight_image':
                #     return self._format_highlight_image(question, template.xml_content)
                # elif template.type == 'highlight_text':
                #     return self._format_highlight_text(question, template.xml_content)
                # elif template.type == 'numeric':
                #     return self._format_numeric(question, template.xml_content)
                else:
                    raise ValueError(f"Formatting not implemented for type: {template.type}")
                    
            except Exception as e:
                # Include question identifier in error message for better debugging
                identifier = question.get('identifier', 'unknown')
                raise ValueError(f"Error formatting question {identifier} of type {template.type}: {str(e)}")

    def _format_mrq(self, question: Dict, template: str) -> str:
            """Format Multiple Response question according to QTI v2.2 specs"""
            # Create a mapping of choices by identifier
            choice_map = {choice['identifier']: choice['text'] for choice in question['choices']}
            
            # Get correct answers
            correct_answers = '\n            '.join(
                f'<value>{choice["identifier"]}</value>'
                for choice in question['choices']
                if choice.get('correct', False)
            )
            
            return template.format(
                identifier=question['identifier'],
                title=question['title'],
                prompt=question['prompt'],
                correct_answers=correct_answers,
                choice_a=choice_map.get('A', ''),
                choice_b=choice_map.get('B', ''),
                choice_c=choice_map.get('C', ''),
                choice_d=choice_map.get('D', ''),
                shuffle=str(question.get('shuffle', True)).lower(),
                max_choices=str(question.get('maxChoices', 0))
            )

    def _format_mcq(self, question: Dict, template: str) -> str:
            """Format Multiple Choice question according to QTI v2.2 specs with support for images"""
            # Create a mapping of choices by identifier
            choice_map = {choice['identifier']: self._escape_xml_chars(choice.get('text', '')) 
                        for choice in question.get('choices', [])}
            
            # Get correct answer - ensure it's not wrapped in quotes
            correct_answer = None
            for choice in question.get('choices', []):
                if choice.get('correct'):
                    correct_answer = choice.get('identifier')
                    break
            
            if not correct_answer:
                correct_answer = "A"  # Default if not found
            
            # Process question text
            question_text = self._escape_xml_chars(question.get('question_text', ''))
            
            # Process question image
            question_image = ''
            if 'question_image' in question and question['question_image']:
                img_html = question['question_image']
                import re
                
                # Extract image source
                src_match = re.search(r'src=["\'](.*?)["\']', img_html)
                if src_match:
                    img_src = src_match.group(1)
                    
                    # Create a proper QTI-compatible image tag
                    question_image = f'<p><img src="{img_src}" alt="Question Image" width="400"/></p>'
            
            # Build the final XML
            xml = template.format(
                identifier=question.get('identifier', ''),
                title=self._escape_xml_chars(question.get('title', '')),
                question_text=question_text,
                question_image=question_image,
                prompt=self._escape_xml_chars(question.get('prompt', '')),
                correct_answer=correct_answer,  # Ensure this is just the ID, not quoted
                choice_a=choice_map.get('A', ''),
                choice_b=choice_map.get('B', ''),
                choice_c=choice_map.get('C', ''),
                choice_d=choice_map.get('D', ''),
                choice_a_image='',
                choice_b_image='',
                choice_c_image='',
                choice_d_image=''
            )
            
            return xml


        #commented on 3/18
        # def _format_fib(self, question: Dict, template: str) -> str:
        #     """Format Fill in Blank question according to QTI v2.2 specs"""
        #     # Generate response declarations
        #     response_declarations = []
            
        #     # Create one response declaration per blank
        #     for i, answers in enumerate(question['correctAnswers'], 1):
        #         values = []
        #         for answer in answers:
        #             # Properly handle a single dash
        #             if answer == '-':
        #                 answer_str = '-'
        #             else:
        #                 answer_str = str(answer)
        #             # Escape XML characters in the answer
        #             answer_str = self._escape_xml_chars(answer_str)
        #             values.append(f'<value>{answer_str}</value>')
                    
        #         declaration = f"""<responseDeclaration identifier="RESPONSE{i}" cardinality="single" baseType="string">
        #         <correctResponse>
        #             {' '.join(values)}
        #         </correctResponse>
        #     </responseDeclaration>"""
        #         response_declarations.append(declaration)
            
        #     # Format text parts with interaction
        #     text = self._escape_xml_chars(question['prompt'])
            
        #     # Count asterisks to know how many blanks we have
        #     num_blanks = text.count('*')
            
        #     # Replace each asterisk with a proper interaction, with unique identifiers
        #     for i in range(1, num_blanks + 1):
        #         interaction = f'<textEntryInteraction responseIdentifier="RESPONSE{i}" expectedLength="{question.get("expectedLength", 20)}"/>'
        #         # Replace only the first occurrence of * each time
        #         text = text.replace('*', interaction, 1)
            
        #     return template.format(
        #         identifier=question['identifier'],
        #         title=self._escape_xml_chars(question['title']),
        #         response_declarations='\n'.join(response_declarations),
        #         text_parts=text
        #     )
        
    def _format_fib(self, question_data: Dict, template_xml: str) -> str:
            """
            Format a Fill-in-the-Blank question into QTI XML.
            
            Args:
                question_data (Dict): The question data from the parsed YAML.
                template_xml (str): The XML template content for the FIB question type.
                
            Returns:
                str: The formatted QTI XML for the question.
            """
            import uuid
            # Extract question data
            identifier = question_data.get('identifier', f"fib_{uuid.uuid4().hex[:8]}")
            title = question_data.get('title', 'Fill in the Blank Question')
            prompt = question_data.get('prompt', '')
            correct_answers = question_data.get('correctAnswers', [])
            expected_length = question_data.get('expectedLength', 20)
            
            # Find all blanks in the prompt
            # Look specifically for standalone asterisks (with spaces before and after, or at beginning/end)
            
            # blank_markers = list(re.finditer(r'(?<=^|[^A-Za-z0-9])_(?=$|[^A-Za-z0-9])', prompt))
            # #blank_markers = re.finditer(r'(?<=\s)\*(?=\s)|^\*(?=\s)|(?<=\s)\*$', prompt)
            # blank_positions = [match.start() for match in blank_markers]
            import re

            # Find all underscores in the prompt
            blank_positions = []
            for match in re.finditer(r'_', prompt):
                pos = match.start()
                # Check the preceding character (if any) is not alphanumeric
                if pos > 0 and prompt[pos - 1].isalnum():
                    continue
                # Check the following character (if any) is not alphanumeric
                if pos < len(prompt) - 1 and prompt[pos + 1].isalnum():
                    continue
                blank_positions.append(pos)

            if len(blank_positions) != len(correct_answers):
                raise ValueError(f"Number of blanks ({len(blank_positions)}) does not match number of answer sets ({len(correct_answers)})")



            # If no blanks found with the regex, fallback to simple character search
            if not blank_positions:
                blank_positions = [pos for pos, char in enumerate(prompt) if char == '*']
            
            if len(blank_positions) != len(correct_answers):
                raise ValueError(f"Number of blanks ({len(blank_positions)}) does not match number of answer sets ({len(correct_answers)})")
            
            # Generate response declarations for each blank
            response_declarations = []
            for i, answers in enumerate(correct_answers, 1):
                response_id = f"RESPONSE{i}"
                response_decl = f"""<responseDeclaration identifier="{response_id}" cardinality="single" baseType="string">
            <correctResponse>
        """
                # Add each possible correct answer
                for answer in answers:
                    response_decl += f"        <value>{answer}</value>\n"
                
                response_decl += """    </correctResponse>
        </responseDeclaration>"""
                response_declarations.append(response_decl)
            
            # Combine all response declarations
            all_response_declarations = "\n".join(response_declarations)
            
            # Split the prompt text around the blanks and create the prompt with interactions
            prompt_parts = []
            prev_pos = 0
            for i, pos in enumerate(blank_positions, 1):
                # Add text before this blank
                prompt_parts.append(prompt[prev_pos:pos])
                # Add the interaction element
                prompt_parts.append(f'<textEntryInteraction responseIdentifier="RESPONSE{i}" expectedLength="{expected_length}"/>')
                # Update previous position to after this blank
                prev_pos = pos + 1
            
            # Add any remaining text after the last blank
            prompt_parts.append(prompt[prev_pos:])
            
            # Join all parts to create the prompt with interactions
            prompt_with_interactions = ''.join(prompt_parts)
            
            # Replace placeholders in the template
            formatted_xml = template_xml.format(
                identifier=identifier,
                title=title,
                adaptive="false",
                timeDependent="false",
                response_declarations=all_response_declarations,
                prompt_with_interactions=prompt_with_interactions
            )
            
            return formatted_xml
        
    def _format_tf(self, question: Dict, template: str) -> str:
            """Format True/False question according to QTI v2.2 specs"""
            return template.format(
                identifier=question['identifier'],
                title=question['title'],
                prompt=question['prompt'],
                correct_answer=str(question['correct']).lower()  # Changed from correct_value to correct_answer
            )

    def _format_match(self, question: Dict, template: str) -> str:
                """Format Matching question according to QTI v2.2 specs"""
                # Format source choices
                source_choices = '\n            '.join(
                    f'<simpleAssociableChoice identifier="{choice["identifier"]}" '
                    f'matchMax="{choice.get("matchMax", 1)}">{choice["text"]}</simpleAssociableChoice>'
                    for choice in question['matchSets']['source']
                )
                
                # Format target choices
                target_choices = '\n            '.join(
                    f'<simpleAssociableChoice identifier="{choice["identifier"]}" '
                    f'matchMax="{choice.get("matchMax", 1)}">{choice["text"]}</simpleAssociableChoice>'
                    for choice in question['matchSets']['target']
                )
                
                # Format correct pairs
                correct_pairs = '\n            '.join(
                    f'<value>{pair[0]} {pair[1]}</value>'
                    for pair in question['correctPairs']
                )
                
                return template.format(
                    identifier=question['identifier'],
                    title=question['title'],
                    prompt=question['prompt'],
                    source_choices=source_choices,
                    target_choices=target_choices,
                    correct_pairs=correct_pairs,
                    shuffle=str(question.get('shuffle', True)).lower(),
                    max_associations=str(question.get('maxAssociations', 0))
                )

    def _format_order(self, question: Dict, template: str) -> str:
            """Format Ordering question according to QTI v2.2 specs with improved error handling"""
            try:
                # Format choices
                choices = '\n            '.join(
                    f'<simpleChoice identifier="{choice["identifier"]}">{choice["text"]}</simpleChoice>'
                    for choice in question['choices']
                )
                
                # Format correct sequence
                correct_sequence = '\n            '.join(
                    f'<value>{choice_id}</value>'
                    for choice_id in question['correctSequence']
                )
                
                return template.format(
                    identifier=question['identifier'],
                    title=question['title'],
                    prompt=question['prompt'],
                    choices=choices,
                    correct_sequence=correct_sequence,
                    shuffle=str(question.get('shuffle', True)).lower()
                )
            except Exception as e:
                raise ValueError(f"Error formatting order question: {str(e)}")

    def _format_essay(self, question: Dict, template: str) -> str:
            """Format Essay question according to QTI v2.2 specs"""
            # Handle response format if specified
            format_attr = ''
            if 'responseFormat' in question:
                format_attr = f' format="{question["responseFormat"]}"'
            
            return template.format(
                identifier=question['identifier'],
                title=question['title'],
                prompt=question['prompt'],
                expected_lines=str(question['expectedLines']),
                format_attr=format_attr
            )

    def _validate_common(self, question: Dict) -> bool:
            """Validate common fields required for all question types with special handling for image-based questions"""
            try:
                # Load common settings from metadata - get the first occurrence
                common_settings = self.metadata.get('common_settings', {})
                
                # Special case for image-based MCQ questions - allow either prompt or question_text
                if question.get('type') == 'mcq' and 'question_image' in question:
                    # For image-based questions, either prompt or question_text must be present
                    if 'prompt' not in question and 'question_text' not in question:
                        raise ValueError(f"Image-based MCQ {question.get('identifier', 'unknown')}: "
                                    f"Either 'prompt' or 'question_text' must be present")
                        
                    # Modify required attributes for image-based questions
                    required_attributes = [attr for attr in common_settings.get('required_attributes', []) 
                                        if attr != 'prompt' or 'prompt' in question]
                else:
                    # Regular required attributes check
                    required_attributes = common_settings.get('required_attributes', 
                                        ['identifier', 'title', 'adaptive', 'timeDependent', 'prompt'])
                
                # Check required attributes
                for attr in required_attributes:
                    if attr not in question:
                        raise ValueError(f"Missing required attribute: {attr}")
                    
                    # Type checking if attribute_types is defined and contains this attribute
                    attribute_types = common_settings.get('attribute_types', {})
                    if attr in attribute_types:
                        expected_type = attribute_types[attr]
                        value = question[attr]
                        if expected_type == 'boolean' and not isinstance(value, bool):
                            raise ValueError(f"Attribute {attr} must be boolean, got {type(value)}")
                        elif expected_type == 'string' and not isinstance(value, str):
                            raise ValueError(f"Attribute {attr} must be string, got {type(value)}")
                
                return True
                
            except KeyError as e:
                # This provides more context about which field is causing issues
                raise ValueError(f"Error in metadata configuration: {str(e)}")
        
    def _validate_choices(self, question: Dict, question_type: str) -> bool:
            """Validate choice-based questions (MCQ, MRQ) with support for images"""
            validation_rules = self.metadata['question_types'][question_type]['validation_rules']
            
            if 'choices' not in question:
                raise ValueError(f"Question {question['identifier']}: Missing choices")
            
            choices = question['choices']
            # Check minimum number of choices
            if len(choices) < validation_rules['min_choices']:
                raise ValueError(
                    f"Question {question['identifier']}: Must have at least "
                    f"{validation_rules['min_choices']} choices, got {len(choices)}"
                )
            
            # Check choice format
            choice_format = validation_rules['choices_format']
            for choice in choices:
                for field in choice_format['required_fields']:
                    if field not in choice:
                        raise ValueError(
                            f"Question {question['identifier']}: Choice missing required field: {field}"
                        )
                    
                    # Type checking for choice fields
                    expected_type = choice_format['field_types'][field]
                    value = choice[field]
                    if expected_type == 'boolean' and not isinstance(value, bool):
                        raise ValueError(
                            f"Question {question['identifier']}: Choice field {field} "
                            f"must be boolean, got {type(value)}"
                        )
                    elif expected_type == 'string' and not isinstance(value, str):
                        raise ValueError(
                            f"Question {question['identifier']}: Choice field {field} "
                            f"must be string, got {type(value)}"
                        )
                
                # Check for image field if present
                if 'image' in choice and not isinstance(choice['image'], str) and choice['image'] is not None:
                    raise ValueError(
                        f"Question {question['identifier']}: Choice image must be a string (HTML) or null"
                    )
            
            # Additional MCQ validation
            if question_type == 'mcq':
                correct_count = sum(1 for c in choices if c.get('correct'))
                if correct_count != 1:
                    raise ValueError(
                        f"MCQ {question['identifier']}: Must have exactly one correct answer, "
                        f"got {correct_count}"
                    )
            # Additional MRQ validation
            elif question_type == 'mrq':
                if not any(c.get('correct') for c in choices):
                    raise ValueError(
                        f"MRQ {question['identifier']}: Must have at least one correct answer"
                    )
            
            # Check for question image if present
            if 'question_image' in question and not isinstance(question['question_image'], str):
                raise ValueError(
                    f"Question {question['identifier']}: question_image must be a string (HTML)"
                )
            
            return True

    def _validate_numeric(self, question: Dict) -> bool:
            """Validate numeric question format"""
            validation_rules = self.metadata['question_types']['numeric']['validation_rules']
            
            # Check correctAnswers
            if 'correctAnswers' not in question:
                raise ValueError(f"Numeric question {question['identifier']}: Missing correctAnswers")
            
            answers = question['correctAnswers']
            if not isinstance(answers, list) or not answers:
                raise ValueError(
                    f"Numeric question {question['identifier']}: correctAnswers must be non-empty array"
                )
            
            # Check each answer can be converted to float
            for answer_set in answers:
                if not isinstance(answer_set, list):
                    raise ValueError(
                        f"Numeric question {question['identifier']}: Each answer set must be an array"
                    )
                for answer in answer_set:
                    try:
                        float(answer)
                    except (ValueError, TypeError):
                        raise ValueError(
                            f"Numeric question {question['identifier']}: "
                            f"Answer '{answer}' must be a valid number"
                        )
            
            # Check expectedLength
            if 'expectedLength' in question:
                length = question['expectedLength']
                try:
                    length = int(length)
                    if not validation_rules['expectedLength']['min'] <= length <= validation_rules['expectedLength']['max']:
                        raise ValueError(
                            f"Numeric question {question['identifier']}: expectedLength must be between "
                            f"{validation_rules['expectedLength']['min']} and {validation_rules['expectedLength']['max']}"
                        )
                except (ValueError, TypeError):
                    raise ValueError(
                        f"Numeric question {question['identifier']}: expectedLength must be an integer"
                    )
            
            # Check tolerance if present
            if 'tolerance' in question:
                try:
                    tolerance = float(question['tolerance'])
                    if not 0 <= tolerance <= validation_rules['tolerance']['max']:
                        raise ValueError(
                            f"Numeric question {question['identifier']}: tolerance must be between "
                            f"0 and {validation_rules['tolerance']['max']}"
                        )
                except (ValueError, TypeError):
                    raise ValueError(
                        f"Numeric question {question['identifier']}: tolerance must be a number"
                    )
            
            return True

    def _validate_fib(self, question: Dict) -> bool:
            """Validate Fill in Blank question format"""
            validation_rules = self.metadata['question_types']['fib']['validation_rules']
            
            # Validate prompt contains blanks
            if '_' not in question['prompt']:
                raise ValueError(f"FIB question {question['identifier']}: Prompt must contain blank(s) marked with _")
            
            # Count blanks - consecutive underscores count as one blank
            import re
            underscores = re.findall(r'_+', question['prompt'])
            num_blanks = len(underscores)
            
            # Validate correctAnswers
            if 'correctAnswers' not in question:
                raise ValueError(f"FIB question {question['identifier']}: Missing correctAnswers")
            
            answers = question['correctAnswers']
            if not isinstance(answers, list) or len(answers) != num_blanks:
                raise ValueError(
                    f"FIB question {question['identifier']}: Number of answer sets ({len(answers) if isinstance(answers, list) else 0}) "
                    f"must match number of blanks ({num_blanks})"
                )
            
            # Check each answer set
            for i, answer_set in enumerate(answers, 1):
                if not isinstance(answer_set, list) or not answer_set:
                    raise ValueError(f"FIB question {question['identifier']}: Answer set {i} must be non-empty array")
                
                # Check answer types and convert to strings
                for answer in answer_set:
                    # Special handling for dash as an answer
                    if answer == '-' or answer == '---':
                        continue  # Skip validation for single dash
                    if not isinstance(answer, (str, int, float)):
                        raise ValueError(f"FIB question {question['identifier']}: All answers must be convertible to strings")

            # Special handling for dashes in answer sets
            for i, answer_set in enumerate(question['correctAnswers']):
                for j, answer in enumerate(answer_set):
                    # Handle special case where answer is just a dash
                    if answer == '-' or answer == '---':
                        answer_set[j] = '-'  # Normalize to a single dash   

            # Validate expectedLength
            if 'expectedLength' in question:
                length = question['expectedLength']
                try:
                    length = int(length)
                    if not validation_rules['expectedLength']['min'] <= length <= validation_rules['expectedLength']['max']:
                        raise ValueError(
                            f"FIB question {question['identifier']}: expectedLength must be between "
                            f"{validation_rules['expectedLength']['min']} and {validation_rules['expectedLength']['max']}"
                        )
                except (ValueError, TypeError):
                    raise ValueError(f"FIB question {question['identifier']}: expectedLength must be an integer")
            
            return True

    def _validate_match(self, question: Dict) -> bool:
            """Validate matching question format"""
            validation_rules = self.metadata['question_types']['match']['validation_rules']
            
            # Check required sections
            if 'matchSets' not in question:
                raise ValueError(f"Match question {question['identifier']}: Missing matchSets")
            
            match_sets = question['matchSets']
            if 'source' not in match_sets or 'target' not in match_sets:
                raise ValueError(f"Match question {question['identifier']}: matchSets must contain both source and target")
            
            # Validate source and target formats
            set_format = validation_rules['matchSets_format']['source_target_format']
            for set_type in ['source', 'target']:
                items = match_sets[set_type]
                if len(items) < validation_rules['min_pairs']:
                    raise ValueError(
                        f"Match question {question['identifier']}: {set_type} must have at least "
                        f"{validation_rules['min_pairs']} items"
                    )
                
                # Check each item's format
                for item in items:
                    for field in set_format['required_fields']:
                        if field not in item:
                            raise ValueError(
                                f"Match question {question['identifier']}: {set_type} item missing required field: {field}"
                            )
                        
                        # Type checking
                        expected_type = set_format['field_types'][field]
                        value = item[field]
                        if expected_type == 'string' and not isinstance(value, str):
                            raise ValueError(
                                f"Match question {question['identifier']}: {set_type} field {field} must be string"
                            )
                        elif expected_type == 'integer' and not isinstance(value, int):
                            raise ValueError(
                                f"Match question {question['identifier']}: {set_type} field {field} must be integer"
                            )
            
            # Validate correctPairs
            if 'correctPairs' not in question:
                raise ValueError(f"Match question {question['identifier']}: Missing correctPairs")
            
            pairs = question['correctPairs']
            if len(pairs) < validation_rules['min_pairs']:
                raise ValueError(
                    f"Match question {question['identifier']}: Must have at least "
                    f"{validation_rules['min_pairs']} correct pairs"
                )
            
            # Validate pair format and references
            source_ids = {item['identifier'] for item in match_sets['source']}
            target_ids = {item['identifier'] for item in match_sets['target']}
            
            for pair in pairs:
                if not isinstance(pair, list) or len(pair) != 2:
                    raise ValueError(f"Match question {question['identifier']}: Each pair must be array of length 2")
                if pair[0] not in source_ids:
                    raise ValueError(f"Match question {question['identifier']}: Invalid source identifier in pair: {pair[0]}")
                if pair[1] not in target_ids:
                    raise ValueError(f"Match question {question['identifier']}: Invalid target identifier in pair: {pair[1]}")
            
            return True

    def _validate_order(self, question: Dict) -> bool:
            """Validate ordering question format"""
            validation_rules = self.metadata['question_types']['order']['validation_rules']
            
            # Check choices
            if 'choices' not in question:
                raise ValueError(f"Order question {question['identifier']}: Missing choices")
            
            choices = question['choices']
            if len(choices) < validation_rules['min_choices']:
                raise ValueError(
                    f"Order question {question['identifier']}: Must have at least "
                    f"{validation_rules['min_choices']} choices"
                )
            
            if len(choices) > validation_rules['max_choices']:
                raise ValueError(
                    f"Order question {question['identifier']}: Cannot have more than "
                    f"{validation_rules['max_choices']} choices"
                )
            
            # Validate choice format
            choice_format = validation_rules['choices_format']
            choice_ids = set()
            for choice in choices:
                for field in choice_format['required_fields']:
                    if field not in choice:
                        raise ValueError(
                            f"Order question {question['identifier']}: Choice missing required field: {field}"
                        )
                    
                    # Type checking
                    expected_type = choice_format['field_types'][field]
                    value = choice[field]
                    if expected_type == 'string' and not isinstance(value, str):
                        raise ValueError(
                            f"Order question {question['identifier']}: Choice field {field} must be string"
                        )
                
                choice_ids.add(choice['identifier'])
            
            # Validate correctSequence
            if 'correctSequence' not in question:
                raise ValueError(f"Order question {question['identifier']}: Missing correctSequence")
            
            sequence = question['correctSequence']
            if len(sequence) != len(choices):
                raise ValueError(
                    f"Order question {question['identifier']}: correctSequence length must match choices length"
                )
            
            # Validate sequence references valid choices
            for item_id in sequence:
                if item_id not in choice_ids:
                    raise ValueError(
                        f"Order question {question['identifier']}: Invalid identifier in sequence: {item_id}"
                    )
            
            # Check for duplicate ids in sequence
            if len(set(sequence)) != len(sequence):
                raise ValueError(f"Order question {question['identifier']}: correctSequence contains duplicates")
            
            return True

    def _validate_tf(self, question: Dict) -> bool:
            """Validate True/False question format"""
            if 'correct' not in question:
                raise ValueError(f"TF question {question['identifier']}: Must provide correct answer")
                
            if not isinstance(question['correct'], bool):
                raise ValueError(f"TF question {question['identifier']}: Correct answer must be boolean")
                
            return True

    def _validate_label_image(self, question: Dict) -> bool:
            """Validate image labeling question format"""
            validation_rules = self.metadata['question_types']['label_image']['validation_rules']
            
            # Validate image section
            if 'image' not in question:
                raise ValueError(f"Label image question {question['identifier']}: Missing image")
            
            image = question['image']
            image_format = validation_rules['image_format']
            for field in image_format['required_fields']:
                if field not in image:
                    raise ValueError(f"Label image question {question['identifier']}: Image missing required field: {field}")
                
                # Type checking for image fields
                expected_type = image_format['field_types'][field]
                value = image[field]
                if expected_type == 'integer' and not isinstance(value, int):
                    raise ValueError(
                        f"Label image question {question['identifier']}: Image field {field} must be integer"
                    )
                elif expected_type == 'string' and not isinstance(value, str):
                    raise ValueError(
                        f"Label image question {question['identifier']}: Image field {field} must be string"
                    )
            
            # Validate image type
            if image['type'] not in self.metadata['common_settings']['media_settings']['allowed_formats']:
                raise ValueError(
                    f"Label image question {question['identifier']}: Invalid image type: {image['type']}"
                )
            
            # Validate labels
            if 'labels' not in question:
                raise ValueError(f"Label image question {question['identifier']}: Missing labels")
            
            labels = question['labels']
            labels_format = validation_rules['labels_format']
            label_ids = set()
            for label in labels:
                for field in labels_format['required_fields']:
                    if field not in label:
                        raise ValueError(
                            f"Label image question {question['identifier']}: Label missing required field: {field}"
                        )
                    
                    # Type checking
                    expected_type = labels_format['field_types'][field]
                    value = label[field]
                    if expected_type == 'string' and not isinstance(value, str):
                        raise ValueError(
                            f"Label image question {question['identifier']}: Label field {field} must be string"
                        )
                        
                label_ids.add(label['identifier'])
            
            # Validate targets
            if 'targets' not in question:
                raise ValueError(f"Label image question {question['identifier']}: Missing targets")
            
            targets = question['targets']
            targets_format = validation_rules['targets_format']
            target_ids = set()
            for target in targets:
                for field in targets_format['required_fields']:
                    if field not in target:
                        raise ValueError(
                            f"Label image question {question['identifier']}: Target missing required field: {field}"
                        )
                    
                    # Type checking
                    expected_type = targets_format['field_types'][field]
                    value = target[field]
                    if expected_type == 'integer' and not isinstance(value, int):
                        raise ValueError(
                            f"Label image question {question['identifier']}: Target field {field} must be integer"
                        )
                    elif expected_type == 'string' and not isinstance(value, str):
                        raise ValueError(
                            f"Label image question {question['identifier']}: Target field {field} must be string"
                        )
                        
                target_ids.add(target['identifier'])
            
            # Validate correctPairs
            if 'correctPairs' not in question:
                raise ValueError(f"Label image question {question['identifier']}: Missing correctPairs")
            
            pairs = question['correctPairs']
            if len(pairs) < validation_rules['min_pairs']:
                raise ValueError(
                    f"Label image question {question['identifier']}: Must have at least "
                    f"{validation_rules['min_pairs']} correct pairs"
                )
            
            for pair in pairs:
                if not isinstance(pair, list) or len(pair) != 2:
                    raise ValueError(f"Label image question {question['identifier']}: Each pair must be array of length 2")
                if pair[0] not in label_ids:
                    raise ValueError(f"Label image question {question['identifier']}: Invalid label identifier in pair: {pair[0]}")
                if pair[1] not in target_ids:
                    raise ValueError(f"Label image question {question['identifier']}: Invalid target identifier in pair: {pair[1]}")
            
            return True

    def _validate_highlight_text(self, question: Dict) -> bool:
            """Validate text highlighting question format"""
            validation_rules = self.metadata['question_types']['highlight_text']['validation_rules']
            
            # Validate text segments
            if 'text' not in question:
                raise ValueError(f"Highlight text question {question['identifier']}: Missing text")
            
            text = question['text']
            text_format = validation_rules['text_format']
            for segment in text:
                for field in text_format['required_fields']:
                    if field not in segment:
                        raise ValueError(
                            f"Highlight text question {question['identifier']}: Text segment missing field: {field}"
                        )
                    
                    # Type checking
                    expected_type = text_format['field_types'][field]
                    value = segment[field]
                    if expected_type == 'string' and not isinstance(value, str):
                        raise ValueError(
                            f"Highlight text question {question['identifier']}: Text segment field {field} must be string"
                        )
                    elif expected_type == 'boolean' and not isinstance(value, bool):
                        raise ValueError(
                            f"Highlight text question {question['identifier']}: Text segment field {field} must be boolean"
                        )
            
            # Validate maxSelections if present
            if 'maxSelections' in question:
                max_selections = question['maxSelections']
                try:
                    max_selections = int(max_selections)
                    if not validation_rules['maxSelections']['min'] <= max_selections <= validation_rules['maxSelections']['max']:
                        raise ValueError(
                            f"Highlight text question {question['identifier']}: maxSelections must be between "
                            f"{validation_rules['maxSelections']['min']} and {validation_rules['maxSelections']['max']}"
                        )
                except (ValueError, TypeError):
                    raise ValueError(
                        f"Highlight text question {question['identifier']}: maxSelections must be an integer"
                    )
            
            return True

    def _validate_essay(self, question: Dict) -> bool:
            """Validate essay question format"""
            validation_rules = self.metadata['question_types']['essay']['validation_rules']
            
            # Validate expectedLines
            if 'expectedLines' not in question:
                raise ValueError(f"Essay question {question['identifier']}: Missing expectedLines")
            
            expected_lines = question['expectedLines']
            try:
                lines = int(expected_lines)
                if not validation_rules['expectedLines']['min'] <= lines <= validation_rules['expectedLines']['max']:
                    raise ValueError(
                        f"Essay question {question['identifier']}: expectedLines must be between "
                        f"{validation_rules['expectedLines']['min']} and {validation_rules['expectedLines']['max']}"
                    )
            except (ValueError, TypeError):
                raise ValueError(f"Essay question {question['identifier']}: expectedLines must be an integer")
            
            # Validate responseFormat if present
            if 'responseFormat' in question:
                response_format = question['responseFormat']
                if response_format not in validation_rules['responseFormat']['allowed']:
                    raise ValueError(
                        f"Essay question {question['identifier']}: Invalid responseFormat. "
                        f"Must be one of: {', '.join(validation_rules['responseFormat']['allowed'])}"
                    )
            
            return True

    def _validate_upload(self, question: Dict) -> bool:
            """Validate file upload question format"""
            validation_rules = self.metadata['question_types']['upload']['validation_rules']
            
            # Validate maxSize
            if 'maxSize' not in question:
                raise ValueError(f"Upload question {question['identifier']}: Missing maxSize")
            
            max_size = question['maxSize']
            try:
                size = int(max_size)
                if not validation_rules['maxSize']['min'] <= size <= validation_rules['maxSize']['max']:
                    raise ValueError(
                        f"Upload question {question['identifier']}: maxSize must be between "
                        f"{validation_rules['maxSize']['min']} and {validation_rules['maxSize']['max']} bytes"
                    )
            except (ValueError, TypeError):
                raise ValueError(f"Upload question {question['identifier']}: maxSize must be an integer")
            
            # Validate allowedTypes if present
            if 'allowedTypes' in question:
                allowed_types = question['allowedTypes']
                if not isinstance(allowed_types, list):
                    raise ValueError(f"Upload question {question['identifier']}: allowedTypes must be an array")
                
                for file_type in allowed_types:
                    if file_type not in validation_rules['allowedTypes']['allowed']:
                        raise ValueError(
                            f"Upload question {question['identifier']}: Invalid file type: {file_type}. "
                            f"Must be one of: {', '.join(validation_rules['allowedTypes']['allowed'])}"
                        )
            
            return True

    def _validate_highlight_image(self, question: Dict) -> bool:
        """Validate image highlighting question format"""
        validation_rules = self.metadata['question_types']['highlight_image']['validation_rules']
        media_settings = self.metadata['common_settings']['media_settings']
        
        # Validate image section
        if 'image' not in question:
            raise ValueError(f"Highlight image question {question['identifier']}: Missing image")
        
        # Validate image metadata
        image = question['image']
        for field in ['source', 'width', 'height', 'type']:
            if field not in image:
                raise ValueError(f"Highlight image question {question['identifier']}: Image missing field: {field}")
        
        # Validate image type
        if image['type'] not in media_settings['allowed_formats']:
            raise ValueError(
                f"Highlight image question {question['identifier']}: Invalid image type: {image['type']}. "
                f"Must be one of: {', '.join(media_settings['allowed_formats'])}"
            )
        
        # Validate image dimensions
        try:
            width = int(image['width'])
            height = int(image['height'])
            min_dim, max_dim = media_settings['min_dimensions'], media_settings['max_dimensions']
            
            if not (min_dim[0] <= width <= max_dim[0] and min_dim[1] <= height <= max_dim[1]):
                raise ValueError(
                    f"Highlight image question {question['identifier']}: Image dimensions must be between "
                    f"{min_dim} and {max_dim} pixels"
                )
        except (ValueError, TypeError):
            raise ValueError(f"Highlight image question {question['identifier']}: Invalid image dimensions")
        
        # Validate hotspots
        if 'hotspots' not in question:
            raise ValueError(f"Highlight image question {question['identifier']}: Missing hotspots")
        
        hotspots = question['hotspots']
        if not hotspots:
            raise ValueError(f"Highlight image question {question['identifier']}: Must have at least one hotspot")
        
        hotspot_ids = set()
        for hotspot in hotspots:
            # Check required fields
            if not all(field in hotspot for field in ['identifier', 'shape', 'x', 'y']):
                raise ValueError(
                    f"Highlight image question {question['identifier']}: "
                    "Hotspot missing required fields (identifier, shape, x, y)"
                )
            
            # Validate shape and coordinates
            shape = hotspot['shape']
            if shape not in ['rect', 'circle', 'poly']:
                raise ValueError(
                    f"Highlight image question {question['identifier']}: "
                    f"Invalid hotspot shape: {shape}. Must be rect, circle, or poly"
                )
            
            try:
                x = int(hotspot['x'])
                y = int(hotspot['y'])
                
                # Check coordinates are within image bounds
                if not (0 <= x <= width and 0 <= y <= height):
                    raise ValueError(
                        f"Highlight image question {question['identifier']}: "
                        f"Hotspot coordinates ({x}, {y}) outside image bounds"
                    )
                    
                # Shape-specific validation
                if shape == 'rect':
                    if not all(field in hotspot for field in ['width', 'height']):
                        raise ValueError(
                            f"Highlight image question {question['identifier']}: "
                            "Rectangle hotspot missing width or height"
                        )
                    w = int(hotspot['width'])
                    h = int(hotspot['height'])
                    if x + w > width or y + h > height:
                        raise ValueError(
                            f"Highlight image question {question['identifier']}: "
                            "Rectangle hotspot extends beyond image bounds"
                        )
                elif shape == 'circle':
                    if 'radius' not in hotspot:
                        raise ValueError(
                            f"Highlight image question {question['identifier']}: "
                            "Circle hotspot missing radius"
                        )
                    r = int(hotspot['radius'])
                    if x + r > width or y + r > height or x - r < 0 or y - r < 0:
                        raise ValueError(
                            f"Highlight image question {question['identifier']}: "
                            "Circle hotspot extends beyond image bounds"
                        )
                elif shape == 'poly':
                    if 'coords' not in hotspot:
                        raise ValueError(
                            f"Highlight image question {question['identifier']}: "
                            "Polygon hotspot missing coords"
                        )
                    coords = hotspot['coords']
                    if not isinstance(coords, list) or len(coords) % 2 != 0:
                        raise ValueError(
                            f"Highlight image question {question['identifier']}: "
                            "Invalid polygon coordinates format"
                        )
                    for coord in coords:
                        if not isinstance(coord, int):
                            raise ValueError(
                                f"Highlight image question {question['identifier']}: "
                                "Polygon coordinates must be integers"
                            )
                        if coord < 0 or coord > max(width, height):
                            raise ValueError(
                                f"Highlight image question {question['identifier']}: "
                                "Polygon coordinates outside image bounds"
                            )
                            
            except (ValueError, TypeError):
                raise ValueError(
                    f"Highlight image question {question['identifier']}: "
                    "Invalid hotspot coordinates"
                )
                
            hotspot_ids.add(hotspot['identifier'])
        
        # Validate correctHotspots
        if 'correctHotspots' not in question:
            raise ValueError(f"Highlight image question {question['identifier']}: Missing correctHotspots")
        
        correct_hotspots = question['correctHotspots']
        if not isinstance(correct_hotspots, list):
            raise ValueError(f"Highlight image question {question['identifier']}: correctHotspots must be an array")
        
        # Validate correctHotspots references valid hotspots
        for hotspot_id in correct_hotspots:
            if hotspot_id not in hotspot_ids:
                raise ValueError(
                    f"Highlight image question {question['identifier']}: "
                    f"Invalid hotspot identifier in correctHotspots: {hotspot_id}"
                )
        
        # Validate maxChoices if present
        if 'maxChoices' in question:
            try:
                max_choices = int(question['maxChoices'])
                if max_choices < 0:
                    raise ValueError(
                        f"Highlight image question {question['identifier']}: "
                        "maxChoices must be non-negative"
                    )
                if max_choices > 0 and max_choices < len(correct_hotspots):
                    raise ValueError(
                        f"Highlight image question {question['identifier']}: "
                        f"maxChoices ({max_choices}) is less than number of correct hotspots ({len(correct_hotspots)})"
                    )
            except (ValueError, TypeError):
                raise ValueError(
                    f"Highlight image question {question['identifier']}: "
                    "maxChoices must be an integer"
                )
        
        return True

    def _prettify(self, xml_str: str) -> str:
        """Format XML string with proper indentation"""
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent='  ')
        return '\n'.join(line for line in pretty_xml.split('\n') if line.strip())

            # Add similar _format_* methods for other question types...



        # def _custom_yaml_parse(self, yaml_str: str) -> List[Dict]:
        #     """Parse YAML content manually to handle LaTeX, HTML, and nested structures"""
        #     import re
            
        #     # Split into individual questions
        #     question_blocks = re.split(r'(?=^- type:)', yaml_str, flags=re.MULTILINE)
        #     questions = []
            
        #     for block in question_blocks:
        #         if not block.strip():
        #             continue
                    
        #         # Process each question
        #         question_dict = {}
        #         lines = block.strip().split('\n')
                
        #         # Process header line (- type: xxx)
        #         if lines[0].startswith('- type:'):
        #             question_dict['type'] = lines[0].split(':', 1)[1].strip().strip('"\'')
                
        #         # Process remaining fields
        #         i = 1
        #         in_choices = False
        #         choices = []
        #         current_choice = None
                
        #         # For match-type questions
        #         in_match_sets = False
        #         match_sets = {'source': [], 'target': []}
        #         in_source = False
        #         in_target = False
        #         current_match_item = None
                
        #         # For correctPairs in match questions
        #         in_correct_pairs = False
        #         correct_pairs = []
                
        #         # For order type questions
        #         in_correct_sequence = False
        #         correct_sequence = []
                
        #         while i < len(lines):
        #             line = lines[i].rstrip()
                    
        #             # Skip empty lines
        #             if not line.strip():
        #                 i += 1
        #                 continue
                    
        #             # Handle match-type questions specifically
        #             if question_dict.get('type') == 'match':
        #                 # Detect matchSets section
        #                 if line.strip() == 'matchSets:':
        #                     in_match_sets = True
        #                     i += 1
        #                     continue
                        
        #                 # Process matchSets subsections
        #                 if in_match_sets:
        #                     # Detect source section
        #                     if line.strip() == 'source:':
        #                         in_source = True
        #                         in_target = False
        #                         i += 1
        #                         continue
                            
        #                     # Detect target section
        #                     elif line.strip() == 'target:':
        #                         in_source = False
        #                         in_target = True
        #                         i += 1
        #                         continue
                            
        #                     # Process items in source or target
        #                     elif (in_source or in_target) and line.strip().startswith('- identifier:'):
        #                         # Store previous item if exists
        #                         if current_match_item:
        #                             if in_source:
        #                                 match_sets['source'].append(current_match_item)
        #                             else:
        #                                 match_sets['target'].append(current_match_item)
                                
        #                         # Start new item
        #                         current_match_item = {'identifier': line.strip()[13:].strip().strip('"\'') }
                            
        #                     # Process item fields
        #                     elif current_match_item and ':' in line and (in_source or in_target):
        #                         field, value = line.strip().split(':', 1)
        #                         field = field.strip()
        #                         value = value.strip().strip('"\'')
                                
        #                         # Special handling for number fields
        #                         if field == 'matchMax':
        #                             try:
        #                                 value = int(value)
        #                             except ValueError:
        #                                 pass
                                
        #                         current_match_item[field] = value
                            
        #                     # Exit matchSets when we hit a new top-level field
        #                     elif not line.startswith(' '):
        #                         # Add the last item
        #                         if current_match_item:
        #                             if in_source:
        #                                 match_sets['source'].append(current_match_item)
        #                             else:
        #                                 match_sets['target'].append(current_match_item)
        #                             current_match_item = None
                                
        #                         question_dict['matchSets'] = match_sets
        #                         in_match_sets = False
        #                         in_source = False
        #                         in_target = False
        #                         continue  # Process this line as a regular field
                        
        #                 # Detect correctPairs section
        #                 elif line.strip() == 'correctPairs:':
        #                     in_correct_pairs = True
        #                     i += 1
        #                     continue
                        
        #                 # Process correctPairs items
        #                 elif in_correct_pairs:
        #                     if line.strip().startswith('- - '):
        #                         # New pair starting - extract first item
        #                         first_item = line.strip()[4:].strip().strip('"\'')
                                
        #                         # Check if the next line has the second item
        #                         next_line_idx = i + 1
        #                         if next_line_idx < len(lines) and lines[next_line_idx].strip().startswith('  - '):
        #                             second_item = lines[next_line_idx].strip()[4:].strip().strip('"\'')
        #                             correct_pairs.append([first_item, second_item])
        #                             i += 1  # Skip the next line since we've processed it
                            
        #                     # Exit correctPairs when we hit a non-indented line
        #                     elif not line.startswith(' '):
        #                         question_dict['correctPairs'] = correct_pairs
        #                         in_correct_pairs = False
        #                         continue  # Process this line as a regular field
                    
        #             # Handle order-type questions specifically
        #             elif question_dict.get('type') == 'order':
        #                 # Detect correctSequence section
        #                 if line.strip() == 'correctSequence:':
        #                     in_correct_sequence = True
        #                     i += 1
        #                     continue
                        
        #                 # Process correctSequence items
        #                 elif in_correct_sequence:
        #                     if line.strip().startswith('- '):
        #                         # Add item to sequence
        #                         item = line.strip()[2:].strip().strip('"\'')
        #                         correct_sequence.append(item)
                            
        #                     # Exit correctSequence when we hit a non-indented line
        #                     elif not line.startswith(' '):
        #                         question_dict['correctSequence'] = correct_sequence
        #                         in_correct_sequence = False
        #                         continue  # Process this line as a regular field
                    
        #             # Handle regular choices section (for mcq, mrq, etc.)
        #             if line.strip() == 'choices:':
        #                 in_choices = True
        #                 i += 1
        #                 continue
                        
        #             # Process choice items
        #             if in_choices:
        #                 # New choice starts with "- identifier:"
        #                 if line.strip().startswith('- identifier:'):
        #                     # Store previous choice if exists
        #                     if current_choice:
        #                         choices.append(current_choice)
                            
        #                     # Start new choice
        #                     current_choice = {'identifier': line.strip()[13:].strip().strip('"\'') }
                            
        #                 # Process choice fields (text, correct)
        #                 elif current_choice and ':' in line:
        #                     field, value = line.strip().split(':', 1)
        #                     field = field.strip()
        #                     value = value.strip().strip('"\'')
                            
        #                     # Special handling for text field which might have LaTeX
        #                     if field == 'text':
        #                         # If value starts with triple quotes, extract until end triple quotes
        #                         if value.startswith('"""') or value.startswith("'''"):
        #                             quote_type = value[:3]
        #                             if quote_type in value[3:]:
        #                                 # Single line with triple quotes
        #                                 end_quote = value.rindex(quote_type)
        #                                 value = value[3:end_quote]
        #                             else:
        #                                 # Multi-line triple quoted string
        #                                 text_parts = [value[3:]]
        #                                 j = i + 1
        #                                 while j < len(lines):
        #                                     if quote_type in lines[j]:
        #                                         end_quote = lines[j].rindex(quote_type)
        #                                         text_parts.append(lines[j][:end_quote])
        #                                         i = j
        #                                         break
        #                                     else:
        #                                         text_parts.append(lines[j])
        #                                     j += 1
        #                                 value = ' '.join(text_parts)
                                
        #                         current_choice[field] = value
        #                     elif field == 'correct':
        #                         current_choice[field] = value.lower() == 'true'
        #                     else:
        #                         current_choice[field] = value
                        
        #                 # Check if choices section ends
        #                 elif not line.startswith(' '):
        #                     # Add the current choice and end choices section
        #                     if current_choice:
        #                         choices.append(current_choice)
        #                         current_choice = None
                            
        #                     question_dict['choices'] = choices
        #                     in_choices = False
        #                     continue  # Process this line again as a regular field
                    
        #             # Process regular fields
        #             if ':' in line and not in_choices and not in_match_sets and not in_correct_pairs and not in_correct_sequence:
        #                 key, value = line.split(':', 1)
        #                 key = key.strip()
        #                 value = value.strip()
                        
        #                 # Strip quotes if present
        #                 if (value.startswith('"') and value.endswith('"')) or \
        #                 (value.startswith("'") and value.endswith("'")):
        #                     value = value[1:-1]
        #                 elif (value.startswith('"""') and value.endswith('"""')) or \
        #                     (value.startswith("'''") and value.endswith("'''")):
        #                     value = value[3:-3]
                        
        #                 # Convert boolean values
        #                 if value.lower() == 'true':
        #                     value = True
        #                 elif value.lower() == 'false':
        #                     value = False
                        
        #                 question_dict[key] = value
                    
        #             i += 1
                
        #         # Don't forget to add the last choice if still in choices section
        #         if in_choices and current_choice:
        #             choices.append(current_choice)
        #             question_dict['choices'] = choices
                
        #         # Handle final items for match questions
        #         if question_dict.get('type') == 'match':
        #             # Add the last match item if we're still in matchSets
        #             if in_match_sets and current_match_item:
        #                 if in_source:
        #                     match_sets['source'].append(current_match_item)
        #                 elif in_target:
        #                     match_sets['target'].append(current_match_item)
        #                 question_dict['matchSets'] = match_sets
                    
        #             # Make sure we store correctPairs if we're at the end of the block
        #             if in_correct_pairs:
        #                 question_dict['correctPairs'] = correct_pairs
                
        #         # Handle final items for order questions
        #         if question_dict.get('type') == 'order' and in_correct_sequence:
        #             question_dict['correctSequence'] = correct_sequence
                
        #         questions.append(question_dict)
            
        #     return questions




        # def _format_fib(self, question: Dict, template: str) -> str:
        #     """Format Fill in Blank question according to QTI v2.2 specs"""
        #     # Generate response declarations
        #     response_declarations = []
            
        #     # Create one response declaration per blank
        #     for i, answers in enumerate(question['correctAnswers'], 1):
        #         values = []
        #         for answer in answers:
        #             # Properly handle a single dash
        #             if answer == '-':
        #                 answer_str = '-'
        #             else:
        #                 answer_str = str(answer)
        #             # Escape XML characters in the answer
        #             answer_str = self._escape_xml_chars(answer_str)
        #             values.append(f'<value>{answer_str}</value>')
                    
        #         declaration = f"""
        #         <responseDeclaration identifier="RESPONSE{i}" cardinality="single" baseType="string">
        #             <correctResponse>
        #                 {' '.join(values)}
        #             </correctResponse>
        #         </responseDeclaration>"""
        #         response_declarations.append(declaration)
            
        #     # Format text parts with interaction
        #     # Replace the blank with the appropriate interaction
        #     text = self._escape_xml_chars(question['prompt'])
        #     interaction = f'<textEntryInteraction responseIdentifier="RESPONSE1" expectedLength="{question.get("expectedLength", 20)}"/>'
        #     text_parts = text.replace('_', interaction)
            
        #     return template.format(
        #         identifier=question['identifier'],
        #         title=self._escape_xml_chars(question['title']),
        #         response_declarations='\n'.join(response_declarations),
        #         text_parts=text_parts
        #     )



        # def _format_match(self, question: Dict, template: str) -> str:
        #     """Format Matching question according to QTI v2.2 specs with improved error handling"""
        #     try:
        #         # Format source choices
        #         source_choices = '\n            '.join(
        #             f'<simpleAssociableChoice identifier="{choice["identifier"]}" '
        #             f'matchMax="{choice.get("matchMax", 1)}">{choice["text"]}</simpleAssociableChoice>'
        #             for choice in question['matchSets']['source']
        #         )
                
        #         # Format target choices
        #         target_choices = '\n            '.join(
        #             f'<simpleAssociableChoice identifier="{choice["identifier"]}" '
        #             f'matchMax="{choice.get("matchMax", 1)}">{choice["text"]}</simpleAssociableChoice>'
        #             for choice in question['matchSets']['target']
        #         )
                
        #         # Format correct pairs with better error handling
        #         pairs = []
        #         for pair in question['correctPairs']:
        #             if isinstance(pair, list) and len(pair) == 2:
        #                 pairs.append(f'<value>{pair[0]} {pair[1]}</value>')
        #             else:
        #                 raise ValueError(f"Invalid pair format in correctPairs: {pair}")
                
        #         correct_pairs = '\n            '.join(pairs)
                
        #         # Apply template
        #         return template.format(
        #             identifier=question['identifier'],
        #             title=question['title'],
        #             prompt=question['prompt'],
        #             source_choices=source_choices,
        #             target_choices=target_choices,
        #             correct_pairs=correct_pairs,
        #             shuffle=str(question.get('shuffle', True)).lower(),
        #             max_associations=str(question.get('maxAssociations', 0))
        #         )
        #     except Exception as e:
        #         raise ValueError(f"Error formatting match question: {str(e)}")

        # def _format_match(self, question_data, template_path=None):
        #     """
        #     Format a match question into QTI v2.2 XML format
            
        #     Args:
        #         question_data (dict): Dictionary containing match question data
        #         template_path (str, optional): Path to the template file. If None, uses default path.
                
        #     Returns:
        #         str: Formatted XML string for the match question
        #     """
        #     import os
            
        #     # Load the template
        #     if template_path is None:
        #         template_path = os.path.join(self.template_dir, "question_types", "match.xml")
            
        #     # Check if template_path is actually a string template or a file path
        #     if template_path.strip().startswith('<?xml'):
        #         # It's already a template string, use it directly
        #         template = template_path
        #     else:
        #         # It's a file path, read the file
        #         with open(template_path, "r") as f:
        #             template = f.read()
            
        #     # Format the correct pairs
        #     correct_pairs_xml = ""
        #     for pair in question_data.get("correctPairs", []):
        #         if len(pair) == 2:
        #             # Format should be <value>source target</value>
        #             correct_pairs_xml += f"<value>{pair[0]} {pair[1]}</value>\n            "
            
        #     # Format source choices
        #     source_choices_xml = ""
        #     for choice in question_data.get("matchSets", {}).get("source", []):
        #         source_choices_xml += f"""<simpleAssociableChoice identifier="{choice['identifier']}" matchMax="{choice.get('matchMax', 1)}">
        #                 {choice['text']}
        #             </simpleAssociableChoice>\n            """
            
        #     # Format target choices
        #     target_choices_xml = ""
        #     for choice in question_data.get("matchSets", {}).get("target", []):
        #         target_choices_xml += f"""<simpleAssociableChoice identifier="{choice['identifier']}" matchMax="{choice.get('matchMax', 1)}">
        #                 {choice['text']}
        #             </simpleAssociableChoice>\n            """
            
        #     # Replace placeholders in template
        #     formatted_xml = template.format(
        #         identifier=question_data.get("identifier", ""),
        #         title=question_data.get("title", ""),
        #         prompt=question_data.get("prompt", ""),
        #         correct_pairs=correct_pairs_xml,
        #         source_choices=source_choices_xml,
        #         target_choices=target_choices_xml
        #     )
            
        #     return formatted_xml







        # def _format_upload(self, question: Dict, template: str) -> str:
        #     """Format File Upload question according to QTI v2.2 specs"""
        #     # Handle allowed types if specified
        #     allowed_types = question.get('allowedTypes', [])
        #     type_attr = ''
        #     if allowed_types:
        #         type_attr = f' type="{" ".join(allowed_types)}"'
            
        #     return template.format(
        #         identifier=question['identifier'],
        #         title=question['title'],
        #         prompt=question['prompt'],
        #         type_attr=type_attr,
        #         max_size=str(question['maxSize'])
        #     )

        # def _format_label_image(self, question: Dict, template: str) -> str:
        #     """Format Image Labeling question according to QTI v2.2 specs"""
        #     # Format image
        #     image = f"""<object type="{question['image']['type']}" 
        #                     width="{question['image']['width']}" 
        #                     height="{question['image']['height']}" 
        #                     data="{question['image']['source']}"/>"""
            
        #     # Format labels
        #     labels = '\n            '.join(
        #         f'<gapImg identifier="{label["identifier"]}">{label["text"]}</gapImg>'
        #         for label in question['labels']
        #     )
            
        #     # Format targets
        #     targets = '\n            '.join(
        #         f'<gapChoice identifier="{target["identifier"]}" '
        #         f'x="{target["x"]}" y="{target["y"]}">{target["text"]}</gapChoice>'
        #         for target in question['targets']
        #     )
            
        #     # Format correct pairs
        #     correct_pairs = '\n            '.join(
        #         f'<value>{pair[0]} {pair[1]}</value>'
        #         for pair in question['correctPairs']
        #     )
            
        #     return template.format(
        #         identifier=question['identifier'],
        #         title=question['title'],
        #         prompt=question['prompt'],
        #         image=image,
        #         labels=labels,
        #         targets=targets,
        #         correct_pairs=correct_pairs
        #     )

        # def _format_highlight_text(self, question: Dict, template: str) -> str:
        #     """Format Text Highlighting question according to QTI v2.2 specs"""
        #     # Format text segments
        #     text_segments = '\n            '.join(
        #         f'<simpleChoice identifier="{segment["identifier"]}">{segment["content"]}</simpleChoice>'
        #         for segment in question['text']
        #     )
            
        #     # Format correct values
        #     correct_values = '\n            '.join(
        #         f'<value>{segment["identifier"]}</value>'
        #         for segment in question['text']
        #         if segment.get('correct', False)
        #     )
            
        #     return template.format(
        #         identifier=question['identifier'],
        #         title=question['title'],
        #         prompt=question['prompt'],
        #         text_segments=text_segments,
        #         correct_values=correct_values,
        #         max_selections=str(question.get('maxSelections', 0))
        #     )

        # def _format_highlight_image(self, question: Dict, template: str) -> str:
        #     """Format image highlighting question into QTI XML"""
            
        #     # Format the hotspot choices
        #     hotspots = []
        #     for hotspot in question['hotspots']:
        #         # Format coordinates based on shape type
        #         if hotspot['shape'] == 'rect':
        #             coords = f"{hotspot['x']},{hotspot['y']}," \
        #                     f"{hotspot['x'] + hotspot['width']},{hotspot['y'] + hotspot['height']}"
        #         elif hotspot['shape'] == 'circle':
        #             coords = f"{hotspot['x']},{hotspot['y']},{hotspot['radius']}"
        #         else:  # poly
        #             coords = ','.join(map(str, hotspot['coords']))
                
        #         hotspot_xml = (
        #             f'<hotspotChoice identifier="{hotspot["identifier"]}" '
        #             f'shape="{hotspot["shape"]}" coords="{coords}"/>'
        #         )
        #         hotspots.append(hotspot_xml)
            
        #     # Format correct hotspots
        #     correct_hotspots = []
        #     for hotspot_id in question['correctHotspots']:
        #         correct_hotspots.append(f'<value>{hotspot_id}</value>')
            
        #     # Format image object
        #     image = question['image']
        #     image_object = (
        #         f'<object type="{image["type"]}" '
        #         f'data="{image["source"]}" '
        #         f'width="{image["width"]}" '
        #         f'height="{image["height"]}"/>'
        #     )
            
        #     # Apply to template
        #     formatted_xml = template.format(
        #         identifier=question['identifier'],
        #         title=question['title'],
        #         prompt=question['prompt'],
        #         image_object=image_object,
        #         hotspots='\n            '.join(hotspots),
        #         correct_hotspots='\n            '.join(correct_hotspots),
        #         max_choices=str(question.get('maxChoices', 0))  # Default to 0 (unlimited) if not specified
        #     )
            
        #     return formatted_xml


        # def _format_numeric(self, question: Dict, template: str) -> str:
        #     """Format numeric question according to QTI v2.2 specs"""
        #     # Handle multiple accepted answers
        #     correct_values = []
        #     for answer_set in question['correctAnswers']:
        #         for answer in answer_set:
        #             correct_values.append(f'<value>{float(answer)}</value>')
            
        #     # Build mapping section for tolerance if specified
        #     mapping = ""
        #     if 'tolerance' in question:
        #         mapping = f"""
        #             <mapping>
        #                 <defaultValue>0</defaultValue>
        #                 <mapEntry mappedValue="1">
        #                     <correctResponse/>
        #                     <tolerance>{question['tolerance']}</tolerance>
        #                 </mapEntry>
        #             </mapping>"""

        #     return template.format(
        #         identifier=question['identifier'],
        #         title=question['title'],
        #         prompt=question['prompt'],
        #         correct_values='\n            '.join(correct_values),
        #         mapping=mapping,
        #         expected_length=str(question.get('expectedLength', 10))
        #     )

        # def _format_mcq(self, question: Dict, template: str) -> str:
        #     """Format Multiple Choice question according to QTI v2.2 specs"""
        #     # Create a mapping of choices by identifier
        #     choice_map = {choice['identifier']: choice['text'] for choice in question['choices']}
            
        #     # Get correct answer
        #     correct_answer = next(
        #         choice['identifier'] 
        #         for choice in question['choices'] 
        #         if choice.get('correct', False)
        #     )
            
        #     return template.format(
        #         identifier=question['identifier'],
        #         title=question['title'],
        #         prompt=question['prompt'],
        #         correct_answer=correct_answer,
        #         choice_a=choice_map.get('A', ''),
        #         choice_b=choice_map.get('B', ''),
        #         choice_c=choice_map.get('C', ''),
        #         choice_d=choice_map.get('D', '')
        #     )

        # def _validate_common(self, question: Dict) -> bool:
        #     """Validate common fields required for all question types"""
        #     # Load common settings from metadata
        #     common_settings = self.metadata['common_settings']
            
        #     # Check required attributes
        #     for attr in common_settings['required_attributes']:
        #         if attr not in question:
        #             raise ValueError(f"Missing required attribute: {attr}")
                
        #         # Type checking
        #         expected_type = common_settings['attribute_types'][attr]
        #         value = question[attr]
        #         if expected_type == 'boolean' and not isinstance(value, bool):
        #             raise ValueError(f"Attribute {attr} must be boolean, got {type(value)}")
        #         elif expected_type == 'string' and not isinstance(value, str):
        #             raise ValueError(f"Attribute {attr} must be string, got {type(value)}")
            
        #     return True
        

        # def _validate_choices(self, question: Dict, question_type: str) -> bool:
        #         """Validate choice-based questions (MCQ, MRQ)"""
        #         validation_rules = self.metadata['question_types'][question_type]['validation_rules']
                
        #         if 'choices' not in question:
        #             raise ValueError(f"Question {question['identifier']}: Missing choices")
                
        #         choices = question['choices']
        #         # Check minimum number of choices
        #         if len(choices) < validation_rules['min_choices']:
        #             raise ValueError(
        #                 f"Question {question['identifier']}: Must have at least "
        #                 f"{validation_rules['min_choices']} choices, got {len(choices)}"
        #             )
                
        #         # Check choice format
        #         choice_format = validation_rules['choices_format']
        #         for choice in choices:
        #             for field in choice_format['required_fields']:
        #                 if field not in choice:
        #                     raise ValueError(
        #                         f"Question {question['identifier']}: Choice missing required field: {field}"
        #                     )
                        
        #                 # Type checking for choice fields
        #                 expected_type = choice_format['field_types'][field]
        #                 value = choice[field]
        #                 if expected_type == 'boolean' and not isinstance(value, bool):
        #                     raise ValueError(
        #                         f"Question {question['identifier']}: Choice field {field} "
        #                         f"must be boolean, got {type(value)}"
        #                     )
        #                 elif expected_type == 'string' and not isinstance(value, str):
        #                     raise ValueError(
        #                         f"Question {question['identifier']}: Choice field {field} "
        #                         f"must be string, got {type(value)}"
        #                     )
                
        #         # Additional MCQ validation
        #         if question_type == 'mcq':
        #             correct_count = sum(1 for c in choices if c.get('correct'))
        #             if correct_count != 1:
        #                 raise ValueError(
        #                     f"MCQ {question['identifier']}: Must have exactly one correct answer, "
        #                     f"got {correct_count}"
        #                 )
        #         # Additional MRQ validation
        #         elif question_type == 'mrq':
        #             if not any(c.get('correct') for c in choices):
        #                 raise ValueError(
        #                     f"MRQ {question['identifier']}: Must have at least one correct answer"
        #                 )
                
        #         return True




# class YAMLtoXMLConverter:
#     def __init__(self, templates_dir: str = "templates"):
#         self.templates_dir = Path(templates_dir)
#         self.templates = {}
#         self.metadata = {}
#         self.load_templates()
#         self.load_metadata()

#     def load_templates(self):
#         template_dir = self.templates_dir / "question_types"
#         for template_file in template_dir.glob("*.xml"):
#             question_type = template_file.stem
#             with open(template_file, 'r') as f:
#                 self.templates[question_type] = f.read()

#     def load_metadata(self):
#         with open(self.templates_dir / "metadata.yaml", 'r') as f:
#             self.metadata = yaml.safe_load(f)

#     def _get_required_fields(self, question_type: str) -> List[str]:
#         """Get required fields for a question type"""
#         base_fields = ['type', 'identifier', 'title', 'prompt']
#         type_specific_fields = {
#         'mcq': ['choices', 'correctResponse'],
#         'mrq': ['choices', 'correctResponse'], 
#         'tf': ['correctResponse'],
#         'fib': ['correctResponse', 'expectedLength'],
#         'essay': ['expectedLines'],
#         'match': ['matchSets', 'correctPairs'],
#         'order': ['choices', 'correctSequence'],
#         'numeric': ['correctResponse', 'expectedLength'],
#         'upload': ['maxSize'],
#         'label_image': ['labels', 'targets', 'correctPairs', 'image'],
#         'highlight_image': ['hotspots', 'correctHotspots', 'image'],
#         'highlight_text': ['text', 'correctHighlights']}
        
#         return base_fields + type_specific_fields.get(question_type, [])

#     def validate_yaml_schema(self, yaml_content: str) -> bool:
#         """Validate YAML content structure"""
#         try:
#             # First try to load the YAML content
#             try:
#                 questions = yaml.safe_load(yaml_content)
#             except yaml.YAMLError as e:
#                 st.error(f"YAML Parsing Error: {str(e)}")
#                 # Log the problematic content for debugging
#                 st.code(yaml_content, language="yaml")
#                 return False

#             if not isinstance(questions, list):
#                 st.error("YAML content must be a list of questions")
#                 return False
                
#             for idx, question in enumerate(questions, 1):
#                 if not isinstance(question, dict):
#                     st.error(f"Question {idx} must be a dictionary")
#                     return False
                    
#                 if 'type' not in question:
#                     st.error(f"Question {idx} missing required 'type' field")
#                     return False
                    
#                 if question['type'] not in self.templates:
#                     st.error(f"Question {idx} has unsupported type: {question['type']}")
#                     return False
                    
#                 # Validate required fields based on question type
#                 required_fields = self._get_required_fields(question['type'])
#                 missing_fields = [field for field in required_fields if field not in question]
#                 if missing_fields:
#                     st.error(f"Question {idx} missing required fields: {', '.join(missing_fields)}")
#                     return False
#             return True
#         except Exception as e:
#             st.error(f"Validation Error: {str(e)}")
#             return False
        
#     def convert_yaml_to_xml(self, yaml_content: str) -> List[str]:
#         """Convert YAML to XML with improved error handling"""
#         try:
#             # Add progress indicators
#             progress_bar = st.progress(0)
#             status_text = st.empty()
#             # Validate YAML schema
#             if not self.validate_yaml_schema(yaml_content):
#                 return []
#             questions = yaml.safe_load(yaml_content)
#             xml_questions = []
#             total = len(questions)
#             for i, question in enumerate(questions, 1):
#                 try:
#                     status_text.text(f"Converting question {i} of {total}")
#                     progress_bar.progress(i/total)
                    
#                     # Validate individual question
#                     if not self.validate_yaml_question(question, question['type']):
#                         st.warning(f"Skipping invalid question {i}")
#                         continue
                    
#                     # Convert question to XML
#                     xml = self.convert_question(question)
#                     if xml:
#                         xml_questions.append(xml)
                    
#                 except Exception as e:
#                     st.error(f"Error converting question {i}: {str(e)}")
#                     # Log the problematic question for debugging
#                     st.code(question, language="yaml")
#                     continue
#             status_text.text(f"Converted {len(xml_questions)} of {total} questions successfully")
#             progress_bar.progress(1.0)
#             return xml_questions
            
#         except Exception as e:
#             st.error(f"Critical error during conversion: {str(e)}")
#             # Log the full YAML content for debugging
#             st.code(yaml_content, language="yaml")
#             return []
        
#     def _convert_mcq(self, question: dict, template: str) -> str:
#         """Convert MCQ question to XML format"""
#         # Format choices
#         choices_xml = []
#         for choice in question['choices']:
#             choices_xml.append(
#                 f'<simpleChoice identifier="{choice["identifier"]}">{choice["text"]}</simpleChoice>'
#             )
        
#         # Get correct answer
#         correct_answer = next(
#             choice['identifier'] 
#             for choice in question['choices'] 
#             if choice.get('correct', False)
#         )
        
#         # Replace placeholders in template
#         xml = template.format(
#             identifier=question['identifier'],
#             title=question['title'],
#             prompt=question['prompt'],
#             choices='\n            '.join(choices_xml),
#             correct_answer=correct_answer,
#             shuffle=str(question.get('shuffle', True)).lower(),
#             max_choices=str(question.get('maxChoices', 1))
#         )
        
#         return xml

#     def _convert_fib(self, question: dict, template: str) -> str:
#         """Convert FIB question to XML format"""
#         # Split text at underscores for blanks
#         import re
#         text_parts = re.split(r'_+', question['prompt'])
#         num_blanks = len(text_parts) - 1
        
#         # Generate response declarations
#         response_declarations = []
#         for i in range(num_blanks):
#             response_id = f"RESPONSE{i+1}"
#             # Convert answers to strings
#             values = [f'<value>{str(ans)}</value>' for ans in question['correctAnswers'][i]]
            
#             declaration = f"""
#                 <responseDeclaration identifier="{response_id}" cardinality="single" baseType="string">
#                     <correctResponse>
#                         {''.join(values)}
#                     </correctResponse>
#                 </responseDeclaration>"""
#             response_declarations.append(declaration)
        
#         # Build prompt with interactions
#         processed_text = ''
#         for i, part in enumerate(text_parts):
#             processed_text += part
#             if i < num_blanks:
#                 processed_text += f'<textEntryInteraction responseIdentifier="RESPONSE{i+1}" expectedLength="{question.get("expectedLength", 20)}"/>'
        
#         # Format template
#         xml = template.format(
#             identifier=question['identifier'],
#             title=question['title'],
#             response_declarations='\n'.join(response_declarations),
#             prompt_text=processed_text
#         )
        
#         return xml

#     def _convert_tf(self, question: dict, template: str) -> str:
#         """Convert True/False question to XML format"""
#         xml = template.format(
#             identifier=question['identifier'],
#             title=question['title'],
#             prompt=question['prompt'],
#             correct_answer=str(question['correct']).lower()
#         )
#         return xml

#     def convert_question(self, question: dict) -> str:
#         """Convert a question from YAML to XML format"""
#         try:
#             question_type = question['type']
#             if question_type not in self.templates:
#                 raise ValueError(f"Unsupported question type: {question_type}")

#             # Validate question
#             if not self.validate_yaml_question(question, question_type):
#                 raise ValueError(f"Question validation failed for type: {question_type}")

#             # Get appropriate converter method
#             converter_method = getattr(self, f"_convert_{question_type}", None)
#             if not converter_method:
#                 raise ValueError(f"No converter implemented for type: {question_type}")

#             # Convert question
#             xml_content = converter_method(question, self.templates[question_type])
            
#             # Add XML declaration if not present
#             if not xml_content.startswith('<?xml'):
#                 xml_content = f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_content}'
                
#             return xml_content
            
#         except Exception as e:
#             raise ValueError(f"Question conversion failed: {str(e)}")

#     def validate_yaml_question(self, question: dict, question_type: str) -> bool:
#         """Validate a YAML question against metadata rules"""
#         try:
#             # Get type-specific metadata
#             type_metadata = self.metadata.get('question_types', {}).get(question_type, {})
#             validation_rules = type_metadata.get('validation_rules', {})
            
#             # Validate required elements
#             required_elements = type_metadata.get('required_elements', [])
#             for element in required_elements:
#                 if element not in question:
#                     raise ValueError(f"Missing required element '{element}'")
            
#             # Validate choices for MCQ/MRQ
#             if question_type in ['mcq', 'mrq']:
#                 choices = question.get('choices', [])
#                 min_choices = validation_rules.get('min_choices', 4)
#                 if len(choices) < min_choices:
#                     raise ValueError(f"Not enough choices (minimum: {min_choices})")
                
#                 # Validate choice format
#                 choice_format = validation_rules.get('choices_format', {})
#                 required_fields = choice_format.get('required_fields', [])
#                 for choice in choices:
#                     for field in required_fields:
#                         if field not in choice:
#                             raise ValueError(f"Choice missing required field: {field}")
            
#             # Validate FIB
#             if question_type == 'fib':
#                 if '_' not in question['prompt']:
#                     raise ValueError("Prompt must contain blank(s) marked with _")
#                 import re
#                 num_blanks = len(re.findall(r'_+', question['prompt']))
#                 answers = question.get('correctAnswers', [])
#                 if len(answers) != num_blanks:
#                     raise ValueError(f"Number of answer sets ({len(answers)}) must match number of blanks ({num_blanks})")
            
#             return True
            
#         except Exception as e:
#             st.error(str(e))
#             return False

#  # # Example highlight image template (for reference)
#     # HIGHLIGHT_IMAGE_TEMPLATE = '''<?xml version="1.0" encoding="UTF-8"?>
#     # <assessmentItem xmlns="http://www.imsglobal.org/xsd/imsqti_v2p2" 
#     #     identifier="{identifier}" 
#     #     title="{title}" 
#     #     adaptive="false" 
#     #     timeDependent="false">
#     #     <responseDeclaration identifier="RESPONSE" cardinality="multiple" baseType="identifier">
#     #         <correctResponse>
#     #             {correct_hotspots}
#     #         </correctResponse>
#     #     </responseDeclaration>
#     #     <itemBody>
#     #         <hotspotInteraction responseIdentifier="RESPONSE" maxChoices="{max_choices}">
#     #             <prompt>{prompt}</prompt>
#     #             {image_object}
#     #             {hotspots}
#     #         </hotspotInteraction>
#     #     </itemBody>
#     # </assessmentItem>'''

#     # # Example usage:
#     # example_question = {
#     #     "type": "highlight_image",
#     #     "identifier": "HIGHLIGHT1",
#     #     "title": "Sample Image Highlighting",
#     #     "adaptive": False,
#     #     "timeDependent": False,
#     #     "prompt": "Highlight all the relevant areas in the image.",
#     #     "image": {
#     #         "source": "media/sample_image.png",
#     #         "type": "image/png",
#     #         "width": 800,
#     #         "height": 600
#     #     },
#     #     "hotspots": [
#     #         {
#     #             "identifier": "hotspot1",
#     #             "shape": "rect",
#     #             "x": 100,
#     #             "y": 100,
#     #             "width": 200,
#     #             "height": 150
#     #         },
#     #         {
#     #             "identifier": "hotspot2",
#     #             "shape": "circle",
#     #             "x": 400,
#     #             "y": 300,
#     #             "radius": 50
#     #         },
#     #         {
#     #             "identifier": "hotspot3",
#     #             "shape": "poly",
#     #             "x": 600,
#     #             "y": 400,
#     #             "coords": [600, 400, 650, 450, 600, 500, 550, 450]
#     #         }
#     #     ],
#     #     "correctHotspots": ["hotspot1", "hotspot3"],
#     #     "maxChoices": 0  # 0 means unlimited selections
#     # }

#     # def _format_numeric(self, question: Dict, template: str) -> str:
#     #     """Format numeric question"""
#     #     correct_value = question.get('correctAnswer', question.get('correctResponse'))
#     #     mapping_str = ""
#     #     if 'tolerance' in question:
#     #         mapping_str = f"""
#     #             <mapping>
#     #                 <defaultValue>0</defaultValue>
#     #                 <mapEntry mappedValue="1" exactMatch="false" tolerance="{question['tolerance']}"/>
#     #             </mapping>"""
        
#     #     return template.format(
#     #         identifier=question['identifier'],
#     #         title=question['title'],
#     #         prompt=question['prompt'],
#     #         correct_answer=str(float(correct_value)),
#     #         mapping=mapping_str,
#     #         expected_length=str(question.get('expectedLength', 10))
#     #     )

#     # def _format_upload(self, question: Dict, template: str) -> str:
#     #     """Format file upload question"""
#     #     allowed_types = question.get('allowedTypes', '')
#     #     if isinstance(allowed_types, list):
#     #         allowed_types = ' '.join(allowed_types)
        
#     #     return template.format(
#     #         identifier=question['identifier'],
#     #         title=question['title'],
#     #         prompt=question['prompt'],
#     #         allowed_types=allowed_types,
#     #         max_size=str(question.get('maxSize', 5242880))  # Default 5MB
#     #     )

#     # def _format_highlight_text(self, question: Dict, template: str) -> str:
#     #     """Format text highlighting question"""
#     #     # Format choices
#     #     choices = '\n            '.join(
#     #         f'<simpleChoice identifier="{segment["identifier"]}">{segment["content"]}</simpleChoice>'
#     #         for segment in question['text']
#     #     )
        
#     #     # Format correct values
#     #     correct_values = '\n            '.join(
#     #         f'<value>{segment["identifier"]}</value>'
#     #         for segment in question['text']
#     #         if segment.get('correct', False)
#     #     )
        
#     #     return template.format(
#     #         identifier=question['identifier'],
#     #         title=question['title'],
#     #         prompt=question['prompt'],
#     #         choices=choices,
#     #         correct_values=correct_values,
#     #         max_selections=str(question.get('maxSelections', len(question['text'])))
#     #     )

#     # def _format_label_image(self, question: Dict, template: str) -> str:
#     #     """Format image labeling question"""
#     #     # Format labels
#     #     labels = '\n            '.join(
#     #         f'<gapImg identifier="{label["identifier"]}" matchMax="{label.get("matchMax", 1)}">'
#     #         f'<object type="{label.get("imageType", "image/png")}" data="{label["image"]}"/>'
#     #         f'</gapImg>'
#     #         for label in question['labels']
#     #     )
        
#     #     # Format targets
#     #     targets = '\n            '.join(
#     #         f'<gap identifier="{target["identifier"]}" '
#     #         f'x="{target["x"]}" y="{target["y"]}" '
#     #         f'width="{target.get("width", 20)}" height="{target.get("height", 20)}"/>'
#     #         for target in question['targets']
#     #     )
        
#     #     # Format correct pairs
#     #     pairs = '\n            '.join(
#     #         f'<value>{pair[0]} {pair[1]}</value>'
#     #         for pair in question['correctPairs']
#     #     )
        
#     #     return template.format(
#     #         identifier=question['identifier'],
#     #         title=question['title'],
#     #         prompt=question['prompt'],
#     #         image=question['image'],
#     #         image_type=question.get('imageType', 'image/png'),
#     #         width=str(question.get('width', 400)),
#     #         height=str(question.get('height', 300)),
#     #         labels=labels,
#     #         targets=targets,
#     #         correct_pairs=pairs
#     #     )

#     # def _format_highlight_image(self, question: Dict, template: str) -> str:
#     #     """Format image highlighting question"""
#     #     # Format hotspots
#     #     hotspots = []
#     #     for hotspot in question['hotspots']:
#     #         coords = ""
#     #         if hotspot['shape'] == 'circle':
#     #             coords = f"{hotspot['x']},{hotspot['y']},{hotspot['radius']}"
#     #         elif hotspot['shape'] == 'poly':
#     #             coords = ','.join(map(str, hotspot['coords']))
#     #         else:  # rect
#     #             coords = f"{hotspot['x']},{hotspot['y']},{hotspot['x'] + hotspot['width']},{hotspot['y'] + hotspot['height']}"
                
#     #         hotspot_xml = (
#     #             f'<hotspotChoice identifier="{hotspot["identifier"]}" '
#     #             f'shape="{hotspot.get("shape", "rect")}" coords="{coords}"/>'
#     #         )
#     #         hotspots.append(hotspot_xml)
        
#     #     # Format correct hotspots
#     #     correct_hotspots = []
#     #     for hotspot_id in question['correctHotspots']:
#     #         correct_hotspots.append(f'<value>{hotspot_id}</value>')
        
#     #     return template.format(
#     #         identifier=question['identifier'],
#     #         title=question['title'],
#     #         prompt=question['prompt'],
#     #         image=question['image'],
#     #         image_type=question.get('imageType', 'image/png'),
#     #         width=str(question.get('width', 400)),
#     #         height=str(question.get('height', 300)),
#     #         hotspots='\n            '.join(hotspots),
#     #         correct_hotspots='\n            '.join(correct_hotspots),
#     #         max_choices=str(question.get('maxChoices', 0))  # 0 means unlimited
#     #     )
    
#     # def _format_fib(self, question: Dict, template: str) -> str:
#     #     """Format Fill in Blank question with dynamic number of blanks"""
#     #     # Count blanks
#     #     num_blanks = question['prompt'].count('_')
        
#     #     # Split text into parts at each underscore
#     #     parts = question['prompt'].split('_')
        
#     #     # Get correct answers from either correctAnswers or correctResponse
#     #     correct_answers = question.get('correctAnswers', question.get('correctResponse', []))
#     #     if not correct_answers:
#     #         raise ValueError(f"FIB question {question['identifier']}: Must provide correctAnswers or correctResponse")
        
#     #     # Ensure we have the right number of answers
#     #     if len(correct_answers) != num_blanks:
#     #         raise ValueError(
#     #             f"FIB question {question['identifier']}: "
#     #             f"Number of blanks ({num_blanks}) does not match number of answers ({len(correct_answers)})"
#     #         )
        
#     #     # Generate response declarations for each blank
#     #     response_declarations = []
#     #     for i, answers in enumerate(correct_answers, 1):
#     #         # Format correct answers without brackets or quotes
#     #         formatted_values = []
#     #         if isinstance(answers, list):
#     #             formatted_values.extend(f"<value>{str(answer)}</value>" for answer in answers)
#     #         else:
#     #             formatted_values.append(f"<value>{str(answers)}</value>")
                
#     #         declaration = f"""    <responseDeclaration identifier="RESPONSE{i}" cardinality="single" baseType="string">
#     #                     <correctResponse>
#     #                         {chr(10) + ' ' * 12 + (' '.join(formatted_values))}
#     #                     </correctResponse>
#     #                 </responseDeclaration>"""
#     #         response_declarations.append(declaration)
        
#     #     # Build text with interactions
#     #     text_parts = []
#     #     for i, part in enumerate(parts):
#     #         text_parts.append(part)
#     #         if i < len(parts) - 1:  # Don't add interaction after last part
#     #             text_parts.append(f'<textEntryInteraction responseIdentifier="RESPONSE{i+1}" expectedLength="20"/>')
        
#     #     # Format template
#     #     return template.format(
#     #         identifier=question['identifier'],
#     #         title=question['title'],
#     #         response_declarations='\n'.join(response_declarations),
#     #         text_parts=''.join(text_parts)
#     #     )

#     # def _format_mcq(self, question: Dict, template: str) -> str:
#     #     """Format Multiple Choice question"""
#     #     # Get correct answer
#     #     correct_answer = next(
#     #         (choice['identifier'] for choice in question['choices'] if choice.get('correct')),
#     #         None
#     #     )
#     #     # Get choice texts by identifier
#     #     choice_mapping = {choice['identifier']: choice['text'] for choice in question['choices']}
        
#     #     return template.format(
#     #         identifier=question['identifier'],
#     #         title=question['title'],
#     #         prompt=question['prompt'],
#     #         correct_answer=correct_answer,
#     #         choice_a=choice_mapping.get('A', ''),
#     #         choice_b=choice_mapping.get('B', ''),
#     #         choice_c=choice_mapping.get('C', ''),
#     #         choice_d=choice_mapping.get('D', '')
#     #     )

#     # def _format_mrq(self, question: Dict, template: str) -> str:
#     #     """Format Multiple Response question"""
#     #     # Get correct answers
#     #     correct_answers = [
#     #         f'<value>{choice["identifier"]}</value>'
#     #         for choice in question['choices']
#     #         if choice.get('correct')
#     #     ]
        
#     #     # Get choice texts by identifier for template compatibility
#     #     choice_mapping = {choice['identifier']: choice['text'] for choice in question['choices']}
        
#     #     # Format all choices dynamically for XML
#     #     choices = '\n            '.join(
#     #         f'<simpleChoice identifier="{c["identifier"]}">{c["text"]}</simpleChoice>'
#     #         for c in question['choices']
#     #     )
        
#     #     return template.format(
#     #         identifier=question['identifier'],
#     #         title=question['title'],
#     #         prompt=question['prompt'],
#     #         correct_answers='\n            '.join(correct_answers),
#     #         choices=choices,
#     #         shuffle=str(question.get('shuffle', True)).lower(),
#     #         max_choices=str(question.get('maxChoices', 0)),
#     #         choice_a=choice_mapping.get('A', ''),
#     #         choice_b=choice_mapping.get('B', ''),
#     #         choice_c=choice_mapping.get('C', ''),
#     #         choice_d=choice_mapping.get('D', '')
#     #     )

#     # def _format_tf(self, question: Dict, template: str) -> str:
#     #     """Format True/False question"""
#     #     return template.format(
#     #         identifier=question['identifier'],
#     #         title=question['title'],
#     #         prompt=question['prompt'],
#     #         correct_answer=str(question['correct']).lower()
#     #     )

#     # def _format_match(self, question: Dict, template: str) -> str:
#     #     """Format Matching question"""
#     #     # Format correct pairs
#     #     pairs = '\n            '.join(
#     #         f'<value>{pair[0]} {pair[1]}</value>'
#     #         for pair in question['correctPairs']
#     #     )
        
#     #     # Format source choices
#     #     source_choices = '\n            '.join(
#     #         f'<simpleAssociableChoice identifier="{c["identifier"]}" matchMax="{c.get("matchMax", 1)}">{c["text"]}</simpleAssociableChoice>'
#     #         for c in question['matchSets']['source']
#     #     )
        
#     #     # Format target choices
#     #     target_choices = '\n            '.join(
#     #         f'<simpleAssociableChoice identifier="{c["identifier"]}" matchMax="{c.get("matchMax", 1)}">{c["text"]}</simpleAssociableChoice>'
#     #         for c in question['matchSets']['target']
#     #     )
        
#     #     return template.format(
#     #         identifier=question['identifier'],
#     #         title=question['title'],
#     #         prompt=question['prompt'],
#     #         correct_pairs=pairs,
#     #         source_choices=source_choices,
#     #         target_choices=target_choices,
#     #         shuffle=str(question.get('shuffle', True)).lower(),
#     #         max_associations=str(question.get('maxAssociations', 0))
#     #     )

#     # def _format_order(self, question: Dict, template: str) -> str:
#     #     """Format Ordering question"""
#     #     # Format correct sequence
#     #     sequence = '\n            '.join(
#     #         f'<value>{choice_id}</value>'
#     #         for choice_id in question['correctSequence']
#     #     )
        
#     #     # Format choices
#     #     choices = '\n            '.join(
#     #         f'<simpleChoice identifier="{c["identifier"]}">{c["text"]}</simpleChoice>'
#     #         for c in question['choices']
#     #     )
        
#     #     return template.format(
#     #         identifier=question['identifier'],
#     #         title=question['title'],
#     #         prompt=question['prompt'],
#     #         correct_sequence=sequence,
#     #         choices=choices,
#     #         shuffle=str(question.get('shuffle', True)).lower()
#     #     )

#     # def _format_essay(self, question: Dict, template: str) -> str:
#     #     """Format Essay question"""
#     #     return template.format(
#     #         identifier=question['identifier'],
#     #         title=question['title'],
#     #         prompt=question['prompt'],
#     #         expected_lines=str(question.get('expectedLines', 5))
#     #     )

