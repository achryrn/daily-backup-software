import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Tuple
from ..utils.crypto import file_hasher
from ..utils.logging_config import get_logger

logger = get_logger('local_target')

class LocalTargetConnector:
    """Handles local file system backup operations"""
    
    def __init__(self):
        self.temp_dir = None
    
    def initialize(self, target_config: dict) -> bool:
        """Initialize the local target connector"""
        try:
            target_path = target_config.get('local_path')
            if not target_path:
                logger.error("No local path specified in target config")
                return False
            
            # Ensure target directory exists
            target_dir = Path(target_path)
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Create temporary directory for staging
            self.temp_dir = tempfile.mkdtemp(prefix='backup_staging_')
            
            logger.info(f"Local target initialized: {target_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize local target: {e}")
            return False
    
    def upload_file(self, source_path: str, target_path: str, 
                   conflict_policy: str = 'rename') -> Tuple[bool, Optional[str]]:
        """
        Copy a file to the local target
        
        Args:
            source_path: Path to source file
            target_path: Path where file should be copied
            conflict_policy: How to handle existing files ('rename', 'overwrite', 'skip')
            
        Returns:
            Tuple of (success: bool, final_path: Optional[str])
        """
        try:
            source = Path(source_path)
            target = Path(target_path)
            
            if not source.exists():
                logger.error(f"Source file does not exist: {source_path}")
                return False, None
            
            # Create target directory if it doesn't exist
            target.parent.mkdir(parents=True, exist_ok=True)
            
            # Handle file conflicts
            final_target = self._handle_conflict(target, conflict_policy)
            if final_target is None:
                logger.info(f"Skipped existing file: {target}")
                return True, str(target)  # Consider skip as success
            
            # Perform atomic copy using temporary file
            temp_file = final_target.parent / f".{final_target.name}.tmp"
            
            try:
                # Copy file to temporary location
                shutil.copy2(source, temp_file)
                
                # Verify integrity
                if not file_hasher.verify_file_integrity(str(source), str(temp_file)):
                    logger.error(f"Integrity check failed for {source_path}")
                    temp_file.unlink(missing_ok=True)
                    return False, None
                
                # Atomically move to final location
                temp_file.replace(final_target)
                
                logger.debug(f"Successfully copied: {source_path} -> {final_target}")
                return True, str(final_target)
                
            except Exception as e:
                # Clean up temp file on failure
                temp_file.unlink(missing_ok=True)
                raise e
                
        except Exception as e:
            logger.error(f"Failed to copy file {source_path}: {e}")
            return False, None
    
    def _handle_conflict(self, target_path: Path, policy: str) -> Optional[Path]:
        """
        Handle file name conflicts based on policy
        
        Returns:
            Path to use for the file, or None if should skip
        """
        if not target_path.exists():
            return target_path
        
        if policy == 'skip':
            return None
        elif policy == 'overwrite':
            return target_path
        elif policy == 'rename':
            # Find unique name by adding counter
            counter = 1
            stem = target_path.stem
            suffix = target_path.suffix
            
            while True:
                new_name = f"{stem}_{counter}{suffix}"
                new_path = target_path.parent / new_name
                if not new_path.exists():
                    return new_path
                counter += 1
                
                # Safety check to prevent infinite loop
                if counter > 9999:
                    logger.warning(f"Too many conflicts for {target_path}, using overwrite")
                    return target_path
        
        return target_path
    
    def create_directory(self, dir_path: str) -> bool:
        """Create a directory in the target"""
        try:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {dir_path}: {e}")
            return False
    
    def file_exists(self, file_path: str) -> bool:
        """Check if a file exists in the target"""
        return Path(file_path).exists()
    
    def get_file_info(self, file_path: str) -> Optional[dict]:
        """Get information about a file in the target"""
        try:
            path = Path(file_path)
            if not path.exists():
                return None
            
            stat = path.stat()
            return {
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'created': stat.st_ctime,
                'is_directory': path.is_dir()
            }
        except Exception as e:
            logger.error(f"Failed to get file info for {file_path}: {e}")
            return None
    
    def list_files(self, directory_path: str) -> list:
        """List files in a target directory"""
        try:
            path = Path(directory_path)
            if not path.exists() or not path.is_dir():
                return []
            
            files = []
            for item in path.iterdir():
                try:
                    info = {
                        'name': item.name,
                        'path': str(item),
                        'is_directory': item.is_dir(),
                        'size': item.stat().st_size if not item.is_dir() else 0,
                        'modified': item.stat().st_mtime
                    }
                    files.append(info)
                except Exception as e:
                    logger.warning(f"Could not get info for {item}: {e}")
            
            return files
        except Exception as e:
            logger.error(f"Failed to list files in {directory_path}: {e}")
            return []
    
    def cleanup(self):
        """Clean up temporary resources"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logger.debug(f"Cleaned up temp directory: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp directory: {e}")
    
    def __del__(self):
        """Ensure cleanup on destruction"""
        self.cleanup()