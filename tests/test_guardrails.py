import os
import sys
import asyncio

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'Health_Chatbot-main')))

from backend.config import Config
from backend.utils.response_generator import ResponseGenerator

async def test():
    print("Loading config...")
    config = Config()
    
    print("Initializing ResponseGenerator...")
    generator = ResponseGenerator(config.GOOGLE_API_KEY)
    
    test_query = "Who won the World Cup in 2022?"
    print(f"Testing guardrails with query: '{test_query}'")
    
    response = await generator.generate_response(
        original_query=test_query,
        sub_queries=[],
        research_results={},
        rag_context=""
    )
    print("\nResponse:")
    print(response)

if __name__ == "__main__":
    asyncio.run(test())
