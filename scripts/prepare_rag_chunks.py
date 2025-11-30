#!/usr/bin/env python3
"""
Prepare questions for RAG (Retrieval-Augmented Generation) retrieval.

This script:
- Splits questions into chunks suitable for RAG
- Creates embeddings-ready format
- Generates metadata for each chunk
- Saves chunks to JSON for vector store ingestion
"""

import json
import os
import re
from typing import List, Dict
from dataclasses import dataclass, asdict

# Import the loader
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from load_data import load_questions

# Get project root directory
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
OUTPUT_DIR = os.path.join(project_root, "data")
CHUNKS_FILE = os.path.join(OUTPUT_DIR, "question_chunks.json")


@dataclass
class Chunk:
    """Represents a chunk of text for RAG."""
    chunk_id: str
    question_id: str
    text: str
    metadata: Dict
    chunk_index: int
    total_chunks: int


def split_text_into_chunks(text: str, max_chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: Text to split
        max_chunk_size: Maximum characters per chunk
        overlap: Number of characters to overlap between chunks
    
    Returns:
        List of text chunks
    """
    if len(text) <= max_chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + max_chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings
            sentence_end = max(
                text.rfind('.', start, end),
                text.rfind('?', start, end),
                text.rfind('!', start, end),
                text.rfind('\n', start, end)
            )
            
            if sentence_end > start:
                end = sentence_end + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start forward with overlap
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks if chunks else [text]


def create_chunks_from_question(question: Dict, max_chunk_size: int = 500) -> List[Chunk]:
    """
    Create chunks from a single question.
    
    Args:
        question: Question dictionary
        max_chunk_size: Maximum characters per chunk
    
    Returns:
        List of Chunk objects
    """
    question_text = question.get("question", "")
    
    # If question is short enough, return single chunk
    if len(question_text) <= max_chunk_size:
        chunk_id = f"q_{question.get('source_file', 'unknown')}_{question.get('question_number', 0)}_0"
        
        return [Chunk(
            chunk_id=chunk_id,
            question_id=f"{question.get('source_file', 'unknown')}_{question.get('question_number', 0)}",
            text=question_text,
            metadata={
                "course": question.get("course"),
                "unit": question.get("unit"),
                "year": question.get("year"),
                "source_file": question.get("source_file"),
                "question_number": question.get("question_number"),
                **question.get("metadata", {})
            },
            chunk_index=0,
            total_chunks=1
        )]
    
    # Split into multiple chunks
    text_chunks = split_text_into_chunks(question_text, max_chunk_size)
    
    chunks = []
    for idx, chunk_text in enumerate(text_chunks):
        chunk_id = f"q_{question.get('source_file', 'unknown')}_{question.get('question_number', 0)}_{idx}"
        
        chunks.append(Chunk(
            chunk_id=chunk_id,
            question_id=f"{question.get('source_file', 'unknown')}_{question.get('question_number', 0)}",
            text=chunk_text,
            metadata={
                "course": question.get("course"),
                "unit": question.get("unit"),
                "year": question.get("year"),
                "source_file": question.get("source_file"),
                "question_number": question.get("question_number"),
                "chunk_index": idx,
                "total_chunks": len(text_chunks),
                **question.get("metadata", {})
            },
            chunk_index=idx,
            total_chunks=len(text_chunks)
        ))
    
    return chunks


def prepare_all_chunks(questions: List[Dict], max_chunk_size: int = 500) -> List[Dict]:
    """
    Prepare chunks from all questions.
    
    Args:
        questions: List of question dictionaries
        max_chunk_size: Maximum characters per chunk
    
    Returns:
        List of chunk dictionaries ready for JSON serialization
    """
    all_chunks = []
    
    for question in questions:
        chunks = create_chunks_from_question(question, max_chunk_size)
        for chunk in chunks:
            all_chunks.append(asdict(chunk))
    
    return all_chunks


def save_chunks_to_json(chunks: List[Dict], output_file: str = CHUNKS_FILE) -> None:
    """Save chunks to JSON file."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Saved {len(chunks)} chunks to {output_file}")


def main():
    """Main function to prepare RAG chunks."""
    print("=" * 70)
    print("PREPARING QUESTIONS FOR RAG RETRIEVAL")
    print("=" * 70)
    
    # Load questions
    loader = load_questions()
    questions = loader.get_all_questions()
    
    print(f"\n📚 Processing {len(questions)} questions...")
    
    # Create chunks
    print("  Creating chunks (max 500 chars per chunk)...")
    chunks = prepare_all_chunks(questions, max_chunk_size=500)
    
    # Statistics
    print(f"\n📊 CHUNK STATISTICS:")
    print(f"  Total chunks created: {len(chunks)}")
    print(f"  Average chunks per question: {len(chunks) / len(questions):.2f}")
    
    # Count multi-chunk questions
    multi_chunk_count = sum(1 for c in chunks if c['total_chunks'] > 1)
    print(f"  Questions split into multiple chunks: {multi_chunk_count}")
    
    # Save to JSON
    print(f"\n💾 Saving chunks...")
    save_chunks_to_json(chunks)
    
    # Show sample chunks
    print(f"\n📄 SAMPLE CHUNKS:")
    for i, chunk in enumerate(chunks[:3], 1):
        print(f"\n  Chunk {i}:")
        print(f"    ID: {chunk['chunk_id']}")
        print(f"    Unit: {chunk['metadata'].get('unit', 'Unknown')}")
        print(f"    Year: {chunk['metadata'].get('year', 'Unknown')}")
        print(f"    Text (first 150 chars): {chunk['text'][:150]}...")
        print(f"    Chunk {chunk['chunk_index']+1} of {chunk['total_chunks']}")
    
    print("\n" + "=" * 70)
    print("✓ RAG chunks prepared successfully!")
    print(f"  File: {CHUNKS_FILE}")
    print("=" * 70)


if __name__ == "__main__":
    main()

