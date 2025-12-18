import os.path
import base64
import time
from tqdm import tqdm  # The progress bar library
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from langchain_ollama import ChatOllama

# --- ⚙️ USER SETTINGS ---
EMAILS_TO_PROCESS = 500  # High volume!
ARCHIVE_SPAM = True      # Set to False to test safely first
MARK_AS_READ = True

CATEGORIES = {
    "Important": "High priority, personal emails, work, real humans, job offers.",
    "Finance": "Receipts, bank notifications, bills, invoices.",
    "Newsletters": "Marketing, weekly digests, substack, promotional offers.",
    "Unnecessary": "Spam, cold outreach, automated notifications, 'no-reply' updates."
}

# Setup Llama 3.2
llm = ChatOllama(model="llama3.2", temperature=0)
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def authenticate_gmail():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def get_or_create_labels(service):
    # (Same as before, simplified for brevity)
    existing_labels = service.users().labels().list(userId='me').execute()
    existing_names = {l['name']: l['id'] for l in existing_labels['labels']}
    label_map = {}
    for name in CATEGORIES.keys():
        full_name = f"AI/{name}"
        if full_name in existing_names:
            label_map[name] = existing_names[full_name]
        else:
            body = {'name': full_name, 'labelListVisibility': 'labelShow', 'messageListVisibility': 'show'}
            created = service.users().labels().create(userId='me', body=body).execute()
            label_map[name] = created['id']
    return label_map

def clean_body(payload):
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
            if 'parts' in part:
                return clean_body(part)
    elif 'body' in payload and 'data' in payload['body']:
        return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
    return ""

def analyze_email(sender, subject, body):
    snippet = body[:600].replace("\n", " ")
    prompt = f"""
    Classify this email into exactly ONE category: {list(CATEGORIES.keys())}.
    Sender: {sender}
    Subject: {subject}
    Body: {snippet}
    Reply ONLY with the category word.
    """
    try:
        response = llm.invoke(prompt)
        category = response.content.strip()
        for key in CATEGORIES.keys():
            if key in category: return key
        return "Unnecessary"
    except:
        return "Unnecessary"

def main():
    print("🚀 Starting Batch Processor (500 Emails)...")
    service = authenticate_gmail()
    label_map = get_or_create_labels(service)
    
    # 1. Fetching the list (Fast)
    print(f"📥 Downloading list of {EMAILS_TO_PROCESS} emails...")
    results = service.users().messages().list(
        userId='me', 
        labelIds=['INBOX', 'UNREAD'], 
        maxResults=EMAILS_TO_PROCESS
    ).execute()
    
    messages = results.get('messages', [])
    if not messages:
        print("🎉 No unread emails found!")
        return

    print(f"✅ Found {len(messages)} emails. Starting AI Processing...")
    print("☕ Go grab a coffee. This will take ~40 minutes.")

    # 2. Processing with Progress Bar (Slow)
    # tqdm creates the visual bar: [=====>      ] 45/500
    for msg in tqdm(messages, desc="Analyzing Inbox", unit="email"):
        try:
            txt = service.users().messages().get(userId='me', id=msg['id']).execute()
            headers = txt['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
            sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown")
            body = clean_body(txt['payload'])
            
            category = analyze_email(sender, subject, body)
            
            # Prepare Actions
            label_id = label_map[category]
            mod_body = {'addLabelIds': [label_id], 'removeLabelIds': []}
            
            if MARK_AS_READ:
                mod_body['removeLabelIds'].append('UNREAD')
            
            if ARCHIVE_SPAM and category == "Unnecessary":
                mod_body['removeLabelIds'].append('INBOX')
            
            service.users().messages().modify(userId='me', id=msg['id'], body=mod_body).execute()
            
        except Exception as e:
            # If one fails, just print error and continue. Don't crash the loop.
            continue

    print("\n✅ Batch Complete!")

if __name__ == '__main__':
    main()