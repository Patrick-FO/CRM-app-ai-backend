import os
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferWindowMemory
from langchain.chains import ConversationChain
from config.database import get_db_connection
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime
import asyncio

class AIService:
    def __init__(self):
        # Initialize Ollama
        self.llm = Ollama(
            model=os.getenv("OLLAMA_MODEL", "llama3.2"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=0.7  # Make responses more conversational
        )
        
        # Store conversation memories for each user - using simple string storage
        self.user_conversations = {}
    
    def get_user_data(self, user_id: str):
        """Get all contacts and notes for a specific user (user_id is UUID string)"""
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Get contacts for this user
                cursor.execute("""
                    SELECT 
                        id, 
                        name, 
                        company, 
                        phone_number, 
                        contact_email
                    FROM contacts 
                    WHERE user_id = %s
                """, (user_id,))
                contacts = [dict(row) for row in cursor.fetchall()]
                
                # Get notes for this user
                cursor.execute("""
                    SELECT 
                        id,
                        title, 
                        description, 
                        contact_ids
                    FROM notes 
                    WHERE user_id = %s
                """, (user_id,))
                raw_notes = cursor.fetchall()
                
                # Process notes and link contact names
                notes = []
                for note in raw_notes:
                    note_dict = dict(note)
                    
                    # Get contact names for the contact_ids in this note
                    contact_names = []
                    if note_dict['contact_ids']:  # contact_ids is a JSON array
                        contact_ids = note_dict['contact_ids']
                        if contact_ids:  # Make sure it's not empty
                            # Create placeholders for the IN clause
                            placeholders = ','.join(['%s'] * len(contact_ids))
                            cursor.execute(f"""
                                SELECT name FROM contacts 
                                WHERE id IN ({placeholders}) AND user_id = %s
                            """, contact_ids + [user_id])
                            contact_names = [row['name'] for row in cursor.fetchall()]
                    
                    note_dict['related_contacts'] = contact_names
                    notes.append(note_dict)
                
                return contacts, notes
                
        finally:
            conn.close()
    
    def build_prompt(self, user_id: str, question: str, contacts: list, notes: list):
        """Build the full prompt with user data and conversation history"""
        # Format contacts for AI (more readable)
        contacts_formatted = []
        for contact in contacts:
            contact_info = f"• {contact['name']}"
            if contact['company']:
                contact_info += f" ({contact['company']})"
            if contact['contact_email']:
                contact_info += f" - {contact['contact_email']}"
            if contact['phone_number']:
                contact_info += f" - {contact['phone_number']}"
            contacts_formatted.append(contact_info)
        
        # Format notes for AI (more readable)
        notes_formatted = []
        for note in notes:
            note_info = f"• {note['title']}"
            if note['description']:
                note_info += f": {note['description']}"
            if note['related_contacts']:
                note_info += f" (Related to: {', '.join(note['related_contacts'])})"
            notes_formatted.append(note_info)
        
        # Create context about user's data
        contacts_text = '\n'.join(contacts_formatted) if contacts_formatted else "No contacts found."
        notes_text = '\n'.join(notes_formatted) if notes_formatted else "No notes found."
        
        # Get conversation history for this user (simple approach)
        if user_id not in self.user_conversations:
            self.user_conversations[user_id] = []
        
        conversation_history = self.user_conversations[user_id]
        
        # Format conversation history
        history_text = ""
        if conversation_history:
            history_items = []
            for item in conversation_history[-6:]:  # Last 6 exchanges (3 back-and-forth)
                history_items.append(f"Human: {item['question']}")
                history_items.append(f"AI: {item['answer']}")
            history_text = "\n".join(history_items)
        
        # Create the full prompt
        full_prompt = f"""You are a helpful AI assistant for a CRM system. You're having a conversation with a user about their business contacts and notes.

Context about the user's data:
CONTACTS:
{contacts_text}

NOTES:
{notes_text}

Instructions: Answer naturally and conversationally. Don't start with phrases like "Based on your data" or "According to your notes". 
Act like you're a helpful assistant who knows this information about the user. Be direct and answer concisely. Don't make out-of-place suggestions, just answer whatever the user is asking and move on.
If you don't have relevant information, just say you don't see that information rather than being overly formal. 
Also, you are not able to create notes or contacts for a user, so if they ask you to actually do something for them which requires any other CRUD operation than reading, tell them you can't. 

{f"Previous conversation:\n{history_text}\n" if history_text else ""}Human: {question}
AI: """
        
        return full_prompt
    
    def ask_question(self, user_id: str, question: str):
        """Ask AI a question about user's contacts and notes with simple conversation memory"""
        try:
            # Get user's data
            contacts, notes = self.get_user_data(user_id)
            
            # Build the full prompt
            full_prompt = self.build_prompt(user_id, question, contacts, notes)
            
            # Get AI response
            response = self.llm.invoke(full_prompt)
            
            # Store this exchange in conversation history
            self.user_conversations[user_id].append({
                "question": question,
                "answer": response.strip(),
                "timestamp": datetime.now().isoformat()
            })
            
            # Keep only last 10 exchanges to prevent memory from growing too large
            if len(self.user_conversations[user_id]) > 10:
                self.user_conversations[user_id] = self.user_conversations[user_id][-10:]
            
            return {
                "success": True,
                "response": response.strip(),
                "data_summary": {
                    "contacts_count": len(contacts),
                    "notes_count": len(notes)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def ask_question_stream(self, user_id: str, question: str):
        """Stream AI response as it's generated (async generator)"""
        try:
            # Get user's data
            contacts, notes = self.get_user_data(user_id)
            
            # Build the full prompt (reuse the same logic)
            full_prompt = self.build_prompt(user_id, question, contacts, notes)
            
            # Get AI response (for now, we simulate streaming by chunking)
            # Note: Real streaming would require Ollama's streaming API
            response = self.llm.invoke(full_prompt)
            
            # Simulate streaming by sending word chunks
            full_response = ""
            words = response.split()
            
            for i, word in enumerate(words):
                full_response += word + " "
                yield {
                    "type": "token",
                    "content": word + " "
                }
                # Small delay to simulate real streaming
                await asyncio.sleep(0.05)
            
            # Store this exchange in conversation history
            self.user_conversations[user_id].append({
                "question": question,
                "answer": response.strip(),
                "timestamp": datetime.now().isoformat()
            })
            
            # Keep only last 10 exchanges
            if len(self.user_conversations[user_id]) > 10:
                self.user_conversations[user_id] = self.user_conversations[user_id][-10:]
            
            # Send completion signal
            yield {
                "type": "complete",
                "full_response": full_response.strip(),
                "data_summary": {
                    "contacts_count": len(contacts),
                    "notes_count": len(notes)
                }
            }
            
        except Exception as e:
            yield {
                "type": "error",
                "error": str(e)
            }
    
    def test_connection(self):
        """Test if Ollama is working"""
        try:
            response = self.llm.invoke("Say 'Hello' if you can hear me.")
            return True, response
        except Exception as e:
            return False, str(e)
    
    def clear_user_memory(self, user_id: str):
        """Clear conversation memory for a specific user"""
        if user_id in self.user_conversations:
            del self.user_conversations[user_id]
            return True
        return False