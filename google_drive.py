import os
import io
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from typing import List, Dict, Optional

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.file']
class GoogleDriveService:
    def __init__(self):
        self.creds = None
        self.service = None
        
        # Get the directory where this script is located
        self.base_dir = Path(__file__).parent
        self.credentials_path = self.base_dir / 'credentials.json'
        self.token_path = self.base_dir / 'token.json'
        
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Drive API"""
        # The file token.json stores the user's access and refresh tokens
        if self.token_path.exists():
            self.creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
        
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f"credentials.json not found at {self.credentials_path}. "
                        f"Please download it from Google Cloud Console and place it in {self.base_dir}"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(self.token_path, 'w') as token:
                token.write(self.creds.to_json())
        
        self.service = build('drive', 'v3', credentials=self.creds)
        print(f"✓ Google Drive authenticated successfully")
    
    
    def list_files(self, mime_types: Optional[List[str]] = None, max_results: int = 100) -> List[Dict]:
        """
        List files from Google Drive
        
        Args:
            mime_types: Filter by MIME types (PDF, DOCX, PPTX)
            max_results: Maximum number of files to return
        
        Returns:
            List of file metadata
        """
        if mime_types is None:
            mime_types = [
                'application/pdf',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                'application/msword',
                'application/vnd.ms-powerpoint'
            ]
        
        query_parts = [f"mimeType='{mime}'" for mime in mime_types]
        query = ' or '.join(query_parts)
        
        try:
            results = self.service.files().list(
                q=query,
                pageSize=max_results,
                fields="files(id, name, mimeType, modifiedTime, size, webViewLink)"
            ).execute()
            
            files = results.get('files', [])
            return files
        
        except Exception as e:
            print(f"Error listing files: {e}")
            return []
    
    def download_file(self, file_id: str) -> bytes:
        """
        Download file content from Google Drive
        
        Args:
            file_id: Google Drive file ID
        
        Returns:
            File content as bytes
        """
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            return file_content.getvalue()
        
        except Exception as e:
            print(f"Error downloading file: {e}")
            return b''
    
    def get_file_metadata(self, file_id: str) -> Dict:
        """Get file metadata"""
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, modifiedTime, size, webViewLink"
            ).execute()
            return file
        except Exception as e:
            print(f"Error getting file metadata: {e}")
            return {}
    
    def search_files_by_name(self, filename: str) -> List[Dict]:
        """Search files by name"""
        query = f"name contains '{filename}'"
        
        try:
            results = self.service.files().list(
                q=query,
                pageSize=20,
                fields="files(id, name, mimeType, modifiedTime, size, webViewLink)"
            ).execute()
            
            return results.get('files', [])
        
        except Exception as e:
            print(f"Error searching files: {e}")
            return []

    def upload_file(self, file_bytes: bytes, filename: str, mime_type: str) -> Dict:
        """Upload file to Google Drive"""
        try:
            from googleapiclient.http import MediaIoBaseUpload
            import io
            
            file_metadata = {'name': filename}
            media = MediaIoBaseUpload(
                io.BytesIO(file_bytes),
                mimetype=mime_type,
                resumable=True
            )
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, mimeType, size, webViewLink'
            ).execute()
            
            print(f"✓ Uploaded {filename} to Google Drive")
            return file
        
        except Exception as e:
            print(f"Error uploading: {e}")
            return {}