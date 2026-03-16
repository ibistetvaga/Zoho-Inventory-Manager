"""History manager for storing and retrieving search history."""

import json
import os
import shutil
from datetime import datetime
from typing import List, Dict, Optional
import platform


class HistoryManager:
    """Manages search history with robust JSON storage."""
    
    # Schema version for future migrations
    SCHEMA_VERSION = 1
    
    def __init__(self, max_history: int = 100):
        """
        Initialize the history manager.
        
        Args:
            max_history: Maximum number of entries to keep in history
        """
        self.max_history = max_history
        self.app_data_dir = self._get_app_data_dir()
        self.data_dir = os.path.join(self.app_data_dir, "data")
        self.history_file = os.path.join(self.data_dir, "search_history.json")
        self.backup_dir = os.path.join(self.data_dir, "backups")
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.history: List[Dict] = []
        self.load_history()
    
    def _get_app_data_dir(self) -> str:
        """Get platform-appropriate application data directory."""
        system = platform.system()
        
        if system == "Windows":
            return os.environ.get("APPDATA", os.path.expanduser("~"))
        elif system == "Darwin":  # macOS
            return os.path.expanduser("~/Library/Application Support")
        else:  # Linux and others
            return os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    
    def _get_app_name(self) -> str:
        """Get the application name for data directory."""
        return "Link Launcher"
    
    def load_history(self) -> List[Dict]:
        """Load history from JSON file with schema validation."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Handle new schema format
                    if isinstance(data, dict):
                        self.history = data.get("entries", [])
                    elif isinstance(data, list):
                        self.history = data
                    else:
                        self.history = []
                        
            except (json.JSONDecodeError, IOError, PermissionError) as e:
                print(f"Error loading history: {e}")
                # Try to restore from backup
                self._restore_from_backup()
                self.history = []
        return self.history
    
    def save_history(self) -> bool:
        """Save history to JSON file with atomic write."""
        try:
            # Ensure data directory exists
            os.makedirs(self.data_dir, exist_ok=True)
            
            # Create backup before saving
            if os.path.exists(self.history_file):
                self._create_backup()
            
            # Write to temp file first
            temp_file = self.history_file + ".tmp"
            schema_data = {
                "version": self.SCHEMA_VERSION,
                "created": self._get_file_creation_time(),
                "last_modified": datetime.now().isoformat(),
                "entries": self.history
            }
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(schema_data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            shutil.move(temp_file, self.history_file)
            return True
            
        except (IOError, PermissionError) as e:
            print(f"Error saving history: {e}")
            return False
    
    def _get_file_creation_time(self) -> str:
        """Get the creation time of the history file or current time."""
        if os.path.exists(self.history_file):
            try:
                timestamp = os.path.getctime(self.history_file)
                return datetime.fromtimestamp(timestamp).isoformat()
            except (OSError, AttributeError):
                pass
        return datetime.now().isoformat()
    
    def _create_backup(self):
        """Create a backup of the history file."""
        try:
            os.makedirs(self.backup_dir, exist_ok=True)
            
            # Get list of existing backups
            backups = []
            for i in range(1, 4):  # Keep last 3 backups
                backup_file = os.path.join(self.backup_dir, f"backup_{i}.json")
                if os.path.exists(backup_file):
                    backups.append(backup_file)
            
            # Shift backups
            for i in range(len(backups), 0, -1):
                old_backup = os.path.join(self.backup_dir, f"backup_{i}.json")
                new_backup = os.path.join(self.backup_dir, f"backup_{i + 1}.json")
                if os.path.exists(old_backup) and i < 3:
                    shutil.move(old_backup, new_backup)
            
            # Create new backup
            if os.path.exists(self.history_file):
                shutil.copy(self.history_file, os.path.join(self.backup_dir, "backup_1.json"))
                
        except (IOError, PermissionError) as e:
            print(f"Error creating backup: {e}")
    
    def _restore_from_backup(self):
        """Restore history from the most recent backup."""
        try:
            if os.path.exists(self.backup_dir):
                # Find the most recent backup
                for i in range(1, 4):
                    backup_file = os.path.join(self.backup_dir, f"backup_{i}.json")
                    if os.path.exists(backup_file):
                        with open(backup_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, dict):
                                self.history = data.get("entries", [])
                            elif isinstance(data, list):
                                self.history = data
                            return
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error restoring from backup: {e}")
    
    def add_entry(self, query: str, sources: Dict[str, bool]) -> None:
        """
        Add a new search entry to history.
        
        Args:
            query: The search query string
            sources: Dictionary of selected sources
        """
        # Filter out sources that weren't selected
        selected_sources = {k: v for k, v in sources.items() if v}
        
        entry = {
            'query': query,
            'sources': selected_sources,
            'timestamp': datetime.now().isoformat(),
            'display_time': self._format_timestamp(datetime.now())
        }
        
        # Remove duplicates (same query and sources)
        self.history = [
            e for e in self.history
            if not (e['query'] == query and e['sources'] == selected_sources)
        ]
        
        # Add new entry at the beginning
        self.history.insert(0, entry)
        
        # Trim to max history size
        self.history = self.history[:self.max_history]
        
        # Save to file
        self.save_history()
    
    def _format_timestamp(self, dt: datetime) -> str:
        """Format timestamp for display."""
        now = datetime.now()
        if dt.date() == now.date():
            return f"Today at {dt.strftime('%I:%M %p')}"
        elif dt.date() == now.date().replace(day=now.day - 1):
            return f"Yesterday at {dt.strftime('%I:%M %p')}"
        else:
            return dt.strftime('%b %d, %Y at %I:%M %p')
    
    def get_history(self) -> List[Dict]:
        """Get all history entries."""
        return self.history.copy()
    
    def get_recent_queries(self, limit: int = 10) -> List[str]:
        """
        Get list of recent unique queries.
        
        Args:
            limit: Maximum number of queries to return
            
        Returns:
            List of unique query strings
        """
        seen = set()
        queries = []
        for entry in self.history:
            if entry['query'] not in seen:
                seen.add(entry['query'])
                queries.append(entry['query'])
            if len(queries) >= limit:
                break
        return queries
    
    def search_history(self, query: str) -> List[Dict]:
        """
        Search history for entries matching the query.
        
        Args:
            query: Search string to match
            
        Returns:
            List of matching history entries
        """
        query_lower = query.lower()
        return [
            e for e in self.history
            if query_lower in e['query'].lower()
        ]
    
    def clear_history(self) -> bool:
        """Clear all history entries."""
        self.history = []
        return self.save_history()
    
    def delete_entry(self, index: int) -> bool:
        """
        Delete a specific history entry by index.
        
        Args:
            index: Index of entry to delete
            
        Returns:
            True if successful, False otherwise
        """
        if 0 <= index < len(self.history):
            del self.history[index]
            self.save_history()
            return True
        return False
    
    def get_entry_count(self) -> int:
        """Get the number of history entries."""
        return len(self.history)
    
    def export_history(self, file_path: str) -> bool:
        """
        Export history to a JSON file.
        
        Args:
            file_path: Path to export file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
            return True
        except (IOError, PermissionError) as e:
            print(f"Error exporting history: {e}")
            return False
    
    def import_history(self, file_path: str, merge: bool = True) -> bool:
        """
        Import history from a JSON file.
        
        Args:
            file_path: Path to import file
            merge: If True, merge with existing history; otherwise replace
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)
                
            if not isinstance(imported_data, list):
                return False
                
            if merge:
                # Merge imported entries with existing ones
                # Remove duplicates based on query and sources
                existing = {(e['query'], frozenset(e['sources'].items())) for e in self.history}
                for entry in imported_data:
                    key = (entry['query'], frozenset(entry['sources'].items()))
                    if key not in existing:
                        self.history.insert(0, entry)
                self.history = self.history[:self.max_history]
            else:
                self.history = imported_data[:self.max_history]
            
            self.save_history()
            return True
        except (IOError, json.JSONDecodeError, KeyError) as e:
            print(f"Error importing history: {e}")
            return False
    
    def get_data_directory(self) -> str:
        """Get the data directory path."""
        return self.data_dir
    
    def get_backup_count(self) -> int:
        """Get the number of available backups."""
        if not os.path.exists(self.backup_dir):
            return 0
        count = 0
        for i in range(1, 4):
            if os.path.exists(os.path.join(self.backup_dir, f"backup_{i}.json")):
                count += 1
        return count
