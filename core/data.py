from pathlib import Path
import sqlite3

#if db doesn't exist in directory already, constructs db using schema commands
BASE_DIR = Path(__file__).resolve().parent
db_path = BASE_DIR / "tomo_data.db"

if not db_path.is_file():

    connection = sqlite3.connect("tomo_data.db")
    cursor = connection.cursor()

    #write-ahead logging -- increased performance benefit but won't work on network filesystems or read only DBs
    cursor.execute("PRAGMA journal_mode=WAL;")

    # creates and populates the PomoDifficulties table (with default splits)
    cursor.executescript("""CREATE TABLE PomoDifficulties (Difficulty INTEGER PRIMARY KEY CHECK (Difficulty <= 4), FocusDuration INTEGER, RestDuration INTEGER);
                         INSERT INTO PomoDifficulties VALUES(1,75,30);
                         INSERT INTO PomoDifficulties VALUES(2,50,10);
                         INSERT INTO PomoDifficulties VALUES(3,25,5);
                         INSERT INTO PomoDifficulties VALUES(4,15,5);""")

    # creates the Todo table
    cursor.execute("""CREATE TABLE Todo (ID Integer PRIMARY KEY AUTOINCREMENT, Name VARCHAR NOT NULL, Difficulty INTEGER, Completed INTEGER CHECK (Completed == 1 OR Completed == 0),
                   Points INTEGER, TimeCreated INTEGER NOT NULL, TimeCompleted INTEGER, ParentID INTEGER REFERENCES Todo (ID));""")

    ## FOR BASE TOMOS ##

    # creates the TomoStats table and populates with data
    cursor.executescript("""CREATE TABLE TomoStats(ID INTEGER PRIMARY KEY, BaseName VARCHAR(45) NOT NULL);
                         INSERT INTO TomoStats VALUES(1,'Pebble');
                         INSERT INTO TomoStats VALUES(2,'Plant');""")

    # creates the TomoLevelingStats table and populates with data
    cursor.executescript("""CREATE TABLE TomoLevelingStats(TomoID INTEGER NOT NULL, BondLevel INTEGER NOT NULL, RequiredXP INTEGER NOT NULL, SpritePath BLOB, HP INTEGER NOT NULL, FOREIGN KEY (TomoID) REFERENCES TomoStats(ID));
                        INSERT INTO TomoLevelingStats VALUES(1,2,100,'sprites/pebble2.png',150);
                        INSERT INTO TomoLevelingStats VALUES(2,2,300,'sprites/plant2.png',400);
                        INSERT INTO TomoLevelingStats VALUES(2,3,500,'sprites/plant3.png',500);
                        INSERT INTO TomoLevelingStats VALUES(1,3,300,'sprites/pebble2.png',300);
                        INSERT INTO TomoLevelingStats VALUES(1,1,0,'sprites/pebble.png',100);
                        INSERT INTO TomoLevelingStats VALUES(2,1,0,'sprites/plant.png',300);""")

    # creates UserTomo table
    cursor.execute("""CREATE TABLE UserTomo(TomoID INTEGER PRIMARY KEY, Name VARCHAR(45) NOT NULL, HP INTEGER NOT NULL, XP INTEGER NOT NULL, BondLevel INTEGER NOT NULL, LastBehaviour VARCHAR,
                   FOREIGN KEY (TomoID) REFERENCES TomoStats(ID));""")


    connection.commit()

else:

    connection = sqlite3.connect(db_path)

    #rows are returned as indexed dictionary instead of tuples
    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()

# generates the SQL bindings for variably sized data
def generate_bindings(data):
    if len(data) == 1:
        bindings = "?"
    else:
        bindings = "?, " * (len(data) - 1) + "?"
    return bindings

### TO-DO DATA ###

#retrieve todo data based on id, or if not given, retrieve all todos from DB
def retrieve_todo_data(*todo_ids : int) -> list[dict]:
    if todo_ids:
        bindings = generate_bindings(todo_ids)
        cursor.execute(f"SELECT * FROM Todo WHERE ID in ({bindings})", todo_ids)
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
        bindings = generate_bindings(todo_ids)
        cursor.execute(f"DELETE FROM Todo WHERE ID in ({bindings})", todo_ids)
        connection.commit()

        #if theres nothing else in the DB then use delete command to ensure the restart the auto increment of ids
        #if you are having continuity issues with other modules in tomo, remove the reset of the auto increment
        cursor.execute(f"SELECT * FROM Todo")
        if not cursor.fetchall():
            cursor.execute("UPDATE SQLITE_SEQUENCE SET SEQ = 0 WHERE NAME = 'Todo'")

        connection.commit()


### TOMO DATA ###

#tomo_ids are the ids of the base tomo -- user can only have one tomo of each type
#retrieves user tomos and their base tomos, sending them both as dicts in a tuple
def retrieve_tomo_data(*tomo_ids : int) -> tuple[list[dict], dict]:
    # if ids are supplied retrieve user tomo data and base tomo data that matches those ids
    if tomo_ids:
        bindings = generate_bindings(tomo_ids)
        cursor.execute(f"SELECT * FROM UserTomo WHERE TomoID in ({bindings})", tomo_ids)
        user_tomo_data = cursor.fetchall()
        # retrieving the name, bondlevel, requiredxp, SpritePath, and hp from the tomostats and tomolevelingstats tables
        # multiple leveling stats for each id -- leveling stats appended to
        cursor.execute(f"""SELECT TomoStats.ID, TomoStats.BaseName, TomoLevelingStats.BondLevel, TomoLevelingStats.RequiredXP, TomoLevelingStats.SpritePath, TomoLevelingStats.HP
                       FROM TomoLevelingStats
                       INNER JOIN TomoStats ON TomoLevelingStats.TomoID=TomoStats.ID
                       WHERE TomoStats.ID IN ({bindings})""", tomo_ids)
        base_tomo_data = cursor.fetchall()

    # if ids are not supplied retrieve ALL data
    else:
        cursor.execute("SELECT * FROM UserTomo")
        user_tomo_data = cursor.fetchall()

        cursor.execute(f"""SELECT TomoStats.ID, TomoStats.BaseName, TomoLevelingStats.BondLevel, TomoLevelingStats.RequiredXP, TomoLevelingStats.SpritePath, TomoLevelingStats.HP
                       FROM TomoLevelingStats
                       INNER JOIN TomoStats ON TomoLevelingStats.TomoID=TomoStats.ID""")

        base_tomo_data = cursor.fetchall()

    organised_base_tomo_data = {}

    #organises the base tomo data into a neat dictionary of the form: {tomo_id : {"basename" : basename, "levels" : { level : {"required_xp" : required_xp, "hp" : hp, "sprite_path" : sprite_path} }}}
    for base_tomo_datum in base_tomo_data:
        base_name = base_tomo_datum["basename"]
        base_id = int(base_tomo_datum["id"])
        level = int(base_tomo_datum["bondlevel"])
        required_xp = int(base_tomo_datum["requiredxp"])
        hp = int(base_tomo_datum["hp"])
        sprite_path = base_tomo_datum["spritepath"]


        level_data = {level : {"required_xp" : required_xp, "hp" : hp, "sprite_path" : sprite_path}}

        if base_id not in organised_base_tomo_data:
            organised_base_tomo_data[base_id] = {"basename" : base_name, "levels" : level_data}
        else:
            organised_base_tomo_data[base_id]["levels"].update(level_data)

    # print(organised_base_tomo_data)
    # input("")

    return user_tomo_data, organised_base_tomo_data

# modifies tomos with the provided base_ids
def modify_tomo_data(*tomo_data : dict):
    cursor.executemany("UPDATE UserTomo SET Name = (?), HP = (?), XP = (?), BondLevel = (?), LastBehaviour = (?) WHERE TomoID = (?)", [(tomo_datum["name"], tomo_datum["hp"], tomo_datum["xp"], tomo_datum["bondlevel"], tomo_datum["lastbehaviour"], tomo_datum["id"]) for tomo_datum in tomo_data])
    connection.commit()

## POMO DATA ##

# retrieves the user-saved pomodoro split data for each difficulty
def retrieve_pomo_difficulties(*difficulties : int) -> dict[str, str]:
    if difficulties:
        bindings = generate_bindings(difficulties)
        cursor.execute(f"SELECT * FROM PomoDifficulties WHERE Difficulty IN ({bindings})", difficulties)
    else:
        cursor.execute("SELECT * FROM PomoDifficulties")

    pomo_difficulties = cursor.fetchall()

    return pomo_difficulties

# changes focus duration/rest duration for a difficulty
def modify_pomo_difficulties(*pomo_difficulties : dict[int : (int, int)]):

    cursor.executemany(f"UPDATE PomoDifficulties SET FocusDuration = (?), RestDuration = (?) WHERE Difficulty = (?)", [(pomo["focusduration"], pomo["restduration"], pomo["difficulty"]) for pomo in pomo_difficulties])
    connection.commit()