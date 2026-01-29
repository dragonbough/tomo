from . import data, events
import xml.etree.ElementTree as eltree
from pathlib import Path

#class defining a state in a state machine
class State():

    def __init__(self, name : str, callback : callable = None):
        self.name = name
        self.callback : callable = None
        if callback:
            self.set_callback(callback)
        # self.transitions = {transition : state}
        self.transitions : dict[str, State] = {}

    #executes the behaviour's function
    def execute(self, *args):
        print(f"TOMO SYSTEM: FSM -- Executing State: {self.name}")
        if self.callback:
            self.callback(*args)
        return

    # sets this state's callback
    def set_callback(self, callback : callable):
        if not callable(callback):
            raise TypeError(f"Invalid callback set for state {self.name}")
        self.callback = callback

#class defining the finite state machine
class StateMachine():

    #defines the collection of states, the current state in the simulation of the FSM, the start state and the stop state
    def __init__(self, file_path : str = None):

        if file_path:
            self.load_from_xml(file_path)

        # self.states = {state_name : State}
        self.states : dict[str, State] = {}
        self.current_state : State = None
        self.start_state : State = None
        self.stop_state : State = None

    # returns all of the states in state machine
    def get_states(self):
        return self.states.values()

    #retrieves a state given its name
    def get_state(self, state_name : str) -> State:
        return self.states[state_name]

    #adds state to the finite state machine
    def add_state(self, state : State):
        self.states[state.name] = state
        if len(self.states) == 1:
            self.start_state = state
            print(f"TOMO SYSTEM: FSM -- Start State: {state.name}")

    #adds transition between two states to FSM
    def add_transition(self, initial_state : State, transition_name : str, final_state : State):
        if transition_name not in initial_state.transitions:
            initial_state.transitions[transition_name] = final_state
        else:
            ValueError(f"Transition '{transition_name}' already exists for state")

    # sets the callback for the specified state
    def set_callback(self, state : State, callback : callable):
        if state in self.states:
            state.set_callback(callback)
        else:
            raise ValueError("State not a member of state machine")

    #deletes states from state machine
    def delete_state(self, *states : State):
        to_delete = []
        for state_name in self.states:
            if self.get_state(state_name) in states:
                to_delete.append(state_name)
        for state_name in to_delete:
            self.states.pop(state_name)

    #transitions between the current state and the next state depending on given input
    def transition(self, input : str):
        if not self.current_state or input not in self.current_state.transitions:
            raise KeyError(f"Invalid state machine input: {input}")
        else:
            self.current_state = self.current_state.transitions[input]
            print(f"TOMO SYSTEM: FSM -- Switching state to {self.current_state.name}")

    #simulates a single step of the state machine
    def tick(self, input : str = None):
        if not self.current_state:
            if self.start_state:
                self.current_state = self.start_state
            else:
                raise Exception("No state to tick FSM with")
        # by default it will input the name of the state as an argument into its callback
        self.current_state.execute(self.current_state.name)
        if input:
            self.transition(input)

    # loads state machine configuration from xml file using eltree
    def load_from_xml(self, file_path : str):

        print(f"Loading {file_path} from XML to create state machine...")

        pass


class BaseTomo():

    def __init__(self, tomo_id : int, base_name : str, levels : dict[int : dict[str, int]]):
        self.tomo_id = tomo_id
        self.base_name = base_name
        # {level : {"hp" : 1, "required_xp" : 1, "sprite" : File}}
        self.levels = levels

    # returns the highest level for the given xp
    def check_for_level(self, xp : int):
        # must be done in order to work -- sorting self.levels by key (level)
        tomo_levels = dict(sorted(self.levels.items(), key=lambda item: item[0]))
        for level in tomo_levels:
            current_level = level
            if self.get_level_stats(level)["required_xp"] > xp:
                return current_level
        return current_level

    # returns dictionary of stats for given level
    def get_level_stats(self, level : int) -> dict[str]:
        return self.levels[level]

#tomo is an agent that relies on a finite state machine for its behaviours
class Tomo():

    def __init__(self, name : str, hp : int, xp : int, level : int, base_tomo : BaseTomo):
        self.base_tomo = base_tomo
        self.name = name
        self.hp = hp
        self.xp = xp
        self.bond_level = level
        self.updated = False

        self.fsm = StateMachine()

        # ties every event in the tomo topic as a parameter into the update_fsm_event
        for event in events.tomo_topic.get_events():
            if event.name != "STATE_CHANGED":
                event.register(self.check_for_fsm_input)

        # precreating the tomo fsm -- eventually i will just be able to pass in some formatted file (maybe DOT) and then it will just save the states + transitions
        self.fsm.add_state(State("idle"))
        self.fsm.add_state(State("playful"))
        self.fsm.add_transition(self.fsm.get_state("idle"), "high_xp_events", self.fsm.get_state("playful"))

    # checks for transition, and if so, triggered STATE_CHANGED event -- also handles incorrect inputs without crashing program
    def tick_fsm(self, input : str = None):
        if input:
            try:
                self.fsm.tick(input)
                events.tomo_topic.get_event("STATE_CHANGED").trigger(self)
            except KeyError:
                print(f"TOMO SYSTEM: FSM -- invalid input (\"{input}\") into state machine, executing regardless")
                self.fsm.current_state.execute(self.fsm.current_state.name)


    # checks for whether any requirements have been met to pass in a certain input into the finite state machine
    def check_for_fsm_input(self):

        fsm_input = None

        # if the number of xp increased events in this session goes above a certain amount, then tick the fsm with the input high_xp_events
        event_stream = events.tomo_topic.get_stream()
        xp_increase_count = 3
        for event_log in event_stream:
            if event_log[1] == "XP_INCREASED":
                xp_increase_count -= 1
            if xp_increase_count <= 0:
                fsm_input = "high_xp_events"

        self.tick_fsm(fsm_input)


    # checks for a level up / level down -- if its possible then level up / down
    # otherwise, returns False
    def check_for_level(self):
        new_level = self.base_tomo.check_for_level(self.xp)
        if new_level != self.bond_level:
            self.bond_level = new_level
            new_stats = self.get_base_stats()
            self.set_stat(hp=new_stats["hp"])

            # triggers level increased event
            events.tomo_topic.get_event("LVL_INCREASED").trigger(self)

            print(f"TOMO SYSTEM: {self.name}'s BOND LVL changed to {self.bond_level}")
        else:
            return False

    # returns the dict of base stats for the level passed in as argument
    # if no level passed in, uses current tomo level
    def get_base_stats(self, level : int = None):
        return self.base_tomo.get_level_stats(self.bond_level if not level else level)

    # increases xp/hp by certain amount
    def increase_stat(self, hp : int = None, xp : int = None):
        if hp:
            if type(hp) != int:
                raise TypeError("Invalid HP increase value")
            self.hp += hp
            print(f"TOMO SYSTEM: {self.name}'s HP increased by {hp}!")
        if xp:
            if type(xp) != int:
                raise TypeError("Invalid XP increase value")
            self.xp += xp
            print(f"TOMO SYSTEM: {self.name}'s XP increased by {xp}!")
            events.tomo_topic.get_event("XP_INCREASED").trigger(self)
            self.check_for_level()
        self.updated = True


    # sets xp/xp to a specific amount
    def set_stat(self, hp: int = None, xp : int = None):
        if hp:
            self.hp = hp
        if xp:
            self.xp = xp
        self.updated = True

    # sets the tomo's name to a new name
    def rename(self, name : str):
        if name:
            self.name = name
        self.updated = True

# collection of Tomos
class UserTomos():

    # factory method to retrieve all of the tomos that belong to user in the DB
    @staticmethod
    def get_user_tomos():
        tomos = []
        base_tomos = {}

        user_tomo_data, base_tomo_data = data.retrieve_tomo_data()

        # creates base tomos
        for base_tomo_id in base_tomo_data:
            base_name = base_tomo_data[base_tomo_id]["basename"]
            levels = base_tomo_data[base_tomo_id]["levels"]
            base_tomo = BaseTomo(tomo_id=base_tomo_id, base_name=base_name, levels=levels)
            # print("BaseTomo retrieved!")
            # print(f"BaseTomo Name: {base_tomo.base_name}:")
            # print(f"{base_tomo.base_name} ID: {base_tomo.tomo_id}")
            # print(f"{base_tomo.base_name} Levels: {base_tomo.levels}")
            base_tomos[base_tomo.tomo_id] = base_tomo

        print("")

        for tomo_datum in user_tomo_data:

            # creating the user tomo
            name = tomo_datum["name"]
            tomo_id = int(tomo_datum["tomoid"])
            hp = int(tomo_datum["hp"])
            xp = int(tomo_datum["xp"])
            bond_level = int(tomo_datum["bondlevel"])
            user_tomo = Tomo(name=name, hp=hp, xp=xp, level=bond_level, base_tomo=base_tomos[tomo_id])

            # print("UserTomo retrieved!")
            # print(f"UserTomo Name: {user_tomo.name}:")
            # print(f"{user_tomo.name} HP: {user_tomo.hp}")
            # print(f"{user_tomo.name} XP: {user_tomo.xp}")
            # print(f"{user_tomo.name} Bond Level: {user_tomo.bond_level}")
            # print(f"{user_tomo.name}'s Base Tomo Name: {user_tomo.base_tomo.base_name}")

            tomos.append(user_tomo)

        return UserTomos(tomos=tomos)

    # takes a list of tomos as argument and saves these in a dictionary
    # in the dictionary the tomo_id is used as the key for the tomo object
    # also stores a current_tomo to keep track of the tomo the user has equipped
    def __init__(self, tomos : list[Tomo]):
        self.tomos = {}
        for tomo in tomos:
            self.tomos[tomo.base_tomo.tomo_id] = tomo
        self.current_tomo = None

        # registers xp increase of selected tomo to the todo completion event
        func = lambda todo : self.current_tomo.increase_stat(xp=todo.difficulty) if self.current_tomo else print("No tomo selected")
        events.todo_topic.get_event("TODO_COMPLETED").register(func)

    # the events that occur when a todo is completed
    # (xp increase, etc)
    def todo_completion(self, todo):
        if self.current_tomo:

            # calculate number of rounds completed since start of timer, using event stream
            completed_rounds = 0
            event_stream = events.todo_topic.stream.get_stream()
            for event_log in event_stream:
                event_name = event_log[1]
                if event_name == "ROUND_COMPLETED":
                    completed_rounds += 1
                elif event_name == "FOCUS_PERIOD_STARTED":
                    break

            # calculate the xp increase using exponential function made in desmos linking xp to difficulty of task and number of rounds:
            # https://www.desmos.com/calculator/cs1y5k6hg3
            if completed_rounds > 0:
                # variable d represents todo difficulty
                d = todo.difficulty
                # variable x represenents number of completed rounds
                x = completed_rounds

                xp_increase = 10 + 10 * ( (d+1) ** (x * (d+1 / 12)) )
                xp_increase = round(xp_increase)

            else:
                xp_increase = 5

            self.current_tomo.increase_stat(xp=xp_increase)
        else:
            print("No tomo selected")

    # takes the tomos marked as updated, unpacks them,
    # and passes them into the data layer to save changes in DB
    def update_tomos(self):
        updated_tomos = [tomo for tomo in self.get_tomos() if tomo.updated]
        data.modify_tomo_data(*self.unpack_tomos(updated_tomos))

    # turns tomo object data into a dictionary for each of the tomos that are passed in
    def unpack_tomos(self, tomos : list[Tomo]):
        unpacked_tomos = []
        for tomo in tomos:
            tomo_datum = {}
            tomo_datum["name"] = tomo.name
            tomo_datum["hp"] = tomo.hp
            tomo_datum["xp"] = tomo.xp
            tomo_datum["bondlevel"] = tomo.bond_level
            tomo_datum["id"] = tomo.base_tomo.tomo_id
            unpacked_tomos.append(tomo_datum)
        return unpacked_tomos

    # returns all of the user's tomos
    def get_tomos(self) -> list[Tomo]:
        return list(self.tomos.values())

    # returns a specific tomo based on its id
    def get_tomo(self, base_tomo_id : int) -> Tomo:
        return self.tomos[base_tomo_id]

    # selects a tomo in the users tomos as the "current"/"main" one
    def select_tomo(self, tomo : Tomo):
        if tomo in self.get_tomos():
            self.current_tomo = tomo
        else:
            raise KeyError(f"Tomo {tomo.name} not in UserTomos")

    # deselects tomo
    def deselect_tomo(self):
        self.current_tomo = None


if __name__ == "__main__":

    import sys
    import os

    def clear_terminal():
        # For Windows

        if os.name == 'nt':
            _ = os.system('cls')
        # For macOS and Linux
        else:
            _ = os.system('clear')

    ### TOMO STATS TESTING ###
    if len(sys.argv) > 1 and sys.argv[1] == "stats":

        # displays CLI tomo stats
        def display_tomo_stats(tomo : Tomo):
            print(f"{tomo.name}'s Stats:")

            print(f"BOND LVL: {tomo.bond_level} ({tomo.xp} XP)")

            base_stats = tomo.get_base_stats()

            base_hp = base_stats["hp"]

            max_bar_length = 10
            bar_length = int(tomo.hp / base_hp * max_bar_length)
            empty_bar_length = max_bar_length - bar_length
            print(f"HP: |{bar_length * "❚" + (empty_bar_length * " ")}| {tomo.hp}/{base_hp}")

        running = True

        user_tomos = UserTomos.get_user_tomos()
        user_tomos.current_tomo = None

        # print("\nData retrieval successful! :D")
        while running:

            tomo_id = ""

            clear_terminal()

            for tomo in user_tomos.get_tomos():
                print(f"[{tomo.base_tomo.tomo_id}] {tomo.name}")

            tomo_id = input("Select Tomo ([E] to exit): ")

            if tomo_id.isdecimal() and int(tomo_id) in user_tomos.tomos:

                clear_terminal()
                tomo = user_tomos.get_tomo(int(tomo_id))
                user_tomos.select_tomo(tomo)

            elif tomo_id.lower() == "e":
                break

            while user_tomos.current_tomo:

                current_tomo = user_tomos.current_tomo
                current_tomo : Tomo

                clear_terminal()
                display_tomo_stats(tomo=current_tomo)

                choice = int(input("[1] Rename  [2] Increase XP  [3] Exit\n"))

                if choice == 1:
                    current_tomo.rename(input("Enter name: "))
                elif choice == 2:
                    current_tomo.increase_stat(xp=int(input("How much XP?")))
                elif choice == 3:
                    user_tomos.deselect_tomo()

        user_tomos.update_tomos()


    ### TOMO FSM TESTING ###
    elif len(sys.argv) > 1 and sys.argv[1] == "fsm":

        from networkx.classes import multidigraph
        from networkx.drawing import draw_networkx, draw_networkx_edge_labels
        from networkx.drawing.layout import arf_layout
        from networkx.readwrite import write_graphml_lxml, read_graphml
        from networkx import get_edge_attributes
        from pathlib import Path
        import matplotlib.pyplot as plt
        import time

        base_dir = Path(__file__).resolve().parent
        folder_path = base_dir / "fsm_saves"

        def create_fsm_graph(fsm : StateMachine):

            #directional graph allowing parellel edges created using networkx
            graph = multidigraph.MultiDiGraph()

            for state_name in fsm.states:
                state = fsm.states[state_name]
                if state.transitions:
                    for transition in state.transitions:
                        connecting_state = state.transitions[transition]
                        graph.add_edge(u_for_edge=state.name, v_for_edge=connecting_state.name, name=transition)
                else:
                    graph.add_node(state_name)

            return graph


        def display_states(fsm_graph : multidigraph.MultiDiGraph, prev_pos : dict):

            plt.clf()

            node_size = 1500

            # defines the layout of the network
            pos = arf_layout(fsm_graph, prev_pos)

            # draws the network via matplotlib
            draw_networkx(fsm_graph, node_size=node_size, pos=pos, connectionstyle="arc3,rad=0.1")

            edge_labels = get_edge_attributes(fsm_graph, "name")
            if edge_labels:
                draw_networkx_edge_labels(G=fsm_graph, pos=pos, edge_labels=edge_labels, label_pos=0.3, connectionstyle="arc3,rad=0.1")

            return pos

        # saves graph to a filepath specified by user as an XML file -- useful for saving finite state machines created for testing
        def save_graph(graph : multidigraph.MultiDiGraph, file_name : str):

            file_path = folder_path / (file_name + ".fsm")

            write_graphml_lxml(G=graph, path=str(file_path))


        running = True

        user_tomos = UserTomos.get_user_tomos()
        tomo = user_tomos.get_tomo(1)
        fsm_input = None
        update = True
        selected_state = None

        # updates automatically
        plt.ion()
        # maintains the positions of each node in graph
        pos = None

        # creates dict of files within the fsm_saves folder
        files = {index + 1 : str(file.relative_to(folder_path)) for index, file in enumerate(folder_path.iterdir())}
        # if there are any files then ask to load one and give the user options to select
        if files:
            load_graph_choice = input("Load Graph? [Y/N]: ").lower()
            if load_graph_choice == "y":
                for index in files:
                    print(f"[{index}] {files[index]}")
                choice = -1
                while not(1 <= choice <= len(files)):
                    choice = int(input("Select a file: "))
                tomo.fsm.load_from_xml(files[choice])

        while running == True:

            clear_terminal()
            #if graph updated then things should update
            if update:
                pos = display_states(create_fsm_graph(tomo.fsm), pos)
                update = False

            user_input = ""
            selected_user_input = ""

            print(f"Tomo: {tomo.name}")
            print(f"Selected State: {selected_state.name if selected_state else None}")
            print(f"Current State (Tick Sim): {tomo.fsm.current_state.name if tomo.fsm.current_state else None}")

            if not selected_state:
                user_input = input("[1] Add State  [2] Simulate Tick  [3] Exit\n").lower()
            else:
                selected_user_input = input("[1] Transition to State  [2] Simulate Tick  [3] Deselect  [4] Exit\n").lower()

            if user_input.isdecimal() or selected_user_input.isdecimal():
                if user_input:
                    user_input = int(user_input)
                if selected_user_input:
                    selected_user_input = int(selected_user_input)

                # adding states
                if user_input == 1:
                    state_name = input("State Name: ")
                    action = input("What should the behaviour say?: ")
                    # callback in lambda form MUST be written like this -- writing lambda : print(action) does not store action locally
                    # rather, it just points to the action variable which changes on every loop
                    callback = lambda x=action : print(x)
                    state = State(state_name, callback)
                    tomo.fsm.add_state(state)

                    update = True

                # simulating a tick
                elif (user_input == 2 or selected_user_input == 2) and tomo.fsm.states:

                    add_input = input("Input? [Y/N]: ").lower()
                    if add_input == "y":
                        fsm_input = input("Input: ")
                    try:
                        tomo.fsm.tick(fsm_input)
                    except KeyError:
                        print("Invalid FSM input")
                    else:
                        time.sleep(2)

                    fsm_input = None
                    update = True

                elif user_input == 3 or selected_user_input == 4:
                    save_choice = input("Save? [Y/N]: ").lower()
                    if save_choice == "y":
                        file_name = input("What would you like to call the file?: ").lower()
                        save_graph(create_fsm_graph(tomo.fsm), file_name)
                    running = False

                # transitioning to another state
                elif selected_user_input == 1:

                    # lists all of the other (non-selected and non-connected) states with an index for the user to select
                    other_state_names = [state.name for state in tomo.fsm.get_states() if state != selected_state and state not in selected_state.transitions.values()]

                    for i in range(len(other_state_names)):
                        print(f"[{i+1}] {other_state_names[i]}")

                    transition_index = int(input("Enter index: "))

                    # creates transition between the current state and the user
                    if 1 <= transition_index <= len(other_state_names):
                        connecting_state = tomo.fsm.get_state(other_state_names[transition_index - 1])
                        transition_name = input("State Transition: ")
                        tomo.fsm.add_transition(selected_state, transition_name, connecting_state)
                        update = True

                # deselects the currently selected state
                elif selected_user_input == 3:
                    selected_state = None


            elif user_input in tomo.fsm.states:
                selected_state = tomo.fsm.get_state(user_input)

            elif selected_user_input in tomo.fsm.states:
                selected_state = tomo.fsm.get_state(selected_user_input)