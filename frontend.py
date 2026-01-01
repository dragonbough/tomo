import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QTreeWidget, QTreeWidgetItem, QHeaderView, QHBoxLayout, QCheckBox, QLineEdit, QLabel)

import todos
import tomos
import pomos

# allows closing the application using CTRL + C
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)


class Window(QMainWindow):

    def __init__(self):
        super().__init__()

# individual item containing a single Todo's information -- does not store Todo contents but acts as reference to the backend Todo object via todo_id
class TodoViewItem(QTreeWidgetItem):

    def __init__(self, todo_id : int, todo_view : "TodoView"):
        super().__init__()

        self.item_id = todo_id

        # references self in the todo_view + references todo_view in self for easy access
        todo_view.items.append(self)
        self.todo_view = todo_view

        # gets its todo and extracts any important info -- does not save in the view item for decoupling purposes
        my_todo = self.todo_view.get_item_todo(self)

        # creating text and checkbox widgets
        self.item_label = QLabel(my_todo.name)
        self.item_checkbox = QCheckBox()
        self.item_checkbox.setChecked(my_todo.completed)
        # checkbox can only focus with clicks instead of tab/space
        self.item_checkbox.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        # checkbox triggers the todo completion by todoview
        # ensure it is the "clicked" signal as otherwise setCheckState calls will trigger this too
        self.item_checkbox.clicked.connect(lambda checked : self.todo_view.item_checked(checked, self))

        # creating layout to store text and checkbox and adding to item_widget
        self.item_widget = QWidget()
        self.item_layout = QHBoxLayout()
        self.item_layout.addWidget(self.item_checkbox)
        self.item_layout.addWidget(self.item_label)
        self.item_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.item_widget.setLayout(self.item_layout)

        # creating line_edit for editing labels
        self.line_edit = QLineEdit()

        # creates difficulty column based on the todo's difficulty
        difficulties =  {1: "Trivial",  2: "Easy",  3: "Normal",  4: "Hard"}
        self.setText(1, difficulties[my_todo.difficulty])

        # creates children todoview items for each child in my_todo
        self.addChildren([TodoViewItem(child.todo_id, self.todo_view) for child in my_todo.children])

    # refreshes the attributes -- use when a change is made that isnt immediately reflected the todoviewitem object
    def refresh_attributes(self):
        my_todo = self.todo_view.get_item_todo(self)
        self.item_checkbox.setChecked(my_todo.completed)

    # turns the QLabel into QLineEdit, allowing user to change what was there
    def enable_edit(self):

        item_text = self.item_label.text()
        self.item_layout.removeWidget(self.item_label)
        self.item_label.setVisible(False)

        self.line_edit.setText(item_text)
        self.item_layout.addWidget(self.line_edit)
        self.line_edit.setVisible(True)

        self.line_edit.setFocus()

    # completes the edit in the qlineedit, renaming the todos and replacing it with a qlabel again
    def complete_edit(self):

        new_text = self.line_edit.text()
        self.item_layout.removeWidget(self.line_edit)
        self.line_edit.setVisible(False)

        self.item_label.setText(new_text)
        self.item_layout.addWidget(self.item_label)
        self.item_label.setVisible(True)

        my_todo = self.todo_view.todo_list.get_todo(self.item_id)
        my_todo.name = new_text

# collection of TodoViewItems that is viewed in window
class TodoView(QTreeWidget):

    def __init__(self, todo_list : todos.TodoList):
        super().__init__()

        self.todo_list = todo_list
        self.items = []
        self.items : list[TodoViewItem]

        # sets up each column of the todo view, ensuring they resize to contents and the last column isnt stretched
        self.setHeaderLabels(["To-dos", "Difficulty"])
        self.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.header().setStretchLastSection(False)


        # adds top level items for the root nodes in the todo list
        todo_view_roots = [TodoViewItem(root_todo.todo_id, self) for root_todo in todo_list.get_roots()]
        self.addTopLevelItems(todo_view_roots)


        # for each todoviewitem in todoview, set its content to its item_widget (checkbox and label)
        for item in self.items:

            item : TodoViewItem

            self.setItemWidget(item, 0, item.item_widget)
            item.item_widget.adjustSize()
            item.setSizeHint(0, item.item_widget.sizeHint())
            item.item_widget.show()

        # if an item is being edited or not
        self.editing_item = None

        self.setSizeAdjustPolicy(self.SizeAdjustPolicy.AdjustToContents)
        self.itemExpanded.connect(self.adjustSize)
        self.itemCollapsed.connect(self.adjustSize)

    # changes todo completion when an items checkbox is checked
    def item_checked(self, checked : bool, todo_view_item : TodoViewItem):

        todo = self.todo_list.get_todo(todo_view_item.item_id)
        self.todo_list.complete_todo(todo=todo, completion=checked)
        self.refresh_item_attributes()

    # refreshes the attributes for all of the items
    def refresh_item_attributes(self):
        for item in self.items:
            item.refresh_attributes()

    # retrieves an item's associated todo, based on the item's item id
    def get_item_todo(self, item : TodoViewItem):
        return self.todo_list.get_todo(item.item_id)

    # detects if ENTER/Return key is released while over a todoviewitem to enable/complete edit
    def keyReleaseEvent(self, a0):
        if a0.key() == Qt.Key.Key_Return:
            if not self.editing_item:
                self.currentItem().enable_edit()
                self.editing_item = self.currentItem()
            elif self.editing_item == self.currentItem():
                self.currentItem().complete_edit()
                self.editing_item = None

        return super().keyReleaseEvent(a0)


# sys.argv allows arguments to be passed into the QApplication from the command line
app = QApplication(sys.argv)

todo_view = TodoView(todos.TodoList.get_user_todos())
todo_view.show()

# starts app event loop
app.exec()