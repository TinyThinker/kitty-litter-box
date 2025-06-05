import os.path
import pickle # Using pickle for token storage as per common Google examples

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import base64 # For decoding message body
import email # For parsing raw email data if you fetch 'raw' format

# If modifying these SCOPES, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly'] # Readonly access is sufficient for listing labels
CREDENTIALS_FILENAME = os.path.join(os.path.dirname(__file__), 'config', 'credentials.json') # TODO: 
TOKEN_FILENAME = os.path.join(os.path.dirname(__file__), 'token.pickle') # Store token in the same dir as the script
 
class MessageAccesor:
    def __init__(self):
        if os.path.exists(CREDENTIALS_FILENAME):
            self.flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILENAME, SCOPES)
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

def main():
    """
    Main function to get the Gmail service, list labels, and fetch messages.
    """
    print("Attempting to connect to Gmail API...")
    msg_accessor = MessageAccesor() # Corrected variable name
    service = msg_accessor.get_gmail_service()

    if not service:
        print("Failed to get Gmail service. Exiting.")
        return

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

        print("\nFetching messages (first 5 from INBOX)...")
        # List messages in the INBOX, get up to 5
        # You can use q for query, like 'from:someone@example.com' or 'is:unread'
        list_response = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=5).execute()
        messages = list_response.get('messages', [])

        if not messages:
            print("No messages found in INBOX.")
        else:
            print("Messages:")
            for message_stub in messages:
                msg_id = message_stub['id']
                try:
                    # Get the full message
                    # 'format' can be 'full', 'metadata', 'raw', 'minimal'
                    # 'full' gives parsed payload, headers, etc.
                    # 'raw' gives the raw, base64url-encoded email
                    # 'metadata' gives only headers
                    message = service.users().messages().get(userId='me', id=msg_id, format='metadata').execute() # Using metadata for brevity
                    
                    # Extract subject from headers
                    subject = "No Subject"
                    snippet = message.get('snippet', 'No snippet available.')
                    headers = message.get('payload', {}).get('headers', [])
                    for header in headers:
                        if header['name'].lower() == 'subject':
                            subject = header['value']
                            break
                    
                    print(f"\n  ID: {msg_id}")
                    print(f"  Subject: {subject}")
                    print(f"  Snippet: {snippet}")

                    # If you fetched with format='full', you could parse the body:
                    # payload = message.get('payload')
                    # if payload:
                    #     parts = payload.get('parts')
                    #     if parts:
                    #         for part in parts:
                    #             if part.get('mimeType') == 'text/plain':
                    #                 body_data = part.get('body', {}).get('data')
                    #                 if body_data:
                    #                     text = base64.urlsafe_b64decode(body_data).decode('utf-8')
                    #                     print(f"  Body (Plain Text):\n{text[:200]}...") # Print first 200 chars
                    #                     break
                    #             elif part.get('mimeType') == 'text/html':
                    #                 # Handle HTML part similarly if needed
                    #                 pass
                    #     elif payload.get('body', {}).get('data'): # For non-multipart messages
                    #         body_data = payload.get('body', {}).get('data')
                    #         if body_data:
                    #             text = base64.urlsafe_b64decode(body_data).decode('utf-8')
                    #             print(f"  Body (Plain Text):\n{text[:200]}...") # Print first 200 chars


                except HttpError as error:
                    print(f'An API error occurred while fetching message {msg_id}: {error}')
                except Exception as e:
                    print(f"An unexpected error occurred while processing message {msg_id}: {e}")


    except HttpError as error:
        print(f'An API error occurred: {error}')
        if "accessNotConfigured" in str(error) or "User Rate Limit Exceeded" in str(error) :
             print("Ensure the Gmail API is enabled in your Google Cloud project.")
             print("Also, check API quotas if you've made many requests.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == '__main__':
    main()
