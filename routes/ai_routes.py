from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from models.schemas import AIQueryRequest, AIQueryResponse
from services.ai_service import AIService
from sse_starlette.sse import EventSourceResponse
import logging
import json
import asyncio

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/ai", tags=["AI"])

# Initialize AI service
ai_service = AIService()

@router.post("/query", response_model=AIQueryResponse)
async def query_ai(request: AIQueryRequest):
    """
    Ask AI a question about user's contacts and notes
    Maintains conversation memory for natural dialogue
    
    Example request:
    {
        "user_id": "123e4567-e89b-12d3-a456-426614174000",
        "query": "Who are my contacts at Google?"
    }
    """
    try:
        logger.info(f"Processing AI query for user {request.user_id}: {request.query}")
        
        # Validate user_id format (basic UUID check)
        if not request.user_id or len(request.user_id) < 10:
            raise HTTPException(
                status_code=400, 
                detail="Invalid user_id format"
            )
        
        # Process the query
        result = ai_service.ask_question(request.user_id, request.query)
        
        if result["success"]:
            logger.info(f"AI query successful for user {request.user_id}")
            return AIQueryResponse(
                success=True,
                response=result["response"],
                data_summary=result["data_summary"]
            )
        else:
            logger.error(f"AI query failed for user {request.user_id}: {result['error']}")
            raise HTTPException(
                status_code=500,
                detail=f"AI processing failed: {result['error']}"
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing AI query: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error processing AI query"
        )
    
@router.post("/query/stream")
async def query_ai_stream(request: AIQueryRequest):
    """
    Stream AI response as Server-Sent Events
    This provides real-time streaming of the AI response as it's generated
    
    Example usage:
    fetch('/ai/query/stream', {
        method: 'POST',
        body: JSON.stringify({
            user_id: 'uuid',
            query: 'Who are my contacts?'
        })
    }).then(response => {
        const reader = response.body.getReader();
        // Handle streaming response
    });
    """
    
    async def generate_ai_stream():
        try:
            logger.info(f"Processing streaming AI query for user {request.user_id}: {request.query}")
            
            # Validate user_id format
            if not request.user_id or len(request.user_id) < 10:
                yield {
                    "event": "error",
                    "data": json.dumps({"error": "Invalid user_id format"})
                }
                return
            
            # Send initial status
            yield {
                "event": "status", 
                "data": json.dumps({"status": "processing", "message": "Getting your data..."})
            }
            
            # Get user data first
            try:
                contacts, notes = ai_service.get_user_data(request.user_id)
                yield {
                    "event": "status",
                    "data": json.dumps({
                        "status": "data_loaded", 
                        "contacts_count": len(contacts),
                        "notes_count": len(notes)
                    })
                }
            except Exception as e:
                yield {
                    "event": "error",
                    "data": json.dumps({"error": f"Failed to load user data: {str(e)}"})
                }
                return
            
            # Send status that AI is thinking
            yield {
                "event": "status",
                "data": json.dumps({"status": "thinking", "message": "AI is processing your question..."})
            }
            
            # Get streaming AI response
            try:
                # Use the streaming version of ask_question
                async for chunk in ai_service.ask_question_stream(request.user_id, request.query):
                    if chunk["type"] == "token":
                        yield {
                            "event": "token",
                            "data": json.dumps({"token": chunk["content"]})
                        }
                    elif chunk["type"] == "complete":
                        yield {
                            "event": "complete",
                            "data": json.dumps({
                                "full_response": chunk["full_response"],
                                "data_summary": chunk["data_summary"]
                            })
                        }
                        
            except Exception as e:
                logger.error(f"AI streaming failed: {str(e)}")
                yield {
                    "event": "error",
                    "data": json.dumps({"error": f"AI processing failed: {str(e)}"})
                }
                
        except Exception as e:
            logger.error(f"Unexpected streaming error: {str(e)}")
            yield {
                "event": "error",
                "data": json.dumps({"error": f"Unexpected error: {str(e)}"})
            }
    
    return EventSourceResponse(generate_ai_stream())

@router.get("/test-ollama")
async def test_ollama():
    """
    Test if Ollama is working and responding
    """
    try:
        is_working, response = ai_service.test_connection()
        
        if is_working:
            return {
                "status": "success",
                "message": "Ollama is working",
                "test_response": response
            }
        else:
            raise HTTPException(
                status_code=503,
                detail=f"Ollama connection failed: {response}"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Error testing Ollama: {str(e)}"
        )

@router.post("/clear-memory/{user_id}")
async def clear_user_memory(user_id: str):
    """
    Clear conversation memory for a user (start fresh conversation)
    """
    try:
        if user_id in ai_service.user_memories:
            del ai_service.user_memories[user_id]
            return {"message": f"Conversation memory cleared for user {user_id}"}
        else:
            return {"message": f"No conversation memory found for user {user_id}"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing memory: {str(e)}"
        )

@router.get("/user-data/{user_id}")
async def get_user_data(user_id: str):
    """
    Debug endpoint to see what data exists for a user
    (Remove this in production for security)
    """
    try:
        contacts, notes = ai_service.get_user_data(user_id)
        
        return {
            "user_id": user_id,
            "contacts": contacts,
            "notes": notes,
            "summary": {
                "total_contacts": len(contacts),
                "total_notes": len(notes)
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching user data: {str(e)}"
        )