"""
Enhanced Data Persistence Module
Provides comprehensive data persistence with backup, transactions, validation, 
and recovery capabilities.
"""

import json
import pickle
import shutil
import hashlib
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading
import csv
from functools import wraps


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StorageFormat(Enum):
    """Supported storage formats."""
    JSON = "json"
    PICKLE = "pickle"
    CSV = "csv"


class OperationType(Enum):
    """Types of operations tracked in change log."""
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    RESTORE = "RESTORE"
    BACKUP = "BACKUP"
    EXPORT = "EXPORT"


@dataclass
class ChangeLogEntry:
    """Represents a single change log entry."""
    timestamp: str
    operation: OperationType
    description: str
    user: Optional[str] = None
    data_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp,
            'operation': self.operation.value,
            'description': self.description,
            'user': self.user,
            'data_hash': self.data_hash,
            'metadata': self.metadata
        }


@dataclass
class BackupMetadata:
    """Metadata for backup files."""
    backup_id: str
    timestamp: str
    source_path: Path
    backup_path: Path
    data_hash: str
    file_size: int
    format: StorageFormat
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'backup_id': self.backup_id,
            'timestamp': self.timestamp,
            'source_path': str(self.source_path),
            'backup_path': str(self.backup_path),
            'data_hash': self.data_hash,
            'file_size': self.file_size,
            'format': self.format.value,
            'description': self.description
        }


class DataValidator:
    """Validates data before storage and after retrieval."""

    def __init__(self):
        """Initialize the validator."""
        self.validators: Dict[str, Callable] = {}

    def register_validator(self, key: str, validator: Callable[[Any], bool]) -> None:
        """
        Register a validation function for a specific key.
        
        Args:
            key: The data key to validate
            validator: Function that returns True if valid, False otherwise
        """
        self.validators[key] = validator
        logger.info(f"Registered validator for key: {key}")

    def validate(self, data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate data against registered validators.
        
        Args:
            data: Dictionary to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        for key, validator in self.validators.items():
            if key in data:
                try:
                    if not validator(data[key]):
                        errors.append(f"Validation failed for key '{key}'")
                except Exception as e:
                    errors.append(f"Validation error for key '{key}': {str(e)}")
        
        return len(errors) == 0, errors

    def validate_json(self, data: Union[str, bytes]) -> tuple[bool, Optional[str]]:
        """
        Validate JSON structure.
        
        Args:
            data: JSON string or bytes
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            json.loads(data)
            return True, None
        except json.JSONDecodeError as e:
            return False, str(e)


class ChangeLog:
    """Maintains a log of all data changes."""

    def __init__(self, log_file: Union[str, Path]):
        """
        Initialize the change log.
        
        Args:
            log_file: Path to store change log
        """
        self.log_file = Path(log_file)
        self.entries: List[ChangeLogEntry] = []
        self._lock = threading.Lock()
        self._load_existing_log()

    def _load_existing_log(self) -> None:
        """Load existing log entries from file."""
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r') as f:
                    data = json.load(f)
                    self.entries = [
                        ChangeLogEntry(
                            timestamp=entry['timestamp'],
                            operation=OperationType(entry['operation']),
                            description=entry['description'],
                            user=entry.get('user'),
                            data_hash=entry.get('data_hash'),
                            metadata=entry.get('metadata', {})
                        )
                        for entry in data
                    ]
                logger.info(f"Loaded {len(self.entries)} change log entries")
            except Exception as e:
                logger.error(f"Failed to load change log: {str(e)}")

    def log_change(
        self,
        operation: OperationType,
        description: str,
        user: Optional[str] = None,
        data_hash: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a change operation.
        
        Args:
            operation: Type of operation
            description: Human-readable description
            user: User performing the operation
            data_hash: Hash of the affected data
            metadata: Additional metadata
        """
        with self._lock:
            entry = ChangeLogEntry(
                timestamp=datetime.utcnow().isoformat(),
                operation=operation,
                description=description,
                user=user,
                data_hash=data_hash,
                metadata=metadata or {}
            )
            self.entries.append(entry)
            self._save_log()
            logger.info(f"Logged operation: {operation.value} - {description}")

    def _save_log(self) -> None:
        """Save log entries to file."""
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, 'w') as f:
                json.dump([entry.to_dict() for entry in self.entries], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save change log: {str(e)}")

    def get_history(
        self,
        operation_type: Optional[OperationType] = None,
        limit: Optional[int] = None
    ) -> List[ChangeLogEntry]:
        """
        Retrieve change history.
        
        Args:
            operation_type: Filter by operation type
            limit: Maximum number of entries to return
            
        Returns:
            List of change log entries
        """
        entries = self.entries
        
        if operation_type:
            entries = [e for e in entries if e.operation == operation_type]
        
        if limit:
            entries = entries[-limit:]
        
        return entries


class BackupManager:
    """Manages data backups with versioning and metadata tracking."""

    def __init__(self, backup_dir: Union[str, Path]):
        """
        Initialize the backup manager.
        
        Args:
            backup_dir: Directory to store backups
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.backup_dir / "backup_metadata.json"
        self.backups: List[BackupMetadata] = []
        self._lock = threading.Lock()
        self._load_metadata()

    def _load_metadata(self) -> None:
        """Load backup metadata from file."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    data = json.load(f)
                    self.backups = [
                        BackupMetadata(
                            backup_id=b['backup_id'],
                            timestamp=b['timestamp'],
                            source_path=Path(b['source_path']),
                            backup_path=Path(b['backup_path']),
                            data_hash=b['data_hash'],
                            file_size=b['file_size'],
                            format=StorageFormat(b['format']),
                            description=b.get('description')
                        )
                        for b in data
                    ]
                logger.info(f"Loaded {len(self.backups)} backup records")
            except Exception as e:
                logger.error(f"Failed to load backup metadata: {str(e)}")

    def create_backup(
        self,
        data: Any,
        source_path: Union[str, Path],
        format: StorageFormat = StorageFormat.JSON,
        description: Optional[str] = None
    ) -> Optional[BackupMetadata]:
        """
        Create a backup of data.
        
        Args:
            data: Data to backup
            source_path: Original source path
            format: Storage format
            description: Optional description
            
        Returns:
            BackupMetadata if successful, None otherwise
        """
        with self._lock:
            try:
                timestamp = datetime.utcnow().isoformat()
                backup_id = hashlib.md5(f"{source_path}{timestamp}".encode()).hexdigest()
                
                # Serialize data
                if format == StorageFormat.JSON:
                    serialized = json.dumps(data).encode()
                elif format == StorageFormat.PICKLE:
                    serialized = pickle.dumps(data)
                else:
                    raise ValueError(f"Unsupported format: {format}")
                
                # Calculate hash
                data_hash = hashlib.sha256(serialized).hexdigest()
                
                # Create backup file
                backup_filename = f"backup_{backup_id}.{format.value}"
                backup_path = self.backup_dir / backup_filename
                
                with open(backup_path, 'wb') as f:
                    f.write(serialized)
                
                # Create metadata
                metadata = BackupMetadata(
                    backup_id=backup_id,
                    timestamp=timestamp,
                    source_path=Path(source_path),
                    backup_path=backup_path,
                    data_hash=data_hash,
                    file_size=backup_path.stat().st_size,
                    format=format,
                    description=description
                )
                
                self.backups.append(metadata)
                self._save_metadata()
                
                logger.info(f"Created backup: {backup_id} for {source_path}")
                return metadata
                
            except Exception as e:
                logger.error(f"Failed to create backup: {str(e)}")
                return None

    def restore_backup(self, backup_id: str) -> Optional[Any]:
        """
        Restore data from a backup.
        
        Args:
            backup_id: ID of the backup to restore
            
        Returns:
            Restored data if successful, None otherwise
        """
        with self._lock:
            try:
                metadata = next((b for b in self.backups if b.backup_id == backup_id), None)
                if not metadata:
                    logger.error(f"Backup not found: {backup_id}")
                    return None
                
                with open(metadata.backup_path, 'rb') as f:
                    data = f.read()
                
                if metadata.format == StorageFormat.JSON:
                    result = json.loads(data)
                elif metadata.format == StorageFormat.PICKLE:
                    result = pickle.loads(data)
                else:
                    raise ValueError(f"Unsupported format: {metadata.format}")
                
                logger.info(f"Restored backup: {backup_id}")
                return result
                
            except Exception as e:
                logger.error(f"Failed to restore backup: {str(e)}")
                return None

    def delete_backup(self, backup_id: str) -> bool:
        """
        Delete a backup.
        
        Args:
            backup_id: ID of the backup to delete
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            try:
                metadata = next((b for b in self.backups if b.backup_id == backup_id), None)
                if not metadata:
                    logger.error(f"Backup not found: {backup_id}")
                    return False
                
                if metadata.backup_path.exists():
                    metadata.backup_path.unlink()
                
                self.backups.remove(metadata)
                self._save_metadata()
                
                logger.info(f"Deleted backup: {backup_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to delete backup: {str(e)}")
                return False

    def list_backups(self, source_path: Optional[Union[str, Path]] = None) -> List[BackupMetadata]:
        """
        List available backups.
        
        Args:
            source_path: Filter by source path (optional)
            
        Returns:
            List of backup metadata
        """
        if source_path:
            source_path = Path(source_path)
            return [b for b in self.backups if b.source_path == source_path]
        return self.backups

    def _save_metadata(self) -> None:
        """Save backup metadata to file."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump([b.to_dict() for b in self.backups], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save backup metadata: {str(e)}")


class TransactionalStorage:
    """Provides transactional storage with ACID properties."""

    def __init__(
        self,
        storage_path: Union[str, Path],
        format: StorageFormat = StorageFormat.JSON,
        auto_backup: bool = True
    ):
        """
        Initialize transactional storage.
        
        Args:
            storage_path: Path to store data
            format: Storage format
            auto_backup: Whether to create backups automatically
        """
        self.storage_path = Path(storage_path)
        self.format = format
        self.auto_backup = auto_backup
        self._lock = threading.RLock()
        self._transaction_stack: List[Dict[str, Any]] = []
        self._data: Dict[str, Any] = {}
        self._load_data()

    def _load_data(self) -> None:
        """Load data from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'rb') as f:
                    content = f.read()
                
                if self.format == StorageFormat.JSON:
                    self._data = json.loads(content)
                elif self.format == StorageFormat.PICKLE:
                    self._data = pickle.loads(content)
                
                logger.info(f"Loaded data from {self.storage_path}")
            except Exception as e:
                logger.error(f"Failed to load data: {str(e)}")
                self._data = {}

    def _save_data(self) -> None:
        """Save data to storage."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            if self.format == StorageFormat.JSON:
                content = json.dumps(self._data).encode()
            elif self.format == StorageFormat.PICKLE:
                content = pickle.dumps(self._data)
            
            # Write to temporary file first
            temp_path = self.storage_path.with_suffix('.tmp')
            with open(temp_path, 'wb') as f:
                f.write(content)
            
            # Atomic rename
            temp_path.replace(self.storage_path)
            logger.info(f"Saved data to {self.storage_path}")
            
        except Exception as e:
            logger.error(f"Failed to save data: {str(e)}")
            raise

    @contextmanager
    def transaction(self):
        """
        Context manager for transactional operations.
        
        Usage:
            with storage.transaction():
                storage.set('key', 'value')
        """
        with self._lock:
            # Create a checkpoint
            checkpoint = self._data.copy()
            self._transaction_stack.append(checkpoint)
            
            try:
                yield
                # Commit
                self._save_data()
                self._transaction_stack.pop()
                logger.info("Transaction committed")
            except Exception as e:
                # Rollback
                if self._transaction_stack:
                    self._data = self._transaction_stack.pop()
                logger.error(f"Transaction rolled back: {str(e)}")
                raise

    def set(self, key: str, value: Any) -> None:
        """
        Set a value.
        
        Args:
            key: Data key
            value: Data value
        """
        with self._lock:
            self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value.
        
        Args:
            key: Data key
            default: Default value if key not found
            
        Returns:
            Data value or default
        """
        with self._lock:
            return self._data.get(key, default)

    def delete(self, key: str) -> bool:
        """
        Delete a key.
        
        Args:
            key: Data key
            
        Returns:
            True if key was deleted, False if not found
        """
        with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False

    def get_all(self) -> Dict[str, Any]:
        """
        Get all data.
        
        Returns:
            Dictionary of all data
        """
        with self._lock:
            return self._data.copy()


class RecoveryManager:
    """Manages data recovery and consistency checks."""

    def __init__(
        self,
        backup_manager: BackupManager,
        change_log: ChangeLog,
        storage_path: Union[str, Path]
    ):
        """
        Initialize recovery manager.
        
        Args:
            backup_manager: BackupManager instance
            change_log: ChangeLog instance
            storage_path: Path to main storage
        """
        self.backup_manager = backup_manager
        self.change_log = change_log
        self.storage_path = Path(storage_path)
        self._lock = threading.Lock()

    def verify_data_integrity(self, data: Any, expected_hash: Optional[str] = None) -> tuple[bool, str]:
        """
        Verify data integrity.
        
        Args:
            data: Data to verify
            expected_hash: Expected hash value
            
        Returns:
            Tuple of (is_valid, message)
        """
        try:
            serialized = json.dumps(data).encode() if isinstance(data, dict) else str(data).encode()
            actual_hash = hashlib.sha256(serialized).hexdigest()
            
            if expected_hash and actual_hash != expected_hash:
                return False, f"Hash mismatch. Expected: {expected_hash}, Got: {actual_hash}"
            
            return True, f"Data integrity verified. Hash: {actual_hash}"
            
        except Exception as e:
            return False, f"Integrity check failed: {str(e)}"

    def recover_from_backup(self, backup_id: str, force: bool = False) -> bool:
        """
        Recover data from a backup.
        
        Args:
            backup_id: ID of the backup to recover from
            force: Force recovery without confirmation
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            try:
                if not force and self.storage_path.exists():
                    logger.warning("Existing data will be overwritten during recovery")
                
                data = self.backup_manager.restore_backup(backup_id)
                if data is None:
                    return False
                
                # Create a backup of current state before recovery
                if self.storage_path.exists():
                    with open(self.storage_path, 'r') as f:
                        current_data = json.load(f)
                    self.backup_manager.create_backup(
                        current_data,
                        self.storage_path,
                        description="Pre-recovery backup"
                    )
                
                # Restore data
                with open(self.storage_path, 'w') as f:
                    json.dump(data, f, indent=2)
                
                self.change_log.log_change(
                    OperationType.RESTORE,
                    f"Recovered from backup: {backup_id}",
                    metadata={'backup_id': backup_id}
                )
                
                logger.info(f"Successfully recovered from backup: {backup_id}")
                return True
                
            except Exception as e:
                logger.error(f"Recovery failed: {str(e)}")
                return False

    def check_consistency(self) -> tuple[bool, List[str]]:
        """
        Check data consistency.
        
        Returns:
            Tuple of (is_consistent, list_of_issues)
        """
        issues = []
        
        try:
            # Check if storage file exists
            if not self.storage_path.exists():
                issues.append("Storage file does not exist")
                return False, issues
            
            # Check if file is readable
            try:
                with open(self.storage_path, 'r') as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                issues.append(f"Invalid JSON: {str(e)}")
            
            # Check backup consistency
            for backup in self.backup_manager.list_backups():
                if not backup.backup_path.exists():
                    issues.append(f"Backup file missing: {backup.backup_id}")
            
            return len(issues) == 0, issues
            
        except Exception as e:
            issues.append(f"Consistency check error: {str(e)}")
            return False, issues


class ExportManager:
    """Manages data export in various formats."""

    def __init__(self):
        """Initialize export manager."""
        self._exporters: Dict[StorageFormat, Callable] = {
            StorageFormat.JSON: self._export_json,
            StorageFormat.PICKLE: self._export_pickle,
            StorageFormat.CSV: self._export_csv
        }

    def export(
        self,
        data: Any,
        output_path: Union[str, Path],
        format: StorageFormat = StorageFormat.JSON,
        **kwargs
    ) -> bool:
        """
        Export data to file.
        
        Args:
            data: Data to export
            output_path: Path to output file
            format: Export format
            **kwargs: Format-specific options
            
        Returns:
            True if successful, False otherwise
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            exporter = self._exporters.get(format)
            if not exporter:
                logger.error(f"Unsupported export format: {format}")
                return False
            
            exporter(data, output_path, **kwargs)
            logger.info(f"Exported data to {output_path} in {format.value} format")
            return True
            
        except Exception as e:
            logger.error(f"Export failed: {str(e)}")
            return False

    @staticmethod
    def _export_json(data: Any, output_path: Path, **kwargs) -> None:
        """Export data as JSON."""
        indent = kwargs.get('indent', 2)
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=indent)

    @staticmethod
    def _export_pickle(data: Any, output_path: Path, **kwargs) -> None:
        """Export data as pickle."""
        with open(output_path, 'wb') as f:
            pickle.dump(data, f)

    @staticmethod
    def _export_csv(data: Any, output_path: Path, **kwargs) -> None:
        """Export data as CSV."""
        if not isinstance(data, list):
            raise ValueError("CSV export requires a list of dictionaries")
        
        if not data:
            return
        
        if not isinstance(data[0], dict):
            raise ValueError("CSV export requires a list of dictionaries")
        
        fieldnames = kwargs.get('fieldnames') or data[0].keys()
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

    def export_batch(
        self,
        data: Dict[str, Any],
        output_dir: Union[str, Path],
        format: StorageFormat = StorageFormat.JSON
    ) -> bool:
        """
        Export multiple data items as separate files.
        
        Args:
            data: Dictionary of data to export
            output_dir: Directory to store exports
            format: Export format
            
        Returns:
            True if all exports successful, False otherwise
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        all_successful = True
        for key, value in data.items():
            filename = f"{key}.{format.value}"
            output_path = output_dir / filename
            
            if not self.export(value, output_path, format):
                all_successful = False
        
        return all_successful


class PersistenceManager:
    """
    Main persistence manager combining all components.
    
    This is the primary interface for all data persistence operations.
    """

    def __init__(
        self,
        storage_dir: Union[str, Path] = "data",
        storage_format: StorageFormat = StorageFormat.JSON,
        auto_backup: bool = True,
        change_log_enabled: bool = True
    ):
        """
        Initialize persistence manager.
        
        Args:
            storage_dir: Base directory for storage
            storage_format: Default storage format
            auto_backup: Enable automatic backups
            change_log_enabled: Enable change logging
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.storage_path = self.storage_dir / f"data.{storage_format.value}"
        self.backup_dir = self.storage_dir / "backups"
        self.log_file = self.storage_dir / "changelog.json"
        
        # Initialize components
        self.backup_manager = BackupManager(self.backup_dir)
        self.change_log = ChangeLog(self.log_file) if change_log_enabled else None
        self.data_validator = DataValidator()
        self.recovery_manager = RecoveryManager(
            self.backup_manager,
            self.change_log,
            self.storage_path
        )
        self.export_manager = ExportManager()
        self.storage = TransactionalStorage(
            self.storage_path,
            storage_format,
            auto_backup
        )
        
        self.auto_backup = auto_backup
        logger.info(f"PersistenceManager initialized at {self.storage_dir}")

    def save(
        self,
        key: str,
        value: Any,
        validate: bool = True,
        backup: bool = None,
        description: Optional[str] = None
    ) -> bool:
        """
        Save data with optional validation and backup.
        
        Args:
            key: Data key
            value: Data value
            validate: Validate data before saving
            backup: Create backup (uses auto_backup if None)
            description: Operation description
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate if enabled
            if validate:
                is_valid, errors = self.data_validator.validate({'key': value})
                if not is_valid:
                    logger.error(f"Validation failed: {errors}")
                    return False
            
            # Create backup if enabled
            backup = backup if backup is not None else self.auto_backup
            if backup:
                self.backup_manager.create_backup(
                    self.storage.get_all(),
                    self.storage_path,
                    description=f"Pre-save backup for key: {key}"
                )
            
            # Save data
            with self.storage.transaction():
                self.storage.set(key, value)
            
            # Log change
            if self.change_log:
                self.change_log.log_change(
                    OperationType.CREATE,
                    description or f"Saved key: {key}",
                    metadata={'key': key}
                )
            
            logger.info(f"Saved key: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Save operation failed: {str(e)}")
            return False

    def load(self, key: str, default: Any = None) -> Any:
        """
        Load data.
        
        Args:
            key: Data key
            default: Default value if not found
            
        Returns:
            Data value or default
        """
        return self.storage.get(key, default)

    def load_all(self) -> Dict[str, Any]:
        """
        Load all data.
        
        Returns:
            Dictionary of all data
        """
        return self.storage.get_all()

    def backup(self, description: Optional[str] = None) -> Optional[BackupMetadata]:
        """
        Create a manual backup.
        
        Args:
            description: Backup description
            
        Returns:
            BackupMetadata if successful, None otherwise
        """
        return self.backup_manager.create_backup(
            self.storage.get_all(),
            self.storage_path,
            description=description
        )

    def export(
        self,
        output_path: Union[str, Path],
        format: StorageFormat = StorageFormat.JSON,
        **kwargs
    ) -> bool:
        """
        Export all data.
        
        Args:
            output_path: Output file path
            format: Export format
            **kwargs: Format-specific options
            
        Returns:
            True if successful, False otherwise
        """
        return self.export_manager.export(
            self.storage.get_all(),
            output_path,
            format,
            **kwargs
        )

    def get_status(self) -> Dict[str, Any]:
        """
        Get persistence status information.
        
        Returns:
            Status dictionary
        """
        is_consistent, issues = self.recovery_manager.check_consistency()
        
        return {
            'storage_dir': str(self.storage_dir),
            'storage_path': str(self.storage_path),
            'backup_count': len(self.backup_manager.backups),
            'change_log_entries': len(self.change_log.entries) if self.change_log else 0,
            'is_consistent': is_consistent,
            'consistency_issues': issues,
            'data_size': len(self.storage.get_all())
        }
