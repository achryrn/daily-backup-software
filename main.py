import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QDir
from PySide6.QtGui import QPalette, QColor

from src.gui.main_window import MainWindow
from src.core.backup_engine import backup_engine

class BackupApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName("Backup Manager Pro")
        self.setApplicationVersion("1.0.0")
        self.setOrganizationName("BackupSoft")
        
        self.setup_theme()
        self.main_window = None
        
    def setup_theme(self):
        self.setStyle("Fusion")
        
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(248, 248, 248))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(50, 49, 48))
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(243, 242, 241))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(50, 49, 48))
        palette.setColor(QPalette.ColorRole.Text, QColor(50, 49, 48))
        palette.setColor(QPalette.ColorRole.Button, QColor(243, 242, 241))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(50, 49, 48))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.ColorRole.Link, QColor(0, 120, 212))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 212))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        self.setPalette(palette)
    
    def run(self):
        self.main_window = MainWindow()
        
        backup_engine.set_progress_callback(self.main_window.activity_panel.update_progress)
        backup_engine.set_log_callback(self.main_window.activity_panel.add_log_entry)
        
        self.main_window.show()
        return self.exec()

def main():
    app = BackupApp(sys.argv)
    return app.run()

if __name__ == "__main__":
    sys.exit(main())