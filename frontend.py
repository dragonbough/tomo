import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QTreeWidget, QTreeWidgetItem, QHeaderView, QHBoxLayout, QCheckBox, QTextEdit, QLineEdit, QLabel, QSizePolicy)

import todos
import tomos
import pomos


class Window(QMainWindow):

    def __init__(self):
        super().__init__()

# individual item containing a single Todo's information -- does not store Todo contents but acts as reference to the backend Todo object via todo_id
class TodoViewItem(QTreeWidgetItem):

    def __init__(self, todo_id : int, todo_view : "TodoView"):
        super().__init__()

        self.item_id = todo_id

        # references self in the todo_view for easy access
        todo_view.items.append(self)

        # gets its todo and extracts any important info -- does not save in the view item for decoupling purposes
        my_todo = todo_view.todo_list.get_todo(todo_id)

        # creates difficulty column based on the todo's difficulty
        difficulties =  {1: "Trivial",  2: "Easy",  3: "Normal",  4: "Hard"}
        self.setText(1, difficulties[my_todo.difficulty])

        # creates children todoview items for each child in my_todo
        self.addChildren([TodoViewItem(child.todo_id, todo_view) for child in my_todo.children])

# collection of TodoViewItems that is viewed in window
class TodoView(QTreeWidget):

    def __init__(self, todo_list : todos.TodoList):
        super().__init__()

        self.todo_list = todo_list
        self.items = []

        # sets up each column of the todo view, ensuring they resize to contents and the last column isnt stretched
        # self.setHeaderLabels(["Completed", "Name", "Difficulty"])
        self.setHeaderLabels(["Stuff", "Difficulty"])
        self.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.header().setStretchLastSection(False)

        # adds top level items for the root nodes in the todo list
        todo_view_roots = [TodoViewItem(root_todo.todo_id, self) for root_todo in todo_list.get_roots()]
        self.addTopLevelItems(todo_view_roots)

        # format a widget holding a checkbox and text for each todoviewitem in view
        for item in self.items:

            item : TodoViewItem

            # creating text and checkbox widgets
            item_todo = self.todo_list.get_todo(item.item_id)
            item_text = QLabel(item_todo.name)
            item_checkbox = QCheckBox()
            item_checkbox.setChecked(item_todo.completed)

            # creating layout to store text and checkbox and adding to item_widget
            item_widget = QWidget()
            item_layout = QHBoxLayout()
            item_layout.addWidget(item_checkbox)
            item_layout.addWidget(item_text)
            item_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
            item_widget.setLayout(item_layout)

            # the widget is assigned to the todoviewitem + the todoviewitem adopts the widgets size hint
            self.setItemWidget(item, 0, item_widget)
            item_widget.adjustSize()
            item.setSizeHint(0, item_widget.sizeHint())


# sys.argv allows arguments to be passed into the QApplication from the command line
app = QApplication(sys.argv)

todo_view = TodoView(todos.TodoList.get_user_todos())
todo_view.show()

# starts app event loop
app.exec()