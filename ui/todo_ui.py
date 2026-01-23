from core import todos

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QWidget, QTreeWidget, QTreeWidgetItem,
                             QHBoxLayout, QCheckBox, QLineEdit,
                             QLabel, QComboBox, QToolButton,
                             QMessageBox, QSizePolicy)
from PyQt6.QtGui import QIcon

# DEBUG
# allows closing the application using CTRL + C (DEBUG)
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)
from PyQt6 import sip

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
        # creating line_edit for editing labels
        self.line_edit = QLineEdit()
        self.line_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # creating layout to store text and checkbox and adding to item_widget
        self.item_widget = QWidget()
        self.item_layout = QHBoxLayout()
        self.item_layout.addWidget(self.item_checkbox)
        self.item_layout.addWidget(self.item_label)
        self.item_widget.setLayout(self.item_layout)

        # so that hovering can be detected for displaying self.add_button/self.delete_buttons
        self.item_widget.setMouseTracking(True)

        # creating difficulty dropdown + label -- used to set todo's difficulty
        difficulties = ["Trivial", "Easy", "Normal", "Hard"]
        self.difficulty_dropdown = QComboBox()
        self.difficulty_dropdown.addItems(difficulties)
        self.difficulty_label = QLabel()

        self.difficulty_widget = QWidget()
        self.difficulty_layout = QHBoxLayout()
        self.difficulty_layout.addWidget(self.difficulty_label)
        self.difficulty_widget.setLayout(self.difficulty_layout)

        self.difficulty_widget.setMouseTracking(True)

        # creating button to add more todos / delete todos
        self.add_button = QToolButton()
        system_add_icon = QIcon.ThemeIcon.ListAdd
        add_button_icon = QIcon("guicons/plus.png")
        self.add_button.setIcon(QIcon.fromTheme(system_add_icon, add_button_icon))
        self.add_button.clicked.connect(lambda : self.todo_view.create_todo_item(self))

        self.delete_button = QToolButton()
        system_delete_icon = QIcon.ThemeIcon.EditDelete
        self.delete_button.setIcon(QIcon.fromTheme(system_delete_icon))
        self.delete_button.clicked.connect(lambda : self.todo_view.delete_todo_item(self))

        self.add_button.setVisible(False)
        self.delete_button.setVisible(False)

        # adds spacer so the add/delete button is always at the end of the item_widget
        self.item_layout.addStretch(1)

        self.item_layout.addWidget(self.add_button)
        self.item_layout.addWidget(self.delete_button)

        # the buttons maintain their space in the item_widget even when hidden
        add_button_sp = self.add_button.sizePolicy()
        delete_button_sp = self.delete_button.sizePolicy()
        add_button_sp.setRetainSizeWhenHidden(True)
        delete_button_sp.setRetainSizeWhenHidden(True)
        self.add_button.setSizePolicy(add_button_sp)
        self.delete_button.setSizePolicy(delete_button_sp)

        # checks to see if the todoviewitem is not a newly created todo -- if it is it wont have an item_id
        if self.item_id:

            # gets its todo and extracts any important info -- does not save in the view item for decoupling purposes
            my_todo = self.todo_view.get_item_todo(self)

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

    # refreshes the checkbox to its todo's completed status -- use when item is completed as it may have an effect on children/parents
    def refresh_completion(self):
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
            new_text = self.item_label.text()

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
            parent : TodoViewItem = self.parent()
            parent_todo = self.todo_view.get_item_todo(parent) if parent else None
            my_todo = self.todo_view.todo_list.create_todo(name=new_text, parent=parent_todo, difficulty=new_difficulty)
            self.item_id = my_todo.todo_id

    # shows the button used to add todo items
    def toggle_item_buttons(self, toggle : bool):

        if not self.todo_view.get_item_todo(self).deleted:
            self.add_button.setVisible(toggle)
            self.delete_button.setVisible(toggle)


# collection of TodoViewItems that is viewed in window
class TodoView(QTreeWidget):

    @staticmethod
    def get_user_todo_view():
        return TodoView(todos.TodoList.get_user_todos())

    def __init__(self, todo_list : todos.TodoList):
        super().__init__()

        self.todo_list = todo_list
        self.items : list[TodoViewItem] = []

        # sets up each column of the todo view
        self.setHeaderLabels(["", "Difficulty"])
        self.header().setStretchLastSection(False)
        self.setUniformRowHeights(True)

        self.min_todo_width = 400
        self.max_difficulty_width = 100

        # adds top level items for the root nodes in the todo list
        todo_view_roots = [TodoViewItem(root_todo.todo_id, self) for root_todo in todo_list.get_roots()]
        self.addTopLevelItems(todo_view_roots)

        # sets the widgets for each item
        self.set_item_widgets()

        # editing of items
        self.editing_item = None
        self.itemActivated.connect(self.toggle_edit)
        self.setExpandsOnDoubleClick(False)

        self.forget_dialog_box = False

        # automatic adjusting of window size to size of whatever is in the widget, as items are expanded/collapsed
        self.setSizeAdjustPolicy(self.SizeAdjustPolicy.AdjustToContents)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.itemExpanded.connect(self.resize_self)
        self.itemCollapsed.connect(self.resize_self)

        # hovering over an todoviewitem shows its add button -- mouse tracking has to be True for this to work
        self.setMouseTracking(True)
        self.current_hover_item : TodoViewItem = None

        self.init_add_button_item(refresh=False)

        self.resize_self()

    # keeps reference to todoviewitem in self.items
    def add_todo_item(self, item : TodoViewItem):
        if item not in self.items:
            self.items.append(item)

    # retrieves an item's associated todo, based on the item's item id
    def get_item_todo(self, item : TodoViewItem):
        return self.todo_list.get_todo(item.item_id)

    # initialises the add_button item, a qtreewidgetitem that allows you to add a todo
    def init_add_button_item(self, refresh : bool = True):

        # we have to initialise the widgets every time because Qt automatically deletes a Qtreewidgetitem's widgets when taketoplevelitem() is called
        self.add_button_widget = QWidget()
        self.add_button_layout = QHBoxLayout()
        self.add_button_widget.setLayout(self.add_button_layout)

        self.add_button = QToolButton()
        system_add_icon = QIcon.ThemeIcon.ListAdd
        add_button_icon = QIcon("guicons/plus.png")
        self.add_button.setIcon(QIcon.fromTheme(system_add_icon, add_button_icon))

        # has to be a lambda function to prevent passing in the boolean as an argument
        self.add_button.clicked.connect(lambda : self.create_todo_item())
        self.add_button_widget.setMouseTracking(True)

        self.add_label = QLabel()
        self.add_label.setText("<i>Add To-do<i>")
        self.add_label.setTextFormat(Qt.TextFormat.RichText)

        self.add_button_layout.addWidget(self.add_button, 0, Qt.AlignmentFlag.AlignLeft)

        # if there are no todoviewitems then display the "add todo" label
        if len(self.items) == 0:
            self.add_button_layout.addWidget(self.add_label, 0, Qt.AlignmentFlag.AlignLeft)

        if refresh == False:

            self.add_button_item = QTreeWidgetItem()
            self.itemClicked.connect(lambda item : self.create_todo_item() if item == self.add_button_item else None)
            self.addTopLevelItem(self.add_button_item)
            self.add_button_item.setFlags(Qt.ItemFlag.ItemNeverHasChildren)
            self.add_button_item.setFirstColumnSpanned(True)

        else:

            self.add_button_item = self.takeTopLevelItem(self.indexOfTopLevelItem(self.add_button_item))
            self.addTopLevelItem(self.add_button_item)

        self.setItemWidget(self.add_button_item, 0, self.add_button_widget)
        self.add_button_item.setSizeHint(0, self.add_button_widget.sizeHint())

    # for each todoviewitem in todoview, set its content to its item_widget (checkbox, name/difficulty label)
    def set_item_widgets(self):

        for item in self.items:

            self.setItemWidget(item, 0, item.item_widget)
            item.setSizeHint(0, item.item_widget.sizeHint())

            self.setItemWidget(item, 1, item.difficulty_widget)
            item.setSizeHint(1, item.difficulty_widget.sizeHint())

    # changes todo completion when an items checkbox is checked
    def item_checked(self, checked : bool, todo_view_item : TodoViewItem):
        if todo_view_item == self.editing_item:
            self.toggle_edit(todo_view_item)
        todo = self.todo_list.get_todo(todo_view_item.item_id)
        self.todo_list.complete_todo(todo=todo, completion=checked)
        self.refresh_completed_items()

    # refreshes the completion status for all of the items
    def refresh_completed_items(self):
        for item in self.items:
            item.refresh_completion()

    # shows/hides button used to add todos/subtodos
    def mouseMoveEvent(self, event):

        hovered_widget = self.viewport().childAt(event.pos())
        hovered_item = self.itemAt(event.pos())

        if self.current_hover_item == hovered_item:
            return

        for item in self.items:
            item.toggle_item_buttons(False)

        if hovered_item:
            self.current_hover_item = hovered_item
        elif hovered_widget:
            self.current_hover_item = hovered_widget.parent()

        if type(self.current_hover_item) == TodoViewItem:
            self.current_hover_item.toggle_item_buttons(True)

        self.adjust_col_width()

        return super().mouseMoveEvent(event)

    # ItemActivated signal is broadcast then toggle edit of that item
    def toggle_edit(self, item : TodoViewItem):

        if type(item) != TodoViewItem:
            return

        if not self.editing_item:
            item.enable_edit()
            self.editing_item = item
        elif self.editing_item:
            self.editing_item.complete_edit()
            if self.editing_item.complete_edit() != False:
                if self.editing_item == item:
                    self.editing_item = None
                else:
                    item.enable_edit()
                    self.editing_item = item

        self.adjust_col_width()

    # creates an empty todoviewitem under a provided parent, which turns into an empty, editable item
    def create_todo_item(self, parent : TodoViewItem = None):

        new_todo_item = TodoViewItem(todo_id=None, todo_view=self)

        if parent:
            parent.addChild(new_todo_item)
        else:
            self.addTopLevelItem(new_todo_item)

        self.set_item_widgets()
        self.expandItem(parent)
        self.setCurrentItem(new_todo_item)
        self.toggle_edit(new_todo_item)
        self.init_add_button_item()
        self.resize_to_item_heights()

    # shows a message box for confirmation before deleting a todo item
    def show_delete_dialog(self):

        if self.forget_dialog_box == True:
            return

        self.delete_dialog = QMessageBox(self)
        self.delete_dialog.setIcon(QMessageBox.Icon.Question)
        self.delete_dialog.setInformativeText("Are you sure?")
        self.delete_dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        self.delete_dialog.setDefaultButton(QMessageBox.StandardButton.No)
        dont_show_again = QCheckBox("Don't show again")
        self.delete_dialog.setCheckBox(dont_show_again)

        choice = self.delete_dialog.exec()
        if choice == QMessageBox.StandardButton.Yes:
            if dont_show_again.checkState() == Qt.CheckState.Checked:
                self.forget_dialog_box = True
            return True
        else:
            return False

    def get_deleted_items(self):
        return [item for item in self.items if item.item_id and self.get_item_todo(item).deleted]

    # displays a dialog to confirm, deletes an item's todo, and for each item in its list of items, deletes if its todo is deleted
    def delete_todo_item(self, item : TodoViewItem):
        if self.editing_item:
            self.toggle_edit(self.editing_item)
        if self.show_delete_dialog() == False:
            return
        if item.item_id:
            self.todo_list.delete_todo(self.get_item_todo(item))
        for item in self.get_deleted_items():
            self.delete_item(item)

    def delete_item(self, item : TodoViewItem):
        if item not in self.items:
            return
        self.items.remove(item)

        item_parent = item.parent()
        if item_parent:
            item_parent.removeChild(item)
        else:
            self.takeTopLevelItem(self.indexOfTopLevelItem(item))
        self.resize_to_item_heights()

    # resizes the item heights to content
    def resize_to_item_heights(self):
        min_height = self.visualItemRect(self.add_button_item).height() + self.header().height() + 5
        max_height = 500
        for item in self.items:
            if item.parent() and not item.parent().isExpanded():
                continue
            min_height += self.visualItemRect(item).height()
        self.setFixedHeight(min(min_height, max_height))

    def adjust_col_width(self):

        # resizing the todo column width
        if self.columnWidth(0) < self.min_todo_width:
            self.setColumnWidth(0, self.min_todo_width)

        # resizing the difficulty column width
        if self.columnWidth(1) > self.max_difficulty_width:
            self.setColumnWidth(1, self.max_difficulty_width)

        # adjusts the window size to fit the col width change
        self.adjustSize()
        self.setFixedWidth(self.columnWidth(0) + self.columnWidth(1))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def resize_self(self):
        self.resize_to_item_heights()
        self.adjust_col_width()

    # occurences that occur on quit -- currently editing item is completed, and the changes are synced to the DB
    def quit_proc(self):

        if self.editing_item:
            self.toggle_edit(self.editing_item)
        self.todo_list.empty_bin()