import sys
from datetime import datetime, timedelta
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QTableWidget, QTableWidgetItem, QProgressBar,
                               QLabel, QFrame, QSplitter, QTextEdit, QTabWidget,
                               QTreeWidget, QTreeWidgetItem, QHeaderView, QMessageBox,
                               QMenu, QMenuBar, QStatusBar, QListWidget, QListWidgetItem,
                               QApplication)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QIcon, QFont, QPalette, QColor, QAction
from .job_wizard import JobWizard
from ..core.database import db_manager, BackupJob, JobExecution
from ..core.backup_engine import backup_engine
from ..utils.logging_config import get_logger

logger = get_logger('main_window')

class ModernButton(QPushButton):
    def __init__(self, text, primary=False):
        super().__init__(text)
        self.setMinimumHeight(36)
        if primary:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-weight: 500;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #106ebe;
                }
                QPushButton:pressed {
                    background-color: #005a9e;
                }
                QPushButton:disabled {
                    background-color: #c8c6c4;
                    color: #a19f9d;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #f3f2f1;
                    color: #323130;
                    border: 1px solid #d2d0ce;
                    border-radius: 6px;
                    font-weight: 400;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #edebe9;
                    border-color: #8a8886;
                }
                QPushButton:pressed {
                    background-color: #e1dfdd;
                }
                QPushButton:disabled {
                    background-color: #f3f2f1;
                    color: #a19f9d;
                    border-color: #d2d0ce;
                }
            """)

class JobsPanel(QWidget):
    job_selected = Signal(int)
    
    def __init__(self):
        super().__init__()
        self.selected_job_id = None
        self.init_ui()
        self.refresh_jobs()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header with title and buttons
        header_layout = QHBoxLayout()
        title = QLabel("Backup Jobs")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # Action buttons
        self.run_job_btn = ModernButton("Run Job")
        self.run_job_btn.clicked.connect(self.run_selected_job)
        self.run_job_btn.setEnabled(False)
        header_layout.addWidget(self.run_job_btn)
        
        self.new_job_btn = ModernButton("New Job", primary=True)
        self.new_job_btn.clicked.connect(self.create_new_job)
        header_layout.addWidget(self.new_job_btn)
        
        layout.addLayout(header_layout)
        
        # Jobs table
        self.jobs_table = QTableWidget()
        self.jobs_table.setColumnCount(5)
        self.jobs_table.setHorizontalHeaderLabels(["Name", "Target", "Status", "Last Run", "Files"])
        self.jobs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.jobs_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.jobs_table.cellClicked.connect(self.on_job_selected)
        
        # Context menu for jobs table
        self.jobs_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.jobs_table.customContextMenuRequested.connect(self.show_context_menu)
        
        self.jobs_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #d2d0ce;
                border-radius: 6px;
                background-color: white;
                gridline-color: #f3f2f1;
                selection-background-color: #deecf9;
            }
            QHeaderView::section {
                background-color: #f8f8f8;
                border: none;
                border-bottom: 1px solid #d2d0ce;
                padding: 8px;
                font-weight: 500;
            }
        """)
        
        layout.addWidget(self.jobs_table)
        self.setLayout(layout)
    
    def show_context_menu(self, position):
        """Show context menu for job operations"""
        if self.jobs_table.itemAt(position):
            menu = QMenu(self)
            
            run_action = QAction("Run Job", self)
            run_action.triggered.connect(self.run_selected_job)
            run_action.setEnabled(self.selected_job_id is not None)
            menu.addAction(run_action)
            
            menu.addSeparator()
            
            edit_action = QAction("Edit Job", self)
            edit_action.triggered.connect(self.edit_selected_job)
            edit_action.setEnabled(self.selected_job_id is not None)
            menu.addAction(edit_action)
            
            delete_action = QAction("Delete Job", self)
            delete_action.triggered.connect(self.delete_selected_job)
            delete_action.setEnabled(self.selected_job_id is not None)
            menu.addAction(delete_action)
            
            menu.exec(self.jobs_table.mapToGlobal(position))
    
    def create_new_job(self):
        wizard = JobWizard(self)
        if wizard.exec() == JobWizard.DialogCode.Accepted:
            self.refresh_jobs()
    
    def run_selected_job(self):
        """Run the currently selected job"""
        if self.selected_job_id:
            if backup_engine.is_running:
                QMessageBox.warning(self, "Backup Running", 
                                  "Another backup is already running. Please wait for it to complete.")
                return
            
            session = db_manager.get_session()
            try:
                job = session.query(BackupJob).filter_by(id=self.selected_job_id).first()
                if job:
                    reply = QMessageBox.question(self, "Run Backup Job", 
                                               f"Are you sure you want to run '{job.name}'?",
                                               QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    
                    if reply == QMessageBox.StandardButton.Yes:
                        logger.info(f"Starting backup job: {job.name}")
                        backup_engine.run_backup_job_async(self.selected_job_id)
                        
                        # Refresh the table to show updated status
                        QTimer.singleShot(1000, self.refresh_jobs)
            finally:
                session.close()
    
    def edit_selected_job(self):
        """Edit the currently selected job"""
        if self.selected_job_id:
            QMessageBox.information(self, "Coming Soon", 
                                  "Job editing functionality will be added in the next release.")
    
    def delete_selected_job(self):
        """Delete the currently selected job"""
        if self.selected_job_id:
            session = db_manager.get_session()
            try:
                job = session.query(BackupJob).filter_by(id=self.selected_job_id).first()
                if job:
                    reply = QMessageBox.question(self, "Delete Job", 
                                               f"Are you sure you want to delete '{job.name}'?\n"
                                               "This action cannot be undone.",
                                               QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    
                    if reply == QMessageBox.StandardButton.Yes:
                        job.is_active = False  # Soft delete
                        session.commit()
                        logger.info(f"Deleted backup job: {job.name}")
                        self.refresh_jobs()
                        self.selected_job_id = None
                        self.run_job_btn.setEnabled(False)
            finally:
                session.close()
    
    def on_job_selected(self, row, column):
        job_id = self.jobs_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if job_id:
            self.selected_job_id = job_id
            self.run_job_btn.setEnabled(not backup_engine.is_running)
            self.job_selected.emit(job_id)
    
    def refresh_jobs(self):
            session = db_manager.get_session()
            try:
                jobs = session.query(BackupJob).filter_by(is_active=True).all()
                self.jobs_table.setRowCount(len(jobs))
                
                for i, job in enumerate(jobs):
                    # Job name
                    name_item = QTableWidgetItem(job.name)
                    name_item.setData(Qt.ItemDataRole.UserRole, job.id)
                    self.jobs_table.setItem(i, 0, name_item)
                    
                    # Target type
                    self.jobs_table.setItem(i, 1, QTableWidgetItem(job.target_type.title()))
                    
                    # Status - check if this job is currently running
                    status = "Active"
                    if backup_engine.is_running:
                        current_job_id = backup_engine.get_current_job_id()
                        if current_job_id == job.id:
                            status = "Running"
                    self.jobs_table.setItem(i, 2, QTableWidgetItem(status))
                    
                    # Last run
                    last_execution = session.query(JobExecution).filter_by(job_id=job.id).order_by(JobExecution.started_at.desc()).first()
                    if last_execution:
                        last_run = last_execution.started_at.strftime("%Y-%m-%d %H:%M")
                        if last_execution.status == 'failed':
                            last_run += " (Failed)"
                        elif last_execution.status == 'completed_with_errors':
                            last_run += " (Errors)"
                    else:
                        last_run = "Never"
                    self.jobs_table.setItem(i, 3, QTableWidgetItem(last_run))
                    
                    # File count from last execution
                    file_count = last_execution.total_files if last_execution else 0
                    self.jobs_table.setItem(i, 4, QTableWidgetItem(str(file_count)))
                    
            except Exception as e:
                logger.error(f"Error refreshing jobs: {e}")
            finally:
                session.close()

class ActivityPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Current Activity")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        layout.addWidget(title)
        
        # Progress section
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #d2d0ce;
                border-radius: 6px;
                text-align: center;
                height: 24px;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("No active backups")
        self.status_label.setStyleSheet("color: #605e5c; font-size: 13px; margin: 4px 0;")
        layout.addWidget(self.status_label)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        
        self.pause_btn = ModernButton("Pause")
        self.pause_btn.clicked.connect(self.pause_backup)
        self.pause_btn.setVisible(False)
        controls_layout.addWidget(self.pause_btn)
        
        self.resume_btn = ModernButton("Resume", primary=True)
        self.resume_btn.clicked.connect(self.resume_backup)
        self.resume_btn.setVisible(False)
        controls_layout.addWidget(self.resume_btn)
        
        self.stop_btn = ModernButton("Stop")
        self.stop_btn.clicked.connect(self.stop_backup)
        self.stop_btn.setVisible(False)
        controls_layout.addWidget(self.stop_btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Resume section for paused backups
        self.resume_section = QWidget()
        self.resume_section.setVisible(False)
        resume_layout = QVBoxLayout()
        
        resume_label = QLabel("Paused Backups")
        resume_label.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        resume_layout.addWidget(resume_label)
        
        self.paused_jobs_list = QListWidget()
        self.paused_jobs_list.setMaximumHeight(100)
        self.paused_jobs_list.itemDoubleClicked.connect(self.resume_paused_job)
        resume_layout.addWidget(self.paused_jobs_list)
        
        resume_buttons_layout = QHBoxLayout()
        self.resume_selected_btn = ModernButton("Resume Selected", primary=True)
        self.resume_selected_btn.clicked.connect(self.resume_selected_paused_job)
        resume_buttons_layout.addWidget(self.resume_selected_btn)
        
        self.cancel_paused_btn = ModernButton("Cancel Selected")
        self.cancel_paused_btn.clicked.connect(self.cancel_paused_job)
        resume_buttons_layout.addWidget(self.cancel_paused_btn)
        resume_buttons_layout.addStretch()
        
        resume_layout.addLayout(resume_buttons_layout)
        self.resume_section.setLayout(resume_layout)
        layout.addWidget(self.resume_section)
        
        # Activity log
        log_label = QLabel("Activity Log")
        log_label.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        log_label.setStyleSheet("margin-top: 16px; margin-bottom: 8px;")
        layout.addWidget(log_label)
        
        self.activity_log = QTextEdit()
        self.activity_log.setReadOnly(True)
        self.activity_log.setStyleSheet("""
            QTextEdit {
                border: 1px solid #d2d0ce;
                border-radius: 6px;
                background-color: #faf9f8;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.activity_log)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # Load paused jobs on initialization
        self.refresh_paused_jobs()
    
    def pause_backup(self):
            """Pause the currently running backup"""
            try:
                if not backup_engine.is_running:
                    QMessageBox.information(self, "No Active Backup", "There is no backup currently running to pause.")
                    return
                    
                if backup_engine.is_paused:
                    QMessageBox.information(self, "Already Paused", "The backup is already paused.")
                    return
                
                self.add_log_entry("Requesting backup pause...")
                
                if backup_engine.pause_backup():
                    self.add_log_entry("Backup paused successfully")
                    self.update_button_states()
                else:
                    self.add_log_entry("Failed to pause backup")
                    QMessageBox.warning(self, "Pause Failed", "Could not pause backup. Please try again.")
                    
            except Exception as e:
                error_msg = f"Error pausing backup: {e}"
                self.add_log_entry(error_msg)
                QMessageBox.critical(self, "Pause Error", f"An error occurred while pausing:\n{str(e)}")
        
    def resume_backup(self):
        """Resume the currently paused backup"""
        try:
            if not backup_engine.is_running:
                QMessageBox.information(self, "No Active Backup", "There is no backup currently running to resume.")
                return
                
            if not backup_engine.is_paused:
                QMessageBox.information(self, "Not Paused", "The backup is not currently paused.")
                return
            
            self.add_log_entry("Requesting backup resume...")
            
            if backup_engine.resume_backup():
                self.add_log_entry("Backup resumed successfully")
                self.update_button_states()
            else:
                self.add_log_entry("Failed to resume backup")
                QMessageBox.warning(self, "Resume Failed", "Could not resume backup. Please try again.")
                
        except Exception as e:
            error_msg = f"Error resuming backup: {e}"
            self.add_log_entry(error_msg)
            QMessageBox.critical(self, "Resume Error", f"An error occurred while resuming:\n{str(e)}")
    
    def stop_backup(self):
        """Stop the currently running backup"""
        try:
            if not backup_engine.is_running:
                QMessageBox.information(self, "No Active Backup", "There is no backup currently running to stop.")
                return
            
            reply = QMessageBox.question(self, "Stop Backup", 
                                       "Are you sure you want to stop the current backup?\n"
                                       "You can resume it later from where it left off.",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                self.add_log_entry("Requesting backup stop...")
                backup_engine.stop_backup()
                self.update_button_states()
                
        except Exception as e:
            error_msg = f"Error stopping backup: {e}"
            self.add_log_entry(error_msg)
            QMessageBox.critical(self, "Stop Error", f"An error occurred while stopping:\n{str(e)}")
    def refresh_paused_jobs(self):
        """Refresh the list of paused jobs"""
        try:
            paused_executions = db_manager.get_paused_executions()
            
            self.paused_jobs_list.clear()
            
            if paused_executions:
                self.resume_section.setVisible(True)
                
                session = db_manager.get_session()
                try:
                    for execution in paused_executions:
                        job = session.query(BackupJob).filter_by(id=execution.job_id).first()
                        if job:
                            progress_pct = execution.get_progress_percentage()
                            item_text = f"{job.name} ({progress_pct}% complete)"
                            
                            item = QListWidgetItem(item_text)
                            item.setData(Qt.ItemDataRole.UserRole, execution.id)
                            self.paused_jobs_list.addItem(item)
                finally:
                    session.close()
            else:
                self.resume_section.setVisible(False)
        except Exception as e:
            logger.error(f"Error refreshing paused jobs: {e}")
    
    def mark_as_resumed(self, job_name):
        """Mark the current activity as a resumed backup"""
        self.add_log_entry(f"📄 RESUMED: {job_name} (continuing from previous session)")
        
        # Update status label to show it's resumed
        current_text = self.status_label.text()
        if "No active backups" not in current_text:
            self.status_label.setText(f"RESUMED - {current_text}")

    
    def resume_paused_job(self, item):
        """Resume a paused job (double-click handler)"""
        self.resume_selected_paused_job()
    
    def resume_selected_paused_job(self):
        """Resume the selected paused job"""
        current_item = self.paused_jobs_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "No Selection", "Please select a paused backup to resume.")
            return
        
        if backup_engine.is_running:
            QMessageBox.warning(self, "Backup Running", 
                              "Another backup is already running. Please wait for it to complete.")
            return
        
        execution_id = current_item.data(Qt.ItemDataRole.UserRole)
        
        session = db_manager.get_session()
        try:
            execution = session.query(JobExecution).filter_by(id=execution_id).first()
            if execution:
                job_id = execution.job_id
                job = session.query(BackupJob).filter_by(id=job_id).first()
                
                if job:
                    reply = QMessageBox.question(self, "Resume Backup", 
                                               f"Resume backup job '{job.name}'?",
                                               QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    
                    if reply == QMessageBox.StandardButton.Yes:
                        self.add_log_entry(f"Resuming paused backup: {job.name}")
                        backup_engine.run_backup_job_async(job_id)
                        self.refresh_paused_jobs()
        finally:
            session.close()
    
    def cancel_paused_job(self):
        """Cancel the selected paused job"""
        current_item = self.paused_jobs_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "No Selection", "Please select a paused backup to cancel.")
            return
        
        execution_id = current_item.data(Qt.ItemDataRole.UserRole)
        
        session = db_manager.get_session()
        try:
            execution = session.query(JobExecution).filter_by(id=execution_id).first()
            if execution:
                job = session.query(BackupJob).filter_by(id=execution.job_id).first()
                job_name = job.name if job else "Unknown"
                
                reply = QMessageBox.question(self, "Cancel Paused Backup", 
                                           f"Are you sure you want to cancel the paused backup '{job_name}'?\n"
                                           "This will mark it as cancelled and it cannot be resumed.",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                
                if reply == QMessageBox.StandardButton.Yes:
                    execution.status = 'cancelled'
                    execution.completed_at = datetime.utcnow()
                    session.commit()
                    
                    self.add_log_entry(f"Cancelled paused backup: {job_name}")
                    self.refresh_paused_jobs()
        finally:
            session.close()
    
    def update_button_states(self):
        """Update button visibility based on backup state"""
        if backup_engine.is_running:
            if backup_engine.is_paused:
                self.pause_btn.setVisible(False)
                self.resume_btn.setVisible(True)
                self.stop_btn.setVisible(True)
            else:
                self.pause_btn.setVisible(True)
                self.resume_btn.setVisible(False)
                self.stop_btn.setVisible(True)
        else:
            self.pause_btn.setVisible(False)
            self.resume_btn.setVisible(False)
            self.stop_btn.setVisible(False)
    
    def update_progress(self, current, total, status_text):
        """Update the progress display"""
        if total > 0:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(int(current / total * 100))
            
            # Show pause/resume status in the label
            if backup_engine.is_paused:
                self.status_label.setText(f"PAUSED - {status_text} ({current}/{total})")
            else:
                self.status_label.setText(f"{status_text} ({current}/{total})")
            
            self.update_button_states()
        else:
            self.progress_bar.setVisible(False)
            self.status_label.setText("No active backups")
            self.update_button_states()
    
    def add_log_entry(self, message):
        """Add an entry to the activity log"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.activity_log.append(f"[{timestamp}] {message}")
        
        # Auto-scroll to bottom
        scrollbar = self.activity_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setup_timer()
        self.setup_menu()
        self.setup_shutdown_protection()
        QTimer.singleShot(2000, self.check_and_offer_resume) 
        
    def init_ui(self):
        self.setWindowTitle("Backup Manager Pro")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f8f8;
            }
            QFrame {
                background-color: white;
                border: 1px solid #d2d0ce;
                border-radius: 8px;
            }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(12, 12, 12, 12)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Jobs panel frame
        jobs_frame = QFrame()
        jobs_layout = QVBoxLayout()
        jobs_layout.setContentsMargins(16, 16, 16, 16)
        self.jobs_panel = JobsPanel()
        self.jobs_panel.job_selected.connect(self.on_job_selected)
        jobs_layout.addWidget(self.jobs_panel)
        jobs_frame.setLayout(jobs_layout)
        
        # Activity panel frame
        activity_frame = QFrame()
        activity_layout = QVBoxLayout()
        activity_layout.setContentsMargins(16, 16, 16, 16)
        self.activity_panel = ActivityPanel()
        activity_layout.addWidget(self.activity_panel)
        activity_frame.setLayout(activity_layout)
        
        splitter.addWidget(jobs_frame)
        splitter.addWidget(activity_frame)
        splitter.setSizes([600, 400])
        
        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        self.activity_panel.add_log_entry("Backup Manager started")
    
    def setup_shutdown_protection(self):
        """Setup system shutdown protection when backup is running"""
        try:
            import signal
            import sys
            
            # Handle common shutdown signals
            if hasattr(signal, 'SIGTERM'):
                signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
            if hasattr(signal, 'SIGINT'):
                signal.signal(signal.SIGINT, self._handle_shutdown_signal)
                
            # On Windows, handle console close events
            if sys.platform == "win32":
                try:
                    import win32api
                    win32api.SetConsoleCtrlHandler(self._handle_console_ctrl, True)
                except ImportError:
                    pass  # win32api not available
                    
        except Exception as e:
            logger.warning(f"Could not setup shutdown protection: {e}")
    
    def _handle_shutdown_signal(self, signum, frame):
        """Handle system shutdown signals"""
        if backup_engine.is_running:
            logger.info(f"Received shutdown signal {signum}, but backup is running")
            # Pause backup and force close
            if backup_engine.pause_backup():
                logger.info("Backup paused due to system shutdown")
                QTimer.singleShot(2000, self._force_close)
            else:
                logger.warning("Could not pause backup for shutdown")
                QTimer.singleShot(1000, self._force_close)
        else:
            logger.info(f"Received shutdown signal {signum}, closing application")
            self._force_close()
            
    def _handle_console_ctrl(self, ctrl_type):
        """Handle Windows console control events"""
        if backup_engine.is_running:
            self._show_shutdown_warning_and_pause()
            return True  # Don't shutdown
        return False  # Allow shutdown
    
    def _show_shutdown_warning_and_pause(self):
        """Show shutdown warning and offer to pause backup"""
        if not backup_engine.is_running:
            return
            
        reply = QMessageBox.warning(
            self, 
            "System Shutdown Detected",
            "The system is trying to shutdown but a backup is currently running.\n\n"
            "What would you like to do?\n\n"
            "• Pause: Save progress and allow shutdown\n"
            "• Continue: Block shutdown and continue backup\n"
            "• Stop: Stop backup and allow shutdown",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Ignore | QMessageBox.StandardButton.Discard,
            QMessageBox.StandardButton.Save
        )
        
        if reply == QMessageBox.StandardButton.Save:  # Pause
            if backup_engine.pause_backup():
                self.activity_panel.add_log_entry("Backup paused due to system shutdown")
                QTimer.singleShot(2000, self._force_close)  # Use _force_close instead
            else:
                self.activity_panel.add_log_entry("Failed to pause backup for shutdown")
        elif reply == QMessageBox.StandardButton.Discard:  # Stop
            backup_engine.stop_backup()
            self.activity_panel.add_log_entry("Backup stopped due to system shutdown")
            QTimer.singleShot(1000, self._force_close)
    
    def setup_menu(self):
        """Setup the application menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_job_action = QAction("New Job", self)
        new_job_action.setShortcut("Ctrl+N")
        new_job_action.triggered.connect(self.jobs_panel.create_new_job)
        file_menu.addAction(new_job_action)
        
        file_menu.addSeparator()
        
        # Resume paused backups action
        resume_paused_action = QAction("Resume Paused Backups", self)
        resume_paused_action.setShortcut("Ctrl+R")
        resume_paused_action.triggered.connect(self.show_paused_backups)
        file_menu.addAction(resume_paused_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        refresh_action = QAction("Refresh Jobs", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.jobs_panel.refresh_jobs)
        tools_menu.addAction(refresh_action)
        
        cleanup_action = QAction("Cleanup Old Executions", self)
        cleanup_action.triggered.connect(self.cleanup_old_executions)
        tools_menu.addAction(cleanup_action)
        
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def show_paused_backups(self):
        """Show the paused backups section"""
        self.activity_panel.refresh_paused_jobs()
        # If there are paused backups, scroll to them
        if not self.activity_panel.resume_section.isVisible():
            QMessageBox.information(self, "No Paused Backups", "There are no paused backups to resume.")
    
    def check_and_offer_resume(self):
        """Check for paused backups on startup and offer to resume them"""
        try:
            paused_executions = db_manager.get_paused_executions()
            
            if not paused_executions:
                return  # No paused backups
            
            # Get job names for the paused executions
            session = db_manager.get_session()
            try:
                paused_jobs_info = []
                for execution in paused_executions:
                    job = session.query(BackupJob).filter_by(id=execution.job_id).first()
                    if job:
                        progress_pct = execution.get_progress_percentage()
                        paused_jobs_info.append({
                            'job_name': job.name,
                            'execution_id': execution.id,
                            'job_id': execution.job_id,
                            'progress': progress_pct,
                            'started_at': execution.started_at
                        })
                
                if not paused_jobs_info:
                    return
                
                # Show dialog to user
                self.show_resume_dialog(paused_jobs_info)
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error checking for paused backups: {e}")
            self.activity_panel.add_log_entry(f"Error checking paused backups: {e}")

    def show_resume_dialog(self, paused_jobs_info):
        """Show dialog asking user if they want to resume paused backups"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget, QListWidgetItem
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QFont
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Resume Paused Backups")
        dialog.setMinimumSize(500, 300)
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Paused Backups Found")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Message
        message = QLabel(f"Found {len(paused_jobs_info)} paused backup(s) from your previous session.\n"
                        "Would you like to resume them?")
        message.setWordWrap(True)
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setStyleSheet("margin: 10px; color: #605e5c;")
        layout.addWidget(message)
        
        # List of paused jobs
        jobs_list = QListWidget()
        jobs_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #d2d0ce;
                border-radius: 6px;
                background-color: #faf9f8;
                padding: 8px;
            }
            QListWidgetItem {
                padding: 8px;
                border-bottom: 1px solid #edebe9;
            }
        """)
        
        for job_info in paused_jobs_info:
            started_str = job_info['started_at'].strftime("%Y-%m-%d %H:%M")
            item_text = f"{job_info['job_name']} ({job_info['progress']}% complete) - Started: {started_str}"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, job_info)
            jobs_list.addItem(item)
        
        layout.addWidget(jobs_list)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        cancel_btn = ModernButton("Not Now")
        cancel_btn.clicked.connect(dialog.reject)
        buttons_layout.addWidget(cancel_btn)
        
        resume_all_btn = ModernButton("Resume All", primary=True)
        resume_all_btn.clicked.connect(lambda: self.handle_resume_all(paused_jobs_info, dialog))
        buttons_layout.addWidget(resume_all_btn)
        
        resume_selected_btn = ModernButton("Resume Selected")
        resume_selected_btn.clicked.connect(lambda: self.handle_resume_selected(jobs_list, dialog))
        buttons_layout.addWidget(resume_selected_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        dialog.setLayout(layout)
        
        # Show dialog non-blocking
        QTimer.singleShot(1000, dialog.show)  # Delay to let main window load first

    def handle_resume_all(self, paused_jobs_info, dialog):
        """Handle resuming all paused jobs"""
        if backup_engine.is_running:
            QMessageBox.warning(dialog, "Backup Running", 
                            "A backup is already running. Please wait for it to complete.")
            return
        
        dialog.accept()
        
        # Resume the first job (we can only run one at a time)
        if paused_jobs_info:
            first_job = paused_jobs_info[0]
            self.activity_panel.add_log_entry(f"Auto-resuming: {first_job['job_name']}")
            backup_engine.run_backup_job_async(first_job['job_id'])
            
            # Queue the rest for later
            if len(paused_jobs_info) > 1:
                self.activity_panel.add_log_entry(f"Queued {len(paused_jobs_info) - 1} additional paused backups for later")
                QMessageBox.information(self, "Multiple Backups", 
                                    f"Resumed '{first_job['job_name']}'. The remaining {len(paused_jobs_info) - 1} "
                                    "paused backups are available in the Activity panel.")

    def handle_resume_selected(self, jobs_list, dialog):
        """Handle resuming selected paused job"""
        current_item = jobs_list.currentItem()
        if not current_item:
            QMessageBox.information(dialog, "No Selection", "Please select a backup to resume.")
            return
        
        if backup_engine.is_running:
            QMessageBox.warning(dialog, "Backup Running", 
                            "A backup is already running. Please wait for it to complete.")
            return
        
        job_info = current_item.data(Qt.ItemDataRole.UserRole)
        dialog.accept()
        
        self.activity_panel.add_log_entry(f"Auto-resuming selected: {job_info['job_name']}")
        backup_engine.run_backup_job_async(job_info['job_id'])
        
    def cleanup_old_executions(self):
        """Clean up old execution records"""
        try:
            reply = QMessageBox.question(
                self, 
                "Cleanup Old Executions",
                "This will remove execution records older than 30 days.\n"
                "This action cannot be undone. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                count = db_manager.cleanup_old_executions()
                QMessageBox.information(self, "Cleanup Complete", f"Removed {count} old execution records.")
                self.activity_panel.add_log_entry(f"Cleaned up {count} old execution records")
        except Exception as e:
            QMessageBox.critical(self, "Cleanup Error", f"Failed to cleanup old executions: {str(e)}")
    
    def show_settings(self):
        """Show settings dialog"""
        QMessageBox.information(self, "Settings", 
                              "Settings dialog will be implemented in the next release.")
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About Backup Manager Pro", 
                         "Backup Manager Pro v1.0.0\n\n"
                         "A professional backup solution with support for local and cloud targets.\n\n"
                         "Features:\n"
                         "• Pause and resume backups\n"
                         "• Progress persistence\n"
                         "• File integrity verification\n"
                         "• Automatic shutdown protection\n\n"
                         "Built with Python and PySide6")
    
    def setup_timer(self):
        """Setup refresh timer"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_activity)
        self.timer.start(5000)  # Refresh every 5 seconds
    
    def on_job_selected(self, job_id):
        """Handle job selection"""
        session = db_manager.get_session()
        try:
            job = session.query(BackupJob).filter_by(id=job_id).first()
            if job:
                self.activity_panel.add_log_entry(f"Selected job: {job.name}")
                self.status_bar.showMessage(f"Selected: {job.name}")
        except Exception as e:
            logger.error(f"Error handling job selection: {e}")
        finally:
            session.close()
    
    def refresh_activity(self):
        """Refresh activity display periodically"""
        # Refresh jobs panel if backup state changed
        current_running = backup_engine.is_running
        
        # Update run button state
        self.jobs_panel.run_job_btn.setEnabled(
            self.jobs_panel.selected_job_id is not None and not current_running
        )
        
        # Refresh paused jobs list
        self.activity_panel.refresh_paused_jobs()
        
        # Update status bar
        if current_running:
            if backup_engine.is_paused:
                self.status_bar.showMessage("Backup paused")
            else:
                self.status_bar.showMessage("Backup in progress...")
        else:
            self.status_bar.showMessage("Ready")
    
    def closeEvent(self, event):
        """Handle application close with backup protection and auto-resume support"""
        if backup_engine.is_running:
            reply = QMessageBox.warning(
                self, 
                "Backup In Progress", 
                "A backup is currently running. What would you like to do?\n\n"
                "• Pause and Exit: Save progress and resume next time you start the app\n"
                "• Stop and Exit: Stop backup and close application\n"
                "• Cancel: Keep application running",
                QMessageBox.StandardButton.Save | 
                QMessageBox.StandardButton.Discard | 
                QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            
            if reply == QMessageBox.StandardButton.Save:
                # Pause backup and close - will be resumed on next startup
                if backup_engine.pause_backup():
                    self.activity_panel.add_log_entry("Backup paused - will resume on next startup")
                    # Give time for database to save the paused state
                    QTimer.singleShot(3000, self._cleanup_and_exit)
                else:
                    QMessageBox.warning(self, "Pause Failed", "Could not pause backup. Please try again.")
                event.ignore()
                
            elif reply == QMessageBox.StandardButton.Discard:
                # Stop backup and close
                backup_engine.stop_backup()
                self.activity_panel.add_log_entry("Backup stopped - closing application")
                QTimer.singleShot(1000, self._cleanup_and_exit)
                event.ignore()
                
            else:
                # Cancel - keep running
                event.ignore()
        else:
            # No backup running, safe to close
            logger.info("Application closing")
            self._cleanup_and_accept(event)

    def _cleanup_and_accept(self, event):
        """Clean up resources and accept close event for normal shutdown"""
        if hasattr(self, 'timer'):
            self.timer.stop()
        db_manager.close()
        event.accept()

    def _cleanup_and_exit(self):
        """Clean up resources and force exit the application"""
        logger.info("Cleaning up and exiting application after backup operation")
        
        # Clean up resources
        if hasattr(self, 'timer'):
            self.timer.stop()
        
        # Close database connection
        db_manager.close()
        
        # Force exit the application
        import sys
        sys.exit(0)
        
    def _force_close(self):
        """Force close the application without further checks"""
        if hasattr(self, '_closing') and self._closing:
            logger.info("Force closing application after backup operation")
            # Close all windows and quit
            QApplication.instance().closeAllWindows()
            QApplication.instance().quit()
            # If that doesn't work, force exit
            QTimer.singleShot(500, lambda: sys.exit(0))

    def _finalize_close(self):
        """Finalize the application close"""
        logger.info("Application closing")
        db_manager.close()
        # Don't try to access the event object here
        self.close() if not self.isVisible() else None