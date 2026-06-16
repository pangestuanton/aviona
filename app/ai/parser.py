from __future__ import annotations

import re
from openai import OpenAI

from app.config import get_settings
from app.database.session import SessionLocal
from app.database.repository import (
    get_user_profile,
    save_chat_message,
    get_chat_history,
    save_memory,
    list_memories,
)
from app.ai.prompts import get_system_prompt


def generate_chat_response(user_id: int, message_text: str) -> str:
    """
    Generate conversational AI chat response:
    1. Retrieve user's profile tutoring mode.
    2. Load long-term facts (memories) and short-term chat logs context window.
    3. Generate response using the OpenAI-compatible client.
    4. Extract any long-term memory tags, store them, and clean response content.
    5. Save exchange to ChatMessage history.
    """
    settings = get_settings()
    
    with SessionLocal() as db:
        profile = get_user_profile(db, user_id)
        mode = profile.mode
        
        # Load long term memories
        mem_objs = list_memories(db, user_id=user_id, limit=8)
        memories = [m.content for m in mem_objs]
        
        # Load chat history
        history = get_chat_history(db, user_id=user_id, limit=10)
        
        # Construct messages payload
        system_content = get_system_prompt(mode, memories)
        messages = [{"role": "system", "content": system_content}]
        
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})
            
        # Add current user message
        messages.append({"role": "user", "content": message_text})
        
        # Save user message to database history
        save_chat_message(db, user_id=user_id, role="user", content=message_text)
        
        if not settings.openai_api_key:
            reply = "Maaf, API Key AI belum dikonfigurasi. Silakan atur OPENAI_API_KEY di file .env Anda."
            save_chat_message(db, user_id=user_id, role="assistant", content=reply)
            return reply
            
        try:
            client = OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.ai_base_url,
            )
            
            response = client.chat.completions.create(
                model=settings.ai_model,
                messages=messages,
                temperature=0.7,
            )
            
            reply = response.choices[0].message.content or ""
            reply = reply.strip()
            
            # Extract long term memories from reply: format [MEMORY: statement]
            memory_match = re.search(r'\[MEMORY:\s*(.*?)\]', reply, re.IGNORECASE | re.DOTALL)
            if memory_match:
                extracted_fact = memory_match.group(1).strip()
                if extracted_fact:
                    save_memory(db, user_id=user_id, content=extracted_fact, category="user_info", importance=1)
                # Strip the memory block from the user-facing response
                reply = re.sub(r'\[MEMORY:\s*.*?\]', '', reply, flags=re.IGNORECASE | re.DOTALL).strip()
            
            # Save assistant reply to database history
            save_chat_message(db, user_id=user_id, role="assistant", content=reply)
            
            return reply
            
        except Exception as exc:
            print(f"Error in generate_chat_response: {exc}")
            fallback_reply = "Duh, maaf ya... Koneksi AI-ku sedang terganggu. Coba kirim pesan lagi sebentar lagi!"
            save_chat_message(db, user_id=user_id, role="assistant", content=fallback_reply)
            return fallback_reply
