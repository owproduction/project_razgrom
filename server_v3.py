import socket, threading, json, sqlite3

HOST = "0.0.0.0"
PORT = 5555

conn = sqlite3.connect("chat.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, password TEXT)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS messages(
    sender TEXT,
    receiver TEXT,
    text TEXT,
    image TEXT,
    file TEXT,
    filename TEXT
)
""")

conn.commit()

server = socket.socket()
server.bind((HOST, PORT))
server.listen()

clients = {}

def send(sock, data):
    sock.send(json.dumps(data).encode())

def broadcast(user, data):
    if user in clients:
        try:
            send(clients[user], data)
        except:
            pass

def handle(client):
    username = None

    while True:
        try:
            data = json.loads(client.recv(1000000).decode())
        except:
            break

        if data["type"] == "register":
            cursor.execute("SELECT * FROM users WHERE username=?", (data["username"],))
            if cursor.fetchone():
                send(client, {"status":"fail"})
            else:
                cursor.execute("INSERT INTO users VALUES(?,?)",(data["username"],data["password"]))
                conn.commit()
                send(client, {"status":"ok"})

        elif data["type"] == "login":
            cursor.execute("SELECT * FROM users WHERE username=? AND password=?",
                           (data["username"],data["password"]))
            if cursor.fetchone():
                username = data["username"]
                clients[username] = client
                send(client, {"status":"ok"})
            else:
                send(client, {"status":"fail"})

        elif data["type"] == "message":
            cursor.execute("INSERT INTO messages(sender,receiver,text) VALUES(?,?,?)",
                           (username,data["to"],data["text"]))
            conn.commit()
            broadcast(data["to"], {"sender":username,"text":data["text"]})

        elif data["type"] == "image":
            cursor.execute("INSERT INTO messages(sender,receiver,image) VALUES(?,?,?)",
                           (username,data["to"],data["image"]))
            conn.commit()
            broadcast(data["to"], {"sender":username,"image":data["image"]})

        elif data["type"] == "file":
            cursor.execute("INSERT INTO messages(sender,receiver,file,filename) VALUES(?,?,?,?)",
                           (username,data["to"],data["file"],data["filename"]))
            conn.commit()
            broadcast(data["to"], {
                "sender":username,
                "file":data["file"],
                "filename":data["filename"]
            })

        elif data["type"] == "get_history":
            cursor.execute("""
            SELECT sender,text,image,file,filename FROM messages
            WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)
            """,(username,data["with"],data["with"],username))

            msgs = []
            for r in cursor.fetchall():
                msgs.append({
                    "sender":r[0],
                    "text":r[1],
                    "image":r[2],
                    "file":r[3],
                    "filename":r[4]
                })
            send(client, {"messages":msgs})

    client.close()

while True:
    c, a = server.accept()
    threading.Thread(target=handle,args=(c,),daemon=True).start()