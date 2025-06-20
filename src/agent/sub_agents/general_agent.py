from pydantic_ai import Agent, ModelRetry
from typing import List
from .base import get_azure_llm, GeneralResponse, MessageHistory
from pydantic_ai.messages import ModelMessage


# Cached agent instance for better performance with enhanced validation
_general_agent_instance = None

def get_general_agent() -> Agent:
    """
    Returns cached general agent instance with enhanced structured output validation.
    
    Returns:
        Agent: Cached general conversation agent with strict validation
    """
    global _general_agent_instance
    
    if _general_agent_instance is None:
        _general_agent_instance = Agent(
    get_azure_llm(),
    output_type=GeneralResponse,
            system_prompt="""You are a helpful and friendly AI assistant with strict output requirements.

STRUCTURED OUTPUT REQUIREMENTS:
- You MUST return a valid GeneralResponse object with ALL required fields
- response: 5-1000 characters, helpful and informative answer
- response_type: Must be one of: answer, clarification, suggestion, greeting, error  
- confidence: Float 0.0-1.0 representing your confidence in the response

YOUR ROLE:
1. Answer general questions with accurate and helpful information
2. Engage in friendly, natural conversation
3. Provide assistance with various topics appropriately
4. Be concise but informative in your responses
5. If users ask about product searches or outfit recommendations, politely guide them to specify those needs
6. Use conversation history to maintain context and provide more relevant responses

RESPONSE GUIDELINES:
- Be accurate and honest - if unsure, indicate lower confidence
- Maintain a positive, helpful tone in all interactions
- Provide practical, actionable information when possible
- Handle follow-up questions contextually using message history
- Classify your response type appropriately:
  * answer: Direct response to a question
  * clarification: Asking for more details
  * suggestion: Recommending an action or alternative
  * greeting: Welcome or acknowledgment messages
  * error: When unable to process the request

QUALITY STANDARDS:
- All responses must be 5-1000 characters (substantive but not overwhelming)
- Set confidence appropriately (0.9+ for factual info, 0.7+ for opinions, 0.5+ for uncertain)
- Always be respectful and inclusive
- Provide sources or context when helpful

VALIDATION GUARANTEE: Every response will be validated for structure and content quality.""",
            retries=4  # Increased retries for reliability
        )
        
        # Add output validator for enhanced reliability
        @_general_agent_instance.output_validator
        async def validate_general_output(output: GeneralResponse) -> GeneralResponse:
            """Validate and enhance general response quality."""
            if not isinstance(output, GeneralResponse):
                raise ModelRetry("Output must be a valid GeneralResponse object")
            
            # Validate response length
            response_text = output.response.strip()
            if len(response_text) < 5:
                raise ModelRetry("Response must be at least 5 characters long")
            
            if len(response_text) > 1000:
                raise ModelRetry("Response must not exceed 1000 characters")
            
            # Ensure response is not empty or just whitespace
            if not response_text:
                raise ModelRetry("Response cannot be empty or whitespace only")
            
            # Validate confidence range
            if not (0.0 <= output.confidence <= 1.0):
                output.confidence = 0.8  # Default reasonable confidence
            
            # Validate response type
            valid_types = ["answer", "clarification", "suggestion", "greeting", "error"]
            if output.response_type not in valid_types:
                output.response_type = "answer"  # Default to answer
            
            # Clean up the response text
            output.response = response_text
            
            return output
    
    return _general_agent_instance


async def handle_general_query(message: str, message_history: List[ModelMessage] = None) -> GeneralResponse:
    """
    Handle general questions and conversations with enhanced structured output validation.
    Now guarantees properly formatted responses!
    
    Args:
        message: The user's message/question
        message_history: Optional list of previous messages for context
        
    Returns:
        GeneralResponse: Strictly validated response to the general query
    """
    try:
        # Use cached agent with enhanced validation
        general_agent = get_general_agent()
        
        # Run the agent with message history if provided
        result = await general_agent.run(
            message,
            message_history=message_history
        )
        return result.data
    except Exception as e:
        print(f"Error in handle_general_query: {e}")
        # Return a friendly error message in proper structured format
        return GeneralResponse(
            response="I'm sorry, I encountered an issue while processing your request. Please try again with a clearer question.",
            response_type="error",
            confidence=0.9
        ) 