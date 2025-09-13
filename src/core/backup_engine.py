import os
import json
import shutil
import hashlib
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Callable, Optional
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal, QThread, QMutex, QMutexLocker
from .database import db_manager, BackupJob, JobExecution, FileTransfer

@dataclass
class TransferItem:
    source_path: str
    target_path: str
    file_size: int
    checksum: Optional[str] = None

class BackupWorker(QThread):
    """Worker thread for backup operations to avoid GUI blocking"""
    
    progress_updated = Signal(int, int, str)
    log_message = Signal(str)
    backup_completed = Signal(bool, str)
    
    def __init__(self, job_id):
        super().__init__()
        self.job_id = job_id
        self.should_stop = False
        self.is_paused = False
        self.pause_condition = threading.Condition()
        self.mutex = QMutex()
        
    def run(self):
        """Run the backup job in a separate thread"""
        try:
            self.log_message.emit(f"Worker thread started for job {self.job_id}")
            self._execute_backup()
        except Exception as e:
            error_msg = f"Backup failed with error: {str(e)}"
            self.log_message.emit(error_msg)
            self.backup_completed.emit(False, error_msg)
        finally:
            self.log_message.emit("Worker thread finishing")
    
    def stop(self):
        """Request the backup to stop"""
        with QMutexLocker(self.mutex):
            self.should_stop = True
            self.log_message.emit("Stop requested for backup worker")
        
        # Wake up thread if it's paused
        with self.pause_condition:
            self.pause_condition.notify()
    

    def pause(self):
            """Pause the backup operation"""
            try:
                with QMutexLocker(self.mutex):
                    if not self.is_paused:
                        self.is_paused = True
                        self.log_message.emit("Backup worker paused")
                    else:
                        self.log_message.emit("Backup worker was already paused")
            except Exception as e:
                self.log_message.emit(f"Error in worker pause: {e}")
                raise
        
    def resume(self):
        """Resume the backup operation"""
        try:
            with QMutexLocker(self.mutex):
                if self.is_paused:
                    self.is_paused = False
                    self.log_message.emit("Backup worker resumed")
                else:
                    self.log_message.emit("Backup worker was not paused")
            
            # Wake up the paused thread
            with self.pause_condition:
                self.pause_condition.notify()
        except Exception as e:
            self.log_message.emit(f"Error in worker resume: {e}")
            raise
        
    def _check_pause_stop(self):
        """Check if we should pause or stop, and handle accordingly"""
        with QMutexLocker(self.mutex):
            if self.should_stop:
                return True  # Should stop
            
            if self.is_paused:
                self.log_message.emit("Backup paused - waiting for resume...")
                
        # Handle pause outside of mutex to avoid deadlock
        while True:
            with QMutexLocker(self.mutex):
                if not self.is_paused or self.should_stop:
                    break
            
            with self.pause_condition:
                self.pause_condition.wait(1.0)  # Wait up to 1 second
        
        with QMutexLocker(self.mutex):
            return self.should_stop
    
    def _execute_backup(self):
        """Execute the actual backup logic"""
        session = db_manager.get_session()
        
        try:
            job = session.query(BackupJob).filter_by(id=self.job_id).first()
            if not job:
                self.log_message.emit(f"Job {self.job_id} not found")
                self.backup_completed.emit(False, "Job not found")
                return
                
            self.log_message.emit(f"Starting backup job: {job.name}")
            
            # Check for existing paused execution
            existing_execution = session.query(JobExecution).filter_by(
                job_id=self.job_id, 
                status='paused'
            ).order_by(JobExecution.started_at.desc()).first()
            
            if existing_execution:
                self.log_message.emit("Resuming from previous paused execution")
                execution = existing_execution
                execution.status = 'running'
                # Get already processed files
                completed_transfers = session.query(FileTransfer).filter_by(
                    execution_id=execution.id,
                    status='completed'
                ).all()
                completed_paths = {t.source_path for t in completed_transfers}
            else:
                execution = JobExecution(
                    job_id=self.job_id,
                    status='running',
                    started_at=datetime.utcnow()
                )
                session.add(execution)
                completed_paths = set()
            
            session.commit()
            
            # Scan sources
            self.log_message.emit("Scanning source files...")
            if self._check_pause_stop():
                self._handle_pause_or_stop(execution, session)
                return
                
            source_files = self._scan_sources(job)
            
            if not source_files:
                self.log_message.emit("No files found to backup")
                execution.status = 'completed'
                execution.completed_at = datetime.utcnow()
                session.commit()
                self.backup_completed.emit(True, "No files to backup")
                return
            
            # Filter out already completed files
            remaining_files = [f for f in source_files if f not in completed_paths]
            
            self.log_message.emit(f"Found {len(source_files)} total files, {len(remaining_files)} remaining")
            
            # Plan transfers for remaining files
            transfer_items = self._plan_transfers(job, remaining_files)
            
            # Update execution totals if this is a new execution
            if not existing_execution:
                execution.total_files = len(source_files)
                execution.total_size = sum(item.file_size for item in self._plan_transfers(job, source_files))
            
            session.commit()
            
            if not transfer_items:
                self.log_message.emit("All files already completed")
                execution.status = 'completed'
                execution.completed_at = datetime.utcnow()
                session.commit()
                self.backup_completed.emit(True, "Backup already completed")
                return
            
            self.log_message.emit(f"Starting transfer of {len(transfer_items)} remaining files...")
            
            # Execute transfers
            successful_transfers = len(completed_paths)
            failed_transfers = execution.failed_files or 0
            
            for i, item in enumerate(transfer_items):
                if self._check_pause_stop():
                    self._handle_pause_or_stop(execution, session)
                    return
                    
                current_progress = successful_transfers + failed_transfers + i
                total_files = execution.total_files
                
                self.progress_updated.emit(
                    current_progress, 
                    total_files, 
                    f"Copying {os.path.basename(item.source_path)}"
                )
                
                if self._execute_local_transfer(item, execution.id):
                    successful_transfers += 1
                    execution.transferred_size += item.file_size
                    self.log_message.emit(f"Successfully copied: {os.path.basename(item.source_path)}")
                else:
                    failed_transfers += 1
                    self.log_message.emit(f"Failed to copy: {os.path.basename(item.source_path)}")
                
                execution.processed_files = successful_transfers + failed_transfers
                execution.failed_files = failed_transfers
                session.commit()
                
                # Small delay to prevent overwhelming the system
                self.msleep(50)
            
            # Complete the job
            with QMutexLocker(self.mutex):
                if not self.should_stop and not self.is_paused:
                    execution.status = 'completed' if failed_transfers == 0 else 'completed_with_errors'
                    execution.completed_at = datetime.utcnow()
                    session.commit()
                    
                    status_msg = f"Backup completed: {successful_transfers} successful, {failed_transfers} failed"
                    self.log_message.emit(status_msg)
                    self.progress_updated.emit(execution.total_files, execution.total_files, "Backup completed")
                    self.backup_completed.emit(True, status_msg)
                else:
                    self._handle_pause_or_stop(execution, session)
        
        except Exception as e:
            error_msg = f"Backup failed: {str(e)}"
            self.log_message.emit(error_msg)
            try:
                execution.status = 'failed'
                execution.error_message = str(e)
                execution.completed_at = datetime.utcnow()
                session.commit()
            except:
                pass
            self.backup_completed.emit(False, error_msg)
        finally:
            session.close()
    
    def _handle_pause_or_stop(self, execution, session):
        """Handle pause or stop request"""
        with QMutexLocker(self.mutex):
            if self.should_stop:
                execution.status = 'cancelled'
                execution.completed_at = datetime.utcnow()
                session.commit()
                self.log_message.emit("Backup cancelled by user")
                self.backup_completed.emit(False, "Cancelled by user")
            elif self.is_paused:
                execution.status = 'paused'
                session.commit()
                self.log_message.emit("Backup paused and saved")
                self.backup_completed.emit(True, "Backup paused")
    
    def _scan_sources(self, job: BackupJob) -> List[str]:
        """Scan source directories for files"""
        sources = json.loads(job.sources)
        include_patterns = job.include_patterns.split(';') if job.include_patterns else []
        exclude_patterns = job.exclude_patterns.split(';') if job.exclude_patterns else []
        
        all_files = []
        
        for source in sources:
            if self._check_pause_stop():
                break
                
            source_path = Path(source)
            
            if source_path.is_file():
                if self._should_include_file(str(source_path), include_patterns, exclude_patterns):
                    all_files.append(str(source_path))
            elif source_path.is_dir():
                for root, dirs, files in os.walk(source_path):
                    if self._check_pause_stop():
                        break
                    for file in files:
                        file_path = os.path.join(root, file)
                        if self._should_include_file(file_path, include_patterns, exclude_patterns):
                            all_files.append(file_path)
        
        return all_files
    
    def _should_include_file(self, file_path: str, include_patterns: List[str], exclude_patterns: List[str]) -> bool:
        """Check if file should be included based on patterns"""
        import fnmatch
        
        file_name = os.path.basename(file_path)
        
        if exclude_patterns:
            for pattern in exclude_patterns:
                pattern = pattern.strip()
                if pattern and (fnmatch.fnmatch(file_name, pattern) or fnmatch.fnmatch(file_path, pattern)):
                    return False
        
        if include_patterns:
            for pattern in include_patterns:
                pattern = pattern.strip()
                if pattern and (fnmatch.fnmatch(file_name, pattern) or fnmatch.fnmatch(file_path, pattern)):
                    return True
            return False
        
        return True
    
    def _plan_transfers(self, job: BackupJob, source_files: List[str]) -> List[TransferItem]:
        """Plan the transfer operations"""
        target_config = json.loads(job.target_config)
        transfer_items = []
        
        if job.target_type == "local":
            base_target = Path(target_config["local_path"])
            
            for source_file in source_files:
                if self._check_pause_stop():
                    break
                    
                source_path = Path(source_file)
                
                relative_path = source_path.name
                target_path = base_target / job.name / relative_path
                
                if job.conflict_policy == "rename" and target_path.exists():
                    counter = 1
                    stem = target_path.stem
                    suffix = target_path.suffix
                    while target_path.exists():
                        target_path = target_path.parent / f"{stem}_{counter}{suffix}"
                        counter += 1
                
                try:
                    file_size = source_path.stat().st_size
                    transfer_items.append(TransferItem(
                        source_path=str(source_path),
                        target_path=str(target_path),
                        file_size=file_size
                    ))
                except (OSError, IOError) as e:
                    self.log_message.emit(f"Error accessing {source_file}: {e}")
        
        return transfer_items
    
    def _execute_local_transfer(self, item: TransferItem, execution_id: int) -> bool:
        """Execute a single file transfer"""
        session = db_manager.get_session()
        transfer_record = None
        
        try:
            # Check if this transfer already exists and is completed
            existing_transfer = session.query(FileTransfer).filter_by(
                execution_id=execution_id,
                source_path=item.source_path,
                status='completed'
            ).first()
            
            if existing_transfer:
                return True  # Already completed
            
            transfer_record = FileTransfer(
                execution_id=execution_id,
                source_path=item.source_path,
                target_path=item.target_path,
                file_size=item.file_size,
                status='in_progress',
                started_at=datetime.utcnow()
            )
            session.add(transfer_record)
            session.commit()
            
            target_path = Path(item.target_path)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            temp_target = target_path.parent / f"{target_path.name}.tmp"
            
            # Copy file
            shutil.copy2(item.source_path, str(temp_target))
            
            # Verify checksum
            source_checksum = self._calculate_checksum(item.source_path)
            target_checksum = self._calculate_checksum(str(temp_target))
            
            if source_checksum and source_checksum == target_checksum:
                temp_target.rename(target_path)
                
                transfer_record.status = 'completed'
                transfer_record.checksum = source_checksum
                transfer_record.transferred_bytes = item.file_size
                transfer_record.completed_at = datetime.utcnow()
                session.commit()
                
                return True
            else:
                temp_target.unlink(missing_ok=True)
                raise Exception("Checksum verification failed")
                
        except Exception as e:
            if transfer_record:
                transfer_record.status = 'failed'
                transfer_record.error_message = str(e)
                transfer_record.completed_at = datetime.utcnow()
                session.commit()
            
            return False
        finally:
            session.close()
    
    def _calculate_checksum(self, file_path: str, chunk_size: int = 8192) -> str:
        """Calculate SHA256 checksum of a file"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except (IOError, OSError):
            return ""

class BackupEngine(QObject):
    """Main backup engine with proper Qt threading support"""
    
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.is_paused = False
        self.current_worker = None
        self.current_execution = None
        self.current_job_id = None
        self.progress_callback: Optional[Callable] = None
        self.log_callback: Optional[Callable] = None
        
    def set_progress_callback(self, callback: Callable[[int, int, str], None]):
        self.progress_callback = callback
        
    def set_log_callback(self, callback: Callable[[str], None]):
        self.log_callback = callback
        
    def log(self, message: str):
        if self.log_callback:
            self.log_callback(message)
            
    def update_progress(self, current: int, total: int, status: str):
        if self.progress_callback:
            self.progress_callback(current, total, status)
    
    def run_backup_job_async(self, job_id: int):
        """Start backup job in a worker thread"""
        if self.is_running:
            self.log("Another backup is already running")
            return False
        
        self.log(f"Starting backup worker for job {job_id}")
        
        # Store the current job ID for status tracking
        self.current_job_id = job_id
        self.is_paused = False
        
        # Create and configure worker
        self.current_worker = BackupWorker(job_id)
        
        # Connect signals
        self.current_worker.progress_updated.connect(self._on_progress_updated)
        self.current_worker.log_message.connect(self._on_log_message)
        self.current_worker.backup_completed.connect(self._on_backup_completed)
        self.current_worker.finished.connect(self._on_worker_finished)
        
        # Start the worker
        self.is_running = True
        self.current_worker.start()
        
        return True
    
    def pause_backup(self):
            """Pause the currently running backup"""
            if not self.is_running:
                self.log("No backup is currently running")
                return False
                
            if not self.current_worker:
                self.log("No worker thread found")
                return False
                
            if self.is_paused:
                self.log("Backup is already paused")
                return True
            
            try:
                self.log("Pausing backup...")
                self.is_paused = True
                self.current_worker.pause()
                return True
            except Exception as e:
                self.log(f"Failed to pause backup: {e}")
                self.is_paused = False
                return False
    
    def resume_backup(self):
        """Resume a paused backup"""
        if not self.is_running:
            self.log("No backup is currently running")
            return False
            
        if not self.current_worker:
            self.log("No worker thread found")
            return False
            
        if not self.is_paused:
            self.log("Backup is not paused")
            return True
        
        try:
            self.log("Resuming backup...")
            self.is_paused = False
            self.current_worker.resume()
            return True
        except Exception as e:
            self.log(f"Failed to resume backup: {e}")
            return False
    
    def _on_progress_updated(self, current: int, total: int, status: str):
        """Handle progress updates from worker thread"""
        self.update_progress(current, total, status)
    
    def _on_log_message(self, message: str):
        """Handle log messages from worker thread"""
        self.log(message)
    
    def _on_backup_completed(self, success: bool, message: str):
        """Handle backup completion"""
        self.log(f"Backup completed: {message}")
        if self.progress_callback:
            self.progress_callback(0, 0, "")  # Clear progress
        
        # Check if there are more paused backups to resume
        try:
            paused_executions = db_manager.get_paused_executions()
            if paused_executions and not self.is_running:  # Only if no backup is currently running
                QTimer.singleShot(5000, lambda: self.activity_panel.refresh_paused_jobs())
        except Exception as e:
            self.log(f"Error checking for additional paused backups: {e}")
        
    def _on_worker_finished(self):
        """Handle worker thread finishing"""
        self.is_running = False
        self.is_paused = False
        self.current_execution = None
        self.current_job_id = None
        
        if self.current_worker:
            self.log("Cleaning up worker thread")
            self.current_worker.wait(5000)  # Wait max 5 seconds
            self.current_worker.deleteLater()
            self.current_worker = None
    
    def stop_backup(self):
        """Stop the currently running backup"""
        if self.is_running and self.current_worker:
            self.log("Requesting backup stop...")
            self.current_worker.stop()
    
    def get_current_job_id(self):
        """Get the ID of the currently running job"""
        return self.current_job_id

backup_engine = BackupEngine()