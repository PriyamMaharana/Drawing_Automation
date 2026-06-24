import logging
import json
import hashlib
import time
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class ImmutableAuditEngine:
    """
    Layer 13 & 14: Immutable Audit & Telemetry Engine
    Records actions to a JSON Lines (.jsonl) file and manages telemetry.
    """
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.audit_dir = self.project_root / "debug" / "audit"
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.telemetry = []

    def get_audit_file(self, document_id: str) -> Path:
        return self.audit_dir / f"{document_id}_audit_log.jsonl"

    def log_action(self, document_id: str, action: str, before: dict, after: dict, user_hash: str):
        """
        Logs an immutable action to the JSONL file.
        """
        timestamp = datetime.utcnow().isoformat()
        
        # Create a hash of the previous state to create a chain (blockchain-lite)
        # For simplicity, we just hash the current payload
        payload = {
            "timestamp": timestamp,
            "action": action,
            "user_hash": user_hash,
            "before": before,
            "after": after
        }
        
        payload_str = json.dumps(payload, sort_keys=True)
        signature = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()
        
        record = {
            "signature": signature,
            "data": payload
        }
        
        audit_file = self.get_audit_file(document_id)
        
        try:
            with open(audit_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
                
            self.telemetry.append({
                "time": time.time(),
                "action": action,
                "document_id": document_id
            })
            logger.debug(f"Audit record appended for {document_id}: {action}")
        except Exception as e:
            logger.error(f"Failed to write to immutable audit log: {e}")

    def dump_telemetry(self, session_id: str):
        """
        Dumps memory telemetry to disk upon session close.
        """
        telemetry_file = self.audit_dir / f"{session_id}_telemetry.json"
        try:
            with open(telemetry_file, "w", encoding="utf-8") as f:
                json.dump(self.telemetry, f, indent=4)
            self.telemetry.clear()
            logger.info(f"Telemetry dumped for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to dump telemetry: {e}")
