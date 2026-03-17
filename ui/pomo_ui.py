from core import pomos, events
import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QProgressBar, QStackedLayout, QStyleFactory, QToolButton, QHBoxLayout)
from PyQt6.QtGui import (QIcon)

class PomoView(QWidget):

    @staticmethod
    def get_pomo_view():
        return PomoView()

    update_buttons_signal = pyqtSignal()

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
        self.play_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.disable_start_button()
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

        # triggers signal instead of directly calling function to allow function to work from another thread
        # we use a lambda function to allow the events.py callback arg passing to work
        events.pomo_topic.get_event("TIMER_ITERATED").register(lambda elapsed : self.timer_view.elapse_signal.emit(elapsed))

        self.timer_view_layout.addWidget(self.timer_view, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.timer_toggle_button = QToolButton()
        self.timer_toggle_button.clicked.connect(self.toggle_pomo_timer)
        self.timer_toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.timer_view_layout.addWidget(self.timer_toggle_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        # contains the buttons available to the user when the timer is paused
        self.paused_buttons_widget = QWidget()
        self.paused_buttons_layout = QHBoxLayout()
        self.paused_buttons_widget.setLayout(self.paused_buttons_layout)

        self.reset_timer_button = QToolButton()
        self.reset_timer_button.setText("Reset")
        reset_button_icon = QIcon.fromTheme(QIcon.ThemeIcon.SystemReboot)
        self.reset_timer_button.setIcon(reset_button_icon)
        self.reset_timer_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.reset_timer_button.clicked.connect(self.reset_pomo_timer)
        self.paused_buttons_layout.addWidget(self.reset_timer_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.cancel_timer_button = QToolButton()
        self.cancel_timer_button.setText("Cancel")
        cancel_button_icon = QIcon.fromTheme(QIcon.ThemeIcon.WindowClose)
        self.cancel_timer_button.setIcon(cancel_button_icon)
        self.cancel_timer_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.cancel_timer_button.clicked.connect(self.cancel_pomo_timer)
        self.paused_buttons_layout.addWidget(self.cancel_timer_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.timer_view_layout.addWidget(self.paused_buttons_widget, alignment=Qt.AlignmentFlag.AlignHCenter)
        paused_buttons_sp = self.paused_buttons_widget.sizePolicy()
        paused_buttons_sp.setRetainSizeWhenHidden(True)
        self.paused_buttons_widget.setSizePolicy(paused_buttons_sp)

        self.focus_completed_widget = QWidget()
        self.stacked_layout.addWidget(self.focus_completed_widget)

        self.focus_completed_layout = QVBoxLayout()
        self.focus_completed_widget.setLayout(self.focus_completed_layout)

        self.completion_text = QLabel("""<h1>Focus Period Completed!</h1>""")
        self.completion_stats = QLabel("""<b>Difficulty:</b> {difficulty} <br>
                                      <b>Rounds:</b> {rounds} rounds<br>
                                      <b>Total Duration:</b> {duration}""")
        self.completion_text.setWordWrap(True)
        self.completion_stats.setWordWrap(True)
        self.focus_completed_layout.addWidget(self.completion_text, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.focus_completed_layout.addWidget(self.completion_stats, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.play_button.setIconSize(self.idle_view_widget.sizeHint())
        self.play_button.setFixedSize(self.idle_view_widget.sizeHint())

        # signal used to update the timer buttons in a thread safe way
        self.update_buttons_signal.connect(self.update_timer_buttons)
        self.update_buttons_signal.emit()

        self.timer_toggle_button.setIconSize(self.reset_timer_button.iconSize())
        self.timer_toggle_button.setFixedSize(self.reset_timer_button.sizeHint())

        events.todo_topic.get_event("TODO_SELECTED").register(self.enable_start_button)
        events.pomo_topic.get_event("TIMER_COMPLETED").register(self.update_timer_view)
        events.pomo_topic.get_event("FOCUS_PERIOD_COMPLETED").register(self.show_focus_stats)

    def set_max_width(self, max_width : int):
        self.setMaximumWidth(max_width)
        self.completion_text.adjustSize()
        self.completion_stats.adjustSize()

    # when a todo is selected, set the difficulty of the pomodoro timer to the difficulty of the todo and enable the start timer button
    def enable_start_button(self, todo_difficulty : int):
        if self.stacked_layout.currentWidget() == self.focus_completed_widget:
            if todo_difficulty != -1:
                self.stacked_layout.setCurrentWidget(self.idle_view_widget)
        # a difficulty of -1 means that no todo is selected / the todo is invalid (e.g completed)
        if todo_difficulty == -1:
            self.disable_start_button()
            return
        self.pomo_timer.set_difficulty(todo_difficulty)
        self.play_button.setText("Start Focus Period")
        self.play_button.setEnabled(True)

    # happens when a todo is not selected / deselected -- goes back to original disabled state
    def disable_start_button(self):
        self.play_button.setText("Select a todo")
        self.play_button.setEnabled(False)

    # starts the display of the pomodoro timer
    def start_timer_view(self, difficulty : int):
        events.pomo_topic.get_event("FOCUS_PERIOD_STARTED").trigger()
        # while in a focus period, tomo hp/xp is not decremented
        pomos.tick_timer.pause_timer()
        durations = self.pomo_timer.get_split(difficulty)
        self.stacked_layout.setCurrentWidget(self.timer_view_widget)
        self.timer_view.start_view(durations=durations, focus_mode=True)
        self.pomo_timer.reset_total_elapsed()
        self.update_rounds(self.pomo_timer.rounds)

    # updates timer view (whenever the timer is completed)
    def update_timer_view(self):
        self.update_rounds(self.pomo_timer.rounds)
        self.timer_view.update_view_signal.emit(self.pomo_timer.focus_mode)
        self.update_buttons_signal.emit()

    # starts the pomodoro timer
    def toggle_pomo_timer(self):
        if self.pomo_timer.current_timer().is_running():
            self.pomo_timer.pause_timer()
        else:
            self.pomo_timer.start_timer()
        self.update_timer_buttons()

    # resets the pomodoro timer/
    def reset_pomo_timer(self):
        self.pomo_timer.reset_timer()
        self.update_timer_view()

    # cancels the focus period, no xp rewarded
    def cancel_pomo_timer(self):
        self.pomo_timer.kill_timer()
        # resumes progress of decrement timer when focus period is ended
        pomos.tick_timer.start_timer()
        events.pomo_topic.get_event("FOCUS_PERIOD_CANCELLED").trigger()
        self.stacked_layout.setCurrentWidget(self.idle_view_widget)

    # update the rounds label
    def update_rounds(self, rounds : int):
        self.rounds.setText(f"<b>Rounds</b>: {rounds}")

    # updates the button to be start or pause based on the current state of the timer
    def update_timer_buttons(self):
        if self.pomo_timer.current_timer().is_running():
            timer_button_icon = QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackPause)
            self.timer_toggle_button.setText("PAUSE")
            self.paused_buttons_widget.hide()
        else:
            self.timer_toggle_button.setText("START")
            timer_button_icon = QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackStart)
            self.paused_buttons_widget.show()
        self.timer_toggle_button.setIcon(timer_button_icon)

    # shows stats about the completion of a focus period
    def show_focus_stats(self):
        # resumes progress of the decrement timer when the focus period is done
        if pomos.tick_timer.is_running() == False:
            pomos.tick_timer.start_timer()
        # if its not in the focus period screen before this is called dont bother
        if self.stacked_layout.currentWidget() != self.timer_view_widget:
            return
        if self.pomo_timer.current_timer().is_running():
            self.pomo_timer.current_timer().pause_timer()
        self.stacked_layout.setCurrentWidget(self.focus_completed_widget)
        difficulties = ["Trivial", "Easy", "Normal", "Hard"]
        difficulty = difficulties[self.pomo_timer.difficulty - 1]
        rounds = self.pomo_timer.rounds
        duration = str(datetime.timedelta(seconds=self.pomo_timer.get_total_elapsed()))
        self.completion_stats.setText(self.completion_stats.text().format(difficulty=difficulty, rounds=rounds, duration=duration))
        self.pomo_timer.current_timer().finish_timer()

    # what happens when the window is closed
    def quit_proc(self):
        self.pomo_timer.kill_timer()
        pomos.tick_timer.kill()

# progress bar that ticks with the pomodoro timer
class PomoTimerView(QProgressBar):

    # signals allow for updates of the main thread's Qobjects from another thread:

    # signal used to set the elapsed time of the pomodoro timer
    elapse_signal = pyqtSignal(int)
    # signal used to update the view on completion of pomodoro timer
    update_view_signal = pyqtSignal(bool)

    # this is only initialised to ensure everything is already there
    def __init__(self):
        super().__init__()

        self.durations = [-1, -1]

        self.setOrientation(Qt.Orientation.Vertical)
        self.setMinimum(0)
        self.setMaximum(0)
        self.setStyle(QStyleFactory.create("Fusion"))
        self.setMinimumWidth(50)

        self.elapse_signal.connect(self.set_elapsed)
        self.update_view_signal.connect(self.update_view)

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