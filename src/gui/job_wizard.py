import json
import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QLineEdit, QTextEdit, QComboBox, QCheckBox,
                               QFileDialog, QListWidget, QGroupBox, QFormLayout,
                               QTabWidget, QWidget, QMessageBox, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ..core.database import db_manager, BackupJob

class ModernFrame(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #d2d0ce;
                border-radius: 8px;
                padding: 16px;
            }
        """)

class SourcesTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        sources_group = QGroupBox("Source Folders and Files")
        sources_layout = QVBoxLayout()
        
        self.sources_list = QListWidget()
        self.sources_list.setMinimumHeight(150)
        sources_layout.addWidget(self.sources_list)
        
        buttons_layout = QHBoxLayout()
        self.add_folder_btn = QPushButton("Add Folder")
        self.add_folder_btn.clicked.connect(self.add_folder)
        self.add_files_btn = QPushButton("Add Files")
        self.add_files_btn.clicked.connect(self.add_files)
        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.clicked.connect(self.remove_selected)
        
        buttons_layout.addWidget(self.add_folder_btn)
        buttons_layout.addWidget(self.add_files_btn)
        buttons_layout.addWidget(self.remove_btn)
        buttons_layout.addStretch()
        
        sources_layout.addLayout(buttons_layout)
        sources_group.setLayout(sources_layout)
        layout.addWidget(sources_group)
        
        filters_group = QGroupBox("Filters (Optional)")
        filters_layout = QFormLayout()
        
        self.include_edit = QLineEdit()
        self.include_edit.setPlaceholderText("e.g., *.docx;*.xlsx;*.pdf")
        filters_layout.addRow("Include patterns:", self.include_edit)
        
        self.exclude_edit = QLineEdit()
        self.exclude_edit.setPlaceholderText("e.g., */temp/*;*.tmp;*.log")
        filters_layout.addRow("Exclude patterns:", self.exclude_edit)
        
        filters_group.setLayout(filters_layout)
        layout.addWidget(filters_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Backup")
        if folder:
            self.sources_list.addItem(folder)
    
    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files to Backup")
        for file in files:
            self.sources_list.addItem(file)
    
    def remove_selected(self):
        current_row = self.sources_list.currentRow()
        if current_row >= 0:
            self.sources_list.takeItem(current_row)
    
    def get_sources(self):
        return [self.sources_list.item(i).text() for i in range(self.sources_list.count())]
    
    def get_include_patterns(self):
        return self.include_edit.text().strip()
    
    def get_exclude_patterns(self):
        return self.exclude_edit.text().strip()

class TargetTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        target_group = QGroupBox("Backup Destination")
        target_layout = QVBoxLayout()
        
        self.target_combo = QComboBox()
        self.target_combo.addItems(["Local Folder", "Google Drive (Coming Soon)"])
        self.target_combo.currentTextChanged.connect(self.on_target_changed)
        target_layout.addWidget(QLabel("Target Type:"))
        target_layout.addWidget(self.target_combo)
        
        self.local_path_layout = QHBoxLayout()
        self.local_path_edit = QLineEdit()
        self.local_path_edit.setPlaceholderText("Select backup destination folder...")
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_local_target)
        self.local_path_layout.addWidget(self.local_path_edit)
        self.local_path_layout.addWidget(self.browse_btn)
        target_layout.addLayout(self.local_path_layout)
        
        self.gdrive_label = QLabel("Google Drive integration coming in next release!")
        self.gdrive_label.setStyleSheet("color: #605e5c; font-style: italic;")
        self.gdrive_label.setVisible(False)
        target_layout.addWidget(self.gdrive_label)
        
        target_group.setLayout(target_layout)
        layout.addWidget(target_group)
        
        options_group = QGroupBox("Backup Options")
        options_layout = QFormLayout()
        
        self.conflict_combo = QComboBox()
        self.conflict_combo.addItems(["Rename (keep both)", "Overwrite existing", "Skip existing"])
        options_layout.addRow("If file exists:", self.conflict_combo)
        
        self.verify_checksum = QCheckBox("Verify file integrity with checksums")
        self.verify_checksum.setChecked(True)
        options_layout.addRow("", self.verify_checksum)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def on_target_changed(self, text):
        is_local = text == "Local Folder"
        self.local_path_edit.setVisible(is_local)
        self.browse_btn.setVisible(is_local)
        self.gdrive_label.setVisible(not is_local)
    
    def browse_local_target(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Backup Destination")
        if folder:
            self.local_path_edit.setText(folder)
    
    def get_target_type(self):
        return "local" if self.target_combo.currentText() == "Local Folder" else "gdrive"
    
    def get_target_config(self):
        if self.get_target_type() == "local":
            return {"local_path": self.local_path_edit.text()}
        return {"gdrive_folder_id": "coming_soon"}
    
    def get_conflict_policy(self):
        policy_map = {
            "Rename (keep both)": "rename",
            "Overwrite existing": "overwrite",
            "Skip existing": "skip"
        }
        return policy_map[self.conflict_combo.currentText()]

class ScheduleTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        schedule_group = QGroupBox("Schedule Settings")
        schedule_layout = QFormLayout()
        
        self.schedule_combo = QComboBox()
        self.schedule_combo.addItems([
            "Manual (Run on demand)",
            "Daily at specific time",
            "Weekly on specific day",
            "Custom schedule"
        ])
        schedule_layout.addRow("Schedule:", self.schedule_combo)
        
        self.time_edit = QLineEdit()
        self.time_edit.setPlaceholderText("e.g., 02:00")
        schedule_layout.addRow("Time:", self.time_edit)
        
        schedule_group.setLayout(schedule_layout)
        layout.addWidget(schedule_group)
        
        preview_group = QGroupBox("Job Summary")
        preview_layout = QVBoxLayout()
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(150)
        preview_layout.addWidget(self.preview_text)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def get_schedule_cron(self):
        schedule = self.schedule_combo.currentText()
        if "Manual" in schedule:
            return None
        elif "Daily" in schedule:
            time = self.time_edit.text() or "02:00"
            hour, minute = time.split(":")
            return f"{minute} {hour} * * *"
        return None
    
    def update_preview(self, sources, target_type, target_config):
        preview = f"Sources: {len(sources)} items\n"
        preview += f"Target: {target_type.title()}\n"
        if target_type == "local":
            preview += f"Path: {target_config.get('local_path', 'Not set')}\n"
        schedule = self.schedule_combo.currentText()
        preview += f"Schedule: {schedule}"
        self.preview_text.setPlainText(preview)

class JobWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("New Backup Job")
        self.setMinimumSize(600, 500)
        self.resize(700, 600)
        
        layout = QVBoxLayout()
        
        title = QLabel("Create New Backup Job")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.DemiBold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        form_layout = QFormLayout()
        self.job_name_edit = QLineEdit()
        self.job_name_edit.setPlaceholderText("Enter a descriptive name for this backup job...")
        form_layout.addRow("Job Name:", self.job_name_edit)
        layout.addLayout(form_layout)
        
        self.tabs = QTabWidget()
        
        self.sources_tab = SourcesTab()
        self.target_tab = TargetTab()
        self.schedule_tab = ScheduleTab()
        
        self.tabs.addTab(self.sources_tab, "Sources")
        self.tabs.addTab(self.target_tab, "Target")
        self.tabs.addTab(self.schedule_tab, "Schedule")
        
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        layout.addWidget(self.tabs)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_btn)
        
        self.create_btn = QPushButton("Create Job")
        self.create_btn.clicked.connect(self.create_job)
        self.create_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 500;
                padding: 8px 24px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        buttons_layout.addWidget(self.create_btn)
        
        layout.addLayout(buttons_layout)
        self.setLayout(layout)
    
    def on_tab_changed(self, index):
        if index == 2:
            sources = self.sources_tab.get_sources()
            target_type = self.target_tab.get_target_type()
            target_config = self.target_tab.get_target_config()
            self.schedule_tab.update_preview(sources, target_type, target_config)
    
    def create_job(self):
        if not self.validate_job():
            return
        
        job_name = self.job_name_edit.text().strip()
        sources = self.sources_tab.get_sources()
        include_patterns = self.sources_tab.get_include_patterns()
        exclude_patterns = self.sources_tab.get_exclude_patterns()
        target_type = self.target_tab.get_target_type()
        target_config = self.target_tab.get_target_config()
        conflict_policy = self.target_tab.get_conflict_policy()
        schedule_cron = self.schedule_tab.get_schedule_cron()
        
        session = db_manager.get_session()
        try:
            job = BackupJob(
                name=job_name,
                sources=json.dumps(sources),
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
                target_type=target_type,
                target_config=json.dumps(target_config),
                conflict_policy=conflict_policy,
                schedule_cron=schedule_cron
            )
            session.add(job)
            session.commit()
            
            QMessageBox.information(self, "Success", f"Backup job '{job_name}' created successfully!")
            self.accept()
            
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to create job: {str(e)}")
        finally:
            session.close()
    
    def validate_job(self):
        if not self.job_name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a job name.")
            return False
        
        if not self.sources_tab.get_sources():
            QMessageBox.warning(self, "Validation Error", "Please add at least one source folder or file.")
            return False
        
        if self.target_tab.get_target_type() == "local":
            local_path = self.target_tab.get_target_config().get("local_path", "")
            if not local_path or not os.path.exists(local_path):
                QMessageBox.warning(self, "Validation Error", "Please select a valid destination folder.")
                return False
        
        return True