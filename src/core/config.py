import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class AppSettings:
    """Application settings configuration"""
    
    # General Settings
    max_concurrent_transfers: int = 3
    chunk_size_mb: int = 5
    checksum_verification: bool = True
    preserve_permissions: bool = True
    
    # UI Settings
    theme: str = "light"  # light, dark, auto
    auto_refresh_interval: int = 5000  # milliseconds
    show_system_tray: bool = True
    minimize_to_tray: bool = True
    
    # Backup Settings
    default_conflict_policy: str = "rename"  # rename, overwrite, skip
    backup_metadata: bool = True
    compress_backups: bool = False
    
    # Logging Settings
    log_level: str = "INFO"
    max_log_files: int = 10
    log_retention_days: int = 30
    
    # Network Settings
    connection_timeout: int = 30
    retry_attempts: int = 3
    retry_delay_seconds: int = 5
    
    # Google Drive Settings
    gdrive_chunk_size_mb: int = 5
    gdrive_timeout_seconds: int = 300

class ConfigManager:
    """Manages application configuration"""
    
    def __init__(self, config_dir: Optional[str] = None):
        if config_dir is None:
            # Use user's app data directory
            if os.name == 'nt':  # Windows
                config_dir = os.path.join(os.environ.get('APPDATA', ''), 'BackupManagerPro')
            else:  # Linux/Mac
                config_dir = os.path.join(os.path.expanduser('~'), '.backupmanagerpro')
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.config_file = self.config_dir / 'settings.json'
        self.settings = self.load_settings()
    
    def load_settings(self) -> AppSettings:
        """Load settings from file or create defaults"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Create settings object with loaded data
                return AppSettings(**data)
            
            except (json.JSONDecodeError, TypeError, ValueError) as e:
                print(f"Error loading config file: {e}. Using defaults.")
                return AppSettings()
        
        # Create default settings file
        default_settings = AppSettings()
        self.save_settings(default_settings)
        return default_settings
    
    def save_settings(self, settings: Optional[AppSettings] = None):
        """Save settings to file"""
        if settings is None:
            settings = self.settings
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(settings), f, indent=2)
            
            self.settings = settings
        except (IOError, OSError) as e:
            print(f"Error saving config file: {e}")
    
    def get_setting(self, key: str) -> Any:
        """Get a specific setting value"""
        return getattr(self.settings, key, None)
    
    def set_setting(self, key: str, value: Any):
        """Set a specific setting value"""
        if hasattr(self.settings, key):
            setattr(self.settings, key, value)
            self.save_settings()
        else:
            raise AttributeError(f"Setting '{key}' does not exist")
    
    def reset_to_defaults(self):
        """Reset all settings to default values"""
        self.settings = AppSettings()
        self.save_settings()
    
    def export_settings(self, export_path: str):
        """Export settings to a specific file"""
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.settings), f, indent=2)
        except (IOError, OSError) as e:
            raise Exception(f"Failed to export settings: {e}")
    
    def import_settings(self, import_path: str):
        """Import settings from a specific file"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            settings = AppSettings(**data)
            self.save_settings(settings)
        except (json.JSONDecodeError, TypeError, ValueError, IOError, OSError) as e:
            raise Exception(f"Failed to import settings: {e}")
    
    def get_app_data_dir(self) -> Path:
        """Get the application data directory"""
        return self.config_dir
    
    def get_logs_dir(self) -> Path:
        """Get the logs directory"""
        logs_dir = self.config_dir / 'logs'
        logs_dir.mkdir(exist_ok=True)
        return logs_dir
    
    def get_cache_dir(self) -> Path:
        """Get the cache directory"""
        cache_dir = self.config_dir / 'cache'
        cache_dir.mkdir(exist_ok=True)
        return cache_dir

# Global configuration manager instance
config_manager = ConfigManager()

# Convenience functions for accessing settings
def get_setting(key: str) -> Any:
    return config_manager.get_setting(key)

def set_setting(key: str, value: Any):
    config_manager.set_setting(key, value)

def get_settings() -> AppSettings:
    return config_manager.settings