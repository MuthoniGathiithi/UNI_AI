#!/usr/bin/env python3
"""
Add metadata tags to existing extracted_questions.json file.

This script updates existing questions with metadata tags:
- KCA_UNI (university tag)
- TECH_FACULTY (faculty tag)
- Unit codes
- Source type
"""

import json
import os
import sys

# Get project root directory
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
DATA_FILE = os.path.join(project_root, "data", "extracted_questions.json")
BACKUP_FILE = os.path.join(project_root, "data", "extracted_questions.json.backup")


def add_metadata_tags():
    """Add metadata tags to all questions in the JSON file."""
    
    # Check if file exists
    if not os.path.exists(DATA_FILE):
        print(f"Error: File not found: {DATA_FILE}")
        sys.exit(1)
    
    # Create backup
    print(f"Creating backup: {BACKUP_FILE}")
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        backup_data = f.read()
    with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
        f.write(backup_data)
    
    # Load questions
    print(f"Loading questions from {DATA_FILE}...")
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    
    print(f"Found {len(questions)} questions")
    
    # Add metadata tags
    updated_count = 0
    for q in questions:
        # Only add if metadata doesn't exist or is incomplete
        if "metadata" not in q or not q.get("metadata"):
            q["metadata"] = {
                "university": "KCA_UNI",
                "faculty": "TECH_FACULTY",
                "unit_code": q.get("unit", "Unknown"),
                "source_type": "past_paper"
            }
            updated_count += 1
    
    # Save updated questions
    print(f"Updating {updated_count} questions with metadata tags...")
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)
    
    # Validate
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        json.load(f)
    
    print(f"✓ Successfully updated {updated_count} questions")
    print(f"✓ Backup saved to: {BACKUP_FILE}")
    print(f"✓ Updated file: {DATA_FILE}")


if __name__ == "__main__":
    print("=" * 70)
    print("ADDING METADATA TAGS TO QUESTIONS")
    print("=" * 70)
    print()
    
    add_metadata_tags()
    
    print("\n" + "=" * 70)
    print("✓ Metadata tags added successfully!")
    print("=" * 70)

