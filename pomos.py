from threading import (Timer, Event)
import events

# right2clicky on StackOverflow --https://stackoverflow.com/a/48741004
# Timer that iterates before executing function -- has its own thread
class IteratingTimer(Timer):

    def __init__(self, interval : int, function : callable, args = None, kwargs = None):
        super().__init__(interval, function, args, kwargs)
        # attribute determining whether to carry out iteration function or not
        self.paused = Event()

    def run(self):
        # while the "finished" event isnt over, carry out function if not paused
        # does this every "self.interval" seconds -- typically 1
        while not self.finished.wait(self.interval):
            if not self.paused.is_set():
                self.function(*self.args)

# individual timer with its own IteratingTimer object
class BaseTimer():

    def __init__(self, duration : int):
        self.elapsed = 0
        self.duration = duration
        self.iterating_timer = IteratingTimer(interval=1, function=self.iterate_timer)
        self.finished = False
        self.paused = False

    # function used by IteratingTimer class to iterate timer
    def iterate_timer(self):
        self.elapsed += 1
        # triggers timer iteration event, passing in the timer as argument
        events.pomo_channel.get_event("TIMER_ITERATED").trigger(self)

        # if the elapsed time is more than duration, carry out completion stuff
        if self.elapsed >= self.duration:
            self.finish_timer()

    def finish_timer(self):
        # marks the finished thread event for the iterating timer, marks self.finished as True
        # triggers TIMER_COMPLETED event passing this timer as argument, before resetting timer
        # ENSURE THE TIMER IS DECLARED AS FINISHED BEFORE BROADCASTING EVENT -- ALL CALLBACKS MUST KNOW IT AS FINISHED VIA THIS EVENT
        # AS IT IS QUICKLY TURNED BACK TO UNFINISHED IN THE RESET_TIMER METHOD
        self.iterating_timer.finished.set()
        self.finished = True
        events.pomo_channel.get_event("TIMER_COMPLETED").trigger(self)
        self.reset_timer()

    def start_timer(self):
        # if the timer is paused then just unpause it
        if self.paused:
            self.iterating_timer.paused.clear()
            self.paused = False
        # if the timer is not paused, its bcs its been reset (new thread) so just start the new thread
        elif self.iterating_timer.is_alive() == False:
            self.iterating_timer.start()

    # activates paused thread event -- stops function from occuring every interval but thread is still alive
    def pause_timer(self):
        self.iterating_timer.paused.set()
        self.paused = True

    # creates a new timer thread to replace prev one, and resets elapsed time, finished status and paused status
    def reset_timer(self):
        self.iterating_timer = IteratingTimer(interval=1, function=self.iterate_timer)
        self.elapsed = 0
        self.finished = False
        self.paused = False

    # returns boolean representing whether the timer is currently running or not
    def is_running(self):
        return self.iterating_timer.is_alive() and not(self.paused or self.finished)

# singleton object (you can only have 1 at a time) -- singleton implementation from Christian Meyer -- https://code.activestate.com/recipes/52558/#c7
# object consisting of two timers -- current timer is dependent on pomodoro focus mode
class _PomodoroTimer():

    def __init__(self, focus_duration : int, rest_duration : int):
        # timers stored in dictionary with the current focus mode as the key
        self.focus_timer = BaseTimer(duration=focus_duration)
        self.rest_timer = BaseTimer(duration=rest_duration)
        self.timers = {True : self.focus_timer, False : self.rest_timer}
        self.focus_mode = True

        # registers callback to timer completion
        events.pomo_channel.get_event("TIMER_COMPLETED").register(lambda timer : self.switch_focus())

    def current_timer(self):
        return self.timers[self.focus_mode]

    def get_both_timers(self) -> list[BaseTimer, BaseTimer]:
        return list(self.timers.values())

    def start_timer(self):
        self.current_timer().start_timer()

    def pause_timer(self):
        self.current_timer().pause_timer()

    def reset_timer(self):
        self.current_timer().reset_timer()

    # on a timer completion event, the focus mode of the pomodoro timer is switched and the current timer changes
    def switch_focus(self):
        self.focus_mode = not self.focus_mode
        # here is where we want to switch the previous timer from finished to not finished

    # as it is a singleton object the durations may need to be changed
    def set_durations(self, focus_duration : int, rest_duration : int):
        self.focus_timer.duration = focus_duration
        self.rest_timer.duration = rest_duration

# the unique singleton object
_pomodoro_timer_singleton = None

# higher-level PomodoroTimer class used to return singleton
def PomodoroTimer(focus_duration : int = None, rest_duration : int = None) -> _PomodoroTimer:

    global _pomodoro_timer_singleton

    # if the singleton hasn't been created yet and the incorrect number of arguments haven't been passed in, raise an exception
    # otherwise, just create the object
    # if it has been created already just return the singleton
    if not _pomodoro_timer_singleton:
        if not focus_duration or not rest_duration:
            raise ValueError("Singleton object for PomodoroTimer yet to be defined. Not enough arguments passed into PomodoroTimer to define.")
        _pomodoro_timer_singleton = _PomodoroTimer(focus_duration=focus_duration, rest_duration=rest_duration)
    return _pomodoro_timer_singleton


if __name__ == "__main__":

    # CLI interface for interacting with pomodoro timers

    import os
    import sys
    from threading import enumerate

    def clear_terminal():
        # For Windows
        if os.name == 'nt':
            _ = os.system('cls')
        # For macOS and Linux
        else:
            _ = os.system('clear')


    focus_duration = int(input("Enter focus duration (in seconds): "))
    rest_duration = int(input("Enter rest duration (in seconds): "))

    user_pomodoro = PomodoroTimer(focus_duration=focus_duration, rest_duration=rest_duration)

    # called on every iteration of the timer -- displays the current elapsed time and commands without worrying about inputs
    def display_timer():

        # this is normally really bad practice -- callback function should not be coupled to global object
        global user_pomodoro
        clear_terminal()

        # displays relevant info about timer, supplying interface for inputs without handling inputs

        # print(f"Ongoing threads: {enumerate()} ")

        timer = user_pomodoro.current_timer()
        print(f"{"FOCUS!" if user_pomodoro.focus_mode else "REST."}")
        print(f"{timer.duration - timer.elapsed}s")

        # print(f"Timer alive: {timer.iterating_timer.is_alive()}")
        # print(f"Timer labelled as finished: {timer.finished}")
        # print(f"Timer labelled as paused: {timer.paused}")
        # print(f"Timer labelled as running: {timer.is_running()}")

        if user_pomodoro.current_timer().is_running():
            print("Stop [S]")
        else:
            print("Start [S]  [R] Reset  [E] Exit")

    # each time the timer is iterated the elapsed is displayed to user
    events.pomo_channel.get_event("TIMER_ITERATED").register(lambda timer : display_timer())
    # if the timer is completed, it will update display one more time in order to switch modes
    events.pomo_channel.get_event("TIMER_COMPLETED").register(lambda timer : display_timer())

    running = True

    while running == True:

        display_timer()

        user_input = input("").lower()

        # handles user input depending on current state of pomodoro timer -- this is handled on the main thread

        # commands for while timer is running (stop timer)
        if user_pomodoro.current_timer().is_running():
            if user_input == "s":
                user_pomodoro.pause_timer()

        # commands for while timer is idle (start timer, reset timer, exit)
        else:
            if user_input == "s":
                user_pomodoro.start_timer()
            elif user_input == "r":
                user_pomodoro.reset_timer()
            elif user_input == "e":
                user_pomodoro.current_timer().finish_timer()
                clear_terminal()
                running = False


    sys.exit()
