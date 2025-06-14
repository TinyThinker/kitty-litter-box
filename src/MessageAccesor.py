import os.path
import pickle # Using pickle for token storage as per common Google examples

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import BatchHttpRequest  # For batch requests

import base64 # For decoding message body
import email # For parsing raw email data if you fetch 'raw' format
import argparse # For command-line interface
import json # For handling JSON string conversions

from src.config import TOKEN_FILENAME, SCOPES, CREDENTIALS_FILENAME
from src.gmail_db import GmailCacheDB
 
class MessageAccesor:
    def __init__(self):
        if os.path.exists(CREDENTIALS_FILENAME):
            self.flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILENAME, SCOPES)
            # Set a default redirect URI if not present, common for installed apps
            if not self.flow.redirect_uri:
                self.flow.redirect_uri = 'http://localhost:0' # Or a specific port
        else:
            raise FileNotFoundError(f"Credentials file not found at {CREDENTIALS_FILENAME}")
        
        self.service = None  # Initialize service as None
        self.all_messages_metadata = [] # To store metadata of all fetched messages
        # Create a database connection
        self.db = GmailCacheDB()
        
    def _get_header(self, headers, name):
        """Helper function to extract header value by name (case-insensitive)
        
        Args:
            headers (list): List of header dictionaries with 'name' and 'value' keys
            name (str): The name of the header to find
            
        Returns:
            str: The value of the header if found, None otherwise
        """
        if not headers:
            return None
            
        for header in headers:
            if header['name'].lower() == name.lower():
                return header['value']
        return None

    def get_gmail_service(self):
        """Gets or creates a Gmail API service object.
        If the service has already been created, returns the existing service.
        Otherwise, creates a new one.
        """
        # Return existing service if already created
        if self.service:
            return self.service
            
        creds = None
        if os.path.exists(TOKEN_FILENAME):
            with open(TOKEN_FILENAME, 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            # Case 1: Try refreshing expired credentials
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    # If refresh succeeds, we can continue with these credentials
                except Exception as e:
                    print(f"Failed to refresh credentials: {e}")
                    creds = None  # Invalidate credentials to trigger new auth flow
            
            # Case 2: No valid credentials available, need to run auth flow
            if not creds or not creds.valid:
                try:
                    creds = self.flow.run_local_server(port=0)  # port=0 finds a free port
                except Exception as e:
                    raise RuntimeError(f"Error during authentication flow: {e}. " 
                                      f"Please ensure your credentials.json is configured correctly.")
            
            # Save the credentials for the next run
            with open(TOKEN_FILENAME, 'wb') as token:
                pickle.dump(creds, token)
                print(f"Token saved to {TOKEN_FILENAME}")

        try:
            self.service = build('gmail', 'v1', credentials=creds)
            return self.service
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

    def list_labels(self):
        """Lists all Gmail labels for the user."""
        try:
            service = self.get_gmail_service()
            if not service:
                print("Failed to get Gmail service.")
                return
                
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

    def list_messages_cmd(self, label_ids, max_results, query):
        """Lists messages based on provided criteria."""
        try:
            service = self.get_gmail_service()
            if not service:
                print("Failed to get Gmail service.")
                return
                
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

    def get_message_detail(self, message_id, msg_format):
        """Gets and displays a specific message."""
        try:
            service = self.get_gmail_service()
            if not service:
                print("Failed to get Gmail service.")
                return
                
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
    
    def get_all_messages(self):
        """Fetches metadata for all messages in the INBOX and stores them in the database."""
        try:
            service = self.get_gmail_service()
            if not service:
                print("Failed to get Gmail service.")
                return

            print("\nFetching all message metadata from INBOX...")
            self.all_messages_metadata = []
            page_token = None
            total_messages_fetched = 0
            
            # Get a database connection
            conn = self.db.get_db_connection()
            cursor = conn.cursor()
            
            try:
                # Fetch message stubs and insert them into the database
                while True:
                    response = service.users().messages().list(
                        userId='me',
                        labelIds=['INBOX'],
                        pageToken=page_token
                    ).execute()
                    
                    messages = response.get('messages', [])
                    if messages:
                        self.all_messages_metadata.extend(messages)
                        total_messages_fetched += len(messages)
                        print(f"Fetched {len(messages)} message stubs... (Total: {total_messages_fetched})")
                        
                        # Insert or update message stubs in the database
                        stub_data = [(msg['id'], msg['threadId']) for msg in messages]
                        cursor.executemany(
                            "INSERT OR REPLACE INTO message_stubs (message_id, thread_id) VALUES (?, ?)",
                            stub_data
                        )
                        conn.commit()

                    page_token = response.get('nextPageToken')
                    if not page_token:
                        break # No more pages
                
                if not self.all_messages_metadata:
                    print("No messages found in INBOX.")
                    return
                
                print(f"\nSuccessfully fetched metadata for {total_messages_fetched} message stubs from INBOX.")
                
                # Now fetch rich metadata for messages that don't have it yet
                print("\nFetching rich metadata for messages...")
                
                # Query to find message IDs without rich metadata
                cursor.execute("""
                    SELECT s.message_id 
                    FROM message_stubs s 
                    LEFT JOIN message_rich_metadata r ON s.message_id = r.message_id 
                    WHERE r.message_id IS NULL
                """)
                
                missing_ids = [row[0] for row in cursor.fetchall()]
                
                if not missing_ids:
                    print("No new messages to fetch rich metadata for.")
                    return
                
                print(f"Need to fetch rich metadata for {len(missing_ids)} messages.")
                
                # Process in batches of 50
                BATCH_SIZE = 50
                total_processed = 0
                
                for i in range(0, len(missing_ids), BATCH_SIZE):
                    batch_ids = missing_ids[i:i + BATCH_SIZE]
                    total_processed += len(batch_ids)
                    print(f"Processing batch {i//BATCH_SIZE + 1} ({len(batch_ids)} messages, {total_processed}/{len(missing_ids)} total)")
                    
                    # Data to insert for this batch
                    rich_metadata_to_insert = []
                    
                    # Create a batch request
                    batch = service.new_batch_http_request()
                    
                    # Define a callback function for each request in the batch
                    def callback_factory(msg_id):
                        def callback(request_id, response, exception):
                            if exception:
                                print(f"Error fetching message {msg_id}: {exception}")
                                return
                                
                            # Extract metadata fields
                            snippet = response.get('snippet', '')
                            internal_date = response.get('internalDate')
                            size_estimate = response.get('sizeEstimate')
                            label_ids = json.dumps(response.get('labelIds', []))
                            
                            payload = response.get('payload', {})
                            headers = payload.get('headers', [])
                            
                            # Extract From and Subject headers
                            from_address = self._get_header(headers, 'From')
                            subject = self._get_header(headers, 'Subject')
                            
                            # Store all headers as JSON
                            payload_headers_json = json.dumps(headers)
                            
                            # Check for attachments
                            has_attachments = 0
                            attachment_filenames = []
                            
                            # Helper function to check for attachments recursively
                            def check_for_attachments(part):
                                if 'filename' in part and part['filename']:
                                    return True, part['filename']
                                
                                if 'parts' in part:
                                    for subpart in part['parts']:
                                        has_att, filename = check_for_attachments(subpart)
                                        if has_att:
                                            return True, filename
                                            
                                return False, None
                            
                            # Check payload for attachments
                            if 'parts' in payload:
                                for part in payload['parts']:
                                    has_att, filename = check_for_attachments(part)
                                    if has_att and filename:
                                        has_attachments = 1
                                        attachment_filenames.append(filename)
                            
                            # Add this message's data to our list for batch insertion
                            rich_metadata_to_insert.append((
                                msg_id,
                                snippet,
                                internal_date,
                                size_estimate,
                                from_address,
                                subject,
                                label_ids,
                                has_attachments,
                                json.dumps(attachment_filenames) if attachment_filenames else None,
                                payload_headers_json
                            ))
                            
                        return callback
                    
                    # Add each message to the batch request
                    for msg_id in batch_ids:
                        batch.add(
                            service.users().messages().get(userId='me', id=msg_id, format='metadata'),
                            callback=callback_factory(msg_id)
                        )
                    
                    # Execute the batch request
                    batch.execute()
                    
                    # Insert all the rich metadata we collected
                    if rich_metadata_to_insert:
                        cursor.executemany("""
                            INSERT OR REPLACE INTO message_rich_metadata (
                                message_id, snippet, internal_date, size_estimate, 
                                from_address, subject, label_ids_json, 
                                has_attachments, attachment_filenames_json, payload_headers_json
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, rich_metadata_to_insert)
                        conn.commit()
                        print(f"Saved rich metadata for {len(rich_metadata_to_insert)} messages.")
                    
                print(f"\nCompleted fetching rich metadata for {total_processed} messages.")
                
            finally:
                # Always close the connection
                self.db.close_connection(conn)
            
        except HttpError as error:
            print(f'An API error occurred while fetching all messages: {error}')
        except Exception as e:
            print(f"An unexpected error occurred while fetching all messages: {e}")


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

    # Subparser for getting all messages metadata from INBOX
    parser_get_all_messages = subparsers.add_parser("get-all-inbox-metadata", help="Fetch metadata for all messages in the INBOX.")
    # No specific arguments for this command yet, but can be added (e.g., batch_size)

    args = parser.parse_args()

    print("Attempting to connect to Gmail API...")
    msg_accessor = MessageAccesor()

    if args.command == "list-labels":
        msg_accessor.list_labels()
    elif args.command == "list-messages":
        msg_accessor.list_messages_cmd(args.label_ids, args.max_results, args.query)
    elif args.command == "get-message":
        msg_accessor.get_message_detail(args.message_id, args.format)
    elif args.command == "get-all-inbox-metadata":
        msg_accessor.get_all_messages()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
