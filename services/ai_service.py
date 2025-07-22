import os
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from config.database import get_db_connection
from psycopg2.extras import RealDictCursor
import json

class AIService:
    def __init__(self):
        # Initialize Ollama
        self.llm = Ollama(
            model=os.getenv("OLLAMA_MODEL", "llama3.2"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        )
        
        # Create prompt template
        self.prompt_template = PromptTemplate(
            input_variables=["contacts", "notes", "query"],
            template="""
You are an AI assistant for a CRM system. Answer questions based ONLY on the user's contacts and notes below.

CONTACTS:
{contacts}

NOTES:
{notes}

Question: {query}

Please provide a helpful answer based only on the information above. If you cannot answer with the given data, say so.
"""
        )
    
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
    
    def ask_question(self, user_id: str, question: str):
        """Ask AI a question about user's contacts and notes"""
        try:
            # Get user's data
            contacts, notes = self.get_user_data(user_id)
            
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
            
            # Create the prompt
            contacts_text = '\n'.join(contacts_formatted) if contacts_formatted else "No contacts found."
            notes_text = '\n'.join(notes_formatted) if notes_formatted else "No notes found."
            
            prompt = self.prompt_template.format(
                contacts=contacts_text,
                notes=notes_text, 
                query=question
            )
            
            # Get AI response
            response = self.llm.invoke(prompt)
            
            return {
                "success": True,
                "response": response,
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
    
    def test_connection(self):
        """Test if Ollama is working"""
        try:
            response = self.llm.invoke("Say 'Hello' if you can hear me.")
            return True, response
        except Exception as e:
            return False, str(e)