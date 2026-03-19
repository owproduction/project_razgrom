import socket, sys, json, base64, threading
from PySide6.QtWidgets import *
from PySide6.QtCore import Signal, QObject

SERVER = "192.168.133.20"
PORT = 5555

sock = socket.socket()
sock.connect((SERVER, PORT))

class Receiver(QObject):
    msg = Signal(dict)

receiver = Receiver()

# ---------- LOGIN ----------
class Login(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Проект Разгром")
        self.resize(300,200)

        layout = QVBoxLayout(self)

        self.u = QLineEdit()
        self.p = QLineEdit()

        btn = QPushButton("Войти")
        btn.clicked.connect(self.login)

        layout.addWidget(self.u)
        layout.addWidget(self.p)
        layout.addWidget(btn)

    def login(self):
        sock.send((json.dumps({
            "type":"login",
            "username":self.u.text(),
            "password":self.p.text()
        })+"\n").encode())

# ---------- MAIN ----------
class Messenger(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Проект Разгром")
        self.resize(900,600)

        layout = QHBoxLayout(self)

        self.users = QListWidget()
        self.users.itemClicked.connect(self.open_chat)

        right = QVBoxLayout()
        self.chat = QTextBrowser()
        self.msg = QLineEdit()

        send = QPushButton("Отправить")
        send.clicked.connect(self.send_msg)

        right.addWidget(self.chat)
        right.addWidget(self.msg)
        right.addWidget(send)

        layout.addWidget(self.users)
        layout.addLayout(right)

        self.current = None

        receiver.msg.connect(self.handle)

    def handle(self, data):
        if data["type"] == "login":
            if data["status"] == "ok":
                self.show()
            else:
                QMessageBox.warning(self,"Ошибка","Логин неверный")

        elif data["type"] == "message":
            self.chat.append(f"{data['sender']}: {data['text']}")

        elif data["type"] == "image":
            self.chat.append(f"<b>{data['sender']}:</b><br><img src='data:image/png;base64,{data['image']}' width='200'>")

        elif data["type"] == "history":
            self.chat.clear()
            for m in data["messages"]:
                if m["text"]:
                    self.chat.append(f"{m['sender']}: {m['text']}")
                if m["image"]:
                    self.chat.append(f"<img src='data:image/png;base64,{m['image']}' width='200'>")

        elif data["type"] == "search":
            if data["found"]:
                self.users.addItem(data["username"])
            else:
                QMessageBox.warning(self,"Ошибка","Нет пользователя")

    def open_chat(self,item):
        self.current = item.text()

        sock.send((json.dumps({
            "type":"get_history",
            "with":self.current
        })+"\n").encode())

    def send_msg(self):
        sock.send((json.dumps({
            "type":"message",
            "to":self.current,
            "text":self.msg.text()
        })+"\n").encode())
        self.msg.clear()

# ---------- LISTENER ----------
def listen():
    buffer = ""
    while True:
        try:
            data = sock.recv(4096)
            if not data:
                continue

            buffer += data.decode()

            while "\n" in buffer:
                msg, buffer = buffer.split("\n",1)
                receiver.msg.emit(json.loads(msg))

        except:
            break

threading.Thread(target=listen,daemon=True).start()

# ---------- RUN ----------
app = QApplication(sys.argv)
login = Login()
main = Messenger()
login.show()
sys.exit(app.exec())