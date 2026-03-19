import socket, threading, json, sqlite3

HOST = "0.0.0.0"
PORT = 5555

conn = sqlite3.connect("chat.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, password TEXT)")
cursor.execute("""
CREATE TABLE IF NOT EXISTS messages(
    sender TEXT,
    receiver TEXT,
    text TEXT,
    image TEXT
)
""")
conn.commit()

clients = {}

def send(sock, data):
    try:
        sock.send((json.dumps(data) + "\n").encode())
    except:
        pass

def handle(client):
    username = None
    buffer = ""

    while True:
        try:
            raw = client.recv(4096)

            if not raw:
                continue

            buffer += raw.decode(errors="ignore")

            while "\n" in buffer:
                msg, buffer = buffer.split("\n", 1)

                if not msg.strip():
                    continue

                try:
                    data = json.loads(msg)
                except:
                    continue  # <-- не падаем

                t = data.get("type")

                # -------- REGISTER --------
                if t == "register":
                    cursor.execute("SELECT * FROM users WHERE username=?", (data["username"],))
                    if cursor.fetchone():
                        send(client, {"type":"register","status":"fail"})
                    else:
                        cursor.execute("INSERT INTO users VALUES(?,?)",(data["username"],data["password"]))
                        conn.commit()
                        send(client, {"type":"register","status":"ok"})

                # -------- LOGIN --------
                elif t == "login":
                    cursor.execute("SELECT * FROM users WHERE username=? AND password=?",
                                   (data["username"],data["password"]))
                    if cursor.fetchone():
                        username = data["username"]
                        clients[username] = client
                        send(client, {"type":"login","status":"ok"})
                    else:
                        send(client, {"type":"login","status":"fail"})

                # -------- MESSAGE --------
                elif t == "message":
                    if not username:
                        continue

                    cursor.execute("INSERT INTO messages VALUES(?,?,?,?)",
                                   (username,data["to"],data["text"],None))
                    conn.commit()

                    if data["to"] in clients:
                        send(clients[data["to"]], {
                            "type":"message",
                            "sender":username,
                            "text":data["text"]
                        })

                # -------- IMAGE --------
                elif t == "image":
                    if not username:
                        continue

                    cursor.execute("INSERT INTO messages VALUES(?,?,?,?)",
                                   (username,data["to"],None,data["image"]))
                    conn.commit()

                    if data["to"] in clients:
                        send(clients[data["to"]], {
                            "type":"image",
                            "sender":username,
                            "image":data["image"]
                        })

                # -------- HISTORY --------
                elif t == "get_history":
                    cursor.execute("""
                    SELECT sender,text,image FROM messages
                    WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)
                    """,(username,data["with"],data["with"],username))

                    msgs = []
                    for r in cursor.fetchall():
                        msgs.append({
                            "sender":r[0],
                            "text":r[1],
                            "image":r[2]
                        })

                    send(client, {"type":"history","messages":msgs})

                # -------- SEARCH --------
                elif t == "search_user":
                    cursor.execute("SELECT username FROM users WHERE username=?", (data["username"],))
                    send(client, {
                        "type":"search",
                        "found": bool(cursor.fetchone()),
                        "username": data["username"]
                    })

        except Exception as e:
            print("ERROR:", e)
            break

    if username in clients:
        del clients[username]

    client.close()

server = socket.socket()
server.bind((HOST, PORT))
server.listen()

print("SERVER STARTED")

while True:
    c,a = server.accept()
    threading.Thread(target=handle,args=(c,),daemon=True).start()