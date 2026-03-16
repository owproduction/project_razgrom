import socket
import threading
import sqlite3
import json
import base64
import os

HOST = "0.0.0.0"
PORT = 5555

clients = {}

if not os.path.exists("uploads"):
    os.mkdir("uploads")

db = sqlite3.connect("database.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
username TEXT PRIMARY KEY,
password TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS messages(
sender TEXT,
receiver TEXT,
message TEXT,
image TEXT
)
""")

db.commit()


def send(client, data):
    client.send(json.dumps(data).encode())


def handle(client, username):

    while True:
        try:
            data = client.recv(10000000)
            data = json.loads(data.decode())

            if data["type"] == "message":

                receiver = data["to"]

                cur.execute(
                    "INSERT INTO messages VALUES (?,?,?,?)",
                    (username, receiver, data["text"], None)
                )
                db.commit()

                if receiver in clients:
                    send(clients[receiver], {
                        "type": "message",
                        "from": username,
                        "text": data["text"]
                    })

            if data["type"] == "image":

                img_data = base64.b64decode(data["image"])
                filename = f"uploads/{username}_{receiver}.png"

                with open(filename, "wb") as f:
                    f.write(img_data)

                cur.execute(
                    "INSERT INTO messages VALUES (?,?,?,?)",
                    (username, receiver, None, filename)
                )
                db.commit()

                if receiver in clients:
                    send(clients[receiver], {
                        "type": "image",
                        "from": username,
                        "image": data["image"]
                    })

        except:
            break

    del clients[username]
    client.close()


def auth(client):

    data = client.recv(4096)
    data = json.loads(data.decode())

    if data["type"] == "register":

        try:
            cur.execute(
                "INSERT INTO users VALUES (?,?)",
                (data["username"], data["password"])
            )
            db.commit()
            send(client, {"status": "ok"})

        except:
            send(client, {"status": "exists"})

    if data["type"] == "login":

        cur.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (data["username"], data["password"])
        )

        if cur.fetchone():

            username = data["username"]
            clients[username] = client

            send(client, {"status": "ok"})
            handle(client, username)

        else:
            send(client, {"status": "fail"})


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()

print("SERVER STARTED")

while True:

    client, addr = server.accept()
    threading.Thread(target=auth, args=(client,)).start()