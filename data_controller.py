from threading import Lock

class DataController:
    def __init__(self):
        self.data_series = ['data1', 'data2', 'data3']  # List of all data series identifiers
        self.active_series = []  # List to keep track of which data series are currently being shown
        self.series_ids = {series: f"id_{index}" for index, series in enumerate(self.data_series, 1)}
        self.lock = Lock()
        
        for series in self.data_series:
            self.series_ids[series] = "id_for_" + series

    def add_active_series(self, series_identifier):
        if series_identifier in self.data_series and series_identifier not in self.active_series:
            self.active_series.append(series_identifier)

    def remove_active_series(self, series_identifier):
        if series_identifier in self.active_series:
            self.active_series.remove(series_identifier)

    def get_active_series(self):
        return self.active_series

    def get_series_id(self, series_identifier):
        return self.series_ids.get(series_identifier, None)