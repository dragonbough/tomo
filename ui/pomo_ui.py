from core import pomos, events
import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QProgressBar, QPushButton, QStackedLayout, QStyleFactory, QToolButton)
from PyQt6.QtGui import (QIcon)

class PomoView(QWidget):

    @staticmethod
    def get_pomo_view():
        return PomoView()

    def __init__(self):
        super().__init__()

        self.setWindowTitle("tomo | pomo")

        self.pomo_timer = pomos.PomodoroTimer()

        self.stacked_layout = QStackedLayout(self)

        # icon that will be used to start the timer for the currently selected Todo
        self.idle_view_widget = QWidget()
        self.stacked_layout.addWidget(self.idle_view_widget)

        self.idle_view_layout = QVBoxLayout()
        self.idle_view_widget.setLayout(self.idle_view_layout)

        self.play_button  = QToolButton()
        play_button_icon = QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackStart)
        self.play_button.setIcon(play_button_icon)
        self.play_button.setText("Select a todo")
        self.play_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.play_button.clicked.connect(self.start_timer_view)
        self.play_button.setEnabled(False)
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

        self.timer_toggle_button = QToolButton()
        self.timer_toggle_button.clicked.connect(self.toggle_pomo_timer)
        self.timer_toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.timer_view_layout.addWidget(self.timer_toggle_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.reset_timer_button = QPushButton()
        self.reset_timer_button.setText("Reset")
        self.reset_timer_button.clicked.connect(self.reset_pomo_timer)
        self.timer_view_layout.addWidget(self.reset_timer_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.play_button.setIconSize(self.idle_view_widget.sizeHint())
        self.play_button.setFixedSize(self.idle_view_widget.sizeHint())

        self.update_timer_buttons()

        events.todo_topic.get_event("TODO_SELECTED").register(self.enable_start_button)
        events.pomo_topic.get_event("TIMER_COMPLETED").register(self.update_timer_view)

    # when a todo is selected, set the difficulty of the pomodoro timer to the difficulty of the todo and enable the start timer button
    def enable_start_button(self, todo_difficulty : int):
        self.pomo_timer.set_difficulty(todo_difficulty)
        self.play_button.setText("Start Focus Period")
        self.play_button.setEnabled(True)

    # starts the display of the pomodoro timer
    def start_timer_view(self, difficulty : int):
        events.pomo_topic.get_event("FOCUS_PERIOD_STARTED").trigger()
        durations = self.pomo_timer.get_split(difficulty)
        self.stacked_layout.setCurrentWidget(self.timer_view_widget)
        self.timer_view.start_view(durations=durations, focus_mode=True)
        self.update_rounds(self.pomo_timer.rounds)
        self.setFixedHeight(350)

    # updates timer view (whenever the timer is completed)
    def update_timer_view(self):
        self.update_rounds(self.pomo_timer.rounds)
        self.timer_view.update_view(self.pomo_timer.focus_mode)
        self.update_timer_buttons()

    # starts the pomodoro timer
    def toggle_pomo_timer(self):
        if self.pomo_timer.current_timer().is_running():
            self.pomo_timer.pause_timer()
        else:
            self.pomo_timer.start_timer()
        self.update_timer_buttons()

    # resets the pomodoro timer
    def reset_pomo_timer(self):
        self.pomo_timer.reset_timer()
        self.timer_view.set_elapsed(0)

    # update the rounds label
    def update_rounds(self, rounds : int):
        self.rounds.setText(f"<b>Rounds</b>: {rounds}")

    # updates the button to be start or pause based on the current state of the timer
    def update_timer_buttons(self):
        if self.pomo_timer.current_timer().is_running():
            timer_button_icon = QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackPause)
            self.timer_toggle_button.setText("PAUSE")
            self.reset_timer_button.hide()
        else:
            self.timer_toggle_button.setText("START")
            timer_button_icon = QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackStart)
            self.reset_timer_button.show()
        self.timer_toggle_button.setIcon(timer_button_icon)

    # what happens when the window is closed
    def quit_proc(self):
        self.pomo_timer.kill_timer()

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

    def update_view(self, focus_mode : bool):
        self.focus_mode = focus_mode
        self.set_max_duration()
        self.set_elapsed(0)

    # sets the mode for the timer
    def set_max_duration(self):
        focus_duration, rest_duration = self.durations
        if self.focus_mode:
            self.setMaximum(focus_duration)
        else:
            self.setMaximum(rest_duration)

    # updates the elapsed time of the timer -- if in work mode then tick upwards, if in rest mode tick downwards
    def set_elapsed(self, seconds : int):
        elapsed_mins = str(datetime.timedelta(seconds=(self.maximum()-seconds)))
        if self.focus_mode == True:
            self.setValue(seconds)
            focus_mode = "FOCUS"
        else:
            rest_duration = self.durations[1]
            self.setValue(rest_duration - seconds)
            focus_mode = "REST"
        self.setFormat(f"{focus_mode}!\n{elapsed_mins}")