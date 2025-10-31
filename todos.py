import data
import datetime
import sys
import os
from typing import Literal

class Todo():

    def __init__(self, name : str, todo_id : int = None, difficulty : int = None, parent = None, completed : bool = False, points : int = 0, time_completed : int = None):
        self.name = name
        self.todo_id = todo_id
        self.difficulty = difficulty
        self.parent : Todo
        self.parent = parent
        self.completed = completed
        self.children = []
        self.points = points
        self.time_created = datetime.datetime.now().timestamp()
        self.time_completed = time_completed
        self.deleted = False

    def adopt(self, todo : "Todo"):
        self.children.append(todo)
        todo.parent = self


class TodoList():

    #factory method for retrieving a todo-list without coupling to an object
    @staticmethod
    def get_user_todos():
        todos = []
        foster_dict = {}

        for todo_data in data.retrieve_todo_data():
            todo_id = int(todo_data["id"])
            name = todo_data["name"]
            difficulty = int(todo_data["difficulty"])

            todo = Todo(name, todo_id, difficulty)

            #adds itself under parent id
            #so it can be adopted later
            parent_id = todo_data["parentid"]
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

        # elif todo_names:
        #     todo_name_dict = {todo.name : todo for todo in self.todos.values()}
        #     for todo_name in todo_names:
        #         if todo_name in todo_name_dict:
        #             todos.append(todo_name_dict[todo_name])
        #         else:
        #             raise NameError(f"To-do named {todo_name} not in To-do list")

        return todos[0] if len(todos) == 1 else todos

    def get_roots(self):
        return [todo for todo in self.todos.values() if not todo.parent]

    #initialises dfs algo with root nodes and retrieves sorted list of todos -- sorts each tree and appends to each other
    #if returning depth information is enabled, a dict of visited nodes and the todo ids to their depths will be sent
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
        self.bin[bin_type].append(todo.todo_id)

    #creates a todo, adding it to todolist and binning it for modifying
    def create_todo(self, name : str, parent : Todo, difficulty : int = 0):
        todo = Todo(name=name, difficulty=difficulty, parent=parent)
        #give the todo a temporary id before replacing when saved to DB
        todo.todo_id = "untitled " + str(max([todo_id for todo_id in self.todos if type(todo_id) == int]) + 1)
        self.add_todos(todo)
        self.bin_todo(todo, "modify")

    #completes todo recursively
    def complete_todo(self, todo : Todo, completion : bool):
        todo.completed = completion
        for child in todo.children:
            self.complete_todo(child)

    #formats all Todo data into a dictionary for DB
    def unpack_todos(self, *todos : Todo):
        if not todos:
            todos = list(self.todos.values())
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
            #how to add parentid if it doesn't exist yet
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

        data.delete_todo_data(*self.bin["delete"])

    #sync todos with DB
    def empty_bin(self):
        self.empty_deleted()
        self.empty_modified()


#cli interface to visualise todos and interact with them -- only deployed if called in terminal
if __name__ == "__main__":

    def display_todos(todo_list : TodoList, selected = None):

        start_bold = "\033[1m"
        end_bold = "\033[0m"
        sorted_todos = todo_list.sort_todos(return_depths=True)
        for todo in sorted_todos["visited"]:
            todo_id = todo.todo_id if type(todo.todo_id) != str else todo.todo_id.replace("untitled ", "")
            print(f"""{start_bold if selected == todo else ""}[{todo_id}] {" "*sorted_todos["depths"][todo.todo_id]}{todo.name} [{"X" if todo.completed else ""}] {end_bold if selected == todo else ""}""")

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

        # clear_screen()
        display_todos(user_todo_list, selected_todo)

        if not selected_todo:
            user_input = input("\n[X] Exit\n")
            if user_input.lower() == "x":
                user_todo_list.empty_bin()
                sys.exit()

        if selected_todo:
            clear_screen()
            display_todos(user_todo_list, selected_todo)
            user_input = input(f"\n[A] Edit  [S] Create Sub-Todo  [D] Delete\n")

            if not user_input.isdecimal():

                user_input = user_input.lower()

                if user_input == "a":
                    user_input = input([parameter for parameter in user_todo_list.unpack_todos().keys()])

                elif user_input == "s":
                    todo_name = input("To-do Name: ")
                    todo_difficulty = int(input("To-do Difficulty: "))
                    user_todo_list.create_todo(name=todo_name, parent=selected_todo, difficulty=todo_difficulty)

                elif user_input == "d":
                    user_todo_list.bin_todo(selected_todo, "delete")
                    selected_todo = None


        if user_input.isdecimal():
                if int(user_input) in user_todo_list.todos:

                    if selected_todo and int(user_input) == selected_todo.todo_id:
                        selected_todo = None
                    else:
                        selected_todo = user_todo_list.get_todo(int(user_input))
