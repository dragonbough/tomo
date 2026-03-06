from ui import (tomos_ui, todo_ui)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
import sys

# sys.argv allows arguments to be passed into the QApplication from the command line
app = QApplication(sys.argv)

todo_view = todo_ui.TodoView.get_user_todo_view()
tomo_view = tomos_ui.TomoViewManager.get_tomos_view()

views = [todo_view, tomo_view]

for view in views:
        view.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        view.setWindowFlag(Qt.WindowType.CustomizeWindowHint, True)
        view.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)

for view in views:
    view.show()

# when the overall application is closed carry out the quit procedure for the todoview

def quit_proc():
    for view in views:
        view.quit_proc()

app.lastWindowClosed.connect(quit_proc)

# starts app event loop
app.exec()