from pydantic_ai import Agent, RunContext
from typing import Union
from sqlalchemy.orm import Session
from dataclasses import dataclass
from .base import get_azure_llm, AgentResponse, ProductList, Outfit, GeneralResponse, MessageHistory
from .search_agent import search_agent
from .outfit_agent import create_outfit_agent  
from .general_agent import general_agent
from src.models.chat import Message as DBMessage


@dataclass
class CoordinatorDependencies:
    """Dependencies for the coordinator agent."""
    user_id: int
    db: Session
    chat_id: int


# Create the coordinator agent that uses tools to delegate to sub-agents
coordinator_agent = Agent(
    get_azure_llm(),
    deps_type=CoordinatorDependencies,
    output_type=AgentResponse,
    system_prompt="""You are a smart coordinator agent that routes user requests to specialized sub-agents.

Analyze the user's message and determine which type of request it is:
- Product search requests: Use search_products tool for finding, buying, shopping, looking for products
- Outfit/wardrobe requests: Use recommend_outfit tool for styling, dressing, outfit coordination
- General conversation: Use handle_general_query tool for other questions

Always use exactly one tool based on the user's request type. Pass the original user message to the chosen tool.

You have access to the conversation history to provide more contextual responses. Use this history to understand the user's preferences and previous interactions."""
)


@coordinator_agent.tool
async def search_products(ctx: RunContext[CoordinatorDependencies], user_message: str) -> ProductList:
    """
    Search for products based on user query.
    
    Args:
        user_message: The user's search request
        
    Returns:
        ProductList: Search results with products
    """
    result = await search_agent.run(user_message)
    return result.data


@coordinator_agent.tool  
async def recommend_outfit(ctx: RunContext[CoordinatorDependencies], user_message: str) -> Outfit:
    """
    Recommend outfit based on user's wardrobe and preferences.
    
    Args:
        user_message: The user's outfit request
        
    Returns:
        Outfit: Outfit recommendation
    """
    user_id = ctx.deps.user_id
    # Create outfit agent for this specific user
    outfit_agent = create_outfit_agent(user_id)
    result = await outfit_agent.run(user_message)
    return result.data


@coordinator_agent.tool
async def handle_general_query(ctx: RunContext[CoordinatorDependencies], user_message: str) -> GeneralResponse:
    """
    Handle general conversation and questions.
    
    Args:
        user_message: The user's general question
        
    Returns:
        GeneralResponse: General response
    """
    # Get chat history from context
    history = await get_chat_history(ctx.deps.db, ctx.deps.chat_id)
    result = await general_agent.run(
        user_message,
        message_history=history.to_pydantic_ai_messages()
    )
    return result.data


async def get_chat_history(db: Session, chat_id: int) -> MessageHistory:
    """Fetch chat history from database."""
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


async def coordinate_request(message: str, user_id: int, db: Session, chat_id: int) -> AgentResponse:
    """
    Coordinate user requests using the PydanticAI agent delegation pattern.
    
    Args:
        message: The user's message/request
        user_id: The ID of the authenticated user
        db: Database session
        chat_id: ID of the current chat
        
    Returns:
        AgentResponse: Structured response from the appropriate agent
    """
    try:
        # Create dependencies
        deps = CoordinatorDependencies(
            user_id=user_id,
            db=db,
            chat_id=chat_id
        )
        
        # Use the coordinator agent to handle the request with history
        result = await coordinator_agent.run(
            message,
            deps=deps
        )
        return result.data
        
    except Exception as e:
        print(f"Error in coordinate_request: {e}")
        # Return a general error response
        error_response = GeneralResponse(
            response="I'm sorry, I encountered an error while processing your request. Please try again."
        )
        return AgentResponse(result=error_response) 