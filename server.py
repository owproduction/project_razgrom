import socket
import threading
import json
import sqlite3
import base64
from datetime import datetime

HOST = "0.0.0.0"
PORT = 5555

# -------------------- БАЗА ДАННЫХ --------------------
conn = sqlite3.connect("chat.db", check_same_thread=False)
cursor = conn.cursor()

# Таблицы
cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    username TEXT PRIMARY KEY,
    password TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS messages(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender TEXT,
    receiver TEXT,
    message TEXT,
    image TEXT,
    favorite INTEGER DEFAULT 0,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS chats(
    user TEXT,
    peer TEXT,
    last_message TEXT,
    last_timestamp DATETIME,
    PRIMARY KEY(user, peer)
)
""")

conn.commit()

# -------------------- СОКЕТ --------------------
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()
print(f"SERVER STARTED ON {HOST}:{PORT}")

clients = {}  # {username: socket}

lock = threading.Lock()

# -------------------- ФУНКЦИИ --------------------
def broadcast(to_user, data):
    """Отправка сообщения конкретному пользователю"""
    if to_user in clients:
        try:
            clients[to_user].send(json.dumps(data).encode())
        except:
            pass

def save_message(sender, receiver, text=None, image=None, favorite=0):
    cursor.execute(
        "INSERT INTO messages(sender,receiver,message,image,favorite) VALUES(?,?,?,?,?)",
        (sender,receiver,text,image,favorite)
    )
    conn.commit()
    update_chat(sender, receiver, text or "[Фото]")

def update_chat(user, peer, last_message):
    now = datetime.now().isoformat()
    for u,p in [(user, peer), (peer, user)]:
        cursor.execute("""
        INSERT INTO chats(user, peer, last_message, last_timestamp)
        VALUES(?,?,?,?)
        ON CONFLICT(user, peer) DO UPDATE SET
        last_message=excluded.last_message,
        last_timestamp=excluded.last_timestamp
        """,(u,p,last_message,now))
    conn.commit()

def get_history(user, peer):
    cursor.execute("""
    SELECT sender,message,image,favorite FROM messages
    WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)
    ORDER BY id ASC
    """,(user,peer,peer,user))
    rows = cursor.fetchall()
    return [{"sender":r[0],"text":r[1],"image":r[2],"favorite":r[3]} for r in rows]

def get_favorites(user):
    cursor.execute("""
    SELECT sender,message,image,favorite FROM messages
    WHERE favorite=1 AND (sender=? OR receiver=?)
    ORDER BY id ASC
    """,(user,user))
    rows = cursor.fetchall()
    return [{"sender":r[0],"text":r[1],"image":r[2],"favorite":r[3]} for r in rows]

def handle_client(client_socket):
    username = None
    while True:
        try:
            data = json.loads(client_socket.recv(10000000).decode())
        except:
            break

        if not data:
            continue

        if data["type"]=="register":
            uname = data["username"]
            pwd = data["password"]
            cursor.execute("SELECT * FROM users WHERE username=?",(uname,))
            if cursor.fetchone():
                client_socket.send(json.dumps({"status":"fail"}).encode())
            else:
                cursor.execute("INSERT INTO users(username,password) VALUES(?,?)",(uname,pwd))
                conn.commit()
                client_socket.send(json.dumps({"status":"ok"}).encode())

        elif data["type"]=="login":
            uname = data["username"]
            pwd = data["password"]
            cursor.execute("SELECT * FROM users WHERE username=? AND password=?",(uname,pwd))
            if cursor.fetchone():
                username = uname
                with lock:
                    clients[username]=client_socket
                client_socket.send(json.dumps({"status":"ok"}).encode())
            else:
                client_socket.send(json.dumps({"status":"fail"}).encode())

        elif data["type"]=="message" and username:
            receiver = data["to"]
            text = data["text"]
            save_message(username, receiver, text=text)
            broadcast(receiver, {"from":username,"text":text})

        elif data["type"]=="image" and username:
            receiver = data["to"]
            image = data["image"]
            save_message(username, receiver, image=image)
            broadcast(receiver, {"from":username,"image":image})

        elif data["type"]=="get_history" and username:
            peer = data["with"]
            history = get_history(username, peer)
            client_socket.send(json.dumps({"messages":history}).encode())

        elif data["type"]=="get_favorites" and username:
            favs = get_favorites(username)
            client_socket.send(json.dumps({"messages":favs}).encode())

        elif data["type"]=="favorite" and username:
            msg_id = data["message_id"]
            cursor.execute("UPDATE messages SET favorite=1 WHERE id=?",(msg_id,))
            conn.commit()

    if username:
        with lock:
            del clients[username]
    client_socket.close()

# -------------------- MAIN LOOP --------------------
while True:
    client_sock, addr = server.accept()
    threading.Thread(target=handle_client,args=(client_sock,),daemon=True).start()