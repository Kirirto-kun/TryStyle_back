import json
from sqlalchemy.orm import Session
from src.agent.sub_agents.coordinator_agent import coordinate_request
from src.utils.token_counter import count_message_tokens


async def process_user_request(
    message: str,
    user_id: int,
    db: Session,
    chat_id: int
) -> str:
    """
    Processes a user's request using the enhanced multi-agent system with strict structured outputs.

    This function routes the user's request to the appropriate sub-agent with guaranteed
    structured response validation:
    - SearchAgent for product search requests (returns ProductList)
    - OutfitAgent for outfit recommendations (returns Outfit)  
    - GeneralAgent for general conversation (returns GeneralResponse)
    
    All responses are now validated through Pydantic models with strict field requirements,
    output validators, and enhanced error handling for maximum reliability.
    
    Args:
        message: The user's message/request.
        user_id: The ID of the authenticated user.
        db: Database session for accessing chat history.
        chat_id: ID of the current chat.
        
    Returns:
        A JSON string containing the agent's validated structured response with:
        - result: The actual response data (ProductList/Outfit/GeneralResponse)
        - agent_type: Which agent handled the request ("search"/"outfit"/"general")
        - processing_time_ms: Time taken to process the request
    """
    try:
        # Use the enhanced coordinator with strict validation
        response = await coordinate_request(message, user_id, db, chat_id)

        # Validate that we have a proper AgentResponse
        if not hasattr(response, 'result') or not hasattr(response, 'agent_type'):
            raise ValueError("Invalid response structure from coordinator")

        # Count tokens for input and output
        response_json = response.model_dump_json(indent=2)
        token_counts = count_message_tokens(message, response_json)
        
        # Add token information to the response
        response.input_tokens = token_counts["input_tokens"]
        response.output_tokens = token_counts["output_tokens"] 
        response.total_tokens = token_counts["total_tokens"]

        # Format and return the validated response with token counts
        return response.model_dump_json(indent=2)
        
    except Exception as e:
        print(f"Critical error in process_user_request: {e}")
        print(f"Error type: {type(e).__name__}")
        print(f"User ID: {user_id}, Chat ID: {chat_id}")
        print(f"Message: {message}")
        
        # Return a properly structured error response as fallback
        from src.agent.sub_agents.base import AgentResponse, GeneralResponse
        
        error_response_text = "I apologize, but I encountered a critical error while processing your request. Please try again, and if the problem persists, contact support."
        
        # Count tokens even for error responses
        token_counts = count_message_tokens(message, error_response_text)
        
        error_response = AgentResponse(
            result=GeneralResponse(
                response=error_response_text,
                response_type="error",
                confidence=0.9
            ),
            agent_type="general",
            processing_time_ms=0.0,
            input_tokens=token_counts["input_tokens"],
            output_tokens=token_counts["output_tokens"],
            total_tokens=token_counts["total_tokens"]
        )
        
        return error_response.model_dump_json(indent=2)


# Enhanced example usage with structured outputs demonstration
# async def main():
#     """
#     Example usage demonstrating the enhanced structured output system.
#     All responses are now guaranteed to be properly validated.
#     """
#     print("🚀 Testing Enhanced Structured Output System...\n")
#     
#     # Test case 1: Product search with validation
#     print("1. Testing Product Search (ProductList output):")
#     response_search = await process_user_request(
#         "Can you find me a black t-shirt under $30?", 
#         user_id=1,
#         db=db_session,
#         chat_id=1
#     )
#     print(response_search)
#     print()
#
#     # Test case 2: Outfit recommendation with validation  
#     print("2. Testing Outfit Recommendation (Outfit output):")
#     response_outfit = await process_user_request(
#         "What should I wear for a business meeting today?", 
#         user_id=1,
#         db=db_session,
#         chat_id=1
#     )
#     print(response_outfit)
#     print()
#
#     # Test case 3: General question with validation
#     print("3. Testing General Question (GeneralResponse output):")
#     response_general = await process_user_request(
#         "What is the weather like today?", 
#         user_id=1,
#         db=db_session,
#         chat_id=1
#     )
#     print(response_general)
#     print()
#     
#     print("✅ All responses are now strictly validated with enhanced structured outputs!")
#
# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(main())