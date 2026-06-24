import json
import os
import shutil
import logging
from pathlib import Path
from cryptography.fernet import Fernet
import base64

logger = logging.getLogger(__name__)

class SessionManager:
    """
    Layer 3.5: Document Session Manager
    Maintains an encrypted local dictionary tracking session state.
    Writes to a .tmp file first, then uses atomic OS rename.
    """
    def __init__(self, workspace_dir: Path):
        self.workspace_dir = Path(workspace_dir)
        self.session_dir = self.workspace_dir / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        # In a real air-gapped system, this key is derived securely (e.g., from hardware hash).
        # For implementation, we'll store a static key or generate one if missing.
        self.key_file = self.workspace_dir / ".session.key"
        if self.key_file.exists():
            with open(self.key_file, "rb") as f:
                self.key = f.read()
        else:
            self.key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(self.key)
                
        self.cipher = Fernet(self.key)
        self.active_sessions = {}

    def get_session_file(self, document_id: str) -> Path:
        return self.session_dir / f"{document_id}.session"

    def initialize_session(self, document_id: str) -> dict:
        session_file = self.get_session_file(document_id)
        
        if session_file.exists():
            # Load existing secure session
            try:
                with open(session_file, "rb") as f:
                    encrypted_data = f.read()
                
                decrypted_data = self.cipher.decrypt(encrypted_data)
                session_data = json.loads(decrypted_data.decode('utf-8'))
                
                logger.info(f"Session Resumed for [{document_id}]")
                self.active_sessions[document_id] = session_data
                return session_data
            except Exception as e:
                logger.error(f"Failed to resume session for [{document_id}]. File may be corrupted or tampered. Starting fresh. {e}")
        
        # Start fresh session
        session_data = {
            "document_id": document_id,
            "current_page": 1,
            "processed_pages": [],
            "committed_pages": [],
            "next_balloon_id": 1,
            "export_status": "PENDING",
            "master_intelligence": []
        }
        self.active_sessions[document_id] = session_data
        self.save_session(document_id)
        logger.info(f"New Session Created for [{document_id}]")
        return session_data

    def update_session(self, document_id: str, updates: dict):
        if document_id in self.active_sessions:
            self.active_sessions[document_id].update(updates)
            self.save_session(document_id)

    def save_session(self, document_id: str):
        if document_id not in self.active_sessions:
            return
            
        session_data = self.active_sessions[document_id]
        json_data = json.dumps(session_data).encode('utf-8')
        encrypted_data = self.cipher.encrypt(json_data)
        
        session_file = self.get_session_file(document_id)
        tmp_file = session_file.with_suffix('.tmp')
        
        # Write to temp file first to prevent corruption
        try:
            with open(tmp_file, "wb") as f:
                f.write(encrypted_data)
                f.flush()
                os.fsync(f.fileno()) # Ensure it hits disk physically
                
            # Atomic rename (replace existing safely)
            os.replace(tmp_file, session_file)
            logger.debug(f"Session {document_id} safely saved to disk.")
        except Exception as e:
            logger.error(f"Critical error saving session for {document_id}: {e}")
            if tmp_file.exists():
                try:
                    tmp_file.unlink()
                except OSError:
                    pass

    def commit_page(self, document_id: str, page_idx: int, page_intelligence: list):
        """Commits page-level intelligence to the master session to support multi-page exports."""
        if document_id not in self.active_sessions:
            logger.error(f"Cannot commit page. Session {document_id} not active.")
            return

        session = self.active_sessions[document_id]
        
        if page_idx not in session["committed_pages"]:
            session["committed_pages"].append(page_idx)
        
        # Update master intelligence avoiding duplicates across pages
        existing_views = {v.get('view_name') for v in session.get("master_intelligence", [])}
        
        for view in page_intelligence:
            if view.get('view_name') not in existing_views:
                session.setdefault("master_intelligence", []).append(view)
                
        self.save_session(document_id)
        logger.info(f"Page {page_idx} securely committed to session [{document_id}].")