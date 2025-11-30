#!/usr/bin/env python3
"""
Analyze extraction issues in the question dataset.

This script identifies:
1. Why 128 questions have "Unknown" unit code
2. Whether OF250 being all 2019 is a problem
3. Data quality issues in the extraction process
"""

import json
import os
from collections import defaultdict
from pathlib import Path

# Get project root directory
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
INPUT_FILE = os.path.join(project_root, "data", "extracted_questions.json")
ANALYSIS_FILE = os.path.join(project_root, "data", "extraction_analysis.json")


def load_questions(json_file: str):
    """Load questions from JSON file."""
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_unknown_units(questions):
    """Analyze why questions have 'Unknown' unit code."""
    unknown_questions = [q for q in questions if q.get('unit') == 'Unknown']
    
    analysis = {
        'total_unknown': len(unknown_questions),
        'percentage': f"{(len(unknown_questions) / len(questions) * 100):.1f}%",
        'by_source_file': defaultdict(list),
        'by_year': defaultdict(int),
        'by_course': defaultdict(int),
        'sample_questions': []
    }
    
    # Group by source file
    for q in unknown_questions:
        source = q.get('source_file', 'Unknown')
        analysis['by_source_file'][source].append({
            'year': q.get('year'),
            'question_number': q.get('question_number'),
            'course': q.get('course')
        })
        analysis['by_year'][q.get('year')] += 1
        analysis['by_course'][q.get('course')] += 1
    
    # Get sample questions
    for q in unknown_questions[:3]:
        analysis['sample_questions'].append({
            'year': q.get('year'),
            'source_file': q.get('source_file'),
            'question_preview': q.get('question', '')[:150] + '...',
            'metadata': q.get('metadata')
        })
    
    return analysis


def analyze_unit_distribution(questions):
    """Analyze unit code distribution."""
    units = defaultdict(lambda: {'count': 0, 'years': set(), 'sources': set()})
    
    for q in questions:
        unit = q.get('unit', 'Unknown')
        units[unit]['count'] += 1
        units[unit]['years'].add(str(q.get('year', 'Unknown')))
        units[unit]['sources'].add(q.get('source_file', 'Unknown'))
    
    # Convert sets to lists for JSON serialization
    analysis = {}
    for unit, data in units.items():
        analysis[unit] = {
            'count': data['count'],
            'years': sorted(list(data['years'])),
            'num_sources': len(data['sources']),
            'sources': sorted(list(data['sources']))[:3]  # Show first 3 sources
        }
    
    return analysis


def analyze_year_distribution(questions):
    """Analyze year distribution."""
    years = defaultdict(lambda: {'count': 0, 'units': set()})
    
    for q in questions:
        year = str(q.get('year', 'Unknown'))
        years[year]['count'] += 1
        unit = q.get('unit', 'Unknown')
        if unit != 'Unknown':
            years[year]['units'].add(unit)
    
    # Convert sets to lists
    analysis = {}
    for year, data in sorted(years.items()):
        analysis[year] = {
            'count': data['count'],
            'unique_units': len(data['units']),
            'units': sorted(list(data['units']))
        }
    
    return analysis


def check_extraction_quality(questions):
    """Check overall extraction quality."""
    issues = {
        'missing_unit': 0,
        'missing_year': 0,
        'missing_course': 0,
        'missing_question': 0,
        'missing_source_file': 0,
        'missing_metadata': 0,
        'total_issues': 0
    }
    
    for q in questions:
        if not q.get('unit') or q.get('unit') == 'Unknown':
            issues['missing_unit'] += 1
        if not q.get('year'):
            issues['missing_year'] += 1
        if not q.get('course'):
            issues['missing_course'] += 1
        if not q.get('question'):
            issues['missing_question'] += 1
        if not q.get('source_file'):
            issues['missing_source_file'] += 1
        if not q.get('metadata'):
            issues['missing_metadata'] += 1
    
    issues['total_issues'] = sum(v for k, v in issues.items() if k != 'total_issues')
    
    return issues


def generate_recommendations(analysis):
    """Generate recommendations based on analysis."""
    recommendations = []
    
    unknown_pct = float(analysis['unknown_units']['percentage'].rstrip('%'))
    
    if unknown_pct > 50:
        recommendations.append({
            'severity': 'HIGH',
            'issue': f"{unknown_pct:.1f}% of questions have 'Unknown' unit code",
            'cause': 'PDF extraction likely failed to capture unit codes from headers/footers',
            'action': 'Review PDF extraction logic - unit codes may be in specific locations',
            'impact': 'Reduces ability to filter questions by unit for RAG system'
        })
    
    recommendations.append({
        'severity': 'MEDIUM',
        'issue': 'Unit codes not extracted from PDFs',
        'cause': 'Extraction script may not be parsing unit code fields correctly',
        'action': 'Manually review a sample of Unknown unit PDFs to identify unit code location',
        'impact': 'Cannot organize questions by curriculum unit'
    })
    
    recommendations.append({
        'severity': 'INFO',
        'issue': 'Duplicate PDFs detected (e.g., file_name.pdf and file_name (1).pdf)',
        'cause': 'Same PDF uploaded/processed multiple times',
        'action': 'Deduplication already handled - keep canonical version with source tracking',
        'impact': 'Resolved - 16 duplicate instances removed'
    })
    
    return recommendations


def main():
    """Main analysis workflow."""
    print("Loading questions...")
    questions = load_questions(INPUT_FILE)
    print(f"✓ Loaded {len(questions)} questions\n")
    
    print("=" * 80)
    print("EXTRACTION QUALITY ANALYSIS")
    print("=" * 80)
    
    # Analyze unknown units
    print("\n1️⃣  UNKNOWN UNIT CODES ANALYSIS")
    print("-" * 80)
    unknown_analysis = analyze_unknown_units(questions)
    print(f"Total questions with 'Unknown' unit: {unknown_analysis['total_unknown']} ({unknown_analysis['percentage']})")
    print(f"\nBreakdown by year:")
    for year in sorted(unknown_analysis['by_year'].keys()):
        count = unknown_analysis['by_year'][year]
        print(f"  {year}: {count} questions")
    
    print(f"\nBreakdown by course:")
    for course, count in sorted(unknown_analysis['by_course'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {course}: {count} questions")
    
    print(f"\nTop sources with Unknown units:")
    for source, items in sorted(unknown_analysis['by_source_file'].items(), 
                                key=lambda x: len(x[1]), reverse=True)[:3]:
        print(f"  {source}: {len(items)} questions")
    
    # Analyze unit distribution
    print("\n\n2️⃣  UNIT CODE DISTRIBUTION")
    print("-" * 80)
    unit_analysis = analyze_unit_distribution(questions)
    print("Units with known codes:")
    for unit, data in sorted(unit_analysis.items(), key=lambda x: x[1]['count'], reverse=True):
        if unit != 'Unknown':
            print(f"  {unit}: {data['count']} questions, Years: {', '.join(data['years'])}")
    
    # Check OF250 specifically
    print("\n\n3️⃣  SPECIFIC UNIT ANALYSIS: OF250")
    print("-" * 80)
    of250_questions = [q for q in questions if q.get('unit') == 'OF250']
    of250_years = set(str(q.get('year')) for q in of250_questions)
    print(f"Total OF250 questions: {len(of250_questions)}")
    print(f"Years found: {sorted(of250_years)}")
    if len(of250_years) == 1:
        print("⚠️  OBSERVATION: All OF250 questions are from a single year (2019)")
        print("   This could be normal if:")
        print("   - Only one OF250 past paper was uploaded")
        print("   - OF250 is a new unit (started in 2019)")
        print("   - Other years' papers are not yet in the system")
    
    # Extraction quality
    print("\n\n4️⃣  EXTRACTION QUALITY METRICS")
    print("-" * 80)
    quality = check_extraction_quality(questions)
    print(f"Missing unit codes: {quality['missing_unit']} ({quality['missing_unit']/len(questions)*100:.1f}%)")
    print(f"Missing years: {quality['missing_year']}")
    print(f"Missing courses: {quality['missing_course']}")
    print(f"Missing questions: {quality['missing_question']}")
    print(f"Missing source files: {quality['missing_source_file']}")
    print(f"Missing metadata: {quality['missing_metadata']}")
    
    # Recommendations
    print("\n\n5️⃣  RECOMMENDATIONS")
    print("-" * 80)
    recommendations = generate_recommendations({
        'unknown_units': unknown_analysis,
        'unit_analysis': unit_analysis,
        'quality': quality
    })
    
    for i, rec in enumerate(recommendations, 1):
        print(f"\n[{rec['severity']}] {i}. {rec['issue']}")
        print(f"  Cause: {rec['cause']}")
        print(f"  Action: {rec['action']}")
        print(f"  Impact: {rec['impact']}")
    
    # Save analysis
    print("\n\n" + "=" * 80)
    analysis_data = {
        'summary': {
            'total_questions': len(questions),
            'unknown_units_count': unknown_analysis['total_unknown'],
            'unknown_units_percentage': unknown_analysis['percentage'],
            'extraction_quality': quality
        },
        'unknown_units': unknown_analysis,
        'unit_distribution': unit_analysis,
        'year_distribution': analyze_year_distribution(questions),
        'recommendations': recommendations
    }
    
    with open(ANALYSIS_FILE, 'w', encoding='utf-8') as f:
        json.dump(analysis_data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Analysis saved to {ANALYSIS_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    main()
