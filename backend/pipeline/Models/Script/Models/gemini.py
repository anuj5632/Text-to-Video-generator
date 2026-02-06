import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
import google.generativeai as genai
from dotenv import dotenv_values
# Import the module to access dynamically overridden paths
import Models.config as models_config
from Models.Script.utils import SYSTEM_PROMPT
from config import SCRIPT_MODEL_TYPE

# Look for .env in the backend folder (one level up from pipeline)
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../.env'))
env_vars = dotenv_values(env_path)
GEMINI_API_KEY = env_vars.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(
    model_name=SCRIPT_MODEL_TYPE,
    system_instruction=SYSTEM_PROMPT,
    generation_config={
        "temperature": 1.2,   
        "top_p": 0.9,         
        "top_k": 50          
    }
)

class ScriptGenerator:
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("❌ GEMINI_API_KEY not found. Check your .env file.")

    def generate_script(self, topic):
        """Generates a script based on the given topic."""
        response = model.generate_content(topic)
        
        script_text = response.text if hasattr(response, "text") else response.result
        # Access path dynamically to get runtime-overridden value
        save_path = models_config.SAVE_SCRIPT_TO
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(script_text)
        
        return script_text

if __name__ == "__main__":
    generator = ScriptGenerator()
    topic = input("Enter a topic: ")
    script = generator.generate_script(topic)
    print("📝 Generated Script Successfully to:", SAVE_SCRIPT_TO)
