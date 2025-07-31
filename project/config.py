import os

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "20040930jqc"

BASE_URL = "https://api2.aigcbest.top/v1"
OPENAI_API_KEY = "sk-zjyyqhELqpJQKMDy7c02C9Fy1iYHyc4CESe8mN6D8khuMYhO"

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PROMPT_TEMPLATE_PATH = os.path.join(
    PROJECT_ROOT, "user_story_generator", "prompts", "story_generate_prompt.txt"
)
