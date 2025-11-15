import os
import sqlite3

connection = sqlite3.connect("tomo_data.db")
#rows are returned as indexed dictionary instead of tuples
connection.row_factory = sqlite3.Row
cursor = connection.cursor()

#if db doesn't exist here, constructs db using schema commands
if not os.path.isfile("tomo_data.db"):
    cursor.executescript("""CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE Todo (ID Integer PRIMARY KEY AUTOINCREMENT, Name VARCHAR NOT NULL, Difficulty INTEGER, Completed INTEGER CHECK (Completed == 1 OR Completed == 0), Points INTEGER, TimeCreated INTEGER NOT NULL, TimeCompleted INTEGER, ParentID INTEGER REFERENCES Todo (ID));
CREATE TABLE TomoStats(ID INTEGER PRIMARY KEY, BaseName VARCHAR(45) NOT NULL);
CREATE TABLE TomoLevelingStats(TomoID INTEGER NOT NULL, BondLevel INTEGER NOT NULL, RequiredXP INTEGER NOT NULL, Sprite BLOB, HP INTEGER NOT NULL, FOREIGN KEY (TomoID) REFERENCES TomoStats(ID));
CREATE TABLE Item(ID INTEGER PRIMARY KEY, ItemName VARCHAR(45) NOT NULL, Sprite BLOB, Effect VARCHAR);
CREATE TABLE UserTomo(TomoID INTEGER PRIMARY KEY, Name VARCHAR(45) NOT NULL, HP INTEGER NOT NULL, XP INTEGER NOT NULL, BondLevel INTEGER NOT NULL, FOREIGN KEY (TomoID) REFERENCES TomoStats(ID));
CREATE TABLE UserTomoItem(TomoID INTEGER NOT NULL, ItemID INTEGER NOT NULL, FOREIGN KEY (TomoID) REFERENCES TomoStats(ID), FOREIGN KEY (ItemID) REFERENCES Item(ID));""")
    #write-ahead logging -- increased performance benefit but won't work on network filesystems or read only DBs
    cursor.execute("PRAGMA journal_mode=WAL;")
    connection.commit()


### TODO DATA ###

#retrieve todo data based on id, or if not given, retrieve all todos from DB
def retrieve_todo_data(*todo_ids : int) -> list[dict]:
    if todo_ids:
        if len(todo_ids) == 1:
            bindings = "?"
        else:
            bindings = "?, " * (len(todo_ids) -1) + "?"
        cursor.execute(f"SELECT * FROM Todo WHERE ID in ({bindings})", todo_ids)
        todo_data = cursor.fetchall()
    else:
        cursor.execute("SELECT * FROM Todo")
        todo_data = cursor.fetchall()
    return todo_data

#updates todo data if its id already exists in db
#otherwise creates new entries in db
def modify_todo_data(*todo_data : dict):

    existing_todos = []
    new_todos = []

    for todo_datum in todo_data:
        if todo_datum["local"] == False:
            existing_todos.append(todo_datum)
        else:
            new_todos.append(todo_datum)

    if existing_todos:
        cursor.executemany("UPDATE Todo SET Name = (?), Difficulty = (?), Completed = (?), Points = (?), TimeCompleted = (?), ParentID = (?) WHERE ID = (?)", [(todo["name"], todo["difficulty"], todo["completed"], todo["points"], todo["timecompleted"], todo["parentid"], todo["id"]) for todo in existing_todos])

    #save all of the new todos with no parents or children that are also new
    #for the remaining todos (they have local parents or local children), use DFS to save in order, storing the last row_id before passing it on to the parentid of the children
    if new_todos:

        search_set = []
        fully_local_todo_data = []

        new_todos_parent_ids = [todo_datum["parentid"] for todo_datum in new_todos]
        new_todos_ids = [todo_datum["id"] for todo_datum in new_todos]

        for todo_datum in new_todos:
            if todo_datum["id"] not in new_todos_parent_ids and todo_datum["parentid"] not in new_todos_ids:
                fully_local_todo_data.append(todo_datum)
            else:
                search_set.append(todo_datum)

        cursor.executemany("INSERT INTO Todo (Name, Difficulty, Completed, Points, TimeCreated, TimeCompleted, ParentID) VALUES ((?), (?), (?), (?), (?), (?), (?))", [(todo["name"], todo["difficulty"], todo["completed"], todo["points"], todo["timecreated"], todo["timecompleted"], todo["parentid"]) for todo in fully_local_todo_data])

        # print(f"Search set: {[datum["name"] for datum in search_set]}")

        search_set_roots = [todo_datum for todo_datum in search_set if todo_datum["parentid"] not in new_todos_ids]

        # print(f"Search set roots: {[datum["name"] for datum in search_set_roots]}")

        todo_datum_heirarchy = {}
        for todo_datum in search_set:
            todo_datum_heirarchy[todo_datum["id"]] = [child_datum for child_datum in search_set if child_datum["parentid"] == todo_datum["id"]]

        for root_datum in search_set_roots:
            dfs_modify_todo_data(datum=root_datum, visited=[], new_parent_id=root_datum["parentid"], heirarchy=todo_datum_heirarchy)

    connection.commit()

def dfs_modify_todo_data(datum : dict, visited : list, new_parent_id : int, heirarchy : dict):
    datum["parentid"] = new_parent_id
    visited.append(datum)
    cursor.execute("INSERT INTO Todo (Name, Difficulty, Completed, Points, TimeCreated, TimeCompleted, ParentID) VALUES ((?), (?), (?), (?), (?), (?), (?))", (datum["name"], datum["difficulty"], datum["completed"], datum["points"], datum["timecreated"], datum["timecompleted"], datum["parentid"]))
    new_parent_id = cursor.lastrowid

    if heirarchy[datum["id"]]:
        for child in heirarchy[datum["id"]]:
            dfs_modify_todo_data(child, visited, new_parent_id, heirarchy)

    if datum in visited:
        return

#deletes todos from db based on id
def delete_todo_data(*todo_ids : int):

    if todo_ids:
        if len(todo_ids) == 1:
            bindings = "?"
        else:
            bindings = "?, " * (len(todo_ids) -1) + "?"
        cursor.execute(f"DELETE FROM Todo WHERE ID in ({bindings})", todo_ids)
        connection.commit()

        #if theres nothing else in the DB then use delete command to ensure the restart the auto increment of ids
        #if you are having continuity issues with other modules in tomo, remove the reset of the auto increment
        cursor.execute(f"SELECT * FROM Todo")
        if not cursor.fetchall():
            cursor.execute("UPDATE SQLITE_SEQUENCE SET SEQ = 0 WHERE NAME = 'Todo'")

        connection.commit()



### TOMO DATA ###

#retrieve all tomo data