import socket, sys, json, base64, threading
from PySide6.QtWidgets import *
from PySide6.QtCore import Signal, QObject

SERVER = "192.168.133.20"
PORT = 5555

sock = socket.socket()
sock.connect((SERVER, PORT))

STYLE = """
QWidget { background:#0f0f0f; color:white; font-size:14px; }
QLineEdit { background:#1e1e1e; border:1px solid #333; padding:6px; }
QPushButton { background:#aa0000; border:none; padding:8px; }
QListWidget { background:#151515; border:none; }
QTextBrowser { background:#121212; border:none; }
"""

class Receiver(QObject):
    msg = Signal(dict)

receiver = Receiver()

# ---------- LOGIN ----------
class Login(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Проект Разгром")
        self.resize(300,220)
        self.setStyleSheet(STYLE)

        layout = QVBoxLayout(self)

        self.u = QLineEdit()
        self.u.setPlaceholderText("Ник")

        self.p = QLineEdit()
        self.p.setPlaceholderText("Пароль")
        self.p.setEchoMode(QLineEdit.Password)

        login_btn = QPushButton("Войти")
        reg_btn = QPushButton("Регистрация")

        login_btn.clicked.connect(self.login)
        reg_btn.clicked.connect(self.register)

        layout.addWidget(self.u)
        layout.addWidget(self.p)
        layout.addWidget(login_btn)
        layout.addWidget(reg_btn)

    def login(self):
        sock.send((json.dumps({
            "type":"login",
            "username":self.u.text(),
            "password":self.p.text()
        })+"\n").encode())

    def register(self):
        sock.send((json.dumps({
            "type":"register",
            "username":self.u.text(),
            "password":self.p.text()
        })+"\n").encode())

# ---------- MAIN ----------
class Messenger(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Проект Разгром")
        self.resize(900,600)
        self.setStyleSheet(STYLE)

        layout = QHBoxLayout(self)

        # левая панель
        left = QVBoxLayout()

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск пользователя")

        search_btn = QPushButton("Найти")
        search_btn.clicked.connect(self.search_user)

        self.users = QListWidget()
        self.users.itemClicked.connect(self.open_chat)

        left.addWidget(self.search)
        left.addWidget(search_btn)
        left.addWidget(self.users)

        # правая панель
        right = QVBoxLayout()

        self.chat = QTextBrowser()
        self.msg = QLineEdit()

        send = QPushButton("Отправить")
        send.clicked.connect(self.send_msg)

        img = QPushButton("Фото")
        img.clicked.connect(self.send_img)

        right.addWidget(self.chat)
        right.addWidget(self.msg)
        right.addWidget(send)
        right.addWidget(img)

        layout.addLayout(left,1)
        layout.addLayout(right,3)

        self.current = None

        receiver.msg.connect(self.handle)

    # -------- ОБРАБОТКА СЕРВЕРА --------
    def handle(self, data):
        if data["type"] == "login":
            if data["status"] == "ok":
                self.show()
                login.close()
            else:
                QMessageBox.warning(self,"Ошибка","Неверный логин")

        elif data["type"] == "register":
            if data["status"] == "ok":
                QMessageBox.information(self,"OK","Аккаунт создан")
            else:
                QMessageBox.warning(self,"Ошибка","Ник занят")

        elif data["type"] == "message":
            self.chat.append(f"<b>{data['sender']}:</b> {data['text']}")

        elif data["type"] == "image":
            self.chat.append(f"<b>{data['sender']}:</b><br><img src='data:image/png;base64,{data['image']}' width='200'>")

        elif data["type"] == "history":
            self.chat.clear()
            for m in data["messages"]:
                if m["text"]:
                    self.chat.append(f"<b>{m['sender']}:</b> {m['text']}")
                if m["image"]:
                    self.chat.append(f"<img src='data:image/png;base64,{m['image']}' width='200'>")

        elif data["type"] == "search":
            if data["found"]:
                # не дублируем
                existing = [self.users.item(i).text() for i in range(self.users.count())]
                if data["username"] not in existing:
                    self.users.addItem(data["username"])
            else:
                QMessageBox.warning(self,"Ошибка","Пользователь не найден")

    # -------- ПОИСК --------
    def search_user(self):
        username = self.search.text().strip()

        if not username:
            return

        sock.send((json.dumps({
            "type": "search_user",
            "username": username
        }) + "\n").encode())

    # -------- ОТКРЫТЬ ЧАТ --------
    def open_chat(self,item):
        self.current = item.text()

        sock.send((json.dumps({
            "type":"get_history",
            "with":self.current
        })+"\n").encode())

    # -------- ОТПРАВКА --------
    def send_msg(self):
        if not self.current:
            return

        sock.send((json.dumps({
            "type":"message",
            "to":self.current,
            "text":self.msg.text()
        })+"\n").encode())

        self.msg.clear()

    def send_img(self):
        if not self.current:
            return

        file,_ = QFileDialog.getOpenFileName(self,"Фото","","Images (*.png *.jpg)")
        if file:
            with open(file,"rb") as f:
                img = base64.b64encode(f.read()).decode()

            sock.send((json.dumps({
                "type":"image",
                "to":self.current,
                "image":img
            })+"\n").encode())

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