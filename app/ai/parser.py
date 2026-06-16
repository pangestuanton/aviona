from __future__ import annotations

import re
from datetime import datetime
from openai import OpenAI

from app.config import get_settings
from app.database.session import SessionLocal
from app.database.repository import (
    get_user_profile,
    save_chat_message,
    get_chat_history,
    save_memory,
    list_memories,
    save_timed_reminder,
)
from app.ai.prompts import get_system_prompt
from app.utils.datetime_utils import now_local, local_to_utc, format_datetime_id


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
        mem_objs = list_memories(db, user_id=user_id, limit=20)
        memories = [m.content for m in mem_objs]
        
        # Load chat history
        history = get_chat_history(db, user_id=user_id, limit=100)
        
        # Get user's local current time
        local_time = now_local(profile.timezone)
        current_local_time = f"{local_time.strftime('%Y-%m-%d %H:%M:%S')} ({format_datetime_id(local_time)})"
        
        # Construct messages payload
        system_content = get_system_prompt(mode, memories, current_local_time)
        messages = [{"role": "system", "content": system_content}]
        
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})
            
        # Add current user message
        messages.append({"role": "user", "content": message_text})
        
        # Save user message to database history
        save_chat_message(db, user_id=user_id, role="user", content=message_text)
        
        if not settings.openrouter_api_key:
            reply = "Maaf, API Key AI belum dikonfigurasi. Silakan atur OPENROUTER_API_KEY di file .env Anda."
            save_chat_message(db, user_id=user_id, role="assistant", content=reply)
            return reply
            
        try:
            client = OpenAI(
                api_key=settings.openrouter_api_key,
                base_url=settings.ai_base_url,
            )
            
            response = client.chat.completions.create(
                model=settings.ai_model,
                messages=messages,
                temperature=0.7,
                max_tokens=4096,
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
            
            # Extract timed reminders from reply: format [REMINDER: YYYY-MM-DD HH:MM:SS | message]
            reminder_matches = re.finditer(r'\[REMINDER:\s*([^|]+?)\s*\|\s*(.*?)\]', reply, re.IGNORECASE | re.DOTALL)
            for match in reminder_matches:
                time_str = match.group(1).strip()
                reminder_msg = match.group(2).strip()
                try:
                    local_dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                    utc_dt = local_to_utc(local_dt, profile.timezone)
                    if utc_dt:
                        save_timed_reminder(db, user_id=user_id, remind_at_utc=utc_dt, message=reminder_msg)
                except Exception as e:
                    print(f"Failed to parse reminder time '{time_str}': {e}")
            
            # Strip all reminder blocks from the user-facing response
            reply = re.sub(r'\[REMINDER:\s*[^|]+?\s*\|\s*.*?\]', '', reply, flags=re.IGNORECASE | re.DOTALL).strip()
            
            # Save assistant reply to database history
            save_chat_message(db, user_id=user_id, role="assistant", content=reply)
            
            return reply
            
        except Exception as exc:
            print(f"Error in generate_chat_response: {exc}")
            key_str = str(settings.openrouter_api_key) if settings.openrouter_api_key else ""
            if len(key_str) > 8:
                sanitized_key = f"{key_str[:5]}...{key_str[-5:]} (len={len(key_str)})"
            else:
                sanitized_key = f"{key_str} (len={len(key_str)})"
            
            fallback_reply = (
                f"Duh, maaf ya... Koneksi AI-ku sedang terganggu. Coba kirim pesan lagi sebentar lagi!\n\n"
                f"<b>Detail Error:</b> {str(exc)}\n"
                f"<b>Sanitized Key:</b> <code>{sanitized_key}</code>\n"
                f"<b>Base URL:</b> <code>{settings.ai_base_url}</code>\n"
                f"<b>Model:</b> <code>{settings.ai_model}</code>"
            )
            save_chat_message(db, user_id=user_id, role="assistant", content=fallback_reply)
            return fallback_reply
