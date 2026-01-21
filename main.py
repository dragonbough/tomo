from ui import (tomos_ui, todo_ui)

from PyQt6.QtWidgets import QApplication
import sys

# sys.argv allows arguments to be passed into the QApplication from the command line
app = QApplication(sys.argv)

todo_view = todo_ui.TodoView.get_user_todo_view()
todo_view.show()

tomos_view = tomos_ui.TomoViewManager.get_tomos_view()
tomos_view.show()

# when the overall application is closed carry out the quit procedure for the todoview

def quit_proc():
    todo_view.quit_proc()
    tomos_view.quit_proc()

app.lastWindowClosed.connect(quit_proc)

# starts app event loop
app.exec()