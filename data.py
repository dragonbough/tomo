import os
import sqlite3

#if db doesn't exist here, constructs db using schema commands
if not os.path.isfile("tomo_data.db"):
    connection = sqlite3.connect("tomo_data.db")
    cursor = connection.cursor()
    cursor.executescript("""CREATE TABLE IF NOT EXISTS "SubTodo"(ParentTodo INTEGER, ChildTodo INTEGER, PRIMARY KEY(ParentTodo, ChildTodo), FOREIGN KEY(ParentTodo) REFERENCES "Todo"(ID),
                         FOREIGN KEY(ChildTodo) REFERENCES "Todo"(ID));
                         CREATE TABLE sqlite_sequence(name,seq);
                         CREATE TABLE Todo (ID Integer PRIMARY KEY AUTOINCREMENT, Name VARCHAR NOT NULL, Difficulty INTEGER, Completed INTEGER CHECK (Completed == 1 OR Completed == 0),
                         Points INTEGER, TimeCreated INTEGER NOT NULL, TimeCompleted INTEGER);""")
    connection.commit()
else:
    connection = sqlite3.connect("tomo_data.db")
    cursor = connection.cursor()