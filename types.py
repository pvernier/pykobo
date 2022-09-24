from typing import Union


class Group:
    def __init__(self, name: str, label: str = None, parent: Union[None, "Group"] = None) -> None:
        self.name = name
        self.label = label
        self.parent = None

        self._build_prefix(parent)

    def _build_prefix(self, parent):
        if parent:
            print('OK',  parent.name)
            self.prefix_name = parent.name
            self.prefix_label = parent.label
        else:
            self.prefix_name = ''
            self.prefix_label = ''

    # def add(self, element):
    #     self.content.append(element)


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


class Repeat:
    def __init__(self, name: str, label: str = None) -> None:
        self.name = None
        self.label = None
        self.questions = []
