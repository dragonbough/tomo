from core import pomos, events
import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QProgressBar, QPushButton, QStackedLayout, QStyleFactory)
from PyQt6.QtGui import (QIcon)

class PomoView(QWidget):

    @staticmethod
    def get_pomo_view():
        return PomoView()

    def __init__(self):
        super().__init__()

        # don't do anything until a pomodoro timer is initialised via event
        # keep everything in methods

        # difficulty decided on currently selected todo:
        # if play button clicked set the current difficulty of the pomodoro timer,
        # and start the focus period

        # once we know difficulty, start the pomotimerview using the start_view, passing in duration and stuff

        self.setWindowTitle("tomo | pomo")

        self.pomo_timer = pomos.PomodoroTimer()

        self.stacked_layout = QStackedLayout(self)

        # icon that will be used to start the timer for the currently selected Todo
        self.idle_view_widget = QWidget()
        self.stacked_layout.addWidget(self.idle_view_widget)

        self.idle_view_layout = QVBoxLayout()
        self.idle_view_widget.setLayout(self.idle_view_layout)

        self.play_button = QPushButton()
        play_button_icon = QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackStart)
        self.play_button.setIcon(play_button_icon)
        self.play_button.clicked.connect(self.start_timer_view)
        self.idle_view_layout.addWidget(self.play_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.stacked_layout.setCurrentWidget(self.idle_view_widget)

        self.timer_view_widget = QWidget()
        self.stacked_layout.addWidget(self.timer_view_widget)

        self.timer_view_layout = QVBoxLayout()
        self.timer_view_widget.setLayout(self.timer_view_layout)

        self.rounds = QLabel()
        self.timer_view_layout.addWidget(self.rounds, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.timer_view = PomoTimerView()
        events.pomo_topic.get_event("TIMER_ITERATED").register(self.timer_view.set_elapsed)
        self.timer_view_layout.addWidget(self.timer_view, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.timer_button = QPushButton()
        self.timer_button.clicked.connect(self.start_pomo_timer)
        self.timer_view_layout.addWidget(self.timer_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.setFixedHeight(350)
        self.play_button.setIconSize(self.idle_view_widget.sizeHint())
        self.play_button.setFixedSize(self.idle_view_widget.sizeHint())

    # starts the display of the pomodoro timer
    def start_timer_view(self, difficulty : int):

        durations = self.pomo_timer.get_split(difficulty)
        self.stacked_layout.setCurrentWidget(self.timer_view_widget)
        self.timer_view.start_view(durations=durations, focus_mode=True)
        self.update_rounds(self.pomo_timer.rounds)
        self.update_timer_button()

    # starts the pomodoro timer
    def start_pomo_timer(self):
        if self.pomo_timer.current_timer().is_running():
            self.pomo_timer.pause_timer()
        else:
            self.pomo_timer.start_timer()
        self.update_timer_button()

    # update the rounds label
    def update_rounds(self, rounds : int):
        self.rounds.setText(f"<b>Rounds</b>: {rounds}")

    # updates the button to be start or pause based on the current state of the timer
    def update_timer_button(self):
        if self.pomo_timer.current_timer().is_running():
            self.timer_button.setText("PAUSE")
        else:
            self.timer_button.setText("START")

    # what happens when the window is closed
    def quit_proc(self):
        self.pomo_timer.pause_timer()

# progress bar that ticks with the pomodoro timer
class PomoTimerView(QProgressBar):

    # this is only initialised to ensure everything is already there
    def __init__(self):
        super().__init__()

        self.durations = [-1, -1]

        self.setOrientation(Qt.Orientation.Vertical)
        self.setMinimum(0)
        self.setMaximum(0)
        self.setStyle(QStyleFactory.create("Fusion"))
        self.setMinimumWidth(50)

    # creates the timer
    def start_view(self, durations : tuple[int, int], focus_mode : bool, elapsed : int = 0):
        self.durations = durations
        self.focus_mode = focus_mode
        self.set_max_duration()
        self.set_elapsed(elapsed)

    # sets the mode for the timer
    def set_max_duration(self):
        if self.focus_mode:
            self.setMaximum(self.durations[0])
        else:
            self.setMaximum(self.durations[1])

    # updates the elapsed time of the timer
    def set_elapsed(self, seconds : int):
        elapsed_mins = str(datetime.timedelta(seconds=(self.maximum()-seconds)))
        self.setValue(seconds)
        self.setFormat(elapsed_mins)