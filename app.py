import os
import tempfile
import logging
from flask import Flask, request, render_template, redirect, url_for, flash
from werkzeug.utils import secure_filename
from cold_email_agent import ColdEmailAgent

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger('cold_email_ui')

ALLOWED_EXTENSIONS = {'xlsx'}
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'change-this-secret')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/process', methods=['POST'])
def process():
    if 'excel_file' not in request.files:
        flash('Please upload an Excel file (.xlsx).', 'error')
        return redirect(url_for('index'))

    file = request.files['excel_file']
    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('index'))

    if not allowed_file(file.filename):
        flash('Only .xlsx files are supported.', 'error')
        return redirect(url_for('index'))

    sender_email = request.form.get('sender_email', '').strip() or None
    smtp_password = request.form.get('smtp_password', '').strip() or None
    gmail_credentials = request.form.get('gmail_credentials', '').strip() or None
    max_emails = request.form.get('max_emails', '').strip()
    rate_limit = request.form.get('rate_limit', '').strip()
    use_gmail_api = request.form.get('use_gmail_api') == 'on'
    send_now = request.form.get('send_now') == 'on'

    try:
        max_emails = int(max_emails) if max_emails else None
    except ValueError:
        max_emails = None

    try:
        rate_limit = float(rate_limit) if rate_limit else 2.0
    except ValueError:
        rate_limit = 2.0

    filename = secure_filename(file.filename)
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'temp_{filename}')
    file.save(temp_path)

    agent = ColdEmailAgent(
        excel_path=temp_path,
        sender_email=sender_email,
        smtp_password=smtp_password,
        gmail_credentials=gmail_credentials,
        rate_limit=rate_limit
    )

    dry_run = not send_now
    if use_gmail_api and not gmail_credentials:
        flash('Gmail API requires a path to credentials JSON.', 'error')
        return redirect(url_for('index'))

    try:
        review_queue = agent.process_and_send_emails(
            max_emails=max_emails,
            dry_run=dry_run,
            use_gmail_api=use_gmail_api,
            review_queue_path=None
        )
    except Exception as exc:
        logger.exception('Processing failed')
        flash(f'Failed to process file: {exc}', 'error')
        return redirect(url_for('index'))
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass

    return render_template(
        'results.html',
        review_queue=review_queue,
        dry_run=dry_run,
        send_now=send_now,
        use_gmail_api=use_gmail_api
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
