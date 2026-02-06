import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from openai import OpenAI
from dotenv import dotenv_values
# Import the module to access dynamically overridden paths
import Models.config as models_config
from Models.Script.utils import SYSTEM_PROMPT
from config import SCRIPT_MODEL_TYPE

class ScriptGenerator:
    def __init__(self):
        env_vars = dotenv_values(".env")
        self.api_key = env_vars.get("DDC_API_KEY")
        self.base_url = "https://beta.sree.shop/v1"
        
        if not self.api_key:
            raise ValueError("❌ DDC_API_KEY not found. Check your .env file.")

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def generate_script(self, topic):
        """Generates a script based on the given topic."""
        response = self.client.chat.completions.create(
            model=SCRIPT_MODEL_TYPE,
            messages=[
                {"role": "developer", "content": SYSTEM_PROMPT},
                {"role": "user", "content": topic}
            ],
            temperature=1.2,
            top_p=0.9,            
            stream=False
        )
        
        script_text = response.choices[0].message.content
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
