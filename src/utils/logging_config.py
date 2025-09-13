import logging
import os
from datetime import datetime
from pathlib import Path

class BackupLogger:
    def __init__(self, log_dir="logs", max_log_files=10):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.max_log_files = max_log_files
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging configuration with file rotation"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"backup_{timestamp}.log"
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Setup file handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        
        # Setup console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        
        # Configure root logger
        logger = logging.getLogger('backup_app')
        logger.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        # Clean old log files
        self.cleanup_old_logs()
        
        return logger
    
    def cleanup_old_logs(self):
        """Remove old log files, keeping only the most recent ones"""
        log_files = list(self.log_dir.glob("backup_*.log"))
        if len(log_files) > self.max_log_files:
            # Sort by modification time and remove oldest
            log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            for old_log in log_files[self.max_log_files:]:
                try:
                    old_log.unlink()
                except OSError:
                    pass
    
    def get_logger(self, name):
        """Get a logger instance for a specific module"""
        return logging.getLogger(f'backup_app.{name}')

# Global logger instance
backup_logger = BackupLogger()

def get_logger(name):
    """Convenience function to get a logger"""
    return backup_logger.get_logger(name)