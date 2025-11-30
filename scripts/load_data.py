#!/usr/bin/env python3
"""
Load KCA University past exam questions from JSON into memory.

This script:
- Loads extracted questions from data/extracted_questions.json
- Validates the data structure
- Provides convenient access methods
- Can filter by unit, year, course, etc.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Set
from collections import defaultdict

# Get project root directory
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
# Use deduplicated dataset by default
DATA_FILE = os.path.join(project_root, "data", "past_questions_deduplicated.json")
# Fallback to original if deduplicated doesn't exist
if not os.path.exists(DATA_FILE):
    DATA_FILE = os.path.join(project_root, "data", "extracted_questions.json")


class QuestionLoader:
    """Load and manage past exam questions in memory."""
    
    def __init__(self, json_file: str = DATA_FILE):
        """Initialize loader with questions from JSON file."""
        self.json_file = json_file
        self.questions: List[Dict] = []
        self.load_questions()
    
    def load_questions(self) -> None:
        """Load questions from JSON file into memory."""
        if not os.path.exists(self.json_file):
            raise FileNotFoundError(f"Questions file not found: {self.json_file}")
        
        with open(self.json_file, 'r', encoding='utf-8') as f:
            self.questions = json.load(f)
        
        print(f"✓ Loaded {len(self.questions)} questions from {self.json_file}")
        self._validate_questions()
    
    def _validate_questions(self) -> None:
        """Validate that all questions have required fields."""
        required_fields = ["course", "unit", "year", "question"]
        
        invalid_count = 0
        for i, q in enumerate(self.questions):
            for field in required_fields:
                if field not in q:
                    print(f"Warning: Question {i+1} missing required field '{field}'")
                    invalid_count += 1
        
        if invalid_count == 0:
            print("✓ All questions validated successfully")
        else:
            print(f"⚠ Found {invalid_count} validation issues")
    
    def get_all_questions(self) -> List[Dict]:
        """Get all questions."""
        return self.questions
    
    def filter_by_unit(self, unit: str) -> List[Dict]:
        """Filter questions by unit code."""
        return [q for q in self.questions if q.get("unit", "").upper() == unit.upper()]
    
    def filter_by_year(self, year: str) -> List[Dict]:
        """Filter questions by year."""
        return [q for q in self.questions if str(q.get("year", "")) == str(year)]
    
    def filter_by_course(self, course: str) -> List[Dict]:
        """Filter questions by course."""
        return [q for q in self.questions if q.get("course", "").upper() == course.upper()]
    
    def filter_by_multiple(self, unit: Optional[str] = None, 
                          year: Optional[str] = None,
                          course: Optional[str] = None) -> List[Dict]:
        """Filter questions by multiple criteria."""
        filtered = self.questions
        
        if unit:
            filtered = [q for q in filtered if q.get("unit", "").upper() == unit.upper()]
        if year:
            filtered = [q for q in filtered if str(q.get("year", "")) == str(year)]
        if course:
            filtered = [q for q in filtered if q.get("course", "").upper() == course.upper()]
        
        return filtered
    
    def get_unique_units(self) -> Set[str]:
        """Get set of unique unit codes."""
        return set(q.get("unit", "Unknown") for q in self.questions)
    
    def get_unique_years(self) -> Set[str]:
        """Get set of unique years."""
        return set(str(q.get("year", "Unknown")) for q in self.questions)
    
    def get_statistics(self) -> Dict:
        """Get statistics about the loaded questions."""
        units = defaultdict(int)
        years = defaultdict(int)
        
        for q in self.questions:
            units[q.get("unit", "Unknown")] += 1
            years[str(q.get("year", "Unknown"))] += 1
        
        return {
            "total_questions": len(self.questions),
            "unique_units": len(self.get_unique_units()),
            "unique_years": len(self.get_unique_years()),
            "questions_per_unit": dict(units),
            "questions_per_year": dict(years),
        }
    
    def search_questions(self, keyword: str) -> List[Dict]:
        """Search questions by keyword in question text."""
        keyword_lower = keyword.lower()
        return [q for q in self.questions if keyword_lower in q.get("question", "").lower()]
    
    def get_question_by_id(self, question_number: int, source_file: str) -> Optional[Dict]:
        """Get a specific question by question number and source file."""
        for q in self.questions:
            if (q.get("question_number") == question_number and 
                q.get("source_file") == source_file):
                return q
        return None
    
    def get_source_info(self, question_index: int) -> Optional[Dict]:
        """
        Get source tracking information for a deduplicated question.
        
        Returns metadata about where this question came from and if it was deduplicated.
        """
        if question_index >= len(self.questions):
            return None
        
        q = self.questions[question_index]
        return {
            'is_deduplicated': q.get('metadata', {}).get('is_deduplicated', False),
            'duplicate_count': q.get('metadata', {}).get('duplicate_count', 1),
            'source_pdfs': q.get('metadata', {}).get('source_pdfs', [q.get('source_file')]),
            'years_found': q.get('metadata', {}).get('years_found', [q.get('year')]),
            'source_metadata': q.get('source_metadata', {})
        }
    
    def get_deduplication_stats(self) -> Dict:
        """Get statistics about deduplicated questions."""
        deduplicated_count = sum(1 for q in self.questions 
                                if q.get('metadata', {}).get('is_deduplicated', False))
        total_duplicates_merged = sum(q.get('metadata', {}).get('duplicate_count', 1) - 1 
                                     for q in self.questions 
                                     if q.get('metadata', {}).get('is_deduplicated', False))
        
        return {
            'total_questions': len(self.questions),
            'deduplicated_questions': deduplicated_count,
            'total_duplicates_removed': total_duplicates_merged,
            'deduplication_rate': f"{(deduplicated_count / len(self.questions) * 100):.1f}%" if self.questions else "0%"
        }


def load_questions(json_file: str = DATA_FILE) -> QuestionLoader:
    """
    Convenience function to load questions.
    
    Usage:
        loader = load_questions()
        all_questions = loader.get_all_questions()
        unit_questions = loader.filter_by_unit("BBIT106")
    """
    return QuestionLoader(json_file)


if __name__ == "__main__":
    # Test the loader
    print("=" * 60)
    print("Loading KCA University Past Exam Questions")
    print("=" * 60)
    
    loader = load_questions()
    
    # Print deduplication stats
    dedup_stats = loader.get_deduplication_stats()
    print(f"\n🔄 Deduplication Status:")
    print(f"  Total questions: {dedup_stats['total_questions']}")
    print(f"  Deduplicated questions: {dedup_stats['deduplicated_questions']}")
    print(f"  Duplicates removed: {dedup_stats['total_duplicates_removed']}")
    print(f"  Deduplication rate: {dedup_stats['deduplication_rate']}")
    
    # Print statistics
    stats = loader.get_statistics()
    print(f"\n📊 Statistics:")
    print(f"  Total questions: {stats['total_questions']}")
    print(f"  Unique units: {stats['unique_units']}")
    print(f"  Unique years: {stats['unique_years']}")
    
    print(f"\n📚 Questions per unit (top 5):")
    sorted_units = sorted(stats['questions_per_unit'].items(), 
                         key=lambda x: x[1], reverse=True)[:5]
    for unit, count in sorted_units:
        print(f"  {unit}: {count} questions")
    
    print(f"\n📅 Questions per year:")
    sorted_years = sorted(stats['questions_per_year'].items())
    for year, count in sorted_years:
        print(f"  {year}: {count} questions")
    
    # Example: Filter by unit
    print(f"\n🔍 Example: Questions from BBIT106")
    bbit106_questions = loader.filter_by_unit("BBIT106")
    print(f"  Found {len(bbit106_questions)} questions")
    if bbit106_questions:
        print(f"  Sample: {bbit106_questions[0]['question'][:100]}...")
        # Show source info for first question
        source_info = loader.get_source_info(0)
        if source_info and source_info['is_deduplicated']:
            print(f"\n📌 Source Tracking Example:")
            print(f"  This question was deduplicated from {source_info['duplicate_count']} instances")
            print(f"  Found in PDFs: {', '.join(source_info['source_pdfs'][:2])}")
            print(f"  Years: {', '.join(source_info['years_found'])}")

