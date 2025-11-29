from threading import (Timer, Event)
import time
import events

# right2clicky on StackOverflow --https://stackoverflow.com/a/48741004
# Timer that iterates before executing function -- has its own thread
class IteratingTimer(Timer):

    def __init__(self, interval : int, function : callable, completion_callback : callable, args = None, kwargs = None):
        super().__init__(interval, function, args, kwargs)
        # attribute determining whether to carry out iteration function or not
        self.paused = Event()
        # callback thats run on completion of the timer
        self.callback = completion_callback

    def run(self):
        # while the "finished" event isnt over, carry out function if not paused
        # does this every "self.interval" seconds -- typically 1
        while not self.finished.wait(self.interval):
            # if self.paused.is_set():
            #     print("Paused")
            # else:
            if not self.paused.is_set():
                self.function(*self.args)

        # callback thats executed on completion of the function
        self.callback(*self.args)

# individual timer with its own IteratingTimer object
class BaseTimer():

    def __init__(self, duration : int):
        self.elapsed = 0
        self.duration = duration
        self.iterating_timer = IteratingTimer(interval=1, function=self.iterate_timer, completion_callback=self.timer_completed_callback)

    # function used by IteratingTimer class to iterate timer
    def iterate_timer(self):
        self.elapsed += 1
        # print(f"{self.elapsed}/{self.duration} secs")
        if self.elapsed >= self.duration:
            self.iterating_timer.finished.set()


    def start_timer(self):
        # if the timer has already finished then create a new timer in another thread
        if self.iterating_timer.finished.is_set():
            self.iterating_timer = IteratingTimer(interval=1, function=self.iterate_timer, completion_callback=self.timer_completed_callback)
        # start the timer
        self.iterating_timer.start()

    # activate the paused event to stop iterating_timer.function() from executing each interval
    def stop_timer(self):
        self.iterating_timer.paused.set()

    # stops the timer and resets the time elapsed
    def reset_timer(self):
        self.stop_timer()
        self.elapsed = 0

    # called when timer completes
    def timer_completed_callback(self):
        events.pomo_channel.get_event("TIMER_COMPLETED").trigger()
        self.reset_timer()

    def set_timer_duration(self, duration : int):
        self.duration = duration

# singleton object (you can only have 1 at a time)
# implementation from Christian Meyer -- https://code.activestate.com/recipes/52558/#c7
class _PomodoroTimer():

    def __init__(self, focus_duration : int, rest_duration : int):
        # timers stored in dictionary with the current focus mode as the key
        self.timers = {True : BaseTimer(focus_duration), False : BaseTimer(rest_duration)}
        self.focus_mode = True
        # registers callback to timer completion
        events.pomo_channel.get_event("TIMER_COMPLETED").register(self.timer_completion_event)

    def get_current_timer(self):
        return self.timers[self.focus_mode]

    def get_both_timers(self) -> list[BaseTimer, BaseTimer]:
        return list(self.timers.values())

    def start_timer(self):
        self.get_current_timer().start_timer()

    def stop_timer(self):
        self.get_current_timer().stop_timer()

    # on a timer completion event, the focus mode of the pomodoro timer is switched
    def timer_completion_event(self):
        self.focus_mode = not self.focus_mode

    def set_split(self, focus_duration : int, rest_duration : int):
        # order sensitive -- dont change order of self.timers!
        focus_timer, rest_timer = self.get_both_timers()
        focus_timer.set_timer_duration(focus_duration)
        rest_timer.set_timer_duration(rest_duration)

# the unique singleton object
_pomodoro_timer_singleton = None

# higher-level class used to return singleton
def PomodoroTimer(focus_duration : int, rest_duration : int) -> _PomodoroTimer:

    global _pomodoro_timer_singleton

    if not _pomodoro_timer_singleton:
        _pomodoro_timer_singleton = _PomodoroTimer(focus_duration=focus_duration, rest_duration=rest_duration)
    return _pomodoro_timer_singleton


if __name__ == "__main__":

    user_pomodoro_timer = PomodoroTimer(focus_duration=30, rest_duration=10)

    # FOCUS
    user_pomodoro_timer.start_timer()
    time.sleep(33)

    # REST
    user_pomodoro_timer.start_timer()
    time.sleep(13)

    # FOCUS (PAUSED 10s IN)
    user_pomodoro_timer.start_timer()
    time.sleep(10)
    user_pomodoro_timer.stop_timer()
