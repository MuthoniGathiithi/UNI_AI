#!/usr/bin/env python3
"""
Embedding Generation for RAG System.

This module handles:
- Loading pre-trained sentence transformer models
- Generating embeddings for questions
- Caching embeddings for performance
- Managing embedding metadata

Uses sentence-transformers for semantic similarity.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
import logging
from pathlib import Path
import pickle
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Generate and manage embeddings for questions.
    
    Attributes:
        model_name (str): Sentence transformer model name
        model: Loaded sentence transformer model
        embedding_dim (int): Dimension of embeddings
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding generator.
        
        Args:
            model_name: Sentence transformer model name
                       (all-MiniLM-L6-v2 is fast and good for semantic search)
        """
        logger.info(f"Loading embedding model: {model_name}")
        
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self.model_name = model_name
            
            # Get embedding dimension
            test_embedding = self.model.encode("test")
            self.embedding_dim = len(test_embedding)
            
            logger.info(f"✓ Model loaded. Embedding dimension: {self.embedding_dim}")
        
        except ImportError:
            logger.error("sentence-transformers not installed. Install with:")
            logger.error("  pip install sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding as numpy array
        """
        if not text or not isinstance(text, str):
            logger.warning("Empty or invalid text provided")
            return np.zeros(self.embedding_dim)
        
        # Truncate very long texts (max 512 tokens for most models)
        text = text[:2000]  # Approximate token limit
        
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding
    
    def embed_texts(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for multiple texts efficiently.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
        
        Returns:
            Array of embeddings (N x embedding_dim)
        """
        logger.info(f"Embedding {len(texts)} texts with batch size {batch_size}")
        
        # Filter out empty texts
        valid_texts = [t if t and isinstance(t, str) else "" for t in texts]
        
        # Truncate long texts
        valid_texts = [t[:2000] for t in valid_texts]
        
        # Encode in batches
        embeddings = self.model.encode(
            valid_texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=True
        )
        
        logger.info(f"✓ Generated {len(embeddings)} embeddings")
        return embeddings
    
    def embed_questions(
        self,
        questions: List[Dict],
        batch_size: int = 32
    ) -> Tuple[np.ndarray, List[Dict]]:
        """
        Generate embeddings for a list of question dictionaries.
        
        Args:
            questions: List of question dicts with 'question' field
            batch_size: Batch size for processing
        
        Returns:
            Tuple of (embeddings array, metadata list)
        """
        logger.info(f"Embedding {len(questions)} questions")
        
        # Extract question texts
        question_texts = [q.get("question", "") for q in questions]
        
        # Generate embeddings
        embeddings = self.embed_texts(question_texts, batch_size=batch_size)
        
        # Create metadata list (preserve original question info)
        metadata = [
            {
                "question": q.get("question", ""),
                "unit": q.get("unit", "Unknown"),
                "year": q.get("year", "Unknown"),
                "course": q.get("course", "Unknown"),
                "source_file": q.get("source_file", "Unknown"),
                "question_number": q.get("question_number", 0),
                "metadata": q.get("metadata", {})
            }
            for q in questions
        ]
        
        logger.info(f"✓ Embedded {len(embeddings)} questions with metadata")
        return embeddings, metadata
    
    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
        
        Returns:
            Similarity score (0-1)
        """
        # Normalize embeddings
        emb1 = embedding1 / (np.linalg.norm(embedding1) + 1e-8)
        emb2 = embedding2 / (np.linalg.norm(embedding2) + 1e-8)
        
        # Cosine similarity
        similarity = np.dot(emb1, emb2)
        return float(similarity)


def cache_embeddings(
    embeddings: np.ndarray,
    metadata: List[Dict],
    cache_file: str
) -> bool:
    """
    Cache embeddings and metadata to disk.
    
    Args:
        embeddings: Embedding array
        metadata: Metadata list
        cache_file: Path to cache file
    
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Caching embeddings to {cache_file}")
        
        cache_data = {
            "embeddings": embeddings,
            "metadata": metadata
        }
        
        with open(cache_file, 'wb') as f:
            pickle.dump(cache_data, f)
        
        logger.info(f"✓ Cached {len(embeddings)} embeddings")
        return True
    
    except Exception as e:
        logger.error(f"Failed to cache embeddings: {e}")
        return False


def load_cached_embeddings(cache_file: str) -> Optional[Tuple[np.ndarray, List[Dict]]]:
    """
    Load cached embeddings and metadata from disk.
    
    Args:
        cache_file: Path to cache file
    
    Returns:
        Tuple of (embeddings, metadata), or None if load fails
    """
    try:
        if not os.path.exists(cache_file):
            logger.warning(f"Cache file not found: {cache_file}")
            return None
        
        logger.info(f"Loading cached embeddings from {cache_file}")
        
        with open(cache_file, 'rb') as f:
            cache_data = pickle.load(f)
        
        embeddings = cache_data.get("embeddings")
        metadata = cache_data.get("metadata")
        
        logger.info(f"✓ Loaded {len(embeddings)} cached embeddings")
        return embeddings, metadata
    
    except Exception as e:
        logger.error(f"Failed to load cached embeddings: {e}")
        return None


if __name__ == "__main__":
    # Test embedding generation
    print("=" * 70)
    print("Testing Embedding Generation")
    print("=" * 70)
    
    # Initialize generator
    generator = EmbeddingGenerator()
    
    # Test single embedding
    print("\n1. Testing single text embedding...")
    text = "What is object-oriented programming?"
    embedding = generator.embed_text(text)
    print(f"✓ Generated embedding with shape: {embedding.shape}")
    
    # Test multiple embeddings
    print("\n2. Testing multiple text embeddings...")
    texts = [
        "What is a database?",
        "What is a network?",
        "What is OOP?",
    ]
    embeddings = generator.embed_texts(texts)
    print(f"✓ Generated {len(embeddings)} embeddings")
    
    # Test similarity
    print("\n3. Testing similarity calculation...")
    emb1 = generator.embed_text("What is OOP?")
    emb2 = generator.embed_text("What is object-oriented programming?")
    emb3 = generator.embed_text("What is a database?")
    
    sim_same = generator.similarity(emb1, emb2)
    sim_diff = generator.similarity(emb1, emb3)
    
    print(f"Similarity (OOP vs OOP): {sim_same:.4f}")
    print(f"Similarity (OOP vs Database): {sim_diff:.4f}")
    print(f"✓ Similarity calculation working")
