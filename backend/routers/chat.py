from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import campaign_service
from ..ai import GeminiProvider
from ..config import GEMINI_API_KEY
from ..database import get_db
from ..models import User
from ..security import get_current_user

router = APIRouter(prefix='/api/chat', tags=['chat'])

MODEL = 'gemini-3.5-flash-lite'

SYSTEM_PROMPT = (
    'You are PulseBoard Assistant, a friendly in-app help chatbot for PulseBoard, a cold-email '
    'automation SaaS. Help the user understand and use the app. Keep answers concise, practical, '
    'and step-based where useful. You know the following about the app:\n'
    '- The core flow: import recipients (Excel/CSV; only the Email column is required, other columns '
    'like Company Name / Website / Job Role are optional), add an AI model with your own API key '
    '(or upgrade to Pro for the managed model), create an AI agent that uses that model, connect an '
    'email account (Google OAuth or SMTP with an app password), create a campaign, generate '
    'personalized emails, review/approve them, then launch. The scheduler sends them automatically.\n'
    '- Email accounts: every user manages their own accounts (Google OAuth or SMTP). Emails are always '
    'sent from the account the user selects for the campaign — never from a shared project address. '
    'One account can be the default and is preselected in the campaign wizard and manual compose. '
    'Accounts are managed under Profile > Email Accounts or the Email Accounts page (add, test, set '
    'default, disconnect, delete).\n'
    '- Campaigns: pick recipients, an AI agent, a sending account, and a schedule. Options include '
    'send window (start/end time), active days, hourly sending speed (Free plan max 10/hour, Pro up '
    'to 50/hour, minimum 4/hour), an optional daily cap, and an optional "stop after N sends" '
    'auto-stop limit. Generation is async: the campaign goes generating -> review_required, then you '
    'approve emails and launch.\n'
    '- Controls: Launch starts sending; Stop pauses; Resume continues; Cancel stops permanently. '
    'The worker runs inside the backend and respects schedule + rate limits.\n'
    '- Email History keeps a full snapshot of every email (generated/scheduled/sent/failed), the '
    'sender account, recipient, subject, and body. Failed emails can be retried manually.\n'
    '- AI Models: add a model with your own API key (OpenAI, Anthropic, or Gemini). The managed '
    'default model is a Pro feature. AI Agents configure tone, length, and research behavior.\n'
    '- Billing: Free vs Pro plans. Pro unlocks the managed AI model and higher sending speeds.\n'
    'If the user asks something unrelated to PulseBoard, briefly say you only help with using this app.\n'
)


class ChatIn(BaseModel):
    message: str
    history: list = []


@router.post('')
def chat(payload: ChatIn, user: User = Depends(get_current_user)):
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail='The assistant is not configured yet (GEMINI_API_KEY missing on the server).',
        )
    message = (payload.message or '').strip()
    if not message:
        raise HTTPException(status_code=400, detail='Message is required')
    history = payload.history or []
    turns = []
    for h in history[-8:]:
        role = 'user' if h.get('role') == 'user' else 'assistant'
        text = (h.get('content') or '').strip()
        if text:
            turns.append(f'{role}: {text}')
    prompt = SYSTEM_PROMPT + '\n\nConversation so far:\n' + '\n'.join(turns) + '\n\nuser: ' + message
    provider = GeminiProvider()
    try:
        reply = provider.complete(prompt, MODEL, 600, 0.5)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Assistant call failed: {exc}')
    if not reply:
        raise HTTPException(status_code=502, detail='The assistant returned an empty response. Check GEMINI_API_KEY.')
    return {'reply': reply, 'model': MODEL}