import time
from inspect import signature

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

        print(f"EVENT SYSTEM: {self.name} event triggered")

        # callback_number = len(self.callbacks)
        # print(f"Executing {callback_number} callback{"s" if callback_number > 1 or callback_number == 0 else ""}...")

        self.topic.log_event(event_name=self.name, timestamp=get_program_elapsed())

        for callback in self.callbacks:
            print(f"EVENT SYSTEM: Executing {callback.__name__} callback function:")

            # ensures that if the number of arguments passed into this method exceed the number of available parameters in the callback function, it will use the least amount available
            event_arg_count = len(event_args)
            callback_arg_count = len(signature(callback).parameters)

            final_event_args = event_args[:min(event_arg_count, callback_arg_count)] if callback_arg_count > 0 else None

            print(f"EVENT SYSTEM: original args {event_args} final args {final_event_args}")

            if final_event_args:
                callback(*final_event_args)
            else:
                callback()

class Topic():

    def __init__(self):
        self.events = {}
        self.events : dict[str, Observable]
        # stores record of events since program execution
        self.stream = Stream()

    # creates an event undet this Topic object and assigns it to self
    def create_event(self, event_name : str):
        event = Observable(event_name=event_name)
        self.add_event(event)

    # adds an event object to this topic
    def add_event(self, event : Observable):
        if type(event) != Observable:
            raise TypeError(f"Invalid type: {type(event)} for event object to be added")
        else:
            self.events[event.name] = event
            event.assign_topic(self)

    # returns a specific event based on its name
    def get_event(self, event_name : str) -> Observable:
        if event_name in self.events:
            return self.events[event_name]

    # returns multiple events based on given names, or if none given, all of the events in the topic
    def get_events(self, *event_names : str) -> list[Observable]:
        if len(event_names) == 0:
            return list(self.events.values())
        else:
            event_list = []
            for event_name in event_names:
                if event_name not in self.events:
                    raise NameError(f"Event name: {event_name} not found in events")
                else:
                    event_list.append(self.events[event_name])
            return event_list

    # WRAPPERS FOR STREAM OBJECT

    # logs event by adding to its stream
    def log_event(self, event_name : str, timestamp : float):
        self.stream.log_event(event_name = event_name, timestamp=timestamp)

    # returns the stream of events from its stream
    def get_stream(self):
        return self.stream.get_stream()

    def get_last(self, event_name : str):
        return self.stream.get_last(event_name)


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

# triggers when a state in a tomo fsm is changed -- allows other things to respond to its events
# passes tomo object -- its current state is the new state, and its callback can be set to something that the thing wants to do on occurence of that state in the future
tomo_topic.create_event("STATE_CHANGED")

# topic for events from pomos.py
pomo_topic = Topic()
pomo_topic.create_event("TIMER_COMPLETED")
pomo_topic.create_event("TIMER_ITERATED")
pomo_topic.create_event("ROUND_COMPLETED")
pomo_topic.create_event("TIMER_PAUSED")
pomo_topic.create_event("FOCUS_PERIOD_STARTED")