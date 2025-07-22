import re
import uuid
from typing import List, Dict, Any
from datetime import datetime
import json

def is_valid_uuid(uuid_string: str) -> bool:
    """
    Check if a string is a valid UUID format
    """
    try:
        uuid.UUID(uuid_string)
        return True
    except ValueError:
        return False

def sanitize_user_input(text: str, max_length: int = 1000) -> str:
    """
    Basic sanitization of user input
    - Remove excessive whitespace
    - Limit length
    - Remove potentially harmful characters
    """
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Limit length
    if len(text) > max_length:
        text = text[:max_length] + "..."
    
    # Remove some potentially problematic characters (adjust as needed)
    text = re.sub(r'[<>{}]', '', text)
    
    return text

def format_contact_for_display(contact: Dict[str, Any]) -> str:
    """
    Format a contact dictionary into a readable string
    """
    parts = [contact.get('name', 'Unknown')]
    
    if contact.get('company'):
        parts.append(f"({contact['company']})")
    
    if contact.get('contact_email'):
        parts.append(f"Email: {contact['contact_email']}")
        
    if contact.get('phone_number'):
        parts.append(f"Phone: {contact['phone_number']}")
    
    return " - ".join(parts)

def format_note_for_display(note: Dict[str, Any]) -> str:
    """
    Format a note dictionary into a readable string
    """
    title = note.get('title', 'Untitled Note')
    description = note.get('description', '')
    
    result = f"**{title}**"
    
    if description:
        # Truncate long descriptions
        if len(description) > 200:
            description = description[:200] + "..."
        result += f": {description}"
    
    # Add related contacts if available
    if note.get('related_contacts'):
        contacts = ", ".join(note['related_contacts'])
        result += f" (Related to: {contacts})"
    
    return result

def prepare_data_for_ai(contacts: List[Dict], notes: List[Dict]) -> tuple[str, str]:
    """
    Format contacts and notes data for AI consumption
    Returns (formatted_contacts, formatted_notes)
    """
    # Format contacts
    if contacts:
        contacts_text = "\n".join([
            f"• {format_contact_for_display(contact)}" 
            for contact in contacts
        ])
    else:
        contacts_text = "No contacts available."
    
    # Format notes
    if notes:
        notes_text = "\n".join([
            f"• {format_note_for_display(note)}" 
            for note in notes
        ])
    else:
        notes_text = "No notes available."
    
    return contacts_text, notes_text

def log_ai_interaction(user_id: str, query: str, response: str, success: bool):
    """
    Log AI interactions for debugging and analytics
    (In production, you might want to store this in a database)
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "query": query[:100] + "..." if len(query) > 100 else query,  # Truncate long queries
        "response_length": len(response) if response else 0,
        "success": success
    }
    
    print(f"AI_LOG: {json.dumps(log_entry)}")

def extract_keywords_from_query(query: str) -> List[str]:
    """
    Extract potential keywords from user query for better search
    (Basic implementation - could be enhanced with NLP)
    """
    # Remove common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
        'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
        'before', 'after', 'above', 'below', 'between', 'among', 'is', 'are', 
        'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
        'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can',
        'who', 'what', 'when', 'where', 'why', 'how', 'i', 'me', 'my', 'you', 
        'your', 'he', 'him', 'his', 'she', 'her', 'it', 'its', 'we', 'us', 
        'our', 'they', 'them', 'their'
    }
    
    # Extract words (alphanumeric only, minimum 2 characters)
    words = re.findall(r'\b[a-zA-Z0-9]{2,}\b', query.lower())
    
    # Filter out stop words
    keywords = [word for word in words if word not in stop_words]
    
    return keywords

def validate_query_safety(query: str) -> tuple[bool, str]:
    """
    Basic safety check for user queries
    Returns (is_safe, reason_if_not_safe)
    """
    # Check for excessive length
    if len(query) > 2000:
        return False, "Query too long"
    
    # Check for potentially malicious patterns (basic)
    malicious_patterns = [
        r'<script',
        r'javascript:',
        r'eval\(',
        r'exec\(',
        r'__import__',
        r'DROP\s+TABLE',
        r'DELETE\s+FROM',
        r'INSERT\s+INTO'
    ]
    
    for pattern in malicious_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            return False, f"Query contains potentially unsafe content"
    
    return True, ""