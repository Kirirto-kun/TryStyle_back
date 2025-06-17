import json
from src.agent.sub_agents.coordinator_agent import coordinate_request


async def process_user_request(message: str, user_id: int) -> str:
    """
    Processes a user's request using the multi-agent system with specialized sub-agents.

    This function routes the user's request to the appropriate sub-agent:
    - SearchAgent for product search requests
    - OutfitAgent for outfit recommendations  
    - GeneralAgent for general conversation

    Args:
        message: The user's message/request.
        user_id: The ID of the authenticated user.

    Returns:
        A JSON string containing the agent's final response.
    """
    try:
        # Use the coordinator to handle the request
        response = await coordinate_request(message, user_id)
        
        # Format and return the response
        return response.model_dump_json(indent=2)

    except Exception as e:
        print(f"An error occurred while processing the request: {e}")
        return json.dumps({"error": f"An error occurred: {str(e)}"}, indent=2)


# Example usage (for testing)
# async def main():
#     print("Processing request...")
#     
#     # Test case 1: Product search
#     response_search = await process_user_request("Can you find me a black t-shirt?", user_id=1)
#     print("\n--- Product Search Response ---")
#     print(response_search)
#
#     # Test case 2: Outfit recommendation (assuming user 1 has items in the DB)
#     response_outfit = await process_user_request("What should I wear today?", user_id=1)
#     print("\n--- Outfit Recommendation Response ---")
#     print(response_outfit)
#
#     # Test case 3: General question
#     response_general = await process_user_request("What is PydanticAI?", user_id=1)
#     print("\n--- General Question Response ---")
#     print(response_general)
#
# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(main())