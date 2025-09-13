Daily Backup Software

Currently Available:
Modern GUI Interface — Clean, professional design with Microsoft Fluent-inspired styling
Job Creation Wizard — Step-by-step backup job configuration
Local File Backup — Reliable copying to local directories with integrity verification
File Filtering — Include/exclude patterns with wildcard support
Conflict Resolution — Rename, overwrite, or skip existing files
Progress Tracking — Real-time progress bars and detailed logging
Database Storage — SQLite-based job and history management
Checksum Verification — SHA256 integrity checking for copied files
Atomic Operations — Safe file transfers with temporary staging

Coming Soon:
Google Drive integration (OAuth authentication and cloud uploads)
Job scheduling (cron-based automatic backups)
System tray background operation with notifications
Settings panel for configurable preferences
Job templates for pre-configured scenarios
Backup history viewer with detailed logs and statistics

Installation:
Prerequisites
Python 3.8 or higher
Windows, macOS, or Linux

Install Dependencies
pip install -r requirements.txt

Run the Application
python main.py

Project Structure:
| File/Folder             | Purpose                                |
|--------------------------|----------------------------------------|
| `gui/`                  | User interface components              |
| `main_window.py`        | Main application window                |
| `job_wizard.py`         | Backup job creation wizard             |
| `components/`           | Reusable UI components                 |
| `core/`                 | Core application logic                 |
| `backup_engine.py`      | Backup execution engine                |
| `database.py`           | Database models and management         |
| `config.py`             | Configuration management               |
| `connectors/`           | Target connectors (local/cloud)        |
| `local_target.py`       | Local file system connector            |
| `gdrive_connector.py`   | Google Drive connector (WIP)           |
| `utils/`                | Utility modules                        |
| `crypto.py`             | Encryption and credential management   |
| `logging_config.py`     | Logging configuration                  |
| `requirements.txt`      | Python dependencies                    |
| `main.py`               | Application entry point                |
| `setup.py`              | Package configuration                  |
| `README.md`             | Project documentation                  |


Usage:
- Creating a Backup Job
- Launch the application and click New Job.
- Sources Tab: Add folders or files you want to back up.
- Include patterns: *.docx;*.xlsx
- Exclude patterns: */temp/*;*.tmp
- Target Tab: Choose a backup destination.
- Select "Local Folder" and browse to a location.
- Configure conflict resolution policy.
- Schedule Tab: Set up when backups should run.
- Manual execution currently supported.
- Automatic scheduling coming soon.
- Create the job and run it immediately or later.

Running Backups:
Select a job from the main window and click Run Job.
Monitor progress in the Activity panel.
View detailed logs in the activity feed.
Stop running backups if needed.

Job Management:
Right-click on jobs for context menu options.
Edit job settings.
Delete jobs when no longer needed.
View execution history and statistics.

Development:
Setting Up
Clone the repository.
Create a virtual environment:
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
Install dependencies:
pip install -r requirements.txt
Run the application:
python main.py

Architecture:
GUI Layer: PySide6-based interface
Core Engine: Business logic and backup operations
Data Layer: SQLAlchemy ORM with SQLite
Connectors: Pluggable backup targets
Utils: Logging, crypto, and configuration
Database Schema
backup_jobs: Job definitions
job_executions: Run history and status
file_transfers: File transfer records

Security:
Secure credential storage with OS keyring
SHA256 checksums for file integrity
Atomic operations to prevent corruption
Minimal file system permissions

Roadmap:
Version 1.1 (Next Release)
Google Drive OAuth integration
Basic scheduling
Settings dialog
System tray integration
Version 1.2 (Future)
Advanced scheduling with cron expressions
Backup compression and encryption
Email notifications
Multi-threaded transfers
Version 2.0 (Long-term)
Additional cloud providers (Dropbox, OneDrive)
Incremental backups with deduplication
Network location support
Advanced reporting and analytics

Contributing:
Contributions, bug reports, and feature requests are welcome.
Fork the repository
Create a feature branch
Make your changes
Add tests if applicable
Submit a pull request

Support:
For support, open an issue on the GitHub repository.
