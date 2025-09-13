from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timedelta
import os
import sqlite3

Base = declarative_base()

class BackupJob(Base):
    __tablename__ = 'backup_jobs'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    sources = Column(Text, nullable=False)
    include_patterns = Column(Text)
    exclude_patterns = Column(Text)
    target_type = Column(String(50), nullable=False)
    target_config = Column(Text)
    conflict_policy = Column(String(50), default='rename')
    schedule_cron = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    executions = relationship("JobExecution", back_populates="job", cascade="all, delete-orphan")

class JobExecution(Base):
    __tablename__ = 'job_executions'
    
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey('backup_jobs.id'), nullable=False)
    status = Column(String(50), default='pending')  # pending, running, paused, completed, completed_with_errors, failed, cancelled
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    paused_at = Column(DateTime)  # New field for pause tracking
    resumed_at = Column(DateTime)  # New field for resume tracking
    total_files = Column(Integer, default=0)
    processed_files = Column(Integer, default=0)
    failed_files = Column(Integer, default=0)
    total_size = Column(Float, default=0.0)
    transferred_size = Column(Float, default=0.0)
    error_message = Column(Text)
    
    job = relationship("BackupJob", back_populates="executions")
    file_transfers = relationship("FileTransfer", back_populates="execution", cascade="all, delete-orphan")
    
    def get_progress_percentage(self):
        """Calculate progress percentage"""
        if self.total_files == 0:
            return 0
        return min(100, int((self.processed_files / self.total_files) * 100))
    
    def get_transfer_rate_mb_per_sec(self):
        """Calculate transfer rate in MB/s"""
        if not self.started_at or self.transferred_size == 0:
            return 0
        
        end_time = self.completed_at or datetime.utcnow()
        duration = (end_time - self.started_at).total_seconds()
        
        if duration == 0:
            return 0
        
        return (self.transferred_size / (1024 * 1024)) / duration

class FileTransfer(Base):
    __tablename__ = 'file_transfers'
    
    id = Column(Integer, primary_key=True)
    execution_id = Column(Integer, ForeignKey('job_executions.id'), nullable=False)
    source_path = Column(Text, nullable=False)
    target_path = Column(Text)
    file_size = Column(Float)
    checksum = Column(String(64))
    status = Column(String(50), default='pending')  # pending, in_progress, completed, failed, skipped
    transferred_bytes = Column(Float, default=0.0)
    retry_count = Column(Integer, default=0)
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    execution = relationship("JobExecution", back_populates="file_transfers")

class DatabaseManager:
    def __init__(self, db_path="backup_app.db"):
        self.db_path = os.path.abspath(db_path)
        
        # Check if we need to migrate the database
        self._migrate_database_if_needed()
        
        self.engine = create_engine(f'sqlite:///{self.db_path}')
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def _migrate_database_if_needed(self):
        """Migrate database schema if needed"""
        if not os.path.exists(self.db_path):
            return  # New database, no migration needed
        
        try:
            # Connect directly with sqlite3 to check and modify schema
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if new columns exist
            cursor.execute("PRAGMA table_info(job_executions)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Add missing columns
            if 'paused_at' not in columns:
                cursor.execute("ALTER TABLE job_executions ADD COLUMN paused_at TIMESTAMP")
                print("Added paused_at column to job_executions table")
            
            if 'resumed_at' not in columns:
                cursor.execute("ALTER TABLE job_executions ADD COLUMN resumed_at TIMESTAMP")
                print("Added resumed_at column to job_executions table")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Database migration error (non-critical): {e}")
            # Continue anyway - SQLAlchemy will handle it
    
    def get_session(self):
        return self.SessionLocal()
    
    def close(self):
        self.engine.dispose()
    
    def get_paused_executions(self):
        """Get all paused executions that can be resumed"""
        session = self.get_session()
        try:
            return session.query(JobExecution).filter_by(status='paused').all()
        finally:
            session.close()
    
    def cleanup_old_executions(self, days_to_keep=30):
        """Clean up old completed/failed executions"""
        session = self.get_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            old_executions = session.query(JobExecution).filter(
                JobExecution.completed_at < cutoff_date,
                JobExecution.status.in_(['completed', 'failed', 'cancelled'])
            ).all()
            
            for execution in old_executions:
                session.delete(execution)
            
            session.commit()
            return len(old_executions)
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

db_manager = DatabaseManager()