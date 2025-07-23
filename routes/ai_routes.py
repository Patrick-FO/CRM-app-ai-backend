from fastapi import APIRouter, HTTPException
from models.schemas import AIQueryRequest, AIQueryResponse
from services.ai_service import AIService
import logging

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