#!/usr/bin/env python3
"""
RAG (Retrieval-Augmented Generation) System using FAISS.

This module implements:
- FAISS index creation and management
- Semantic search over past paper questions
- Caching for common topics
- Index persistence and reloading
- Integration with MCP for orchestration

RAG Pipeline:
1. User query → Embed query
2. Search FAISS index → Get top N similar questions
3. Combine retrieved questions into prompt
4. Send to LLaMA via MCP
5. Return augmented answer
"""

import numpy as np
import faiss
import logging
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import json
import os
from datetime import datetime

from scripts.embeddings import EmbeddingGenerator, cache_embeddings, load_cached_embeddings
from scripts.load_data import load_questions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGSystem:
    """
    RAG System using FAISS for semantic search over past papers.
    
    Attributes:
        embedding_generator (EmbeddingGenerator): Generates embeddings
        faiss_index: FAISS index for similarity search
        metadata: Question metadata corresponding to index
        topic_cache: Cache for common topics
        index_path: Path to save/load index
    """
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        index_path: str = "data/rag_index.faiss",
        metadata_path: str = "data/rag_metadata.json"
    ):
        """
        Initialize RAG system.
        
        Args:
            model_name: Sentence transformer model name
            index_path: Path to save/load FAISS index
            metadata_path: Path to save/load metadata
        """
        logger.info("Initializing RAG System")
        
        self.embedding_generator = EmbeddingGenerator(model_name=model_name)
        self.faiss_index = None
        self.metadata = []
        self.topic_cache = {}  # Cache for common topics
        self.index_path = index_path
        self.metadata_path = metadata_path
        
        logger.info("✓ RAG System initialized")
    
    def build_index(self, questions: List[Dict]) -> bool:
        """
        Build FAISS index from questions.
        
        Args:
            questions: List of question dictionaries
        
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Building FAISS index for {len(questions)} questions")
        
        try:
            # Generate embeddings
            embeddings, metadata = self.embedding_generator.embed_questions(questions)
            
            # Create FAISS index
            embedding_dim = embeddings.shape[1]
            self.faiss_index = faiss.IndexFlatL2(embedding_dim)
            
            # Add embeddings to index
            embeddings_float32 = embeddings.astype(np.float32)
            self.faiss_index.add(embeddings_float32)
            
            self.metadata = metadata
            
            logger.info(f"✓ Built FAISS index with {len(questions)} questions")
            logger.info(f"  Index size: {self.faiss_index.ntotal} vectors")
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to build index: {e}")
            return False
    
    def save_index(self) -> bool:
        """
        Save FAISS index and metadata to disk.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Saving index to {self.index_path}")
            
            # Create directory if needed
            Path(self.index_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Save FAISS index
            faiss.write_index(self.faiss_index, self.index_path)
            
            # Save metadata
            Path(self.metadata_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.metadata_path, 'w') as f:
                json.dump(self.metadata, f, indent=2)
            
            logger.info(f"✓ Saved index and metadata")
            return True
        
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
            return False
    
    def load_index(self) -> bool:
        """
        Load FAISS index and metadata from disk.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(self.index_path):
                logger.warning(f"Index file not found: {self.index_path}")
                return False
            
            logger.info(f"Loading index from {self.index_path}")
            
            # Load FAISS index
            self.faiss_index = faiss.read_index(self.index_path)
            
            # Load metadata
            if os.path.exists(self.metadata_path):
                with open(self.metadata_path, 'r') as f:
                    self.metadata = json.load(f)
            
            logger.info(f"✓ Loaded index with {self.faiss_index.ntotal} vectors")
            return True
        
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            return False
    
    def retrieve_notes(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.3
    ) -> List[Dict]:
        """
        Retrieve top K similar questions from past papers.
        
        This is the main RAG retrieval function that:
        1. Embeds the query
        2. Searches FAISS index
        3. Returns top K results with metadata
        
        Args:
            query: Query string
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score (0-1)
        
        Returns:
            List of retrieved questions with metadata
        """
        if self.faiss_index is None or len(self.metadata) == 0:
            logger.warning("FAISS index not initialized")
            return []
        
        logger.info(f"Retrieving top {top_k} similar questions for: {query[:100]}...")
        
        try:
            # Embed query
            query_embedding = self.embedding_generator.embed_text(query)
            query_embedding = query_embedding.astype(np.float32).reshape(1, -1)
            
            # Search index
            distances, indices = self.faiss_index.search(query_embedding, top_k)
            
            # Convert distances to similarity scores (L2 distance to similarity)
            # For L2 distance: similarity ≈ 1 / (1 + distance)
            similarities = 1.0 / (1.0 + distances[0])
            
            # Build results
            results = []
            for idx, similarity in zip(indices[0], similarities):
                if idx < len(self.metadata) and similarity >= similarity_threshold:
                    result = self.metadata[idx].copy()
                    result["similarity_score"] = float(similarity)
                    result["distance"] = float(distances[0][list(indices[0]).index(idx)])
                    results.append(result)
            
            logger.info(f"✓ Retrieved {len(results)} similar questions")
            
            return results
        
        except Exception as e:
            logger.error(f"Failed to retrieve notes: {e}")
            return []
    
    def retrieve_by_unit(
        self,
        unit: str,
        query: str = None,
        top_k: int = 3
    ) -> List[Dict]:
        """
        Retrieve questions from a specific unit.
        
        Args:
            unit: Unit code (e.g., "BBIT106")
            query: Optional query for semantic filtering
            top_k: Number of results
        
        Returns:
            List of questions from unit
        """
        logger.info(f"Retrieving {top_k} questions from unit: {unit}")
        
        # Filter metadata by unit
        unit_questions = [
            m for m in self.metadata
            if m.get("unit", "").upper() == unit.upper()
        ]
        
        if not unit_questions:
            logger.warning(f"No questions found for unit: {unit}")
            return []
        
        # If query provided, rank by semantic similarity
        if query:
            query_embedding = self.embedding_generator.embed_text(query)
            
            # Calculate similarities
            for q in unit_questions:
                # Re-embed question for similarity
                q_embedding = self.embedding_generator.embed_text(q.get("question", ""))
                similarity = self.embedding_generator.similarity(query_embedding, q_embedding)
                q["similarity_score"] = similarity
            
            # Sort by similarity
            unit_questions.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
        
        return unit_questions[:top_k]
    
    def cache_topic(self, topic: str, questions: List[Dict]) -> None:
        """
        Cache questions for a common topic.
        
        Args:
            topic: Topic name (e.g., "OOP", "Networks", "DBMS")
            questions: List of questions for topic
        """
        logger.info(f"Caching {len(questions)} questions for topic: {topic}")
        self.topic_cache[topic.lower()] = questions
    
    def get_cached_topic(self, topic: str) -> Optional[List[Dict]]:
        """
        Get cached questions for a topic.
        
        Args:
            topic: Topic name
        
        Returns:
            Cached questions or None
        """
        return self.topic_cache.get(topic.lower())
    
    def get_index_stats(self) -> Dict:
        """
        Get statistics about the FAISS index.
        
        Returns:
            Dictionary with index statistics
        """
        if self.faiss_index is None:
            return {"status": "not_initialized"}
        
        # Count questions per unit
        units = {}
        for m in self.metadata:
            unit = m.get("unit", "Unknown")
            units[unit] = units.get(unit, 0) + 1
        
        # Count questions per year
        years = {}
        for m in self.metadata:
            year = str(m.get("year", "Unknown"))
            years[year] = years.get(year, 0) + 1
        
        return {
            "total_questions": self.faiss_index.ntotal,
            "embedding_dimension": self.faiss_index.d,
            "questions_per_unit": units,
            "questions_per_year": years,
            "cached_topics": list(self.topic_cache.keys()),
            "index_path": self.index_path,
            "metadata_path": self.metadata_path
        }
    
    def update_index(self, new_questions: List[Dict]) -> bool:
        """
        Update FAISS index with new questions.
        
        This method:
        1. Generates embeddings for new questions
        2. Adds them to existing index
        3. Updates metadata
        
        Args:
            new_questions: New questions to add
        
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Updating index with {len(new_questions)} new questions")
        
        try:
            # Generate embeddings for new questions
            new_embeddings, new_metadata = self.embedding_generator.embed_questions(new_questions)
            
            # Add to index
            new_embeddings_float32 = new_embeddings.astype(np.float32)
            self.faiss_index.add(new_embeddings_float32)
            
            # Update metadata
            self.metadata.extend(new_metadata)
            
            logger.info(f"✓ Updated index. Total questions: {self.faiss_index.ntotal}")
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to update index: {e}")
            return False


def initialize_rag_system(
    force_rebuild: bool = False
) -> Optional[RAGSystem]:
    """
    Initialize RAG system with questions from database.
    
    This function:
    1. Loads questions from load_data.py
    2. Tries to load cached index
    3. Builds index if needed
    4. Saves index for future use
    
    Args:
        force_rebuild: Force rebuild even if index exists
    
    Returns:
        Initialized RAGSystem or None if failed
    """
    logger.info("Initializing RAG system with past papers")
    
    try:
        # Initialize RAG system
        rag = RAGSystem()
        
        # Try to load existing index
        if not force_rebuild and rag.load_index():
            logger.info("✓ Loaded existing FAISS index")
            return rag
        
        # Load questions
        logger.info("Loading questions from database...")
        loader = load_questions()
        questions = loader.get_all_questions()
        logger.info(f"✓ Loaded {len(questions)} questions")
        
        # Build index
        if not rag.build_index(questions):
            logger.error("Failed to build FAISS index")
            return None
        
        # Save index
        rag.save_index()
        
        logger.info("✓ RAG system initialized successfully")
        return rag
    
    except Exception as e:
        logger.error(f"Failed to initialize RAG system: {e}")
        return None


if __name__ == "__main__":
    # Test RAG system
    print("=" * 70)
    print("Testing RAG System")
    print("=" * 70)
    
    # Initialize
    print("\n1. Initializing RAG system...")
    rag = initialize_rag_system(force_rebuild=False)
    
    if not rag:
        print("❌ Failed to initialize RAG system")
        exit(1)
    
    # Get stats
    print("\n2. Index statistics:")
    stats = rag.get_index_stats()
    print(f"  Total questions: {stats['total_questions']}")
    print(f"  Embedding dimension: {stats['embedding_dimension']}")
    print(f"  Units: {len(stats['questions_per_unit'])}")
    
    # Test retrieval
    print("\n3. Testing retrieval...")
    query = "What is object-oriented programming?"
    results = rag.retrieve_notes(query, top_k=3)
    
    print(f"  Query: {query}")
    print(f"  Retrieved {len(results)} results:")
    for i, result in enumerate(results, 1):
        print(f"    {i}. Unit: {result['unit']}, Year: {result['year']}")
        print(f"       Similarity: {result['similarity_score']:.4f}")
        print(f"       Question: {result['question'][:80]}...")
    
    # Test unit retrieval
    print("\n4. Testing unit-based retrieval...")
    unit_results = rag.retrieve_by_unit("BBIT106", query=query, top_k=2)
    print(f"  Retrieved {len(unit_results)} questions from BBIT106")
    
    print("\n✓ RAG system test complete")
