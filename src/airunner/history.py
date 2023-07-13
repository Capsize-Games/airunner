class History:
    event_history = []
    undone_history = []

    def add_event(self, data: dict):
        self.event_history.append(data)
        self.undone_history = []

    def clear(self):
        self.event_history = []
        self.undone_history = []
