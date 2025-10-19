import data
import datetime

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

    def adopt(self, todo):
        self.children.append(todo)
        todo.parent = self


class TodoList():

    #factory method for retrieving a todo-list without coupling to an object
    @staticmethod
    def get():
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

    #adds a todo to the todolist
    def add_todos(self, *todos : Todo):
        for todo in todos:
            self.todos.update({todo.todo_id : todo})

    #adds todo to a bin to prepare for deletion or for updating depending on inputted type
    def bin_todo(self, todo : Todo, bin_type : str):
        if bin_type != "modify" or bin_type != "delete":
            raise NameError("Invalid bin type.")
        self.bin[bin_type].append(todo.todo_id)

    #creates a todo, adding it to todolist and binning it for modifying
    def create_todo(self, name : str, parent : Todo, points : int = 0):
        todo = Todo(name=name, difficulty=difficulty, parent=parent, points=points)
        self.add_todos(todo)
        self.bin_todo(todo, "modify")

    #formats all Todo data into a dictionary for DB
    def unpack_todos(self, *todos):
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
            todo_datum["parentid"] = todo.parent.todo_id
            todo_data.append(todo_datum)

        return todo_data[0] if len(todo_data) == 1 else todo_data

    #sends unpacked todo_data in modify bin to be updated for DB
    def save_todos(self):
        binned_todos = []
        for todo_id in self.bin["modify"]:
            binned_todos.append(self.todos[todo_id])
        data.update_todo_data(*self.unpack_todos(*binned_todos))


    def delete_todos(self):
        pass


    def sync_to_db(self):
        delete_todos()
        save_todos()


#not called via import
if __name__ == "__main__":
    pass