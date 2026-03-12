from ui import (tomos_ui, todo_ui, pomo_ui)

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout
from PyQt6.QtCore import Qt
import sys

class MainView(QMainWindow):

    @staticmethod
    def get_main_view():
        todo_view = todo_ui.TodoView.get_user_todo_view()
        tomo_view = tomos_ui.TomoViewManager.get_tomos_view()
        pomo_view = pomo_ui.PomoView.get_pomo_view()
        return MainView(todo_view=todo_view, tomo_view=tomo_view, pomo_view=pomo_view)

    def __init__(self, todo_view : todo_ui.TodoView, tomo_view : tomos_ui.TomoViewManager, pomo_view : pomo_ui.PomoView):

        super().__init__()

        self.todo_view = todo_view
        self.tomo_view = tomo_view
        self.pomo_view = pomo_view
        self.views = self.todo_view, self.tomo_view, self.pomo_view

        self.views_widget = QWidget()
        self.views_layout = QHBoxLayout()
        self.views_widget.setLayout(self.views_layout)

        self.views_layout.addWidget(self.tomo_view)
        self.views_layout.addWidget(self.todo_view)
        self.views_layout.addWidget(self.pomo_view)

        self.setCentralWidget(self.views_widget)

        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setWindowFlag(Qt.WindowType.CustomizeWindowHint, True)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)

        self.tomo_view.set_scale(1)

        # basically the same as setting a fixed height
        self.todo_view.set_min_height(self.tomo_view.height())
        self.todo_view.set_max_height(self.tomo_view.height())
        self.pomo_view.setFixedHeight(self.tomo_view.height())

        self.setFixedSize(self.sizeHint())

    # allows each view to detach into their own separate moveable windows
    # NOT COMPLETED
    def detach_views(self):

        for view in self.views:
            self.views_layout.removeWidget(view)
            view.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
            view.setWindowFlag(Qt.WindowType.CustomizeWindowHint, True)
            view.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)

    # when the overall application is closed carry out the quit procedure for each view
    def closeEvent(self, a0):
        for view in self.views:
            view.quit_proc()
        return super().closeEvent(a0)

app = QApplication(sys.argv)

main_view = MainView.get_main_view()
main_view.show()

# starts app event loop
app.exec()