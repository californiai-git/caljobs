import base64
from email.mime.text import MIMEText
import logging
from .auth_utils import get_service

logger = logging.getLogger(__name__)

def check_inbox(query: str) -> list[dict]:
    """
    Searches Gmail for messages matching the query and returns parsed job info.
    """
    logger.info(f"Checking Gmail inbox for query: {query}")
    service = get_service('gmail', 'v1')
    
    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages', [])
    
    parsed_jobs = []
    if not messages:
        logger.info("No new matching emails found.")
        return parsed_jobs

    for msg in messages:
        # Fetch full message
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        
        # Parse headers
        headers = msg_data.get('payload', {}).get('headers', [])
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "Unknown Subject")
        sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown Sender")
        
        # We extract snippet for the description for now
        snippet = msg_data.get('snippet', '')
        
        # Very naive mapping for email to job dict
        parsed_jobs.append({
            "title": subject,
            "company": sender.split('<')[0].strip() if '<' in sender else sender,
            "description": snippet,
            "source": "gmail",
            "is_remote": "remote" in snippet.lower() or "remote" in subject.lower(),
            "location": "Email Source" # Ideally parse location from body
        })
        
    return parsed_jobs

def send_summary_email(to_address: str, valid_jobs: list, emails: list):
    """
    Sends a summary email using the Gmail API.
    """
    logger.info(f"Sending summary email to {to_address}...")
    service = get_service('gmail', 'v1')
    
    job_count = len(valid_jobs)
    body = f"Hello,\n\nThe Daily Job Search Agent has completed its run.\n\n"
    body += f"Total Valid Jobs Found: {job_count}\n"
    body += "Please check your Google Drive daily folder for the tailored CVs and full details.\n\nBest,\nYour Automated Agent"
    
    message = MIMEText(body)
    message['to'] = to_address
    message['subject'] = f"Daily Job Search Summary: {job_count} Jobs Found"
    
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    
    try:
        service.users().messages().send(userId='me', body={'raw': raw}).execute()
        logger.info("Summary email sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
