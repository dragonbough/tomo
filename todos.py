import data
from datetime import datetime
import sys
import os
from typing import Literal
import events

class Todo():

    def __init__(self, name : str, todo_id : int = None, difficulty : int = None, parent = None, completed : bool = False, points : int = 0, time_created : int = None, time_completed : int = None):
        self.name = name
        self.todo_id = todo_id
        self.difficulty = difficulty
        self.parent : Todo
        self.parent = parent
        if self.parent:
            self.parent.adopt(self)
        self.completed = completed
        self.children : list[Todo]
        self.children = []
        self.points = points
        if not time_created:
            self.time_created = datetime.now().timestamp()
        else:
            self.time_created = time_created
        self.time_completed = time_completed
        self.deleted = False
        self.local = False

    #the todo's previous parent disowns it and this new parent adopts it
    def adopt(self, todo : "Todo"):
        if todo.parent:
            todo.parent.disown(todo)
        self.children.append(todo)
        todo.parent = self

    #todo gets rid of parent and parent gets rid of todo
    def disown(self, todo : "Todo"):
        if todo in self.children:
            self.children.remove(todo)
        todo.parent = None

class TodoList():

    #factory method for retrieving a todo-list without coupling to an object
    @staticmethod
    def get_user_todos():
        todos = []
        foster_dict = {}

        for todo_datum in data.retrieve_todo_data():
            todo_id = int(todo_datum["id"])
            name = todo_datum["name"]
            difficulty = int(todo_datum["difficulty"])
            completed = True if todo_datum["completed"] else False
            time_created = int(todo_datum["timecreated"])
            time_completed = todo_datum["timecompleted"]

            todo = Todo(name=name, todo_id=todo_id, difficulty=difficulty, completed=completed, time_created=time_created, time_completed=time_completed)

            #adds itself under parent id
            #so it can be adopted later
            parent_id = todo_datum["parentid"]
            if parent_id in foster_dict:
                foster_dict[parent_id].append(todo)
            else:
                foster_dict[parent_id] = [todo]

            todos.append(todo)

        for todo in todos:

            #adopts any children in foster matching its id
            if todo.todo_id in foster_dict:
                for child in foster_dict[todo.todo_id]:
                    todo.adopt(child)

        return TodoList(todos)


    def __init__(self, todos : list[Todo] = None):
        self.todos = {}
        self.add_todos(*todos)
        self.bin = {"modify" : [], "delete" : []}


    #retrieves a todo from the todo list based on either todo_id or todo_name -- better way than accessing attributes directly
    def get_todo(self, *todo_ids : int | str) -> Todo:
        todos = []

        if todo_ids:

            for todo_id in todo_ids:

                if todo_id in self.todos:
                    todos.append(self.todos[todo_id])
                else:
                    raise NameError(f"To-do ID {todo_id} not in To-do list")

        return todos[0] if len(todos) == 1 else todos

    def get_todos(self) -> list[Todo]:
        return list(self.todos.values())

    def get_roots(self):
        return [todo for todo in self.get_todos() if not todo.parent]

    #initialises dfs algo with root nodes and retrieves sorted list of todos -- sorts each tree and appends to each other
    #if returning depth information is enabled, a dict of visited nodes and the todo depths will be sent
    def sort_todos(self, return_depths = False) -> list[Todo]:
        root_nodes = self.get_roots()
        sorted_todos = {"visited" : [], "depths" : {}} if return_depths else []
        for root_node in root_nodes:
            sorted_tree = self.depth_first_search(node=root_node, visited=[], depth=0, node_depths={}, return_depths=return_depths)
            if sorted_tree:

                if return_depths:
                    sorted_todos["visited"].extend(sorted_tree["visited"])
                    sorted_todos["depths"].update(sorted_tree["depths"])

                else:
                    sorted_todos.extend(sorted_tree)

        return sorted_todos

    #recursive DFS algorithm that ignores deleted nodes and optionally returns depth information
    def depth_first_search(self, node : Todo, visited : list, depth : int, node_depths : dict, return_depths = False) -> list[Todo]:
        if node.deleted:
            return

        #if returning depth information is enabled then the dict is either initialised or updated with depth data
        if return_depths:
            if visited == []:
                node_depths = {node.todo_id : 0}
            else:
                node_depths[node.todo_id] = depth

        visited.append(node)

        if return_depths and node.children:
            depth += 1

        for child in node.children:
            if child not in visited:
                self.depth_first_search(child, visited, depth, node_depths, return_depths)

        if node in visited:
            return visited if not return_depths else {"visited" : visited, "depths" : node_depths}

    #adds a todo to the todolist
    def add_todos(self, *todos : Todo):
        for todo in todos:
            self.todos.update({todo.todo_id : todo})

    #adds todo to a bin to prepare for deletion or for updating depending on inputted type
    def bin_todo(self, todo : Todo, bin_type : Literal["modify", "delete"]):
        if bin_type != "modify" and bin_type != "delete":
            raise NameError("Invalid bin type.")
        if bin_type == "delete":
            todo.deleted = True
            for child in todo.children:
                self.bin_todo(child, "delete")

        if todo.todo_id not in self.bin[bin_type]:
            self.bin[bin_type].append(todo.todo_id)

    #creates a todo, adding it to todolist and binning it for modifying
    def create_todo(self, name : str, parent : Todo, difficulty : int = 0):
        todo = Todo(name=name, difficulty=difficulty, parent=parent)
        #give the todo a temporary id before replacing when saved to DB
        #setting the local attribute to True to make sure DB knows it doesnt exist in DB yet
        todo.todo_id = max(self.todos) + 1 if self.todos else 1
        todo.local = True
        self.add_todos(todo)
        self.bin_todo(todo, "modify")

    #completes todo recursively
    def complete_todo(self, todo : Todo, completion : bool = None):
        if completion == None:
            completion = not todo.completed
        todo.completed = completion

        # triggers event declaring that a todo was completed, passing in the todo as argument
        if todo.completed == True:
            events.todo_topic.get_event("TODO_COMPLETED").trigger(todo)

        for child in todo.children:
            self.complete_todo(child, completion)
        if todo.parent:
            self.check_if_completed(todo.parent)

    #todo checks for completion based on whether all the children are completed or not
    def check_if_completed(self, todo : Todo):
        completed = not([child for child in todo.children if child.completed == False])
        todo.completed = completed
        # ensures that parents of parents are also updated in response to completion if needed
        if todo.parent:
            self.check_if_completed(todo.parent)

    #formats all Todo data into a dictionary for DB
    def unpack_todos(self, *todos : Todo):
        todo_data = []
        for todo in todos:
            todo : Todo
            todo_datum = {}
            todo_datum["id"] = todo.todo_id
            todo_datum["name"] = todo.name
            todo_datum["difficulty"] = todo.difficulty
            todo_datum["completed"] = 1 if todo.completed else 0
            todo_datum["points"] = todo.points
            todo_datum["timecreated"] = todo.time_created
            todo_datum["timecompleted"] = todo.time_completed
            todo_datum["parentid"] = todo.parent.todo_id if todo.parent else None
            todo_datum["local"] = todo.local

            todo_data.append(todo_datum)

        return todo_data

    #sends unpacked todo_data in modify bin to be updated for DB
    def empty_modified(self):
        binned_todos = []
        for todo_id in self.bin["modify"]:
            binned_todos.append(self.get_todo(todo_id))
        data.modify_todo_data(*self.unpack_todos(*binned_todos))

    #deletes the todos in the delete bin
    def empty_deleted(self):

        #removes them from the modify bin, to prevent them from being saved to later
        for todo_id in self.bin["delete"]:
            if todo_id in self.bin["modify"]:
                self.bin["modify"].remove(todo_id)

        data.delete_todo_data(*self.bin["delete"])

    #sync todos with DB
    def empty_bin(self):
        self.empty_deleted()
        self.empty_modified()


#cli interface to visualise todos and interact with them -- only deployed if called in terminal
if __name__ == "__main__":

    def display_todos(todo_list : TodoList, selected = None):

        start_bold = "\033[1m"
        start_green = "\033[92m"
        end_format = "\033[0m"

        sorted_todos = todo_list.sort_todos(return_depths=True)

        points = ["•", "◦", "▪"]

        for todo in sorted_todos["visited"]:

            indent = sorted_todos["depths"][todo.todo_id]
            point = points[indent % len(points)]

            padding = " " * ( len(str(max(todo_list.todos))) - len(str(todo.todo_id)) )

            print(f"""{start_bold if selected == todo else ""}[{todo.todo_id}] {start_green if todo.completed else ""}{padding}{"   " * indent}{point} {todo.name} {"X" if todo.completed else ""} {end_format if selected == todo else ""}{end_format if todo.completed else ""}""")


    def clear_screen():
        # For Windows
        if os.name == 'nt':
            _ = os.system('cls')
        # For macOS and Linux
        else:
            _ = os.system('clear')


    user_todo_list = TodoList.get_user_todos()
    running = True
    hud = False
    selected_todo = None


    while running:

        clear_screen()
        display_todos(user_todo_list, selected_todo)

        if not selected_todo:
            user_input = input("\n[A] Create To-do  [X] Exit\n").lower()
            if user_input == "a":
                todo_name = input("To-do Name: ")
                todo_difficulty = int(input("To-do Difficulty: [1] Trivial  [2] Easy  [3] Normal  [4] Hard\n"))
                user_todo_list.create_todo(name=todo_name, parent=None, difficulty=todo_difficulty)

        if selected_todo:
            clear_screen()
            display_todos(user_todo_list, selected_todo)
            user_input = input(f"\n[M] Mark Completed  [A] Create Sub-Todo  [S] Edit  [D] Delete  [F] View  [X] Exit\n")

            if not user_input.isdecimal():

                user_input = user_input.lower()

                if user_input == "m":
                    user_todo_list.complete_todo(selected_todo)
                    user_todo_list.bin_todo(selected_todo, "modify")

                elif user_input == "a":
                    todo_name = input("To-do Name: ")
                    todo_difficulty = -1
                    while not(1 <= todo_difficulty <= 4):
                        todo_difficulty = int(input("To-do Difficulty: [1] Trivial  [2] Easy  [3] Normal  [4] Hard\n"))
                    user_todo_list.create_todo(name=todo_name, parent=selected_todo, difficulty=todo_difficulty)


                if user_input == "s":
                    edit_option = input(f"[A] Name  [S] Difficulty [D] Parent\n").lower()

                    if edit_option == "a":
                        selected_todo.name = input("\nEdit To-do Name: ")

                    elif edit_option == "s":
                        todo_difficulty = -1
                        while not(1 <= todo_difficulty <= 4):
                            todo_difficulty = int(input("Edit To-do Difficulty: [1] Trivial  [2] Easy  [3] Normal  [4] Hard\n"))
                        selected_todo.difficulty = todo_difficulty

                    elif edit_option == "d":
                        clear_screen()
                        display_todos(user_todo_list, selected_todo)
                        parent_id = input("\nEnter ID of New Parent or [ENTER] to Disown: ")

                        old_parent = None

                        if not parent_id:

                            if selected_todo.parent:
                                old_parent = selected_todo.parent
                                selected_todo.parent.disown(selected_todo)

                        else:

                            parent_id = int(parent_id)

                            if parent_id in user_todo_list.todos and parent_id != selected_todo.todo_id:
                                parent_todo = user_todo_list.get_todo(parent_id)
                                parent_todo.adopt(selected_todo)

                        user_todo_list.bin_todo(selected_todo, "modify")
                        if old_parent:
                            user_todo_list.bin_todo(old_parent, "modify")
                        if selected_todo.parent:
                            user_todo_list.bin_todo(selected_todo.parent, "modify")


                elif user_input == "d":
                    choice = input("Are you sure? [Y][N]\n").lower()
                    if choice.lower() == "y":
                        user_todo_list.bin_todo(selected_todo, "delete")
                        selected_todo = None
                    else:
                        continue

                elif user_input == "f":

                    choice = None
                    time_created = datetime.fromtimestamp(selected_todo.time_created).strftime("%Y/%m/%d, %H:%M:%S")
                    time_completed = datetime.fromtimestamp(selected_todo.time_completed).strftime("%Y/%m/%d, %H:%M:%S") if selected_todo.time_completed else None
                    difficulties = ["Trivial", "Easy", "Hard", "Very Hard"]

                    while choice != "f":

                        clear_screen()
                        print(f"\033[1m{selected_todo.name}\033[0m")
                        print(f"Time Created: {time_created}  {f"Time Completed: {time_completed} " if time_completed else ""}Difficulty: {selected_todo.difficulty} ({difficulties[selected_todo.difficulty - 1]})\n")
                        choice = input("[F] Close\n").lower()

        if user_input == "x":
                user_todo_list.empty_bin()
                sys.exit()

        if user_input.isdecimal():
                if int(user_input) in user_todo_list.todos:

                    if selected_todo and int(user_input) == selected_todo.todo_id:
                        selected_todo = None
                    else:
                        selected_todo = user_todo_list.get_todo(int(user_input))
