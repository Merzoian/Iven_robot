import json
import os
import re


def clean_phrase(text, max_len=80):
    text = " ".join((text or "").strip().split())
    text = re.sub(r"[^\w\s'\-]", "", text)
    return text[:max_len].strip()


def save_session_memory(session_memory, memory_lock, memory_path):
    with memory_lock:
        payload = {
            "name": session_memory.get("name"),
            "likes": session_memory.get("likes", [])[-20:],
            "facts": session_memory.get("facts", [])[-40:],
        }
    try:
        with open(memory_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception as e:
        print(f"Memory save warning: {e}")


def load_session_memory(session_memory, memory_lock, memory_path):
    if not os.path.exists(memory_path):
        return
    try:
        with open(memory_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        with memory_lock:
            session_memory["name"] = clean_phrase(data.get("name", ""), max_len=32) or None
            session_memory["likes"] = [
                clean_phrase(x, 48)
                for x in data.get("likes", [])
                if clean_phrase(x, 48)
            ][-20:]
            session_memory["facts"] = [
                clean_phrase(x, 128)
                for x in data.get("facts", [])
                if clean_phrase(x, 128)
            ][-40:]
    except Exception as e:
        print(f"Memory load warning: {e}")


def apply_memory_from_text(text, session_memory, save_callback):
    if not text:
        return

    normalized_text = " ".join(text.strip().split())
    lower_text = normalized_text.lower()
    changed = False

    name_match = re.search(
        r"\b(?:my name is|i am|i'm)\s+([a-zA-Z][a-zA-Z '\-]{0,30})",
        normalized_text,
        re.IGNORECASE,
    )
    if name_match:
        name = clean_phrase(name_match.group(1), 32)
        if name and name != session_memory.get("name"):
            session_memory["name"] = name
            changed = True

    for like_match in re.finditer(r"\bi like ([^.,!?]{1,40})", lower_text):
        thing = clean_phrase(like_match.group(1), 48).lower()
        if thing and thing not in session_memory["likes"]:
            session_memory["likes"].append(thing)
            session_memory["likes"] = session_memory["likes"][-20:]
            changed = True

    remember_match = re.search(
        r"\b(?:remember that|please remember|note that)\s+([^.!?]{3,140})",
        normalized_text,
        re.IGNORECASE,
    )
    if remember_match:
        fact = clean_phrase(remember_match.group(1), 128)
        if fact and fact not in session_memory["facts"]:
            session_memory["facts"].append(fact)
            session_memory["facts"] = session_memory["facts"][-40:]
            changed = True

    favorite_match = re.search(r"\bmy favorite ([a-z ]{2,20}) is ([^.,!?]{1,30})", lower_text)
    if favorite_match:
        category = clean_phrase(favorite_match.group(1), 24).lower()
        value = clean_phrase(favorite_match.group(2), 40).lower()
        fact = f"favorite {category} is {value}"
        if fact not in session_memory["facts"]:
            session_memory["facts"].append(fact)
            session_memory["facts"] = session_memory["facts"][-40:]
            changed = True

    if changed:
        save_callback()
