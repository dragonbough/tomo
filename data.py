import os
import sqlite3

#if db doesn't exist here, constructs db using schema commands
if not os.path.isfile("tomo_data.db"):
    connection = sqlite3.connect("tomo_data.db")
    cursor = connection.cursor()
    cursor.executescript("""CREATE TABLE Todo (ID Integer PRIMARY KEY AUTOINCREMENT, Name VARCHAR NOT NULL, Difficulty INTEGER, Completed INTEGER CHECK (Completed == 1 OR Completed == 0),
 Points INTEGER, TimeCreated INTEGER NOT NULL, TimeCompleted INTEGER, ParentID INTEGER REFERENCES Todo (ID));""")
    connection.commit()
else:
    connection = sqlite3.connect("tomo_data.db")
    cursor = connection.cursor()

#rows are returned as indexed dictionary instead of tuples
connection.row_factory = sqlite3.Row


#retrieve todo data based on id, or if not given, retrieve all todos from DB
def retrieve_todo_data(*todo_ids : int) -> list[dict]:
    if todo_ids:
        todo_data = cursor.fetchall("SELECT * FROM Todo WHERE ID in (?)", todo_ids)
    else:
        todo_data = cursor.fetchall("SELECT * FROM Todo")
    return todo_data

#updates todo data if its id already exists in db
#otherwise creates new entries in db
def update_todo_data(*todo_data : list[dict]):

    existing_todos = []
    new_todos = []

    for todo_datum in todo_data:
        if todo_datum["id"]:
            existing_todos.append(todo_datum)
        else:
            new_todos.append(todo_datum)

    if existing_todos:
        cursor.executemany("UPDATE Todo SET Name = (?), Difficulty = (?), Completed = (?), Points = (?), TimeCompleted = (?) WHERE ID = (?)", [(todo["name"], todo["difficulty"], todo["completed"], todo["points"], todo["timecompleted"], todo["id"]) for todo in existing_todos])
    if new_todos:
        cursor.executemany("INSERT INTO Todo (Name, Difficulty, Completed, Points, TimeCreated, TimeCompleted, ParentID) VALUES ((?), (?), (?), (?), (?), (?), (?))", [(todo["name"], todo["difficulty"], todo["completed"], todo["points"], todo["timecreated"], todo["timecompleted"], todo["parentid"]) for todo in new_todos])
