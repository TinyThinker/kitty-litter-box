import os.path
import pickle # Using pickle for token storage as per common Google examples

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these SCOPES, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly'] # Readonly access is sufficient for listing labels

class MessageAccesor:
    def get_gmail_service():
        """Shows basic usage of the Gmail API.
        Lists the user's Gmail labels.
        """
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        # Note: Google's newer examples might use token.json.
        # For consistency with many existing setups, this example uses token.pickle.
        # If you prefer token.json, you can adapt the credential saving/loading.
        token_file = 'token.pickle'
        credentials_file = 'credentials.json'

        if not os.path.exists(credentials_file):
            print(f"Error: {credentials_file} not found. Please download it from Google Cloud Console.")
            return None

        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
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
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_file, SCOPES)
                    # Ensure redirect_uris in credentials.json includes "http://localhost:port"
                    # or "urn:ietf:wg:oauth:2.0:oob" for installed apps.
                    # The port for localhost can be any available port.
                    # For this example, let's assume it will use a default or prompt.
                    creds = flow.run_local_server(port=0) # port=0 finds a free port
                except Exception as e:
                    print(f"Error during authentication flow: {e}")
                    print("Please ensure your credentials.json is configured correctly for an Installed App.")
                    print("The redirect URI might need to be 'http://localhost:PORT' or 'urn:ietf:wg:oauth:2.0:oob'.")
                    return None
            # Save the credentials for the next run
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)
                print(f"Token saved to {token_file}")

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
    Main function to get the Gmail service and list labels.
    """
    print("Attempting to connect to Gmail API...")
    msg_accesor = MessageAccesor()
    service = msg_accesor.get_gmail_service()

    if not service:
        print("Failed to get Gmail service. Exiting.")
        return

    try:
        print("\nFetching Gmail labels...")
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])

        if not labels:
            print('No labels found.')
            return

        print('Labels:')
        for label in labels:
            print(f"- {label['name']} (ID: {label['id']})")

    except HttpError as error:
        print(f'An API error occurred while fetching labels: {error}')
        # Specific advice for label fetching errors if any common ones exist
        if "accessNotConfigured" in str(error) or "User Rate Limit Exceeded" in str(error) :
             print("Ensure the Gmail API is enabled in your Google Cloud project.")
             print("Also, check API quotas if you've made many requests.")
    except Exception as e:
        print(f"An unexpected error occurred while fetching labels: {e}")


if __name__ == '__main__':
    main()
