import os.path
import pickle # Using pickle for token storage as per common Google examples

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import base64 # For decoding message body
import email # For parsing raw email data if you fetch 'raw' format
import argparse # For command-line interface

# If modifying these SCOPES, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly'] # Readonly access is sufficient for listing labels
CREDENTIALS_FILENAME = os.path.join(os.path.dirname(__file__), 'config', 'credentials.json') # TODO: 
TOKEN_FILENAME = os.path.join(os.path.dirname(__file__), 'token.pickle') # Store token in the same dir as the script
 
class MessageAccesor:
    def __init__(self):
        if os.path.exists(CREDENTIALS_FILENAME):
            self.flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILENAME, SCOPES)
            # Set a default redirect URI if not present, common for installed apps
            if not self.flow.redirect_uri:
                self.flow.redirect_uri = 'http://localhost:0' # Or a specific port
        else:
            print(f"Error: Credentials file not found at {CREDENTIALS_FILENAME}")


    def get_gmail_service(self):
        """Shows basic usage of the Gmail API.
        Lists the user's Gmail labels.
        """
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        # Note: Google's newer examples might use token.json.
        # If you prefer token.json, you can adapt the credential saving/loading.
        # token_file = 'token.pickle' # Old way

        if os.path.exists(TOKEN_FILENAME):
            with open(TOKEN_FILENAME, 'rb') as token:
                creds = pickle.load(token)

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Failed to refresh token: {e}")
                    print("Attempting to re-authenticate...")
                    creds = None # Force re-authentication
            if not creds: # If refresh failed or no creds at all
                try:
                    # Ensure redirect_uris in credentials.json includes "http://localhost:port"
                    # or "urn:ietf:wg:oauth:2.0:oob" for installed apps.
                    # The port for localhost can be any available port.
                    # For this example, let's assume it will use a default or prompt.
                    creds = self.flow.run_local_server(port=0) # port=0 finds a free port
                except Exception as e:
                    print(f"Error during authentication flow: {e}")
                    print("Please ensure your credentials.json is configured correctly for an Installed App.")
                    print("The redirect URI might need to be 'http://localhost:PORT' or 'urn:ietf:wg:oauth:2.0:oob'.")
                    return None
            # Save the credentials for the next run
            with open(TOKEN_FILENAME, 'wb') as token:
                pickle.dump(creds, token)
                print(f"Token saved to {TOKEN_FILENAME}")

        try:
            service = build('gmail', 'v1', credentials=creds)
            return service
        except HttpError as error:
            print(f'An API error occurred: {error}')
            # Details for common errors
            if error.resp.status == 403:
                print("This might be due to the Gmail API not being enabled in your Google Cloud project.")
            elif error.resp.status == 401:
                print("This might be an issue with your OAuth token. Try deleting token.pickle and re-running.")
            return None
        except Exception as e:
            print(f"An unexpected error occurred while building the service: {e}")
            return None

def list_labels(service):
    """Lists all Gmail labels for the user."""
    try:
        print("\nFetching Gmail labels...")
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        if not labels:
            print('No labels found.')
        else:
            print('Labels:')
            for label in labels:
                print(f"- {label['name']} (ID: {label['id']})")
    except HttpError as error:
        print(f'An API error occurred while listing labels: {error}')

def list_messages_cmd(service, label_ids, max_results, query):
    """Lists messages based on provided criteria."""
    try:
        print(f"\nFetching messages (max: {max_results}, labels: {label_ids}, query: '{query or 'N/A'}')...")
        list_response = service.users().messages().list(
            userId='me',
            labelIds=label_ids,
            maxResults=max_results,
            q=query
        ).execute()
        messages = list_response.get('messages', [])

        if not messages:
            print("No messages found matching your criteria.")
        else:
            print("Found Messages (ID and Thread ID):")
            for message_stub in messages:
                print(f"  ID: {message_stub['id']}, Thread ID: {message_stub['threadId']}")
            print("\nUse 'get-message <ID>' to fetch full details of a message.")
    except HttpError as error:
        print(f'An API error occurred while listing messages: {error}')

def get_message_detail(service, message_id, msg_format):
    """Gets and displays a specific message."""
    try:
        print(f"\nFetching message ID: {message_id} with format: {msg_format}...")
        message = service.users().messages().get(userId='me', id=message_id, format=msg_format).execute()

        print(f"Message ID: {message.get('id')}")
        print(f"Thread ID: {message.get('threadId')}")
        print(f"Snippet: {message.get('snippet', 'N/A')}")

        if 'labelIds' in message:
            print(f"Labels: {', '.join(message['labelIds'])}")

        if msg_format == 'raw':
            if 'raw' in message:
                raw_email_data = base64.urlsafe_b64decode(message['raw'].encode('ASCII'))
                print("\n--- Raw Email Data (decoded) ---")
                email_message = email.message_from_bytes(raw_email_data)
                print(f"Subject (from raw): {email_message['subject']}")
                print(f"From (from raw): {email_message['from']}")
                print(f"To (from raw): {email_message['to']}")

                if email_message.is_multipart():
                    for part in email_message.walk():
                        ctype = part.get_content_type()
                        cdispo = str(part.get('Content-Disposition'))
                        if ctype == 'text/plain' and 'attachment' not in cdispo:
                            body = part.get_payload(decode=True)
                            print("\n--- Plain Text Body (from raw) ---")
                            print(body.decode('utf-8', errors='replace'))
                            break
                else:
                    body = email_message.get_payload(decode=True)
                    print("\n--- Body (from raw) ---")
                    print(body.decode('utf-8', errors='replace'))
            else:
                print("Raw data not found in response.")
        elif msg_format == 'full' or msg_format == 'metadata': # 'metadata' also includes payload headers
            payload = message.get('payload')
            if payload:
                headers = payload.get('headers', [])
                print("\n--- Headers ---")
                for header in headers:
                    print(f"{header['name']}: {header['value']}")

                if msg_format == 'full': # Only parse body if 'full' format requested
                    print("\n--- Message Body (from 'full' format) ---")
                    parts = payload.get('parts')
                    if parts: # Multipart message
                        for part in parts:
                            if part.get('mimeType') == 'text/plain':
                                body_data = part.get('body', {}).get('data')
                                if body_data:
                                    text = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='replace')
                                    print("Plain Text Part:\n", text)
                                    break # Show first plain text part
                            # Could add handling for text/html here too
                    elif payload.get('body', {}).get('data'): # Non-multipart message
                        body_data = payload.get('body', {}).get('data')
                        if body_data:
                            text = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='replace')
                            print("Body:\n", text)
                    else:
                        print("No decodable body found in 'full' format payload.")
            else:
                print("Payload not found in response.")

    except HttpError as error:
        print(f'An API error occurred while fetching message {message_id}: {error}')
    except Exception as e:
        print(f"An unexpected error occurred while processing message {message_id}: {e}")


def main():
    """
    Main function to parse command-line arguments and interact with the Gmail API.
    """
    parser = argparse.ArgumentParser(description="A command-line tool to interact with your Gmail account.")
    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)

    # Subparser for listing labels
    parser_list_labels = subparsers.add_parser("list-labels", help="List all Gmail labels.")

    # Subparser for listing messages
    parser_list_messages = subparsers.add_parser("list-messages", help="List messages.")
    parser_list_messages.add_argument("--label-ids", nargs='*', default=['INBOX'], help="Space-separated list of label IDs to filter by (e.g., INBOX, SENT, SPAM). Default: INBOX")
    parser_list_messages.add_argument("--max-results", type=int, default=10, help="Maximum number of messages to return. Default: 10")
    parser_list_messages.add_argument("--query", "-q", type=str, help="Gmail search query (e.g., 'from:user@example.com is:unread').")

    # Subparser for getting a specific message
    parser_get_message = subparsers.add_parser("get-message", help="Get a specific message by ID.")
    parser_get_message.add_argument("message_id", help="The ID of the message to retrieve.")
    parser_get_message.add_argument("--format", choices=['full', 'metadata', 'raw', 'minimal'], default='metadata', help="Format of the message to retrieve. Default: metadata")

    args = parser.parse_args()

    print("Attempting to connect to Gmail API...")
    msg_accessor = MessageAccesor()
    service = msg_accessor.get_gmail_service()

    if not service:
        print("Failed to get Gmail service. Exiting.")
        return

    if args.command == "list-labels":
        list_labels(service)
    elif args.command == "list-messages":
        list_messages_cmd(service, args.label_ids, args.max_results, args.query)
    elif args.command == "get-message":
        get_message_detail(service, args.message_id, args.format)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
