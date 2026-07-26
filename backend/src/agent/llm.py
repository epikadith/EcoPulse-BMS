import json
import re
import ollama
from src.config.settings import Config

def query_llm(prompt: str, system_prompt: str, config: Config) -> dict:
    """
    Query the local Ollama LLM and return a parsed JSON response.
    
    Args:
        prompt: The user prompt (typically the building status)
        system_prompt: Instructions for the LLM
        config: The system configuration (determines model and temp)
        
    Returns:
        A dictionary parsed from the LLM's JSON output.
    """
    try:
        response = ollama.chat(
            model=config.llm.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            options={
                "temperature": config.llm.temperature
            }
        )
        
        content = response.get("message", {}).get("content", "")
        
        # Gemma 4 E4B often outputs "Thinking Process..." before the actual JSON.
        # We need to extract just the JSON block (from the first '{' to the last '}').
        json_str = content
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            json_str = match.group(0)
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {"error": "Failed to parse JSON", "raw_content": content}
            
    except Exception as e:
        # Catch connection errors if ollama isn't running
        return {"error": f"LLM Query Failed: {str(e)}"}
