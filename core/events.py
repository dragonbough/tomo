import time

# start time used for timestamps
program_start_time = time.time()

# returns the current time in seconds since the program started
def get_program_elapsed():
    return time.time() - program_start_time

class Observable():

    def __init__(self, event_name : str):
        self.name = event_name
        # All of the functions that occur when this event is triggered
        self.callbacks : list[function] = []
        self.topic = None
        self.topic : "Topic"

    def assign_topic(self, topic : "Topic"):
        self.topic = topic

    def register(self, callback : callable):
        self.callbacks.append(callback)

    # triggers all of the registered functions
    def trigger(self, *event_args):

        print(f"\n{self.name} EVENT TRIGGERED")
        print("-" * len(self.name + "EVENT TRIGGERED") )

        # callback_number = len(self.callbacks)
        # print(f"Executing {callback_number} callback{"s" if callback_number > 1 or callback_number == 0 else ""}...")

        self.topic.log_event(event_name=self.name, timestamp=get_program_elapsed())

        for callback in self.callbacks:
            print(f"Executing {callback.__name__}")
            callback(*event_args)


class Topic():

    def __init__(self):
        self.events = {}
        self.events : dict[str : Observable]
        # stores record of events since program execution
        self.stream = Stream()

    # creates an event undet this Topic object and assigns it to self
    def create_event(self, event_name : str):
        event = Observable(event_name=event_name)
        self.events[event_name] = event
        event.assign_topic(self)

    # returns a specific event based on its name
    def get_event(self, event_name : str) -> Observable:
        if event_name in self.events:
            return self.events[event_name]

    # logs event by adding to its stream
    def log_event(self, event_name : str, timestamp : float):
        self.stream.log_event(event_name = event_name, timestamp=timestamp)


# logs the occurence of events since program started
class Stream():

    def __init__(self):
        # stream acts as queue kinda, storing tuple of timestamp and event name
        self.stream = []
        self.stream : list[tuple[float, str]]


    # logs the occurence of an event to its stream, using timestamp and event in tuple
    def log_event(self, event_name : str, timestamp : float):
        self.stream.append((timestamp, event_name))

    # returns the entire stream of events (from latest to last)
    def get_stream(self):
        return self.stream[::-1]

    # get last timstamp of event
    def get_last(self, event_name : str):
        for event_log in self.get_stream():
            if event_log[1] == event_name:
                return event_log


# topic for events from todos.py
todo_topic = Topic()
todo_topic.create_event("TODO_COMPLETED")

# topic for events from tomos.py
# these events may be passed into the finite state machine of the currently selected tomo
tomo_topic = Topic()
tomo_topic.create_event("XP_INCREASED")
tomo_topic.create_event("LVL_INCREASED")

# topic for events from pomos.py
pomo_topic = Topic()
pomo_topic.create_event("TIMER_COMPLETED")
pomo_topic.create_event("TIMER_ITERATED")
pomo_topic.create_event("ROUND_COMPLETED")
pomo_topic.create_event("TIMER_PAUSED")
pomo_topic.create_event("FOCUS_PERIOD_STARTED")