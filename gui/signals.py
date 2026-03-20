from PyQt6.QtCore import pyqtSignal, QObject

class WorkerSignals(QObject):
    status = pyqtSignal(str, str)
    progress = pyqtSignal(float, str)
    ask_phone = pyqtSignal()
    ask_code = pyqtSignal(str)
    ask_location_success = pyqtSignal(object, str)
    success = pyqtSignal(str)
    error = pyqtSignal(str)
    ready = pyqtSignal()
    download_started = pyqtSignal()
    bulk_list_fetched = pyqtSignal(list)
    bulk_table_refresh = pyqtSignal()
