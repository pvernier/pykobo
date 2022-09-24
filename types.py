from typing import Union


class Question:
    def __init__(self, index: str, name: str, type: str, label: str = None) -> None:
        self.index = index
        self.name = name
        self.type = type
        self.label = label
        self.group_name = None
        self.group_label = None
        self.repeat_name = None
        self.repeat_label = None
        self.select_from_list_name = None
        self.choices = None

    def __repr__(self):
        return f"Question('{self.index}, {self.name}, {self.type}, {self.label}')"
