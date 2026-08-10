import os
import tempfile
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from backend.cold_email_agent import ColdEmailAgent

app = FastAPI(title='Cold Email Automation Backend')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/health')
def health_check():
    return {'status': 'ok'}


@app.post('/process')
async def process_excel(
    excel_file: UploadFile = File(...),
    sender_email: str = Form(None),
    smtp_password: str = Form(None),
    gmail_credentials: str = Form(None),
    max_emails: int = Form(None),
    rate_limit: float = Form(2.0),
    use_gmail_api: bool = Form(False),
    send_now: bool = Form(False),
):
    if excel_file.content_type not in (
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/octet-stream',
    ):
        raise HTTPException(status_code=400, detail='Upload an .xlsx file')

    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
        temp_file.write(await excel_file.read())
        temp_path = temp_file.name

    try:
        agent = ColdEmailAgent(
            excel_path=temp_path,
            sender_email=sender_email,
            smtp_password=smtp_password,
            gmail_credentials=gmail_credentials,
            rate_limit=rate_limit,
        )

        results = agent.process_and_send_emails(
            max_emails=max_emails,
            dry_run=not send_now,
            use_gmail_api=use_gmail_api,
        )

        return {
            'dry_run': not send_now,
            'use_gmail_api': use_gmail_api,
            'results': results,
        }
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass
