#!/usr/bin/env python3
"""
Extract questions from KCA University past exam papers PDFs and save to structured JSON.

This script:
- Processes all PDFs in data/raw_pdf/
- Extracts text using PyMuPDF (fitz)
- Identifies individual questions
- Structures data with course, unit, year, and question fields
- Outputs a single JSON file with all questions
"""

import fitz  # PyMuPDF
import json
import os
import re
from pathlib import Path
from typing import List, Dict, Optional
from collections import Counter
import sys

# Get project root directory
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))

# Define paths
RAW_PDF_DIR = os.path.join(project_root, "data", "raw_pdf")
OUTPUT_DIR = os.path.join(project_root, "data")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "extracted_questions.json")

# Course name (fixed)
COURSE_NAME = "Tech_Faculty"


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from a PDF file."""
    try:
        doc = fitz.open(pdf_path)
        full_text = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            full_text.append(text)
        doc.close()
        return "\n".join(full_text)
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
        return ""


def extract_year_from_filename(filename: str) -> Optional[str]:
    """Try to extract year from filename using common patterns."""
    # Common patterns: "2023", "2024", "(2023)", "[2023]", "year_2023", etc.
    year_patterns = [
        r'\b(19|20)\d{2}\b',  # 4-digit year (1900-2099)
        r'\((\d{4})\)',  # Year in parentheses
        r'\[(\d{4})\]',  # Year in brackets
    ]
    
    for pattern in year_patterns:
        matches = re.findall(pattern, filename)
        if matches:
            # Get the last match (most likely to be the year)
            if isinstance(matches[-1], tuple):
                return matches[-1]
            return matches[-1]
    return None


def extract_year_from_content(text: str) -> Optional[str]:
    """Try to extract year from PDF content (header, title, etc.)."""
    # Look for year in common patterns in the first few lines
    lines = text.split('\n')[:20]  # Check first 20 lines
    for line in lines:
        year_match = re.search(r'\b(19|20)\d{2}\b', line)
        if year_match:
            return year_match.group(0)
    return None


def extract_unit_from_content(text: str, filename: str) -> str:
    """Try to extract unit/course code from PDF content or filename."""
    # Common unit patterns: "CSC 101", "COM 301", "ICT 201", "BBIT106", etc.
    unit_patterns = [
        r'\b[A-Z]{2,4}\s*\d{3}\b',  # Pattern: ABC 123 or ABC123
        r'\b[A-Z]{2,4}\d{3}\b',     # Pattern: ABC123
        r'COURSE\s*CODE[:\s]+([A-Z]{2,4}\s*\d{3})',  # "COURSE CODE: CSC 101"
        r'UNIT[:\s]+([A-Z]{2,4}\s*\d{3})',           # "UNIT: CSC 101"
    ]
    
    # Check filename first
    for pattern in unit_patterns[:2]:  # Use simpler patterns for filename
        matches = re.findall(pattern, filename.upper())
        if matches:
            result = matches[0] if isinstance(matches[0], str) else matches[0]
            return result.replace(' ', '').replace(':', '')
    
    # Check PDF content (first 50 lines and throughout for patterns with labels)
    lines = text.split('\n')[:50]
    for line in lines:
        for pattern in unit_patterns:
            matches = re.findall(pattern, line.upper())
            if matches:
                # Handle tuple results from groups
                if isinstance(matches[0], tuple):
                    result = matches[0][0] if matches[0][0] else matches[0]
                else:
                    result = matches[0]
                result = result.replace(' ', '').replace(':', '')
                if len(result) >= 5:  # Minimum length check (e.g., "CSC101")
                    return result
    
    # Try searching the entire document for course codes (slower but more thorough)
    full_matches = re.findall(r'\b[A-Z]{2,4}\s*\d{3}\b', text.upper())
    if full_matches:
        # Return the most common course code (likely the actual unit)
        cleaned_matches = [m.replace(' ', '').replace(':', '') for m in full_matches if len(m.replace(' ', '')) >= 5]
        if cleaned_matches:
            most_common = Counter(cleaned_matches).most_common(1)[0][0]
            return most_common
    
    return "Unknown"


def is_instruction_block(text: str) -> bool:
    """Check if text is an instruction block rather than a question."""
    instruction_keywords = [
        r'INSTRUCTIONS?:',
        r'DIRECTIONS?:',
        r'NOTE:',
        r'READ\s+THE\s+FOLLOWING',
        r'^SECTION\s+[A-Z]+\s*:?\s*\d+\s*MARKS?$',
        r'^SECTION\s+[A-Z]+\s*$',
    ]
    
    text_upper = text.upper().strip()
    
    # Check if it starts with exam header boilerplate
    exam_header_start = [
        r'^UNIVERSITY\s+EXAMINATIONS?:',
        r'^EXAMINATION\s+FOR\s+THE\s+DEGREE',
        r'^FULL\s+TIME/PART\s+TIME',
    ]
    
    for pattern in exam_header_start:
        if re.match(pattern, text_upper):
            # If the text is mostly header (less than 300 chars), filter it out
            if len(text) < 300:
                return True
    
    for pattern in instruction_keywords:
        if re.search(pattern, text_upper):
            # If it's mostly just instructions without actual question content
            if len(text) < 200 and not re.search(r'[?]', text):
                return True
    
    # Check if it's just a section header
    if re.match(r'^(SECTION\s+[A-Z]+|QUESTION\s+ONE|QUESTION\s+TWO)[\s:]*(\d+\s*MARKS?)?\s*$', text_upper):
        return True
    
    return False


def clean_question_text(text: str) -> str:
    """Clean up question text by removing excessive whitespace, headers, and section markers."""
    
    # Remove degree/course header lines at the beginning (multi-line patterns)
    lines = text.split('\n')
    cleaned_lines = []
    skip_header_mode = True
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        line_upper = line_stripped.upper()
        
        # Skip header lines at the beginning
        if skip_header_mode:
            if any(pattern in line_upper for pattern in [
                'UNIVERSITY EXAMINATIONS',
                'EXAMINATION FOR THE DEGREE',
                'BACHELOR OF SCIENCE',
                'INFORMATION TECHNOLOGY/ BUSINESS',
                'APPLIED COMPUTING/ SOFTWARE',
                'INFORMATION SECURITY',
                'FULL TIME/PART TIME',
                'DATE:',
                'TIME:',
                'INSTRUCTIONS:',
            ]):
                continue
            
            # Skip course code lines (like "BIT 3101A/ BBIT 106/...")
            if re.match(r'^[A-Z]+\s+\d+[A-Z]*/\s*[A-Z]+\s+\d+', line_upper):
                continue
            
            # Once we find actual content, stop skipping
            if line_stripped and len(line_stripped) > 10:
                skip_header_mode = False
        
        cleaned_lines.append(line)
    
    text = '\n'.join(cleaned_lines)
    
    # Remove exam headers/boilerplate patterns (if they slipped through)
    exam_header_patterns = [
        r'^UNIVERSITY\s+EXAMINATIONS?:.*?\n',
        r'^EXAMINATION\s+FOR\s+THE\s+DEGREE.*?\n',
        r'^BACHELOR\s+OF\s+SCIENCE.*?\n',
        r'^INFORMATION\s+TECHNOLOGY/.*?\n',
        r'^FULL\s+TIME/PART\s+TIME/DISTANCE\s+LEARNING.*?\n',
        r'^DATE:.*?\n',
        r'^TIME:.*?\n',
        r'^INSTRUCTIONS?:.*?\n',
        r'^[A-Z]+\s+\d+[A-Z]*/\s*[A-Z]+\s+\d+.*?:.*?\n',  # Course codes like "BIT 3101A/ BBIT 106: DATA..."
    ]
    
    for pattern in exam_header_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)
    
    # Remove section headers that appear anywhere (embedded in questions)
    section_patterns = [
        r'\n\s*SECTION\s+[IVX]+\s*:\s*[A-Z]+\s*\.?\s*\d*\s*MARKS?\.?\s*\n',  # "SECTION II: PRACTICAL. 20 MARKS."
        r'\n\s*SECTION\s+[A-Z]+\s*:?\s*\d*\s*MARKS?\.?\s*\n',  # "SECTION A: 20 MARKS" or "SECTION B. 10 MARKS"
        r'\n\s*SECTION\s+[A-Z]+\s*\.?\s*\n',  # "SECTION C."
    ]
    
    for pattern in section_patterns:
        text = re.sub(pattern, '\n', text, flags=re.IGNORECASE)
    
    # Remove section headers from the end
    section_end_patterns = [
        r'\n\s*SECTION\s+[A-Z]+\s*:?\s*\(?\s*\d*\s*MARKS?\s*\)?\s*$',
        r'\n\s*SECTION\s+[A-Z]+\s*$',
        r'\s+SECTION\s+[A-Z]+\s*:?\s*\(?\s*\d*\s*MARKS?\s*\)?\s*$',
        r'\s+SECTION\s+[A-Z]+\s*$',
    ]
    
    for pattern in section_end_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)
    
    # Replace multiple newlines with double newline
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Replace multiple spaces with single space
    text = re.sub(r' {2,}', ' ', text)
    # Remove trailing whitespace from each line
    lines = [line.rstrip() for line in text.split('\n')]
    text = '\n'.join(lines)
    
    # Remove empty lines from the beginning and end
    text = text.strip()
    
    # Remove any remaining section markers at the very end
    text = re.sub(r'\s+SECTION\s+[A-Z]+\s*:?\s*\(?\s*\d*\s*MARKS?\s*\)?\s*$', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+SECTION\s+[A-Z]+\s*$', '', text, flags=re.IGNORECASE)
    
    return text.strip()


def split_combined_questions(text: str) -> List[str]:
    """
    Split text that may contain multiple main questions combined into one.
    Looks for patterns like QUESTION ONE, QUESTION TWO, Q1, Q2, etc.
    """
    # Patterns for main question starts (not subparts)
    # Also handle common misspellings like "QESTION"
    main_question_patterns = [
        r'^Q[UE]+ESTION\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|\d+)',  # Handles QUESTION and QESTION
        r'^Q\s*(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|\d+)',
        r'^Q\s*\d+\s*[\.\)]',
        r'^Q[UE]+ESTION\s+\d+',
    ]
    
    lines = text.split('\n')
    splits = []  # Start positions for each question
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        # Check if this line starts a new main question
        line_upper = line_stripped.upper()
        
        # Check for question patterns (more flexible matching)
        is_question_line = any([
            re.match(pattern, line_stripped, re.IGNORECASE) for pattern in main_question_patterns
        ]) or re.search(r'\bQ[UE]+ESTION\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|\d+)', line_upper)
        
        if is_question_line:
            # Verify it's a real question start
            next_lines = ' '.join(lines[i:min(i+3, len(lines))]).upper()
            
            # Check if it's a main question (has marks, is numbered, or is clearly a question header)
            is_main_question = any([
                'MARK' in next_lines or 'MARKS' in next_lines,
                'COMPULSORY' in next_lines,
                re.search(r'Q[UE]+ESTION\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|\d+)', line_upper),
                re.search(r'\bQ\s*\d+\s*[\.\)]', line_upper),
                re.search(r'\bQ\s*(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN)\b', line_upper),
            ])
            
            if is_main_question:
                splits.append(i)
    
    # If we found multiple splits, create separate questions
    if len(splits) > 1:
        questions = []
        for i in range(len(splits)):
            start = splits[i]
            end = splits[i + 1] if i + 1 < len(splits) else len(lines)
            question_text = '\n'.join(lines[start:end]).strip()
            if question_text and len(question_text) > 50:
                questions.append(question_text)
        return questions if questions else [text]
    
    return [text]


def identify_questions(text: str) -> List[str]:
    """
    Split text into individual questions.
    Questions typically start with numbers like "1.", "QUESTION 1", "(a)", etc.
    """
    questions = []
    
    # Expanded question patterns to catch more variants (including misspellings)
    question_patterns = [
        r'^\s*\d+[\.\)]\s+',  # "1. " or "1) "
        r'^Q[UE]+ESTION\s+\d+',   # "QUESTION 1", "QESTION 2", etc. (handles misspellings)
        r'^Q[UE]+ESTION\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN)',  # "QUESTION ONE", "QESTION TWO", etc.
        r'^Q\s*\d+[\.\)]?\s*',   # "Q1" or "Q1." or "Q1)"
        r'^Q\s*(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN)',  # "Q ONE", "Q TWO", etc.
        r'^\s*\(\d+\)',       # "(1)"
    ]
    
    lines = text.split('\n')
    current_question = []
    question_started = False
    skip_instructions = True
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # Skip empty lines at the start
        if not line_stripped and not question_started:
            continue
        
        # Check if this line starts a new question
        is_question_start = False
        for pattern in question_patterns:
            if re.match(pattern, line_stripped, re.IGNORECASE):
                is_question_start = True
                break
        
        if is_question_start:
            # Save previous question if exists
            if current_question and question_started:
                question_text = clean_question_text('\n'.join(current_question))
                if question_text and len(question_text) > 30:  # Minimum length check
                    # Filter out instruction blocks
                    if not is_instruction_block(question_text):
                        questions.append(question_text)
            # Start new question
            current_question = [line]
            question_started = True
            skip_instructions = False
        elif question_started:
            # Continue current question
            current_question.append(line)
        elif not question_started and not skip_instructions:
            # Check if we should start (sometimes questions don't have clear markers)
            if len(line_stripped) > 20:
                # Skip if it's clearly an instruction
                if is_instruction_block(line_stripped):
                    continue
                # Start if it looks like a question
                if any(keyword in line_stripped.upper() 
                      for keyword in ['QUESTION', 'MARKS', 'ANSWER', 'REQUIRED', 'TASK']):
                    question_started = True
                    current_question = [line]
    
    # Add last question
    if current_question and question_started:
        question_text = clean_question_text('\n'.join(current_question))
        if question_text and len(question_text) > 30:
            if not is_instruction_block(question_text):
                questions.append(question_text)
    
    # Post-process: Split questions that contain multiple main questions
    split_questions = []
    for q in questions:
        # Check if this question contains multiple main questions
        split_result = split_combined_questions(q)
        for split_q in split_result:
            cleaned = clean_question_text(split_q)
            if cleaned and len(cleaned) > 30:
                if not is_instruction_block(cleaned):
                    split_questions.append(cleaned)
    
    questions = split_questions if split_questions else questions
    
    # Filter out very short questions that are likely fragments
    filtered_questions = []
    for q in questions:
        # Remove questions that are too short or look like fragments
        if len(q.strip()) < 50:
            # Allow short questions only if they contain a question mark
            if '?' not in q:
                continue
        # Remove questions that are just numbers or single words
        words = q.split()
        if len(words) < 5 and not re.search(r'[?]', q):
            continue
        filtered_questions.append(q)
    
    # If no questions found with patterns, try alternative approach
    if not filtered_questions:
        # Try splitting by double newlines or page breaks
        sections = re.split(r'\n{3,}', text)
        for s in sections:
            s_clean = clean_question_text(s)
            if len(s_clean) > 100 and not is_instruction_block(s_clean):
                filtered_questions.append(s_clean)
    
    return filtered_questions


def process_pdf(pdf_path: str) -> List[Dict]:
    """Process a single PDF and return list of question dictionaries."""
    filename = os.path.basename(pdf_path)
    print(f"Processing: {filename}")
    
    # Extract text
    text = extract_text_from_pdf(pdf_path)
    if not text or len(text.strip()) < 50:
        print(f"  Warning: Could not extract meaningful text from {filename}")
        return []
    
    # Extract metadata
    year = extract_year_from_filename(filename)
    if not year:
        year = extract_year_from_content(text)
    
    unit = extract_unit_from_content(text, filename)
    
    # Identify questions
    questions = identify_questions(text)
    print(f"  Found {len(questions)} question(s)")
    
    # Create question dictionaries with final cleanup
    question_dicts = []
    for idx, question_text in enumerate(questions, 1):
        # Apply final cleaning pass to ensure headers and section markers are removed
        cleaned_question = clean_question_text(question_text)
        
        # Skip if question is too short after cleaning
        if len(cleaned_question) < 30:
            continue
            
        question_dict = {
            "course": COURSE_NAME,
            "unit": unit,
            "year": year if year else "Unknown",
            "question": cleaned_question,
            "source_file": filename,
            "question_number": idx,
            # Metadata tags
            "metadata": {
                "university": "KCA_UNI",
                "faculty": "TECH_FACULTY",
                "unit_code": unit,
                "source_type": "past_paper"
            }
        }
        question_dicts.append(question_dict)
    
    return question_dicts


def validate_json(data: List[Dict]) -> bool:
    """Validate that JSON data has correct structure."""
    required_fields = ["course", "unit", "year", "question"]
    
    for item in data:
        if not isinstance(item, dict):
            return False
        for field in required_fields:
            if field not in item:
                print(f"Warning: Missing required field '{field}' in question")
                return False
        if not isinstance(item["question"], str) or len(item["question"].strip()) < 5:
            print(f"Warning: Invalid or empty question text")
            return False
    
    return True


def main():
    """Main function to process all PDFs and create JSON output."""
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Check if raw PDF directory exists
    if not os.path.exists(RAW_PDF_DIR):
        print(f"Error: Directory not found: {RAW_PDF_DIR}")
        print(f"Please ensure PDFs are in the data/raw_pdf/ folder")
        sys.exit(1)
    
    # Get all PDF files
    pdf_files = list(Path(RAW_PDF_DIR).glob("*.pdf"))
    if not pdf_files:
        print(f"Error: No PDF files found in {RAW_PDF_DIR}")
        sys.exit(1)
    
    print(f"Found {len(pdf_files)} PDF file(s) to process\n")
    
    # Process all PDFs
    all_questions = []
    processed_count = 0
    error_count = 0
    
    for pdf_path in sorted(pdf_files):
        try:
            questions = process_pdf(str(pdf_path))
            all_questions.extend(questions)
            processed_count += 1
        except Exception as e:
            print(f"  Error processing {pdf_path.name}: {e}")
            error_count += 1
    
    print(f"\n{'='*60}")
    print(f"Processing complete!")
    print(f"  Processed: {processed_count} PDF(s)")
    print(f"  Errors: {error_count} PDF(s)")
    print(f"  Total questions extracted: {len(all_questions)}")
    
    if not all_questions:
        print("\nWarning: No questions were extracted. Check PDF formats and extraction logic.")
        sys.exit(1)
    
    # Validate JSON structure
    if not validate_json(all_questions):
        print("\nWarning: Some questions have invalid structure. Proceeding anyway...")
    
    # Save to JSON file
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_questions, f, indent=2, ensure_ascii=False)
        
        # Validate JSON file can be read back
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            json.load(f)
        
        print(f"\n✓ Successfully saved {len(all_questions)} questions to:")
        print(f"  {OUTPUT_FILE}")
        print(f"\n✓ JSON file validated successfully")
        
        # Print sample
        if all_questions:
            print(f"\nSample question:")
            sample = all_questions[0]
            print(f"  Course: {sample['course']}")
            print(f"  Unit: {sample['unit']}")
            print(f"  Year: {sample['year']}")
            print(f"  Question (first 100 chars): {sample['question'][:100]}...")
    
    except Exception as e:
        print(f"\nError saving JSON file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

