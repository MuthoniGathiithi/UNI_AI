#!/usr/bin/env python3
"""
Phase 4 Test: Local AI Model + MCP Routing.

This script demonstrates:
1. Loading KCA University past exam questions
2. Filtering questions by unit
3. Sending questions to MCPClient in exam mode
4. Displaying questions and answers

This is a proof-of-concept for the MCP routing system.
"""

import sys
import os
from typing import List, Dict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scripts.load_data import load_questions
from mcp.client import MCPClient
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_phase4():
    """
    Main Phase 4 test function.
    
    Workflow:
    1. Load KCA questions from deduplicated dataset
    2. Filter questions by unit (BBIT106)
    3. Initialize MCP client
    4. Send questions to MCP in exam mode
    5. Display results
    """
    
    print("=" * 80)
    print("PHASE 4 TEST: Local AI Model + MCP Routing")
    print("=" * 80)
    
    # Step 1: Load questions
    print("\n[1/5] Loading KCA University past exam questions...")
    try:
        loader = load_questions()
        all_questions = loader.get_all_questions()
        print(f"✓ Loaded {len(all_questions)} questions")
    except Exception as e:
        print(f"❌ Failed to load questions: {e}")
        return False
    
    # Step 2: Filter by unit
    print("\n[2/5] Filtering questions by unit (BBIT106)...")
    unit_questions = loader.filter_by_unit("BBIT106")
    
    if not unit_questions:
        print("❌ No questions found for BBIT106")
        print(f"Available units: {loader.get_unique_units()}")
        return False
    
    print(f"✓ Found {len(unit_questions)} BBIT106 questions")
    
    # Limit to first 2 questions for testing
    test_questions = unit_questions[:2]
    print(f"  Using first {len(test_questions)} questions for testing")
    
    # Step 3: Initialize MCP client
    print("\n[3/5] Initializing MCP Client...")
    client = MCPClient(default_mode="exam")
    
    # Check connection
    if not client.check_connection():
        print("❌ Cannot connect to Ollama server")
        print("   Make sure Ollama is running: ollama serve")
        return False
    
    print("✓ Connected to Ollama server")
    print(f"✓ Available modes: {', '.join(client.get_available_modes())}")
    
    # Step 4: Send questions to MCP
    print("\n[4/5] Sending questions to MCP Client (EXAM mode)...")
    print("-" * 80)
    
    results = []
    
    for i, question_obj in enumerate(test_questions, 1):
        question_text = question_obj.get("question", "")
        question_number = question_obj.get("question_number", i)
        year = question_obj.get("year", "Unknown")
        
        print(f"\n📝 Question {i}/{len(test_questions)} (Q{question_number}, {year})")
        print(f"   Unit: {question_obj.get('unit')}")
        print(f"   Preview: {question_text[:100]}...")
        
        # Send to MCP
        print(f"   Generating answer in EXAM mode...")
        answer = client.answer_question(question_text, mode="exam")
        
        if answer:
            print(f"   ✓ Answer generated ({len(answer)} chars)")
            results.append({
                "question_number": question_number,
                "year": year,
                "question": question_text,
                "answer": answer,
                "mode": "exam"
            })
        else:
            print(f"   ❌ Failed to generate answer")
            results.append({
                "question_number": question_number,
                "year": year,
                "question": question_text,
                "answer": None,
                "mode": "exam"
            })
    
    # Step 5: Display results
    print("\n[5/5] Displaying Results...")
    print("=" * 80)
    
    for i, result in enumerate(results, 1):
        print(f"\n{'='*80}")
        print(f"RESULT {i}/{len(results)}")
        print(f"{'='*80}")
        print(f"\n📌 Question Details:")
        print(f"   Number: Q{result['question_number']}")
        print(f"   Year: {result['year']}")
        print(f"   Mode: {result['mode'].upper()}")
        
        print(f"\n❓ Question:")
        print(f"   {result['question'][:200]}...")
        
        if result['answer']:
            print(f"\n✅ Answer:")
            print(f"   {result['answer'][:300]}...")
            if len(result['answer']) > 300:
                print(f"   [... {len(result['answer']) - 300} more characters ...]")
        else:
            print(f"\n❌ No answer generated")
    
    print("\n" + "=" * 80)
    print("✓ PHASE 4 TEST COMPLETE")
    print("=" * 80)
    
    return True


def test_multiple_modes():
    """
    Test MCP client with different answer modes.
    
    This demonstrates how the same question can be answered
    in different modes (exam, local, global, mixed).
    """
    
    print("\n" + "=" * 80)
    print("BONUS: Testing Multiple Answer Modes")
    print("=" * 80)
    
    # Load a single question
    loader = load_questions()
    questions = loader.filter_by_unit("BBIT106")
    
    if not questions:
        print("❌ No questions found")
        return False
    
    question_obj = questions[0]
    question_text = question_obj.get("question", "")
    
    print(f"\n📝 Test Question (Q{question_obj.get('question_number')}):")
    print(f"   {question_text[:150]}...")
    
    # Initialize client
    client = MCPClient()
    
    if not client.check_connection():
        print("❌ Cannot connect to Ollama")
        return False
    
    # Test each mode
    modes = ["exam", "local", "global", "mixed"]
    
    for mode in modes:
        print(f"\n{'─'*80}")
        print(f"Testing {mode.upper()} mode...")
        print(f"{'─'*80}")
        
        answer = client.answer_question(question_text, mode=mode)
        
        if answer:
            print(f"✓ {mode.upper()} mode answer:")
            print(f"   {answer[:200]}...")
            if len(answer) > 200:
                print(f"   [... {len(answer) - 200} more characters ...]")
        else:
            print(f"❌ Failed to generate {mode} mode answer")
    
    return True


if __name__ == "__main__":
    # Run Phase 4 test
    success = test_phase4()
    
    if success:
        # Optionally test multiple modes
        try:
            test_multiple_modes()
        except Exception as e:
            logger.warning(f"Multiple modes test failed: {e}")
    
    sys.exit(0 if success else 1)
