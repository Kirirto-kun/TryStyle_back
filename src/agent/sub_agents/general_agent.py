from pydantic_ai import Agent
from .base import get_azure_llm, GeneralResponse


# Create the general conversation agent
general_agent = Agent(
    get_azure_llm(),
    output_type=GeneralResponse,
    system_prompt="""You are a helpful and friendly AI assistant. Your role is to:

1. Answer general questions with accurate and helpful information
2. Engage in friendly conversation
3. Provide assistance with various topics
4. Be concise but informative in your responses
5. If users ask about product searches or outfit recommendations, politely suggest they specify those needs

Always maintain a positive and helpful tone. Provide accurate information and be honest if you don't know something.""",
)


async def handle_general_query(message: str) -> GeneralResponse:
    """
    Handle general questions and conversations.
    
    Args:
        message: The user's message/question
        
    Returns:
        GeneralResponse: Structured response to the general query
    """
    try:
        result = await general_agent.run(message)
        return result.data
    except Exception as e:
        print(f"Error in handle_general_query: {e}")
        # Return a friendly error message
        return GeneralResponse(
            response="I'm sorry, I encountered an issue while processing your request. Please try again."
        ) 