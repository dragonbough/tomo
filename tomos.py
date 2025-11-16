#class defining a state in a state machine
class State():

    def __init__(self, name : str, callback : callable):
        self.name = name
        self.callback = callback
        # self.transitions = {transition : state}
        self.transitions = {}

    #executes the behaviour's function
    def execute(self, *args):
        self.callback(*args)

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
    def get_state(self, state_name : str):
        return self.states[state_name]

    #adds state to the finite state machine
    def add_state(self, state : State):
        self.states[state.name] = state
        if len(self.states) == 1:
            self.start_state = state

    #adds transition between two states to FSM
    def add_transition(self, initial_state : State, transition_name : str, final_state : State):
        if transition_name not in initial_state.transitions:
            initial_state.transitions[transition_name] = final_state
            print(f"State Transitions: {initial_state.transitions}")
            print(f"Initial State: {initial_state.name}, Transition: {transition_name}, Final State: {final_state.name}")
        else:
            ValueError(f"Transition '{transition_name}' already exists for state")

    #deletes states from state machine
    def delete_state(self, *states : State):
        to_delete = []
        for state_name in self.states:
            if self.states[state_name] in states:
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
        self.current_state.execute()
        if input:
            self.transition(input)

#tomo is an agent that relies on a finite state machine for its behaviours
class Tomo():

    def __init__(self, name : str, hp : int, xp : int):
        self.name = name
        self.hp = hp
        self.xp = xp
        self.fsm = StateMachine()


if __name__ == "__main__":

    import networkx as nx
    import matplotlib.pyplot as plt
    import os

    def clear_terminal():
        # For Windows
        if os.name == 'nt':
            _ = os.system('cls')
        # For macOS and Linux
        else:
            _ = os.system('clear')

    def display_states(fsm : StateMachine):

        # converting the state machine object into an adjacency list for displaying as a network
        adjacency_list = {}
        for state_name in fsm.states:
            # print(state_name)
            adjacency_list[state_name] = [state.name for state in fsm.states[state_name].transitions.values()]

        # print(f"Adjacency List: {adjacency_list}")

        edge_labels = {}

        # converting the transitions for each state into format for displaying edge labels in network
        for state_name in fsm.states:
            for transition in fsm.states[state_name].transitions:
                final_state_name = fsm.states[state_name].transitions[transition].name
                edge_labels[(state_name, final_state_name)] = transition

        # print(f"Edge Labels: {edge_labels}")

        #directional graph allowing parellel edges created using networkx and the adjacency list made
        fsm_graph = nx.MultiDiGraph(adjacency_list)

        # current state is green while everything else is red
        colours = ["red" if fsm.current_state and state_name != fsm.current_state.name else "limegreen" for state_name in fsm_graph]
        plt.clf()

        node_size = 1500
        ring_node_size = 500 + node_size

        # defines the layout of the network
        pos = nx.arf_layout(fsm_graph)

        # display the start state with a ring around it (drawing a larger node below)
        if fsm.start_state:
            nx.draw_networkx_nodes(fsm_graph, node_size=ring_node_size, pos=pos, nodelist=[fsm.start_state.name])

        # draws the network via matplotlib
        nx.draw_networkx(fsm_graph, node_size=node_size, node_color=colours, pos=pos, connectionstyle="arc3,rad=0.1")

        if edge_labels:
            nx.draw_networkx_edge_labels(G=fsm_graph, pos=pos, edge_labels=edge_labels, label_pos=0.3, connectionstyle="arc3,rad=0.1")

        plt.show(block=False)

    running = True

    tomo = Tomo("test", 100, 100)
    # idle_behaviour = State("idle", lambda : print("Tomo is idle"))
    # tomo.fsm.add_state("idle", idle_behaviour)
    fsm_input = None
    update = True
    selected_state = None

    while running == True:

        clear_terminal()
        #if graph updated then things should update
        if update:
            display_states(fsm=tomo.fsm)
            update = False

        print(f"Selected State: {selected_state.name if selected_state else None}")
        if not selected_state:
            user_input = input("[1] Add State  [3] Simulate Tick  [4] Exit\n").lower()
        else:
            user_input = input("[1] Add State  [2] Transition to State  [3] Simulate Tick  [4] Exit\n").lower()

        if user_input.isdecimal():
            user_input = int(user_input)

            if user_input == 1:
                state_name = input("State Name: ")
                action = input("What should the behaviour say?: ")
                state = State(name=state_name, callback=lambda : print(action))
                tomo.fsm.add_state(state=state)
                # transition_name = input("State Transition Name: ")
                # tomo.fsm.add_transition(initial_state=tomo.fsm.current_state, transition_name=transition_name, final_state=state)
                update = True

            elif user_input == 2 and selected_state:

                # lists all of the other (non-selected and non-connected) states with an index for the user to select
                other_state_names = [state.name for state in tomo.fsm.get_states() if state != selected_state and state not in selected_state.transitions.values()]

                for i in range(len(other_state_names)):
                    print(f"[{i+1}] {other_state_names[i]}")

                transition_index = int(input("Enter index: "))

                # creates transition between the current state and the user
                if 1 <= transition_index <= len(tomo.fsm.states):
                    connecting_state = tomo.fsm.states[other_state_names[transition_index - 1]]
                    transition_name = input("State Transition: ")
                    tomo.fsm.add_transition(selected_state, transition_name, connecting_state)
                update = True

            elif user_input == 3:
                add_input = input("Input? [Y/N]: ").lower()
                if add_input == "y":
                    fsm_input = input("Input: ")
                try:
                    tomo.fsm.tick(fsm_input)
                except KeyError:
                    print("Invalid FSM input")
                fsm_input = None
                update = True

            elif user_input == 4:
                running = False

        elif user_input in tomo.fsm.states:
            selected_state = tomo.fsm.get_state(user_input)
            tomo.fsm.current_state = selected_state