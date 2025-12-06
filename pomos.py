from threading import (Timer, Event)
import events
import data

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

    def __init__(self, difficulty : int = 1):

        # difficulties range from 1 to 4:
        # 1: Trivial  2: Easy  3: Normal  4: Hard

        if not(1 <= difficulty <= 4):
            raise ValueError("Invalid difficulty value as argument for PomodoroTimer")

        self.difficulties = {}
        self.difficulties : dict[int : (int, int)]
        self.difficulty = difficulty

        # retrieves the user saved difficulties for each pomodoro split
        # converts the minutes for the focus and rest duration into seconds (*60)
        for pomo_difficulty in data.retrieve_pomo_difficulties():
            diff = int(pomo_difficulty["difficulty"])
            focus_dur = int(pomo_difficulty["focusduration"]) * 60
            rest_dur = int(pomo_difficulty["restduration"]) * 60
            self.difficulties[diff] = (focus_dur, rest_dur)

        # defines the current timers for based on the difficulty

        self.focus_timer = None
        self.focus_timer : BaseTimer
        self.rest_timer = None
        self.rest_timer : BaseTimer
        self.timers = {}
        self.timers : dict[bool : BaseTimer]

        self.set_difficulty(difficulty)

        # defines the current pomodoro mode and the number of rounds
        self.focus_mode = True
        self.rounds = 0

        # defines the bin used to save updates to difficulty presets
        self.modify_bin = []

        # registers callback to timer completion
        events.pomo_channel.get_event("TIMER_COMPLETED").register(lambda timer : self.switch_focus())


    # on a timer completion event, the focus mode of the pomodoro timer is switched and the current timer changes
    # number of rounds incremented if the previous timer was a rest
    def switch_focus(self):
        if self.focus_mode == False:
            self.rounds += 1
            # triggers ROUND_COMPLETED event after every round
            events.pomo_channel.get_event("ROUND_COMPLETED").trigger()
        self.focus_mode = not self.focus_mode

    # changes pomodoro difficulty + defines the focus and rest timers based on pomodoro split derived from difficulty
    def set_difficulty(self, difficulty : int):

        self.validate_difficulty(difficulty)

        self.difficulty = difficulty

        focus_duration, rest_duration = self.get_split(self.difficulty)

        self.focus_timer = BaseTimer(duration=focus_duration)
        self.rest_timer = BaseTimer(duration=rest_duration)
        self.timers = {True : self.focus_timer, False : self.rest_timer}
        self.focus_mode = True

    # changes durations for this difficulty -- if no difficulty provided, uses current difficulty
    # durations stored in seconds
    def edit_split(self, focus_duration : int, rest_duration : int, difficulty : int = None):

        if not difficulty:
            difficulty = self.difficulty

        self.validate_difficulty(difficulty)

        focus_duration_secs = focus_duration * 60
        rest_duration_secs = rest_duration * 60

        self.difficulties[difficulty] = (focus_duration_secs, rest_duration_secs)
        self.focus_timer.duration, self.rest_timer.duration = focus_duration_secs, rest_duration_secs

        self.bin_modified(difficulty=difficulty)

    # validates difficulties passed into PomodoroTimer methods based on whether they actually exist in self.difficulties or not
    def validate_difficulty(self, difficulty : int):

        if type(difficulty) != int:
            raise TypeError(f"Invalid type for difficulty value: {type(difficulty)}")

        if difficulty not in self.difficulties:
            raise ValueError(f"Invalid difficulty value: {difficulty} as argument for PomodoroTimer")

    # bins a difficulty preset for it to be modified in the DB later
    # saved in DB in minutes
    def bin_modified(self, difficulty : int):

        self.validate_difficulty(difficulty)
        modified_pomo_difficulty = {}
        modified_pomo_difficulty["difficulty"] = difficulty
        focus_duration_mins, rest_duration_mins = self.get_split(difficulty)
        focus_duration_mins /= 60
        rest_duration_mins /= 60
        modified_pomo_difficulty["focusduration"], modified_pomo_difficulty["restduration"] = focus_duration_mins, rest_duration_mins
        self.modify_bin.append(modified_pomo_difficulty)

    def empty_modified_bin(self):

        if self.modify_bin:
            data.modify_pomo_difficulties(*[pomo_difficulty for pomo_difficulty in self.modify_bin])

    def get_split(self, difficulty : int):

        self.validate_difficulty(difficulty)
        return self.difficulties[difficulty]

    def current_timer(self) -> BaseTimer:
        return self.timers[self.focus_mode]

    def get_both_timers(self) -> list[BaseTimer, BaseTimer]:
        return list(self.timers.values())

    def start_timer(self):
        self.current_timer().start_timer()

    def pause_timer(self):
        self.current_timer().pause_timer()

    def reset_timer(self):
        self.current_timer().reset_timer()

# the unique singleton object
_pomodoro_timer_singleton = None

# higher-level PomodoroTimer class used to define singleton if it doesnt exist and return singleton
def PomodoroTimer(difficulty : int = 1) -> _PomodoroTimer:

    global _pomodoro_timer_singleton

    if not _pomodoro_timer_singleton:
        _pomodoro_timer_singleton = _PomodoroTimer(difficulty=difficulty)

    return _pomodoro_timer_singleton


if __name__ == "__main__":

    # CLI interface for interacting with pomodoro timers

    import os
    import sys
    import datetime
    # from threading import enumerate

    def clear_terminal():
        # For Windows
        if os.name == 'nt':
            _ = os.system('cls')
        # For macOS and Linux
        else:
            _ = os.system('clear')


    # focus_duration = int(input("Enter focus duration (in seconds): "))
    # rest_duration = int(input("Enter rest duration (in seconds): "))

    user_pomodoro = PomodoroTimer()

    difficulty_strings = ["Trivial", "Easy", "Normal", "Hard"]

    while True:

        running = False

        clear_terminal()
        print("Difficulty:  Focus/Rest:")
        for difficulty in user_pomodoro.difficulties:
            difficulty_string = difficulty_strings[difficulty-1]
            padding = " " * (10 - len(difficulty_string))
            focus_duration, rest_duration = user_pomodoro.get_split(difficulty)
            print(f"[{difficulty}] {difficulty_string}{padding}    {int(focus_duration / 60)}/{int(rest_duration / 60)}")


        user_input = input("\n[1-4] Select  [X] Exit:\n").lower()

        # validating inputs before progressing
        if not user_input or (user_input.isdecimal() and int(user_input) not in user_pomodoro.difficulties) or (not user_input.isdecimal() and user_input != "x"):
            while not user_input or (user_input.isdecimal() and int(user_input) not in user_pomodoro.difficulties) or (not user_input.isdecimal() and user_input != "x"):
                user_input = input("[1-4] Select  [X] Exit:\n").lower()
        if user_input.isdecimal():
            choice = input("[E] Edit  [ENTER] Start:\n").lower()
            if len(choice) == 0:
                difficulty = int(user_input)
                user_pomodoro.set_difficulty(difficulty)
                running = True
            elif choice == "e":
                focus_dur = int(input("Focus duration (mins): "))
                rest_dur = int(input("Rest duration (mins): "))
                user_pomodoro.edit_split(focus_duration=focus_dur, rest_duration=rest_dur, difficulty=int(user_input))
        elif user_input == "x":
            break

        # called on every iteration of the timer -- displays the current elapsed time and commands without worrying about inputs
        def display_timer():

            # this is normally really bad practice -- callback function should not be coupled to global object
            global user_pomodoro
            clear_terminal()

            # displays relevant info about timer, supplying interface for inputs without handling inputs

            # print(f"Ongoing threads: {enumerate()} ")

            timer = user_pomodoro.current_timer()
            rounds = user_pomodoro.rounds
            mins_secs = datetime.timedelta(seconds=(timer.duration - timer.elapsed))

            print(f"{"FOCUS!" if user_pomodoro.focus_mode else "REST."} { ( "{" + str(rounds) + "}" ) if rounds > 0 else "" }")
            print(f"{mins_secs}")

            # print(f"Timer alive: {timer.iterating_timer.is_alive()}")
            # print(f"Timer labelled as finished: {timer.finished}")
            # print(f"Timer labelled as paused: {timer.paused}")
            # print(f"Timer labelled as running: {timer.is_running()}")

            if user_pomodoro.current_timer().is_running():
                print("\nStop [S]")
            else:
                print("\nStart [S]  [R] Reset  [E] Exit")

        # each time the timer is iterated the elapsed is displayed to user
        events.pomo_channel.get_event("TIMER_ITERATED").register(lambda timer : display_timer())
        # if the timer is completed, it will update display one more time in order to switch modes
        events.pomo_channel.get_event("TIMER_COMPLETED").register(lambda timer : display_timer())

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
                    user_pomodoro.current_timer().reset_timer()
                    clear_terminal()
                    running = False

    user_pomodoro.empty_modified_bin()
    sys.exit()
