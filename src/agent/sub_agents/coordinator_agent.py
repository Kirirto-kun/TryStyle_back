import time
from pydantic_ai import Agent, RunContext, ModelRetry
from typing import Union, List
from sqlalchemy.orm import Session
from dataclasses import dataclass
from .base import get_azure_llm, AgentResponse, ProductList, Outfit, GeneralResponse, MessageHistory
from .catalog_search_agent import get_catalog_search_agent, search_catalog_products  # Поиск в локальном каталоге
from .outfit_agent import create_outfit_agent  
from .general_agent import get_general_agent
from src.models.chat import Message as DBMessage
from pydantic_ai.messages import ModelMessage


@dataclass
class CoordinatorDependencies:
    """Dependencies for the coordinator agent."""
    user_id: int
    db: Session
    chat_id: int


# Cached coordinator agent for better performance with enhanced validation
_coordinator_agent_instance = None

def get_coordinator_agent() -> Agent:
    """
    Returns cached coordinator agent instance with enhanced structured output validation.
    
    Returns:
        Agent: Cached coordinator agent with strict validation
    """
    global _coordinator_agent_instance
    
    if _coordinator_agent_instance is None:
        _coordinator_agent_instance = Agent(
    get_azure_llm(),
    deps_type=CoordinatorDependencies,
    output_type=AgentResponse,
            tools=[search_products, recommend_outfit, handle_general_query],
            system_prompt="""You are a smart coordinator agent with context awareness and strict structured output requirements.

STRUCTURED OUTPUT REQUIREMENTS:
- You MUST return a valid AgentResponse object with ALL required fields
- result: The output from the chosen specialized agent (ProductList, Outfit, or GeneralResponse)
- agent_type: Must be exactly "search", "outfit", or "general"
- processing_time_ms: Will be automatically calculated

CONTEXT AWARENESS:
You have access to conversation history to understand the context and provide better routing decisions:
- Analyze previous messages to understand what the user was discussing
- If user provides feedback or modifications to previous requests, maintain context
- Create contextual prompts that include relevant conversation history
- Handle follow-up questions and refinements intelligently

ROUTING DECISION LOGIC WITH CONTEXT:
Analyze the user's message AND conversation history to determine the appropriate agent:

1. CATALOG SEARCH AGENT ("search") - Use search_products tool for:
   - Looking for specific clothing items, brands, categories
   - Price queries, size/color searches in local catalog
   - Style recommendations and outfit coordination
   - Keywords: "find", "looking for", "want", "need", "search", "show me"
   - Examples: "I want business pants", "show me black t-shirts", "what goes with jeans"
   - Follow-ups to previous searches (refinements, alternatives, styling)

2. OUTFIT AGENT ("outfit") - Use recommend_outfit tool for:
   - Styling, dressing, outfit coordination
   - Fashion advice, wardrobe management
   - "What to wear" questions
   - Keywords: "wear", "outfit", "style", "fashion", "clothes", "wardrobe"
   - Follow-ups to previous outfit recommendations (modifications, alternatives, different occasions)

3. GENERAL AGENT ("general") - Use handle_general_query tool for:
   - General questions and conversations
   - Information requests not related to products or fashion
   - Greetings, small talk, general assistance
   - All other queries not covered above

CONTEXTUAL PROMPT CREATION:
When routing to agents, create enhanced prompts that include:
- Original user message
- Relevant context from conversation history
- Clear indication of what the user is trying to achieve
- Any specific preferences or constraints mentioned previously

DECISION RULES:
- Use EXACTLY ONE tool per request - never combine tools
- Analyze conversation history to understand user intent better
- For follow-up requests, maintain context from previous interactions
- Choose the most specific agent first (search/outfit) before defaulting to general
- Create contextual prompts that help agents understand the full picture

QUALITY GUARANTEE:
- Every response will be properly structured and validated
- All agent outputs will be type-checked and verified
- Context will be preserved across conversation turns
- Error handling ensures graceful fallbacks with proper structure""",
            retries=4  # Increased retries for reliability
        )
        
        # Add output validator for enhanced reliability
        @_coordinator_agent_instance.output_validator
        async def validate_coordinator_output(output: AgentResponse) -> AgentResponse:
            """Validate and enhance coordinator output quality."""
            if not isinstance(output, AgentResponse):
                raise ModelRetry("Output must be a valid AgentResponse object")
            
            # Validate agent_type
            valid_agent_types = ["search", "outfit", "general"]
            if output.agent_type not in valid_agent_types:
                raise ModelRetry(f"agent_type must be one of: {valid_agent_types}")
            
            # Validate result type matches agent_type
            if output.agent_type == "search" and not isinstance(output.result, ProductList):
                raise ModelRetry("Search agent must return ProductList")
            elif output.agent_type == "outfit" and not isinstance(output.result, Outfit):
                raise ModelRetry("Outfit agent must return Outfit")
            elif output.agent_type == "general" and not isinstance(output.result, GeneralResponse):
                raise ModelRetry("General agent must return GeneralResponse")
            
            # Ensure processing_time_ms is valid
            if output.processing_time_ms < 0:
                output.processing_time_ms = 0.0
            
            # Ensure token counts are valid (they will be updated later in process_user_request)
            if not hasattr(output, 'input_tokens') or output.input_tokens < 0:
                output.input_tokens = 0
            if not hasattr(output, 'output_tokens') or output.output_tokens < 0:
                output.output_tokens = 0
            if not hasattr(output, 'total_tokens') or output.total_tokens < 0:
                output.total_tokens = 0
            
            return output
    
    return _coordinator_agent_instance


def create_contextual_prompt(user_message: str, chat_history: MessageHistory, agent_type: str) -> str:
    """
    Create a contextual prompt that includes relevant conversation history.
    
    Args:
        user_message: Current user message
        chat_history: Previous conversation history
        agent_type: Type of agent (search/outfit/general)
        
    Returns:
        Enhanced prompt with context
    """
    if not chat_history.messages:
        return user_message
    
    # Get last few relevant messages for context
    recent_messages = chat_history.messages[-6:]  # Last 6 messages for context
    
    context_info = []
    
    # Extract relevant context based on agent type
    for msg in recent_messages:
        if agent_type == "search" and any(keyword in msg.get("content", "").lower() for keyword in ["product", "buy", "find", "search", "price", "shop"]):
            context_info.append(f"Previous: {msg.get('content', '')}")
        elif agent_type == "outfit" and any(keyword in msg.get("content", "").lower() for keyword in ["outfit", "wear", "style", "clothes", "wardrobe", "fashion"]):
            context_info.append(f"Previous: {msg.get('content', '')}")
    
    if context_info:
        context_str = "\n".join(context_info[-3:])  # Last 3 relevant messages
        enhanced_prompt = f"""Based on our conversation context:
{context_str}

Current request: {user_message}

Please consider the conversation history when providing your response. If this is a follow-up or refinement to a previous request, build upon that context."""
        return enhanced_prompt
    
    return user_message


async def search_products(ctx: RunContext[CoordinatorDependencies], user_message: str) -> ProductList:
    """
    Search for products in the internal H&M catalog based on user query.
    Now searches only in local database catalog instead of external sources.
    
    Args:
        user_message: The user's search request
        
    Returns:
        ProductList: Search results from internal H&M catalog
    """
    try:
        # Get chat history for context
        history = await get_chat_history(ctx.deps.db, ctx.deps.chat_id)
        
        # Поиск в локальном каталоге H&M
        result = await search_catalog_products(
            message=user_message,
            user_id=ctx.deps.user_id,
            db=ctx.deps.db,
            chat_id=ctx.deps.chat_id,
            message_history=history.to_pydantic_ai_messages()
        )
        return result
        
    except Exception as e:
        print(f"Error in search_products (catalog search): {e}")
        # Return valid empty result on error
        return ProductList(
            products=[],
            search_query=user_message,
            total_found=0
        )


async def recommend_outfit(ctx: RunContext[CoordinatorDependencies], user_message: str) -> Outfit:
    """
    Recommend outfit based on user's wardrobe and preferences with conversation context.
    Enhanced with chat history for better contextual understanding.
    
    Args:
        user_message: The user's outfit request
        
    Returns:
        Outfit: Outfit recommendation
    """
    try:
        user_id = ctx.deps.user_id
        
        # Get chat history for context
        history = await get_chat_history(ctx.deps.db, ctx.deps.chat_id)
        
        # Create contextual prompt
        contextual_prompt = create_contextual_prompt(user_message, history, "outfit")
        
        # Create outfit agent for this specific user
        outfit_agent = create_outfit_agent(user_id)
        result = await outfit_agent.run(
            contextual_prompt,
            message_history=history.to_pydantic_ai_messages()
        )
        return result.data
    except Exception as e:
        print(f"Error in recommend_outfit: {e}")
        # Return valid error outfit
        return Outfit(
            outfit_description="Sorry, I couldn't access your wardrobe right now. Please try again or ensure you have clothing items added.",
            items=[],
            reasoning="Technical issue prevented wardrobe access. Please retry your request.",
            occasion="casual"
        )


async def handle_general_query(ctx: RunContext[CoordinatorDependencies], user_message: str) -> GeneralResponse:
    """
    Handle general conversation and questions using cached general agent.
    Enhanced with validation to ensure reliable results.
    
    Args:
        user_message: The user's general question
        
    Returns:
        GeneralResponse: General response
    """
    try:
        # Get chat history from context
        history = await get_chat_history(ctx.deps.db, ctx.deps.chat_id)
        general_agent = get_general_agent()
        result = await general_agent.run(
            user_message,
            message_history=history.to_pydantic_ai_messages()
        )
        return result.data
    except Exception as e:
        print(f"Error in handle_general_query: {e}")
        # Return valid error response
        return GeneralResponse(
            response="I encountered an issue processing your request. Please try rephrasing your question.",
            response_type="error",
            confidence=0.8
        )


async def get_chat_history(db: Session, chat_id: int) -> MessageHistory:
    """Fetch chat history from database with error handling."""
    try:
        messages = (
            db.query(DBMessage)
            .filter(DBMessage.chat_id == chat_id)
            .order_by(DBMessage.created_at.asc())
            .all()
        )
        # Convert SQLAlchemy models to dictionaries
        message_dicts = [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in messages
        ]
        return MessageHistory(messages=message_dicts)
    except Exception as e:
        print(f"Error fetching chat history: {e}")
        return MessageHistory(messages=[])


async def coordinate_request(message: str, user_id: int, db: Session, chat_id: int) -> AgentResponse:
    """
    Coordinate user requests using enhanced PydanticAI agent delegation with context awareness.
    Now understands conversation context and creates contextual prompts for better agent performance!
    
    Args:
        message: The user's message/request
        user_id: The ID of the authenticated user
        db: Database session
        chat_id: ID of the current chat
        
    Returns:
        AgentResponse: Strictly validated response from the appropriate agent
    """
    start_time = time.time()
    
    try:
        # Create dependencies
        deps = CoordinatorDependencies(
            user_id=user_id,
            db=db,
            chat_id=chat_id
        )
        
        # Get chat history for better routing decisions
        history = await get_chat_history(db, chat_id)
        
        # Use the cached coordinator agent to handle the request with context
        coordinator_agent = get_coordinator_agent()
        result = await coordinator_agent.run(
            message,
            deps=deps,
            message_history=history.to_pydantic_ai_messages()
        )
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Ensure we have the processing time set
        response = result.data
        response.processing_time_ms = processing_time
        
        return response
        
    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        print(f"Error in coordinate_request: {e}")
        print(f"Error type: {type(e).__name__}")
        print(f"User ID: {user_id}, Chat ID: {chat_id}")
        print(f"Message: {message}")
        print(f"Processing time: {processing_time:.2f}ms")
        
        # Return a valid structured error response
        error_response = GeneralResponse(
            response="I'm sorry, I encountered an error while processing your request. Please try again. If you're asking about your wardrobe, make sure you have some clothing items added to it.",
            response_type="error",
            confidence=0.9
        )
        return AgentResponse(
            result=error_response,
            agent_type="general",
            processing_time_ms=processing_time,
            input_tokens=0,
            output_tokens=0,
            total_tokens=0
        ) 