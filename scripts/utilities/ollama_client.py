import requests
import yaml
import json
import os

# Load config - look for config.yaml in project root
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
config_path = os.path.join(project_root, "config.yaml")

with open(config_path, "r") as f:
    config = yaml.safe_load(f)

OLLAMA_URL = config["ollama_url"]
MODEL_NAME = config["model_name"]

def query_model(prompt, temperature=0.7, max_tokens=256):
    """
    Send a prompt to the local Ollama model and return the response.
    Ollama can return streaming (multiple JSON objects, one per line) or non-streaming responses.
    """
    url = f"{OLLAMA_URL}/api/generate"
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,  # Request non-streaming response
        "temperature": temperature,
        "num_predict": max_tokens
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        # Check if response contains multiple lines (streaming format)
        response_text = response.text
        lines = response_text.strip().split('\n')
        
        # If multiple lines, parse as streaming JSON
        if len(lines) > 1:
            full_response = ""
            for line in lines:
                line = line.strip()
                if line:
                    try:
                        chunk = json.loads(line)
                        if "response" in chunk:
                            full_response += chunk["response"]
                        if chunk.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
            if full_response:
                return full_response
        else:
            # Single JSON object (non-streaming)
            try:
                data = json.loads(response_text)
                if "response" in data:
                    return data["response"]
            except json.JSONDecodeError:
                pass
        
        return "No response returned."
    except Exception as e:
        return f"Error: {e}"

# --- Run a test if script is executed directly ---
if __name__ == "__main__":
    print("Testing local Ollama model...")
    test_prompt = "Hello, Ollama! Introduce yourself."
    result = query_model(test_prompt)
    print(result)
