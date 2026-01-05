import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QWidget, QApplication,
                             QTreeWidget, QTreeWidgetItem, QHeaderView,
                             QHBoxLayout, QCheckBox, QLineEdit,
                             QLabel, QComboBox, QToolButton,
                             QSpacerItem, QSizePolicy, QMessageBox)
from PyQt6.QtGui import QIcon

sys.path.append("../backend")
import todos
import tomos
import pomos

# allows closing the application using CTRL + C
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)


# individual item containing a single Todo's information -- does not store Todo contents but acts as reference to the backend Todo object via todo_id
class TodoViewItem(QTreeWidgetItem):

    def __init__(self, todo_id : int | None, todo_view : "TodoView"):
        super().__init__()

        self.item_id = todo_id

        # references self in the todo_view + references todo_view in self for easy access
        self.todo_view = todo_view
        self.todo_view.add_todo_item(self)

        # creating text and checkbox widgets
        self.item_label = QLabel()
        self.item_checkbox = QCheckBox()
        # checkbox can only focus with clicks instead of tab/space
        self.item_checkbox.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        # checkbox triggers the todo completion by todoview -- ensure it is the "clicked" signal as otherwise setCheckState calls will trigger this too
        self.item_checkbox.clicked.connect(lambda checked : self.todo_view.item_checked(checked, self))

        # creating difficulty dropdown + label -- used to set todo's difficulty
        difficulties = ["Trivial", "Easy", "Normal", "Hard"]
        self.difficulty_dropdown = QComboBox()
        self.difficulty_dropdown.addItems(difficulties)
        self.difficulty_label = QLabel()

        self.difficulty_widget = QWidget()
        self.difficulty_layout = QHBoxLayout()
        self.difficulty_layout.addWidget(self.difficulty_label)
        self.difficulty_widget.setLayout(self.difficulty_layout)

        # creating layout to store text and checkbox and adding to item_widget
        self.item_widget = QWidget()
        self.item_layout = QHBoxLayout()
        self.item_layout.addWidget(self.item_checkbox)
        self.item_layout.addWidget(self.item_label)
        self.item_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.item_widget.setLayout(self.item_layout)

        # creating line_edit for editing labels
        self.line_edit = QLineEdit()

        # creating button to add more todos / delete todos
        self.add_button = QToolButton()
        system_add_icon = QIcon.ThemeIcon.ListAdd
        add_button_icon = QIcon("guicons/plus.png")
        self.add_button.setIcon(QIcon.fromTheme(system_add_icon, add_button_icon))
        self.add_button.clicked.connect(lambda : self.todo_view.create_todo_item(self))

        self.delete_button = QToolButton()
        system_delete_icon = QIcon.ThemeIcon.EditDelete
        self.delete_button.setIcon(QIcon.fromTheme(system_delete_icon))
        self.delete_button.clicked.connect(lambda : self.todo_view.show_delete_dialog(self))

        # adds spacer so the add/delete button is always at the end of the item_widget
        self.item_layout.addSpacerItem(QSpacerItem(20, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed))
        self.item_layout.addWidget(self.add_button)
        self.item_layout.addWidget(self.delete_button)

        self.add_button.setVisible(False)
        self.delete_button.setVisible(False)

        # so that hovering can be detected for displaying self.add_button
        self.item_widget.setMouseTracking(True)

        if self.item_id:

            # gets its todo and extracts any important info -- does not save in the view item for decoupling purposes
            my_todo = self.todo_view.get_item_todo(self)

            if my_todo.deleted:
                self.todo_view.mark_item_deleted(self)

            self.item_label.setText(my_todo.name)
            self.item_checkbox.setChecked(my_todo.completed)
            self.difficulty_dropdown.setCurrentIndex(my_todo.difficulty - 1)
            self.difficulty_label.setText(difficulties[my_todo.difficulty - 1])

            # creates children todoview items for each child in my_todo
            self.addChildren([TodoViewItem(child.todo_id, self.todo_view) for child in my_todo.children])

        else:

            self.item_label.setText("New To-do")
            self.item_checkbox.setChecked(False)
            self.difficulty_dropdown.setCurrentIndex(0)
            self.difficulty_label.setText(difficulties[0])

    # refreshes the attributes -- use when a change is made that isnt immediately reflected the todoviewitem object
    def refresh_attributes(self):
        my_todo = self.todo_view.get_item_todo(self)
        self.item_checkbox.setChecked(my_todo.completed)

    # turns the todo name QLabel into QLineEdit and todo difficulty QLabel into QComboBox, allowing user to remame todo and change difficulty
    def enable_edit(self):

        item_text = self.item_label.text()
        self.item_layout.removeWidget(self.item_label)
        self.item_label.setVisible(False)

        self.line_edit.setText(item_text)
        self.item_layout.insertWidget(1, self.line_edit)
        self.line_edit.setVisible(True)

        self.difficulty_layout.removeWidget(self.difficulty_label)
        self.difficulty_label.setVisible(False)

        self.difficulty_layout.addWidget(self.difficulty_dropdown)
        self.difficulty_dropdown.setVisible(True)

        self.line_edit.setFocus()
        self.line_edit.selectAll()

    # completes the edit in the qlineedit and qcombobox, renaming the todos and setting new difficulties before replacing both forms with a qlabel
    # if the item has no item_id, will create a todo with the given text and difficulty
    def complete_edit(self):

        new_text = self.line_edit.text()

        if not new_text:
            return

        self.item_layout.removeWidget(self.line_edit)
        self.line_edit.setVisible(False)

        self.item_label.setText(new_text)
        self.item_layout.insertWidget(1, self.item_label)
        self.item_label.setVisible(True)

        new_difficulty = self.difficulty_dropdown.currentIndex() + 1
        difficulty_text = self.difficulty_dropdown.itemText(new_difficulty - 1)
        self.difficulty_layout.removeWidget(self.difficulty_dropdown)
        self.difficulty_dropdown.setVisible(False)

        self.difficulty_label.setText(difficulty_text)
        self.difficulty_layout.addWidget(self.difficulty_label)
        self.difficulty_label.setVisible(True)

        if self.item_id:
            my_todo = self.todo_view.todo_list.get_todo(self.item_id)
            self.todo_view.todo_list.rename_todo(my_todo, new_text)
            self.todo_view.todo_list.set_todo_difficulty(my_todo, new_difficulty)
        else:
            parent = self.parent()
            parent : TodoViewItem
            parent_todo = self.todo_view.get_item_todo(parent)
            my_todo = self.todo_view.todo_list.create_todo(name=new_text, parent=parent_todo, difficulty=new_difficulty)
            self.item_id = my_todo.todo_id

    # shows the button used to add todo items
    def toggle_item_buttons(self, toggle : bool):
        self.add_button.setVisible(toggle)
        self.delete_button.setVisible(toggle)
        self.item_widget.adjustSize()


# collection of TodoViewItems that is viewed in window
class TodoView(QTreeWidget):

    @staticmethod
    def get_user_todo_view():
        return TodoView(todos.TodoList.get_user_todos())

    def __init__(self, todo_list : todos.TodoList):
        super().__init__()

        self.todo_list = todo_list
        self.items = []
        self.items : list[TodoViewItem]
        self.deleted_items = []
        self.deleted_items : list[TodoViewItem]

        # sets up each column of the todo view, ensuring they resize to contents and the last column is stretched so that it fits
        self.setHeaderLabels(["To-dos", "Difficulty"])
        self.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.header().setStretchLastSection(True)

        self.setMaximumWidth(450)

        # adds top level items for the root nodes in the todo list
        todo_view_roots = [TodoViewItem(root_todo.todo_id, self) for root_todo in todo_list.get_roots()]
        self.addTopLevelItems(todo_view_roots)

        # for each todoviewitem in todoview, set its content to its item_widget (checkbox, name/difficulty label)
        for item in self.items:

            item : TodoViewItem

            self.setItemWidget(item, 0, item.item_widget)
            item.item_widget.adjustSize()
            item.setSizeHint(0, item.item_widget.sizeHint())

            self.setItemWidget(item, 1, item.difficulty_widget)
            item.difficulty_widget.adjustSize()
            item.setSizeHint(1, item.difficulty_widget.sizeHint())

        # if an item is being edited or not
        self.editing_item = None
        # if ENTER/Return Key is pressed or an item is double clicked -- toggle edit of the item
        self.itemActivated.connect(self.toggle_edit)
        self.setExpandsOnDoubleClick(False)

        # automatic adjusting to size of whatever is in the widget, as items are expanded/collapsed
        self.setSizeAdjustPolicy(self.SizeAdjustPolicy.AdjustToContents)
        self.itemExpanded.connect(self.adjustSize)
        self.itemCollapsed.connect(self.adjustSize)

        # hovering over an todoviewitem shows its add button -- mouse tracking has to be True for this to work
        self.setMouseTracking(True)

    # keeps reference to todoviewitem in self.items
    def add_todo_item(self, item : TodoViewItem):
        if item not in self.items:
            self.items.append(item)

    # recreates the todo items
    def recreate_todo_items(self):

        self.clear()
        self.items = []
        todo_view_roots = [TodoViewItem(root_todo.todo_id, self) for root_todo in self.todo_list.get_roots()]
        self.addTopLevelItems(todo_view_roots)

        # for each todoviewitem in todoview, set its content to its item_widget (checkbox, name/difficulty label)
        self.reset_items()
        self.adjustSize()

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

    # shows/hides button used to add todos/subtodos
    def mouseMoveEvent(self, event):
        hovered_item = self.itemAt(event.pos())
        if hovered_item in self.items:
            hovered_item : TodoViewItem
            hovered_item.toggle_item_buttons(True)

        for item in self.items:
            if item != hovered_item and item.isSelected() != True:
                item.toggle_item_buttons(False)

        self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)

        return super().mouseMoveEvent(event)

    # ItemActivated signal is broadcast then toggle edit of that item
    def toggle_edit(self, item : TodoViewItem):

        if not self.editing_item:
            item.enable_edit()
            self.editing_item = item
        elif self.editing_item:
            self.editing_item.complete_edit()
            if self.editing_item == item:
                self.editing_item = None
            else:
                item.enable_edit()
                self.editing_item = item

    # creates an empty todoviewitem under a provided parent, which turns into an empty, editable item
    def create_todo_item(self, parent : TodoViewItem = None):

        new_todo_item = TodoViewItem(todo_id=None, todo_view=self)
        if parent:
            parent.addChild(new_todo_item)
        self.reset_items()
        self.expandItem(parent)
        self.setCurrentItem(new_todo_item)
        self.toggle_edit(new_todo_item)

    # deletes an item's todo before refreshing all of the items
    def delete_item_todo(self, item : TodoViewItem):

        if item == self.editing_item:
            item.complete_edit()
        item_todo = self.get_item_todo(item)
        self.todo_list.delete_todo(item_todo)
        self.recreate_todo_items()

    # marks an item as deleted
    def mark_item_deleted(self, item : TodoViewItem):
        if item not in self.deleted_items:
            self.deleted_items.append(item)

    # resets all of the items, applying a widget to each and deleting the ones marked as deleted
    def reset_items(self):

        for item in self.items:

            if item in self.deleted_items and item.parent():
                item.parent().removeChild(item)

            item : TodoViewItem

            self.setItemWidget(item, 0, item.item_widget)
            item.item_widget.adjustSize()
            item.setSizeHint(0, item.item_widget.sizeHint())

            self.setItemWidget(item, 1, item.difficulty_widget)
            item.difficulty_widget.adjustSize()
            item.setSizeHint(1, item.difficulty_widget.sizeHint())

    # shows a message box for confirmation before deleting a todo item
    def show_delete_dialog(self, item : TodoViewItem):

        self.delete_dialog = QMessageBox(self)
        self.delete_dialog.setIcon(QMessageBox.Icon.Question)
        self.delete_dialog.setInformativeText("Are you sure?")
        self.delete_dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        self.delete_dialog.setDefaultButton(QMessageBox.StandardButton.No)
        choice = self.delete_dialog.exec()
        if choice == QMessageBox.StandardButton.Yes:
            self.delete_item_todo(item)

    # occurences that occur on quit -- currently editing items are completed, and the changes are synced to the DB
    def quit_proc(self):

        if self.editing_item:
            self.editing_item.complete_edit()
        self.todo_list.empty_bin()

# sys.argv allows arguments to be passed into the QApplication from the command line
app = QApplication(sys.argv)

todo_view = TodoView.get_user_todo_view()
todo_view.show()

# when the overall application is closed carry out the quit procedure for the todoview
app.lastWindowClosed.connect(todo_view.quit_proc)

# starts app event loop
app.exec()