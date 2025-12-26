import data
import events
import math

#class defining a state in a state machine
class State():

    def __init__(self, name : str, callback : callable):
        self.name = name
        self.callback = callback
        # self.transitions = {transition : state}
        self.transitions = {}

    #executes the behaviour's function
    def execute(self, *args):
        # print(f"Executing State: {self.name}")
        # print(f"Executing State Transitions: {self.transitions}")
        # print(f"Execution:", end=" ")
        self.callback(*args)
        return

#class defining the finite state machine
class StateMachine():

    #defines the collection of states, the current state in the simulation of the FSM, the start state and the stop state
    def __init__(self):
        # self.states = {state_name : State}
        self.states = {}
        self.current_state = None
        self.start_state = None
        self.stop_state = None

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
            print(f"Start State: {state.name}")

    #adds transition between two states to FSM
    def add_transition(self, initial_state : State, transition_name : str, final_state : State):
        if transition_name not in initial_state.transitions:
            initial_state.transitions[transition_name] = final_state
            # print(f"State Transitions: {initial_state.transitions}")
            # print(f"Initial State: {initial_state.name}, Transition: {transition_name}, Final State: {final_state.name}")
        else:
            ValueError(f"Transition '{transition_name}' already exists for state")

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
            raise KeyError(f"Invalid state machine input ('{input})")
        else:
            self.current_state = self.current_state.transitions[input]

    #simulates a single step of the state machine
    def tick(self, input : str = None):
        self.current_state : State
        self.current_state.execute()
        if input:
            self.transition(input)


class BaseTomo():

    def __init__(self, tomo_id : int, base_name : str, levels : dict[int : dict[str : int]]):
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
            print(self.levels)
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
        self.fsm = StateMachine()
        self.updated = False

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

            print(f"{self.name}'s BOND LVL changed to {self.bond_level}")
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
            print(f"{self.name}'s HP increased by {hp}!")
        if xp:
            if type(xp) != int:
                raise TypeError("Invalid XP increase value")
            self.xp += xp
            print(f"{self.name}'s XP increased by {xp}!")
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
        func = lambda todo : self.current_tomo.increase_xp(todo.difficulty) if self.current_tomo else print("No tomo selected")
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
        return self.tomos.values()

    # returns a specific tomo based on its id
    def get_tomo(self, base_tomo_id : int):
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

        import networkx as nx
        import matplotlib.pyplot as plt
        import time

        def display_states(fsm : StateMachine):

            # converting the state machine object into an adjacency list for displaying as a network
            adjacency_list = {}
            for state_name in fsm.states:
                adjacency_list[state_name] = [state.name for state in fsm.get_state(state_name).transitions.values()]

            # print(f"Adjacency List: {adjacency_list}")

            edge_labels = {}

            # converting the transitions for each state into format for displaying edge labels in network
            for state_name in fsm.states:
                for transition in fsm.get_state(state_name).transitions:
                    final_state_name = fsm.get_state(state_name).transitions[transition].name
                    edge_labels[(state_name, final_state_name)] = transition

            # print(f"Edge Labels: {edge_labels}")

            #directional graph allowing parellel edges created using networkx and the adjacency list made
            fsm_graph = nx.MultiDiGraph(adjacency_list)

            # current state is green while everything else is red
            colours = ["limegreen" if fsm.current_state and state_name == fsm.current_state.name else "red" for state_name in fsm_graph]
            plt.clf()

            node_size = 1500

            # defines the layout of the network
            pos = nx.arf_layout(fsm_graph)

            # draws the network via matplotlib
            nx.draw_networkx(fsm_graph, node_size=node_size, node_color=colours, pos=pos, connectionstyle="arc3,rad=0.1")

            if edge_labels:
                nx.draw_networkx_edge_labels(G=fsm_graph, pos=pos, edge_labels=edge_labels, label_pos=0.3, connectionstyle="arc3,rad=0.1")

            plt.show(block=False)

        running = True

        user_tomos = UserTomos.get_user_tomos()
        tomo = user_tomos.get_tomo(1)
        fsm_input = None
        update = True
        selected_state = None

        while running == True:

            clear_terminal()
            #if graph updated then things should update
            if update:
                display_states(fsm=tomo.fsm)
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
                    state = State(name=state_name, callback=callback)
                    tomo.fsm.add_state(state=state)

                    update = True

                # simulating a tick
                elif (user_input == 2 or selected_user_input == 2) and tomo.fsm.states:

                    # if there isnt a current state in the FSM, start from the start state of the FSM
                    if not tomo.fsm.current_state:
                        tomo.fsm.current_state = tomo.fsm.start_state

                    if selected_user_input:
                        start_from_selected = input(f"Start from selected state ({selected_state.name})? [Y/N]: ").lower()
                        if start_from_selected == "y":
                            tomo.fsm.current_state = selected_state

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