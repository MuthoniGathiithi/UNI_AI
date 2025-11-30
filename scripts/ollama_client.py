#!/usr/bin/env python3
"""
Ollama Client for Local LLaMA Model Integration.

This module handles communication with a local Ollama server running LLaMA.
It provides a simple interface to send prompts and retrieve responses.

Configuration:
- Ollama server: http://localhost:11434
- Model: llama2 (or configured in environment)
"""

import requests
import json
import os
from typing import Optional, Dict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OllamaClient:
    """
    Client for communicating with Ollama local LLM server.
    
    Attributes:
        base_url (str): Ollama server URL
        model (str): LLM model name (default: llama2)
        timeout (int): Request timeout in seconds
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama2",
        timeout: int = 300
    ):
        """
        Initialize Ollama client.
        
        Args:
            base_url: Ollama server URL
            model: Model name to use
            timeout: Request timeout in seconds (default 300 for long responses)
        """
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.endpoint = f"{base_url}/api/generate"
        
        logger.info(f"Initialized OllamaClient: {base_url}, model: {model}")
    
    def query_model(
        self,
        prompt: str,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        num_predict: int = 512
    ) -> Optional[str]:
        """
        Send a prompt to the Ollama model and get a response.
        
        Args:
            prompt: The prompt to send to the model
            temperature: Sampling temperature (0.0-1.0). Higher = more creative
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
            num_predict: Maximum tokens to generate
        
        Returns:
            Model response as string, or None if request fails
        
        Raises:
            requests.RequestException: If connection to Ollama fails
        """
        try:
            # Prepare request payload
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "num_predict": num_predict
            }
            
            logger.info(f"Sending prompt to {self.model} (temp={temperature})")
            
            # Send request to Ollama
            response = requests.post(
                self.endpoint,
                json=payload,
                timeout=self.timeout
            )
            
            # Check if request was successful
            if response.status_code != 200:
                logger.error(f"Ollama error: {response.status_code} - {response.text}")
                return None
            
            # Parse response
            result = response.json()
            answer = result.get("response", "").strip()
            
            logger.info(f"Received response ({len(answer)} chars)")
            return answer
        
        except requests.exceptions.ConnectionError:
            logger.error("Failed to connect to Ollama server. Is it running?")
            return None
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout after {self.timeout} seconds")
            return None
        except json.JSONDecodeError:
            logger.error("Failed to parse Ollama response")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return None
    
    def check_connection(self) -> bool:
        """
        Check if Ollama server is running and accessible.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            if response.status_code == 200:
                logger.info("✓ Connected to Ollama server")
                return True
            else:
                logger.warning(f"Ollama server returned status {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Cannot connect to Ollama: {str(e)}")
            return False
    
    def list_models(self) -> Optional[list]:
        """
        List available models on Ollama server.
        
        Returns:
            List of model names, or None if request fails
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name") for m in models]
                logger.info(f"Available models: {model_names}")
                return model_names
            return None
        except Exception as e:
            logger.error(f"Failed to list models: {str(e)}")
            return None


# Convenience function for quick access
def query_model(
    prompt: str,
    model: str = "llama2",
    temperature: float = 0.7
) -> Optional[str]:
    """
    Convenience function to query Ollama model directly.
    
    Args:
        prompt: The prompt to send
        model: Model name (default: llama2)
        temperature: Sampling temperature
    
    Returns:
        Model response or None
    """
    client = OllamaClient(model=model)
    return client.query_model(prompt, temperature=temperature)


if __name__ == "__main__":
    # Test the Ollama client
    print("=" * 60)
    print("Testing Ollama Client")
    print("=" * 60)
    
    client = OllamaClient()
    
    # Check connection
    print("\n1. Checking connection...")
    if not client.check_connection():
        print("❌ Cannot connect to Ollama. Make sure it's running:")
        print("   ollama serve")
        exit(1)
    
    # List available models
    print("\n2. Available models:")
    models = client.list_models()
    if models:
        for model in models:
            print(f"   - {model}")
    
    # Test query
    print("\n3. Testing query...")
    test_prompt = "What is the capital of Kenya? Answer in one sentence."
    response = client.query_model(test_prompt, temperature=0.5)
    
    if response:
        print(f"✓ Response received:")
        print(f"   {response}")
    else:
        print("❌ Failed to get response")
