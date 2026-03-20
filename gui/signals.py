from PyQt6.QtCore import pyqtSignal, QObject

class WorkerSignals(QObject):
    # Single Download Signals
    single_progress = pyqtSignal(float, str)
    single_status = pyqtSignal(str, str)
    
    # Bulk Download Signals
    bulk_progress = pyqtSignal(float, str)
    bulk_status = pyqtSignal(str, str)
    
    # Common Signals
    error = pyqtSignal(str)
    success = pyqtSignal(str)
    ready = pyqtSignal()
    ask_phone = pyqtSignal()
    ask_code = pyqtSignal(str)
    ask_location_success = pyqtSignal(object, str)
    bulk_list_fetched = pyqtSignal(list)
    bulk_table_refresh = pyqtSignal()
