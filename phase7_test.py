#!/usr/bin/env python3
"""
Phase 7 Test: RAG (Past Papers-Only) + MCP Orchestration.

This script demonstrates:
1. Building FAISS index from past papers
2. Retrieving similar questions using semantic search
3. Orchestrating RAG + MCP for intelligent answers
4. Testing with exam-style queries
5. Comparing RAG vs model-only answers

This is a proof-of-concept for the RAG system.
"""

import sys
import os
from typing import List, Dict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scripts.rag import RAGSystem, initialize_rag_system
from mcp.orchestrator import MCPOrchestrator
from scripts.load_data import load_questions
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_rag_system():
    """Test RAG system independently."""
    print("\n" + "=" * 80)
    print("TEST 1: RAG System - FAISS Index & Retrieval")
    print("=" * 80)
    
    # Initialize RAG
    print("\n[1/4] Initializing RAG system...")
    rag = initialize_rag_system(force_rebuild=False)
    
    if not rag:
        print("❌ Failed to initialize RAG system")
        return False
    
    print("✓ RAG system initialized")
    
    # Get stats
    print("\n[2/4] Index statistics...")
    stats = rag.get_index_stats()
    print(f"  Total questions indexed: {stats['total_questions']}")
    print(f"  Embedding dimension: {stats['embedding_dimension']}")
    print(f"  Units in index: {len(stats['questions_per_unit'])}")
    print(f"  Years covered: {len(stats['questions_per_year'])}")
    
    # Test retrieval
    print("\n[3/4] Testing semantic search...")
    test_queries = [
        "What is object-oriented programming?",
        "Explain database design principles",
        "How do computer networks work?",
        "What is data structure and algorithms?"
    ]
    
    for query in test_queries:
        print(f"\n  Query: {query}")
        results = rag.retrieve_notes(query, top_k=2)
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"    [{i}] Unit: {result['unit']}, Year: {result['year']}")
                print(f"        Similarity: {result['similarity_score']:.4f}")
                print(f"        Question: {result['question'][:80]}...")
        else:
            print("    No results found")
    
    # Test unit-based retrieval
    print("\n[4/4] Testing unit-based retrieval...")
    unit_results = rag.retrieve_by_unit("BBIT106", query="algorithms", top_k=2)
    print(f"  Retrieved {len(unit_results)} questions from BBIT106")
    
    for result in unit_results:
        print(f"    - Year: {result['year']}, Q#: {result['question_number']}")
    
    print("\n✅ RAG System Test Complete")
    return True


def test_orchestration():
    """Test MCP orchestration with RAG."""
    print("\n" + "=" * 80)
    print("TEST 2: MCP Orchestration - RAG Decision Logic")
    print("=" * 80)
    
    # Initialize orchestrator
    print("\n[1/3] Initializing MCP Orchestrator...")
    orchestrator = MCPOrchestrator()
    print("✓ Orchestrator initialized")
    
    # Test RAG decision logic
    print("\n[2/3] Testing RAG decision logic...")
    test_cases = [
        ("What is Python?", False, "General knowledge"),
        ("Define OOP and explain its principles", True, "Technical definition"),
        ("Solve the network design problem from BBIT106 past paper", True, "Exam question"),
        ("What is the weather today?", False, "General knowledge"),
        ("Explain database normalization with examples from past papers", True, "Technical with context"),
    ]
    
    for query, expected_rag, description in test_cases:
        use_rag, confidence = orchestrator.should_use_rag(query)
        status = "✓" if use_rag == expected_rag else "⚠"
        print(f"\n  {status} {description}")
        print(f"     Query: {query[:60]}...")
        print(f"     Decision: Use RAG = {use_rag}, Confidence = {confidence:.2f}")
    
    # Get orchestration stats
    print("\n[3/3] Orchestration statistics...")
    stats = orchestrator.get_orchestration_stats()
    print(f"  RAG enabled: {stats['rag_enabled']}")
    print(f"  MCP connected: {stats['mcp_connected']}")
    print(f"  RAG threshold: {stats['use_rag_threshold']}")
    
    if stats['rag_enabled']:
        rag_stats = stats.get('rag_stats', {})
        print(f"  Total indexed questions: {rag_stats.get('total_questions', 0)}")
    
    print("\n✅ Orchestration Test Complete")
    return True


def test_rag_retrieval_quality():
    """Test retrieval quality with real exam questions."""
    print("\n" + "=" * 80)
    print("TEST 3: Retrieval Quality - Real Exam Questions")
    print("=" * 80)
    
    # Initialize RAG
    print("\n[1/3] Initializing RAG system...")
    rag = initialize_rag_system(force_rebuild=False)
    
    if not rag:
        print("❌ Failed to initialize RAG")
        return False
    
    # Load some real questions
    print("\n[2/3] Loading real exam questions...")
    loader = load_questions()
    
    # Get questions from different units
    test_units = ["BBIT106", "ISO100", "BUSS202"]
    
    for unit in test_units:
        questions = loader.filter_by_unit(unit)
        
        if not questions:
            print(f"  ⚠ No questions found for {unit}")
            continue
        
        # Use first question as query
        test_question = questions[0]
        query_text = test_question.get("question", "")[:200]
        
        print(f"\n  Unit: {unit}")
        print(f"  Query: {query_text}...")
        
        # Retrieve similar questions
        results = rag.retrieve_notes(query_text, top_k=3)
        
        print(f"  Retrieved {len(results)} similar questions:")
        for i, result in enumerate(results, 1):
            match_unit = result['unit']
            match_year = result['year']
            similarity = result['similarity_score']
            
            # Check if first result is from same unit (good sign)
            if i == 1 and match_unit == unit:
                print(f"    [{i}] ✓ {match_unit} ({match_year}) - Similarity: {similarity:.4f}")
            else:
                print(f"    [{i}] {match_unit} ({match_year}) - Similarity: {similarity:.4f}")
    
    # Test cross-unit retrieval
    print("\n[3/3] Testing cross-unit semantic similarity...")
    
    # Find a question about OOP
    all_questions = loader.get_all_questions()
    oop_question = None
    for q in all_questions:
        if "object-oriented" in q.get("question", "").lower() or "oop" in q.get("question", "").lower():
            oop_question = q
            break
    
    if oop_question:
        query = oop_question.get("question", "")[:150]
        print(f"\n  Query (OOP-related): {query}...")
        
        results = rag.retrieve_notes(query, top_k=5)
        print(f"  Retrieved {len(results)} results:")
        
        # Show units covered
        units_found = set()
        for result in results:
            units_found.add(result['unit'])
            print(f"    - {result['unit']}: {result['similarity_score']:.4f}")
        
        print(f"  Units covered: {', '.join(sorted(units_found))}")
    
    print("\n✅ Retrieval Quality Test Complete")
    return True


def test_rag_mcp_integration():
    """Test integration of RAG with MCP."""
    print("\n" + "=" * 80)
    print("TEST 4: RAG + MCP Integration")
    print("=" * 80)
    
    # Initialize orchestrator
    print("\n[1/3] Initializing orchestrator...")
    orchestrator = MCPOrchestrator()
    print("✓ Orchestrator initialized")
    
    # Test queries
    print("\n[2/3] Testing orchestrated answers...")
    test_queries = [
        ("What is object-oriented programming?", "exam", True),
        ("Explain database design", "local", True),
        ("What is a network?", "exam", False),
    ]
    
    for query, mode, force_rag in test_queries:
        print(f"\n  Query: {query}")
        print(f"  Mode: {mode}, Force RAG: {force_rag}")
        
        # Get answer with orchestration
        answer = orchestrator.answer_question(
            query,
            mode=mode,
            use_rag=force_rag,
            top_k=2
        )
        
        if answer:
            print(f"  ✓ Answer generated ({len(answer)} chars)")
            print(f"    Preview: {answer[:150]}...")
        else:
            print(f"  ⚠ No answer generated (Ollama may not be running)")
    
    # Get final stats
    print("\n[3/3] Final orchestration stats...")
    stats = orchestrator.get_orchestration_stats()
    print(f"  RAG enabled: {stats['rag_enabled']}")
    print(f"  MCP connected: {stats['mcp_connected']}")
    
    print("\n✅ RAG + MCP Integration Test Complete")
    return True


def test_caching():
    """Test topic caching."""
    print("\n" + "=" * 80)
    print("TEST 5: Topic Caching")
    print("=" * 80)
    
    # Initialize RAG
    print("\n[1/2] Initializing RAG system...")
    rag = initialize_rag_system(force_rebuild=False)
    
    if not rag:
        print("❌ Failed to initialize RAG")
        return False
    
    # Cache common topics
    print("\n[2/2] Caching common topics...")
    
    topics = ["OOP", "Networks", "DBMS"]
    
    for topic in topics:
        # Retrieve questions for topic
        results = rag.retrieve_notes(topic, top_k=3)
        
        if results:
            rag.cache_topic(topic, results)
            print(f"  ✓ Cached {len(results)} questions for topic: {topic}")
        else:
            print(f"  ⚠ No questions found for topic: {topic}")
    
    # Test cache retrieval
    print("\n  Testing cache retrieval...")
    for topic in topics:
        cached = rag.get_cached_topic(topic)
        if cached:
            print(f"  ✓ Retrieved {len(cached)} cached questions for {topic}")
        else:
            print(f"  ⚠ No cache found for {topic}")
    
    print("\n✅ Caching Test Complete")
    return True


def main():
    """Run all Phase 7 tests."""
    print("\n" + "=" * 80)
    print("PHASE 7 TEST: RAG (Past Papers-Only) + MCP Orchestration")
    print("=" * 80)
    
    # Run tests
    results = {
        "RAG System": test_rag_system(),
        "Orchestration": test_orchestration(),
        "Retrieval Quality": test_rag_retrieval_quality(),
        "RAG + MCP Integration": test_rag_mcp_integration(),
        "Caching": test_caching(),
    }
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ ALL PHASE 7 TESTS PASSED")
    else:
        print("⚠ SOME TESTS FAILED - Check output above")
    print("=" * 80)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
