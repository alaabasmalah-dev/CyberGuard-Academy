import json
from typing import Optional
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/mentor", tags=["mentor"])

# Simple keyword → hint mapping. This is NOT a real AI model — it's a
# lightweight placeholder so the chat feature works end-to-end today.
# Swap this out later for a call to an LLM API (OpenAI/Anthropic/etc.)
# once you have an API key — you'd just replace _pick_answer() below and
# keep streaming the response the same way.
_HINTS = {
    "xss": "XSS (Cross-Site Scripting) happens when untrusted input is rendered as HTML/JS in a browser. Look for places where user input is reflected back into the page without escaping.",
    "sql": "SQL injection happens when user input is concatenated directly into a SQL query. Try thinking about what happens if the input contains a quote character.",
    "csrf": "CSRF tricks a logged-in user's browser into making a request they didn't intend. Check whether the app validates a per-session token on state-changing requests.",
    "arp": "ARP poisoning works by sending forged ARP replies so traffic gets routed through the attacker's machine instead of the real gateway.",
    "mitm": "A Man-in-the-Middle attack intercepts communication between two parties. Think about how you'd verify the identity of who you're really talking to.",
    "wireshark": "Wireshark captures and inspects network packets. Start by filtering for the protocol you're investigating (e.g. `http`, `tcp.port == 80`).",
    "flag": "I can't give you the flag or a full solution — that's against the lab rules. I can help you understand the underlying concept instead.",
}

_DEFAULT_HINT = (
    "Good question! Try breaking the problem into smaller steps: what is the "
    "attacker's goal, what input can they control, and what does the "
    "vulnerable code do with that input? Re-read the lab's task description "
    "for a clue about which of those three matters most here."
)


class MentorAskRequest(BaseModel):
    question: str
    hintsUsed: Optional[int] = 0


def _pick_answer(question: str) -> str:
    question_lower = question.lower()
    for keyword, hint in _HINTS.items():
        if keyword in question_lower:
            return hint
    return _DEFAULT_HINT


def _pick_level(hints_used: int) -> int:
    # 1 Concept -> 2 Hint -> 3 Guided -> 4 Blocked, escalating with usage.
    return min(4, 1 + (hints_used or 0) // 2)


@router.post("/ask")
def ask_mentor(payload: MentorAskRequest):
    answer = _pick_answer(payload.question)
    level = _pick_level(payload.hintsUsed or 0)

    def event_stream():
        chunk = {"content": answer, "done": False}
        yield f"data: {json.dumps(chunk)}\n\n"
        done_chunk = {"content": "", "done": True, "responseLevel": level}
        yield f"data: {json.dumps(done_chunk)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
