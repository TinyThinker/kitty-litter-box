import os

# Define paths
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CREDENTIALS_FILENAME = os.path.join(os.path.dirname(__file__), 'config', 'credentials.json')
TOKEN_FILENAME = os.path.join(os.path.dirname(__file__), 'token.pickle')