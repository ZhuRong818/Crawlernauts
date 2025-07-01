from __future__ import annotations
from dotenv import load_dotenv,find_dotenv
load_dotenv(find_dotenv()) # ← make sure we load root‐level .env first

import os
import logging
import requests
from typing import List, Dict, Optional
from flask import Blueprint, request, jsonify, session, current_app
from models import db, ChatMessage
ai_bp = Blueprint("ai", __name__, url_prefix="/ai")

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL=os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()

LOGGER = logging.getLogger(__name__)

@ai_bp.post("/suggest")
def suggest():
    data= request.get_json(silent=True) or {}
    user_input = (data.get("message") or "").strip()
    if not user_input:
        return jsonify(error="Empty message"), 400
    uid= session.get("user_id")
    history= _load_history(uid) + [{"role": "user", "content": user_input}]
## msg need be precise
    system_msg = {
        "role": "system",
        "content": (
            "You are a concise AI assistant that gives plain-text answers "
            "about web-crawling and scraping.\n\n"
            "Write in short paragraphs separated by a blank line.\n"
            "Do NOT use any Markdown syntax.\n"
            "If the user asks off-topic, steer them back to web-crawling."
        )
    }


def _load_history(uid: Optional[int]) -> List[Dict]:
    if uid:
        msgs=(
            ChatMessage.query
                       .filter_by(user_id=uid)
                       .order_by(ChatMessage.id.desc())
                       .limit(200)
                       .all()
        )
        return[{"role": m.role, "content": m.content} for m in reversed(msgs)]
    return session.get("chat_history", [])[-100:]


def _save_to_history(uid: Optional[int], role: str, content: str) -> None:
    if uid:
        db.session.add(ChatMessage(user_id=uid, role=role, content=content))
        db.session.commit()
    else:
        hist = session.setdefault("chat_history", [])
        hist.append({"role": role, "content": content})
        session["chat_history"] = hist[-100:]
    
    
    try:
        if mock_mode():
            ai_reply = f"(mock) I received: {user_input[:60]}…"
        else:
            resp = requests.post(
                DEEPSEEK_API_URL,
                json={
                    "model":       DEEPSEEK_MODEL,
                    "messages":    messages,
                    "temperature": 0.7,
                    "max_tokens":  400
                },
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_KEY}",
                    "Content-Type":  "application/json"
                },
                timeout=30
            )
            resp.raise_for_status()
            ai_reply = resp.json()["choices"][0]["message"]["content"].strip()
    except requests.HTTPError as e:
        LOGGER.error("DeepSeek error: %s • body=%s", e, e.response.text)
        return jsonify(error="AI backend error"), 500
    except Exception as e:
        LOGGER.exception("AI assistant failure")
        return jsonify(error=str(e)), 500

    _save_to_history(uid, "user", user_input)
    _save_to_history(uid, "assistant", ai_reply)
    return jsonify(reply=ai_reply)
@ai_bp.get("/history")
def history():
    uid = session.get("user_id")
    return jsonify(history=_load_history(uid))
@ai_bp.post("/history/clear")
def clear_history():
    uid=session.get("user_id")
    if uid:
        ChatMessage.query.filter_by(user_id=uid).delete()
        db.session.commit()
    session["chat_history"] = []
    return jsonify(msg="cleared")
