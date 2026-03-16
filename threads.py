"""QThread subclasses for background API operations."""

from PyQt6.QtCore import QThread, pyqtSignal


class SyncThread(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, client):
        super().__init__()
        self.client = client

    def run(self):
        try:
            self.client.sync_all_items()
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))


class DetailsThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, client, item_id):
        super().__init__()
        self.client = client
        self.item_id = item_id

    def run(self):
        try:
            data = self.client.get_item_details(self.item_id)
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))


class StatusUpdateThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, client, item_id, activate):
        super().__init__()
        self.client = client
        self.item_id = item_id
        self.activate = activate

    def run(self):
        try:
            self.client.update_item_status(self.item_id, self.activate)
            data = self.client.get_item_details(self.item_id)
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))


class DescriptionUpdateThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, client, item_id, sales_desc, purchase_desc):
        super().__init__()
        self.client = client
        self.item_id = item_id
        self.sales_desc = sales_desc
        self.purchase_desc = purchase_desc

    def run(self):
        try:
            self.client.update_item_descriptions(self.item_id, self.sales_desc, self.purchase_desc)
            data = self.client.get_item_details(self.item_id)
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))

class BrandUpdateThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, client, item_id, new_brand):
        super().__init__()
        self.client = client
        self.item_id = item_id
        self.new_brand = new_brand

    def run(self):
        try:
            data = self.client.update_item_brand(self.item_id, self.new_brand)
            # Fetch updated details to refresh cache
            updated = self.client.get_item_details(self.item_id)
            self.finished.emit(updated)
        except Exception as e:
            self.error.emit(str(e))


class FetchBrandsThread(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, client):
        super().__init__()
        self.client = client

    def run(self):
        try:
            brands = self.client.get_all_brands()
            self.finished.emit(brands)
        except Exception as e:
            self.error.emit(str(e))