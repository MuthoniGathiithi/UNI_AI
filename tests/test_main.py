#!/usr/bin/env python3
"""
Unit Tests for I-TUTOR Main Application.

This module contains pytest tests for:
- get_unit(): Retrieve questions by unit
- get_answer(): Generate answers
- generate_cat_quiz(): Create random quizzes

Run tests with:
    pytest tests/test_main.py -v
    pytest tests/test_main.py --cov=app --cov-report=html
"""

import pytest
import sys
import os
from typing import List, Dict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import ITutorApp, get_app
from scripts.load_data import load_questions


class TestITutorApp:
    """Test suite for ITutorApp class."""
    
    @pytest.fixture
    def app(self):
        """
        Fixture: Create ITutorApp instance for testing.
        
        This fixture is automatically used by test methods that
        include 'app' as a parameter.
        """
        return ITutorApp(default_mode="exam")
    
    @pytest.fixture
    def question_loader(self):
        """Fixture: Load questions for testing."""
        return load_questions()
    
    # ==================== Tests for get_unit() ====================
    
    def test_get_unit_returns_list(self, app):
        """Test that get_unit() returns a list."""
        result = app.get_unit("BBIT106")
        assert isinstance(result, list), "get_unit() should return a list"
    
    def test_get_unit_with_valid_unit(self, app):
        """Test get_unit() with a valid unit code."""
        result = app.get_unit("BBIT106")
        
        # Should return questions
        assert len(result) > 0, "BBIT106 should have questions"
        
        # Each question should be a dict
        for question in result:
            assert isinstance(question, dict), "Each question should be a dict"
            assert "question" in question, "Question should have 'question' field"
    
    def test_get_unit_with_invalid_unit(self, app):
        """Test get_unit() with an invalid unit code."""
        result = app.get_unit("INVALID_UNIT_XYZ")
        
        # Should return empty list
        assert isinstance(result, list), "Should return a list"
        assert len(result) == 0, "Invalid unit should return empty list"
    
    def test_get_unit_case_insensitive(self, app):
        """Test that get_unit() is case-insensitive."""
        result_upper = app.get_unit("BBIT106")
        result_lower = app.get_unit("bbit106")
        
        # Should return same number of questions
        assert len(result_upper) == len(result_lower), \
            "Unit codes should be case-insensitive"
    
    def test_get_unit_returns_dict_with_required_fields(self, app):
        """Test that returned questions have required fields."""
        result = app.get_unit("BBIT106")
        
        if result:
            question = result[0]
            required_fields = ["question", "unit", "year"]
            
            for field in required_fields:
                assert field in question, \
                    f"Question should have '{field}' field"
    
    # ==================== Tests for get_answer() ====================
    
    def test_get_answer_returns_string_or_none(self, app):
        """Test that get_answer() returns string or None."""
        question = "What is Python?"
        result = app.get_answer(question, mode="exam")
        
        assert result is None or isinstance(result, str), \
            "get_answer() should return string or None"
    
    def test_get_answer_with_valid_mode(self, app):
        """Test get_answer() with valid modes."""
        question = "What is object-oriented programming?"
        modes = ["exam", "local", "global", "mixed"]
        
        for mode in modes:
            result = app.get_answer(question, mode=mode)
            # Result can be None if Ollama is not running
            assert result is None or isinstance(result, str), \
                f"get_answer() with mode '{mode}' should return string or None"
    
    def test_get_answer_uses_default_mode(self, app):
        """Test that get_answer() uses default mode when not specified."""
        question = "What is a database?"
        result = app.get_answer(question)
        
        # Should work with default mode
        assert result is None or isinstance(result, str), \
            "Should work with default mode"
    
    def test_get_answer_with_context(self, app):
        """Test get_answer() with optional context."""
        question = "Explain this concept"
        context = "This is context from a past paper"
        
        result = app.get_answer(question, mode="exam", context=context)
        
        assert result is None or isinstance(result, str), \
            "get_answer() with context should return string or None"
    
    def test_get_answer_with_empty_question(self, app):
        """Test get_answer() with empty question."""
        result = app.get_answer("", mode="exam")
        
        # Should handle gracefully
        assert result is None or isinstance(result, str)
    
    # ==================== Tests for generate_cat_quiz() ====================
    
    def test_generate_cat_quiz_returns_dict_or_none(self, app):
        """Test that generate_cat_quiz() returns dict or None."""
        result = app.generate_cat_quiz("BBIT106", num_questions=3)
        
        assert result is None or isinstance(result, dict), \
            "generate_cat_quiz() should return dict or None"
    
    def test_generate_cat_quiz_with_valid_unit(self, app):
        """Test generate_cat_quiz() with a valid unit."""
        result = app.generate_cat_quiz("BBIT106", num_questions=3)
        
        if result:
            assert "unit" in result, "Quiz should have 'unit' field"
            assert "questions" in result, "Quiz should have 'questions' field"
            assert "num_questions" in result, "Quiz should have 'num_questions' field"
            assert len(result["questions"]) > 0, "Quiz should have questions"
    
    def test_generate_cat_quiz_with_invalid_unit(self, app):
        """Test generate_cat_quiz() with an invalid unit."""
        result = app.generate_cat_quiz("INVALID_UNIT_XYZ", num_questions=3)
        
        # Should return None
        assert result is None, "Invalid unit should return None"
    
    def test_generate_cat_quiz_respects_num_questions(self, app):
        """Test that generate_cat_quiz() respects num_questions parameter."""
        result = app.generate_cat_quiz("BBIT106", num_questions=2)
        
        if result:
            assert result["num_questions"] == 2, \
                "Quiz should have requested number of questions"
            assert len(result["questions"]) == 2, \
                "Quiz questions list should match num_questions"
    
    def test_generate_cat_quiz_handles_insufficient_questions(self, app):
        """Test generate_cat_quiz() when unit has fewer questions than requested."""
        # Request more questions than available
        result = app.generate_cat_quiz("BBIT106", num_questions=1000)
        
        if result:
            # Should return available questions
            assert result["num_questions"] <= 1000, \
                "Should not exceed available questions"
    
    def test_generate_cat_quiz_randomness(self, app):
        """Test that generate_cat_quiz() returns different questions each time."""
        quiz1 = app.generate_cat_quiz("BBIT106", num_questions=3)
        quiz2 = app.generate_cat_quiz("BBIT106", num_questions=3)
        
        if quiz1 and quiz2:
            # Get question texts
            q1_texts = [q.get("question") for q in quiz1["questions"]]
            q2_texts = [q.get("question") for q in quiz2["questions"]]
            
            # At least one question should be different (very likely)
            # Note: This test might occasionally fail due to randomness
            # but probability is very low
            assert q1_texts != q2_texts or len(q1_texts) == 0, \
                "Quizzes should likely be different (randomness test)"
    
    # ==================== Tests for utility methods ====================
    
    def test_get_available_units(self, app):
        """Test get_available_units() method."""
        units = app.get_available_units()
        
        assert isinstance(units, list), "Should return a list"
        assert len(units) > 0, "Should have at least one unit"
        assert all(isinstance(u, str) for u in units), \
            "All units should be strings"
    
    def test_get_available_years(self, app):
        """Test get_available_years() method."""
        years = app.get_available_years()
        
        assert isinstance(years, list), "Should return a list"
        assert len(years) > 0, "Should have at least one year"
        assert all(isinstance(y, str) for y in years), \
            "All years should be strings"
    
    def test_get_statistics(self, app):
        """Test get_statistics() method."""
        stats = app.get_statistics()
        
        assert isinstance(stats, dict), "Should return a dict"
        assert "total_questions" in stats, "Should have total_questions"
        assert "unique_units" in stats, "Should have unique_units"
        assert "unique_years" in stats, "Should have unique_years"
        assert stats["total_questions"] > 0, "Should have questions"
    
    def test_check_connection(self, app):
        """Test check_connection() method."""
        result = app.check_connection()
        
        assert isinstance(result, bool), "Should return a boolean"
    
    # ==================== Tests for global app instance ====================
    
    def test_get_app_returns_instance(self):
        """Test that get_app() returns an ITutorApp instance."""
        app = get_app()
        
        assert isinstance(app, ITutorApp), "Should return ITutorApp instance"
    
    def test_get_app_singleton_pattern(self):
        """Test that get_app() follows singleton pattern."""
        app1 = get_app()
        app2 = get_app()
        
        assert app1 is app2, "get_app() should return same instance"


class TestIntegration:
    """Integration tests for complete workflows."""
    
    def test_workflow_get_unit_and_answer(self):
        """Test complete workflow: get unit -> get answer."""
        app = ITutorApp()
        
        # Get questions for a unit
        questions = app.get_unit("BBIT106")
        assert len(questions) > 0, "Should find questions"
        
        # Get answer for first question
        question_text = questions[0].get("question", "")
        if question_text:
            result = app.get_answer(question_text, mode="exam")
            # Result can be None if Ollama not running
            assert result is None or isinstance(result, str)
    
    def test_workflow_generate_quiz(self):
        """Test complete workflow: generate quiz."""
        app = ITutorApp()
        
        # Generate quiz
        quiz = app.generate_cat_quiz("BBIT106", num_questions=2)
        
        if quiz:
            assert quiz["unit"] == "BBIT106"
            assert len(quiz["questions"]) == 2
            
            # Verify questions are valid
            for q in quiz["questions"]:
                assert "question" in q
                assert "unit" in q


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_question_string(self):
        """Test handling of empty question string."""
        app = ITutorApp()
        result = app.get_answer("", mode="exam")
        
        # Should handle gracefully
        assert result is None or isinstance(result, str)
    
    def test_very_long_question(self):
        """Test handling of very long question."""
        app = ITutorApp()
        long_question = "What is " + "very " * 100 + "long?"
        
        result = app.get_answer(long_question, mode="exam")
        
        # Should handle gracefully
        assert result is None or isinstance(result, str)
    
    def test_special_characters_in_question(self):
        """Test handling of special characters."""
        app = ITutorApp()
        question = "What is @#$%^&*()? <html>test</html>"
        
        result = app.get_answer(question, mode="exam")
        
        # Should handle gracefully
        assert result is None or isinstance(result, str)
    
    def test_unicode_in_question(self):
        """Test handling of unicode characters."""
        app = ITutorApp()
        question = "What is 你好世界? Привет мир!"
        
        result = app.get_answer(question, mode="exam")
        
        # Should handle gracefully
        assert result is None or isinstance(result, str)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
