from ui import todo_ui

from PyQt6.QtWidgets import QApplication
import sys

# sys.argv allows arguments to be passed into the QApplication from the command line
app = QApplication(sys.argv)

todo_view = todo_ui.TodoView.get_user_todo_view()
todo_view.show()

# when the overall application is closed carry out the quit procedure for the todoview
app.lastWindowClosed.connect(todo_view.quit_proc)

# starts app event loop
app.exec()