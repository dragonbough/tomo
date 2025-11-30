import time

class Observable():

    def __init__(self, event_name : str):
        self.name = event_name
        # All of the functions that occur when this event is triggered
        self.callbacks = []

    def register(self, callback : callable):
        self.callbacks.append(callback)

    # triggers all of the registered functions
    def trigger(self, *event_args):
        # callback_number = len(self.callbacks)
        # print(f"Executing {callback_number} callback{"s" if callback_number > 1 or callback_number == 0 else ""}...")
        for callback in self.callbacks:
            callback(*event_args)
        # time.sleep(1)

class Channel():

    def __init__(self):
        self.channel = {}
        self.channel : dict[str : Observable]

    def create_event(self, event_name : str):
        event = Observable(event_name=event_name)
        self.channel[event_name] = event

    def get_event(self, event_name : str) -> Observable:
        if event_name in self.channel:
            return self.channel[event_name]

# channel for events from todos.py
todo_channel = Channel()
todo_channel.create_event("TODO_COMPLETED")

# channel for events from tomos.py
tomo_channel = Channel()

# channel for events from pomos.py
pomo_channel = Channel()
pomo_channel.create_event("TIMER_COMPLETED")
pomo_channel.create_event("TIMER_ITERATED")