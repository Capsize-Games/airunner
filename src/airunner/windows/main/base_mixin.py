class BaseMixin:
    def __init__(self, data):
        self.data = data

    def get_all(self):
        return self.data

    def get_by_filter(self, filter_dict):
        return [item for item in self.data if all(item.get(k) == v for k, v in filter_dict.items())]

    def create(self, item):
        self.data.append(item)

    def update(self, item):
        for i, existing_item in enumerate(self.data):
            if existing_item['name'] == item['name']:
                self.data[i] = item
                break

    def delete(self, item):
        self.data = [existing_item for existing_item in self.data if existing_item['name'] != item['name']]
