#!/usr/bin/env python3
"""
MCP Orchestrator with RAG Integration.

This module orchestrates the decision of when to use RAG vs model-only answers:
- Analyzes query complexity
- Decides whether to retrieve past papers
- Combines retrieved context with prompt
- Routes to LLaMA via MCP

Orchestration Logic:
1. Analyze query (keywords, complexity, domain)
2. Decide: Use RAG? (Yes for exam/homework, No for general knowledge)
3. If RAG: Retrieve top K similar questions from past papers
4. Combine context: Retrieved questions + original query
5. Send to MCP client with appropriate mode
6. Return augmented answer
"""

import logging
from typing import Optional, List, Dict, Tuple
import re

from scripts.rag import RAGSystem, initialize_rag_system
from mcp.client import MCPClient
from scripts.prompts import format_prompt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MCPOrchestrator:
    """
    Orchestrate RAG + MCP for intelligent answer generation.
    
    Attributes:
        rag_system (RAGSystem): RAG system for retrieval
        mcp_client (MCPClient): MCP client for LLM queries
        use_rag_threshold (float): Confidence threshold for using RAG
    """
    
    def __init__(
        self,
        rag_system: Optional[RAGSystem] = None,
        mcp_client: Optional[MCPClient] = None,
        use_rag_threshold: float = 0.5
    ):
        """
        Initialize MCP Orchestrator.
        
        Args:
            rag_system: RAG system instance (will initialize if None)
            mcp_client: MCP client instance (will initialize if None)
            use_rag_threshold: Threshold for deciding to use RAG
        """
        logger.info("Initializing MCP Orchestrator")
        
        # Initialize RAG system if not provided
        if rag_system is None:
            logger.info("Initializing RAG system...")
            rag_system = initialize_rag_system()
            if rag_system is None:
                logger.warning("Failed to initialize RAG system")
        
        self.rag_system = rag_system
        
        # Initialize MCP client if not provided
        if mcp_client is None:
            logger.info("Initializing MCP client...")
            mcp_client = MCPClient()
        
        self.mcp_client = mcp_client
        self.use_rag_threshold = use_rag_threshold
        
        # Keywords that indicate exam/homework questions
        self.exam_keywords = {
            "exam", "question", "quiz", "test", "assignment",
            "homework", "cat", "past paper", "previous", "mark",
            "define", "explain", "describe", "discuss", "analyze",
            "solve", "calculate", "write", "design", "implement"
        }
        
        # Keywords that indicate general knowledge questions
        self.general_keywords = {
            "what", "how", "why", "tell", "explain", "describe",
            "general", "overview", "introduction", "basics"
        }
        
        logger.info("✓ MCP Orchestrator initialized")
    
    def should_use_rag(self, query: str) -> Tuple[bool, float]:
        """
        Decide whether to use RAG for this query.
        
        Decision factors:
        1. Query length (longer = more specific = use RAG)
        2. Presence of exam keywords
        3. Presence of technical terms
        4. Query specificity
        
        Args:
            query: User query
        
        Returns:
            Tuple of (use_rag: bool, confidence: float)
        """
        logger.info(f"Analyzing query for RAG decision: {query[:100]}...")
        
        score = 0.0
        max_score = 0.0
        
        # Factor 1: Query length (0-0.2)
        max_score += 0.2
        query_length = len(query.split())
        if query_length > 10:
            score += 0.2
        elif query_length > 5:
            score += 0.1
        
        # Factor 2: Exam keywords (0-0.3)
        max_score += 0.3
        query_lower = query.lower()
        exam_keyword_count = sum(1 for kw in self.exam_keywords if kw in query_lower)
        if exam_keyword_count > 0:
            score += min(0.3, exam_keyword_count * 0.1)
        
        # Factor 3: Technical terms (0-0.3)
        max_score += 0.3
        # Look for technical patterns (CamelCase, code-like, acronyms)
        if re.search(r'[A-Z][a-z]+[A-Z]', query):  # CamelCase
            score += 0.15
        if re.search(r'\b[A-Z]{2,}\b', query):  # Acronyms
            score += 0.15
        
        # Factor 4: Specificity (0-0.2)
        max_score += 0.2
        # Questions with specific context are more likely to benefit from RAG
        if any(word in query_lower for word in ["unit", "course", "year", "paper"]):
            score += 0.2
        
        # Normalize confidence
        confidence = score / max_score if max_score > 0 else 0.0
        use_rag = confidence >= self.use_rag_threshold
        
        logger.info(f"  RAG score: {confidence:.2f}, Use RAG: {use_rag}")
        
        return use_rag, confidence
    
    def format_context(
        self,
        retrieved_questions: List[Dict],
        max_context_length: int = 2000
    ) -> str:
        """
        Format retrieved questions into context string.
        
        Args:
            retrieved_questions: List of retrieved question dicts
            max_context_length: Maximum context length
        
        Returns:
            Formatted context string
        """
        if not retrieved_questions:
            return ""
        
        logger.info(f"Formatting context from {len(retrieved_questions)} questions")
        
        context_parts = []
        context_parts.append("RELEVANT PAST PAPER QUESTIONS:")
        context_parts.append("-" * 50)
        
        total_length = 0
        
        for i, q in enumerate(retrieved_questions, 1):
            question_text = q.get("question", "")
            unit = q.get("unit", "Unknown")
            year = q.get("year", "Unknown")
            similarity = q.get("similarity_score", 0)
            
            # Format question entry
            entry = f"\n[Q{i}] Unit: {unit}, Year: {year} (Relevance: {similarity:.2%})\n{question_text[:500]}"
            
            # Check if adding this would exceed limit
            if total_length + len(entry) > max_context_length:
                context_parts.append(f"\n... and {len(retrieved_questions) - i + 1} more questions")
                break
            
            context_parts.append(entry)
            total_length += len(entry)
        
        context = "\n".join(context_parts)
        logger.info(f"  Formatted context: {len(context)} characters")
        
        return context
    
    def answer_question(
        self,
        query: str,
        mode: str = "exam",
        use_rag: Optional[bool] = None,
        top_k: int = 3
    ) -> Optional[str]:
        """
        Answer a question using RAG + MCP orchestration.
        
        This is the main orchestration function that:
        1. Decides whether to use RAG
        2. Retrieves relevant past papers if needed
        3. Formats context
        4. Sends to MCP with context
        5. Returns answer
        
        Args:
            query: User query
            mode: Answer mode (exam, local, global, mixed)
            use_rag: Override RAG decision (None = auto-decide)
            top_k: Number of past papers to retrieve
        
        Returns:
            Generated answer or None
        """
        logger.info(f"Answering question in '{mode}' mode with RAG orchestration")
        
        # Decide whether to use RAG
        if use_rag is None:
            use_rag, confidence = self.should_use_rag(query)
            logger.info(f"Auto-decided to use RAG: {use_rag} (confidence: {confidence:.2f})")
        else:
            logger.info(f"Using provided RAG decision: {use_rag}")
        
        # Retrieve context if using RAG
        context = ""
        if use_rag and self.rag_system:
            logger.info(f"Retrieving top {top_k} similar past papers...")
            retrieved = self.rag_system.retrieve_notes(query, top_k=top_k)
            
            if retrieved:
                context = self.format_context(retrieved)
                logger.info(f"✓ Retrieved {len(retrieved)} relevant questions")
            else:
                logger.warning("No relevant past papers found")
        
        # Send to MCP with context
        logger.info("Sending to MCP client...")
        
        if context:
            # Combine context with query
            combined_query = f"{context}\n\nQUESTION:\n{query}"
        else:
            combined_query = query
        
        # Get answer from MCP
        answer = self.mcp_client.answer_question_with_context(
            combined_query,
            context=context if context else None,
            mode=mode
        )
        
        if answer:
            logger.info(f"✓ Generated answer ({len(answer)} chars)")
        else:
            logger.warning("Failed to generate answer")
        
        return answer
    
    def batch_answer_questions(
        self,
        queries: List[str],
        mode: str = "exam",
        use_rag: bool = True
    ) -> Dict[str, Optional[str]]:
        """
        Answer multiple questions with RAG orchestration.
        
        Args:
            queries: List of queries
            mode: Answer mode
            use_rag: Whether to use RAG for all
        
        Returns:
            Dictionary mapping queries to answers
        """
        logger.info(f"Answering {len(queries)} questions with RAG orchestration")
        
        results = {}
        for i, query in enumerate(queries, 1):
            logger.info(f"Processing query {i}/{len(queries)}")
            answer = self.answer_question(query, mode=mode, use_rag=use_rag)
            results[query] = answer
        
        return results
    
    def get_orchestration_stats(self) -> Dict:
        """
        Get statistics about orchestration system.
        
        Returns:
            Dictionary with stats
        """
        stats = {
            "rag_enabled": self.rag_system is not None,
            "mcp_connected": self.mcp_client.check_connection(),
            "use_rag_threshold": self.use_rag_threshold,
        }
        
        if self.rag_system:
            stats["rag_stats"] = self.rag_system.get_index_stats()
        
        return stats


if __name__ == "__main__":
    # Test orchestrator
    print("=" * 70)
    print("Testing MCP Orchestrator")
    print("=" * 70)
    
    # Initialize
    print("\n1. Initializing orchestrator...")
    orchestrator = MCPOrchestrator()
    
    # Test RAG decision
    print("\n2. Testing RAG decision logic...")
    test_queries = [
        "What is a database?",
        "Define object-oriented programming and explain its principles",
        "Solve this network design problem from BBIT106",
        "What is the capital of Kenya?"
    ]
    
    for query in test_queries:
        use_rag, confidence = orchestrator.should_use_rag(query)
        print(f"  Query: {query[:60]}...")
        print(f"    Use RAG: {use_rag}, Confidence: {confidence:.2f}")
    
    # Get stats
    print("\n3. Orchestration stats:")
    stats = orchestrator.get_orchestration_stats()
    print(f"  RAG enabled: {stats['rag_enabled']}")
    print(f"  MCP connected: {stats['mcp_connected']}")
    
    print("\n✓ Orchestrator test complete")
