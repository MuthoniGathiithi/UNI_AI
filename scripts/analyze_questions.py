#!/usr/bin/env python3
"""
Analyze KCA University past exam questions for patterns.

This script:
- Identifies repeated/similar questions
- Finds common topics and keywords
- Analyzes question distribution by unit/year
- Generates statistics and insights
"""

import json
import os
import re
from collections import Counter, defaultdict
from typing import List, Dict, Set
from difflib import SequenceMatcher

# Import the loader
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from load_data import load_questions


def similarity_score(text1: str, text2: str) -> float:
    """Calculate similarity score between two texts (0-1)."""
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()


def find_repeated_questions(questions: List[Dict], threshold: float = 0.8) -> List[Dict]:
    """
    Find questions that are similar/repeated.
    
    Args:
        questions: List of question dictionaries
        threshold: Similarity threshold (0-1) for considering questions similar
    
    Returns:
        List of dictionaries with similar question pairs
    """
    repeated = []
    
    for i, q1 in enumerate(questions):
        for j, q2 in enumerate(questions[i+1:], start=i+1):
            similarity = similarity_score(q1["question"], q2["question"])
            
            if similarity >= threshold:
                repeated.append({
                    "question1": {
                        "unit": q1.get("unit"),
                        "year": q1.get("year"),
                        "source": q1.get("source_file"),
                        "text": q1["question"][:200] + "..."
                    },
                    "question2": {
                        "unit": q2.get("unit"),
                        "year": q2.get("year"),
                        "source": q2.get("source_file"),
                        "text": q2["question"][:200] + "..."
                    },
                    "similarity": round(similarity, 3)
                })
    
    return sorted(repeated, key=lambda x: x["similarity"], reverse=True)


def extract_keywords(text: str, min_length: int = 4) -> List[str]:
    """Extract keywords from question text."""
    # Remove common words
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "are", "was", "were", "be",
        "been", "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "can", "this", "that",
        "these", "those", "what", "which", "who", "where", "when", "why",
        "how", "all", "each", "every", "some", "any", "no", "not", "only"
    }
    
    # Extract words
    words = re.findall(r'\b[a-zA-Z]{' + str(min_length) + r',}\b', text.lower())
    
    # Filter stop words and return unique keywords
    keywords = [w for w in words if w not in stop_words]
    return list(set(keywords))


def find_common_topics(questions: List[Dict], top_n: int = 20) -> List[tuple]:
    """Find most common topics/keywords across all questions."""
    all_keywords = []
    
    for q in questions:
        keywords = extract_keywords(q["question"])
        all_keywords.extend(keywords)
    
    keyword_counts = Counter(all_keywords)
    return keyword_counts.most_common(top_n)


def analyze_by_unit(questions: List[Dict]) -> Dict:
    """Analyze question distribution and topics by unit."""
    unit_analysis = defaultdict(lambda: {"count": 0, "years": set(), "keywords": []})
    
    for q in questions:
        unit = q.get("unit", "Unknown")
        unit_analysis[unit]["count"] += 1
        unit_analysis[unit]["years"].add(str(q.get("year", "Unknown")))
        
        keywords = extract_keywords(q["question"], min_length=5)
        unit_analysis[unit]["keywords"].extend(keywords)
    
    # Process results
    results = {}
    for unit, data in unit_analysis.items():
        keyword_counts = Counter(data["keywords"])
        results[unit] = {
            "count": data["count"],
            "years": sorted(list(data["years"])),
            "top_keywords": keyword_counts.most_common(10)
        }
    
    return results


def analyze_question_lengths(questions: List[Dict]) -> Dict:
    """Analyze question length distribution."""
    lengths = [len(q["question"]) for q in questions]
    
    return {
        "min": min(lengths),
        "max": max(lengths),
        "avg": sum(lengths) / len(lengths),
        "median": sorted(lengths)[len(lengths) // 2]
    }


def generate_report(loader) -> None:
    """Generate comprehensive analysis report."""
    questions = loader.get_all_questions()
    
    print("=" * 70)
    print("KCA UNIVERSITY TECH FACULTY - QUESTION ANALYSIS REPORT")
    print("=" * 70)
    
    # Basic statistics
    stats = loader.get_statistics()
    print(f"\n📊 BASIC STATISTICS")
    print(f"  Total questions: {stats['total_questions']}")
    print(f"  Unique units: {stats['unique_units']}")
    print(f"  Unique years: {stats['unique_years']}")
    
    # Question length analysis
    length_stats = analyze_question_lengths(questions)
    print(f"\n📏 QUESTION LENGTH ANALYSIS")
    print(f"  Average length: {length_stats['avg']:.0f} characters")
    print(f"  Min length: {length_stats['min']} characters")
    print(f"  Max length: {length_stats['max']} characters")
    print(f"  Median length: {length_stats['median']} characters")
    
    # Common topics
    common_topics = find_common_topics(questions, top_n=15)
    print(f"\n🔑 COMMON TOPICS/KEYWORDS (Top 15)")
    for keyword, count in common_topics:
        print(f"  {keyword}: {count} occurrences")
    
    # Analysis by unit
    unit_analysis = analyze_by_unit(questions)
    print(f"\n📚 ANALYSIS BY UNIT")
    for unit in sorted(unit_analysis.keys()):
        data = unit_analysis[unit]
        print(f"\n  {unit}:")
        print(f"    Questions: {data['count']}")
        print(f"    Years: {', '.join(data['years'][:5])}{'...' if len(data['years']) > 5 else ''}")
        print(f"    Top keywords: {', '.join([k for k, v in data['top_keywords'][:5]])}")
    
    # Repeated questions
    print(f"\n🔁 SEARCHING FOR REPEATED/SIMILAR QUESTIONS...")
    print("  (This may take a moment...)")
    repeated = find_repeated_questions(questions, threshold=0.85)
    
    if repeated:
        print(f"\n  Found {len(repeated)} similar question pairs (similarity >= 85%):")
        for i, pair in enumerate(repeated[:10], 1):  # Show top 10
            print(f"\n  Pair {i} (Similarity: {pair['similarity']:.1%}):")
            print(f"    Unit: {pair['question1']['unit']} ({pair['question1']['year']}) vs {pair['question2']['unit']} ({pair['question2']['year']})")
            print(f"    Text 1: {pair['question1']['text']}")
            print(f"    Text 2: {pair['question2']['text']}")
    else:
        print("  No highly similar questions found (threshold: 85%)")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    # Load questions
    loader = load_questions()
    
    # Generate report
    generate_report(loader)

