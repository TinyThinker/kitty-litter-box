import sqlite3
import os
import json
from datetime import datetime

# Get path to token.pickle from MessageAccesor
from MessageAccesor import TOKEN_FILENAME

# Define the default database filename
DB_FILENAME = 'gmail_cache.db'
DEFAULT_DB_PATH = os.path.join(os.path.dirname(TOKEN_FILENAME), DB_FILENAME)

class GmailCacheDB:
    """
    A class for managing the SQLite database that caches Gmail message data.
    This class handles database initialization, connection management,
    and operations for storing and retrieving Gmail message metadata.
    """
    
    def __init__(self, db_path=None):
        """
        Initialize the GmailCacheDB with an optional custom database path.
        
        Args:
            db_path (str, optional): Path to the SQLite database file.
                                    If None, uses the default path.
        """
        # If no path provided, use the default path (same directory as token.pickle)
        self.db_path = db_path if db_path else DEFAULT_DB_PATH
        
        # Create directory if it doesn't exist (in case db_path includes a directory)
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        # Initialize the database (create tables if they don't exist)
        self._initialize_database()
    
    def _initialize_database(self):
        """
        Private method to initialize the database by creating necessary tables
        if they don't already exist.
        """
        # Establish a connection to the SQLite database
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Create message_stubs table for basic message metadata
        # This table stores the minimal info about each message
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS message_stubs (
            message_id TEXT PRIMARY KEY,
            thread_id TEXT NOT NULL,
            stub_last_fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create message_rich_metadata table for detailed message information
        # This table stores more comprehensive metadata that requires additional API calls
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS message_rich_metadata (
            message_id TEXT PRIMARY KEY,
            snippet TEXT,
            internal_date INTEGER,
            size_estimate INTEGER,
            from_address TEXT,
            subject TEXT,
            label_ids_json TEXT,
            has_attachments INTEGER,
            attachment_filenames_json TEXT,
            payload_headers_json TEXT,
            rich_last_fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(message_id) REFERENCES message_stubs(message_id)
        )
        ''')
        
        # Commit changes and close the connection
        conn.commit()
        conn.close()
    
    def get_db_connection(self):
        """
        Get a new SQLite connection to the database.
        
        Returns:
            sqlite3.Connection: A new connection to the SQLite database.
        """
        # Connect to the SQLite database file
        # Setting isolation_level=None enables autocommit mode
        # which is often useful for simpler transaction management
        return sqlite3.connect(self.db_path)
    
    def close_connection(self, conn):
        """
        Close a database connection safely.
        
        Args:
            conn (sqlite3.Connection): The SQLite connection to close.
        """
        if conn:
            conn.close()
