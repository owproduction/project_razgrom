import socket
import sys
import json
import base64
import threading

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

SERVER = "192.168.133.20"
PORT = 5555

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((SERVER, PORT))


STYLE = """
QWidget{
background:#0f0f0f;
color:white;
font-size:14px;
}

QLineEdit{
background:#1e1e1e;
border:1px solid #333;
padding:6px;
}

QPushButton{
background:#aa0000;
border:none;
padding:8px;
}

QListWidget{
background:#151515;
border:none;
}

QTextEdit{
background:#121212;
border:none;
}
"""


# ---------------- LOGIN ----------------

class Login(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Проект Разгром")
        self.resize(300,200)
        self.setStyleSheet(STYLE)

        layout = QVBoxLayout()

        self.user = QLineEdit()
        self.user.setPlaceholderText("Ник")

        self.password = QLineEdit()
        self.password.setPlaceholderText("Пароль")
        self.password.setEchoMode(QLineEdit.Password)

        login = QPushButton("Войти")
        reg = QPushButton("Регистрация")

        login.clicked.connect(self.login)
        reg.clicked.connect(self.register)

        layout.addWidget(self.user)
        layout.addWidget(self.password)
        layout.addWidget(login)
        layout.addWidget(reg)

        self.setLayout(layout)

    def login(self):

        data = {
            "type":"login",
            "username":self.user.text(),
            "password":self.password.text()
        }

        sock.send(json.dumps(data).encode())
        resp = json.loads(sock.recv(1024).decode())

        if resp["status"] == "ok":

            self.chat = Messenger()
            self.chat.show()
            self.close()

        else:
            QMessageBox.warning(self,"Ошибка","Неверный логин")

    def register(self):

        data = {
            "type":"register",
            "username":self.user.text(),
            "password":self.password.text()
        }

        sock.send(json.dumps(data).encode())
        resp = json.loads(sock.recv(1024).decode())

        if resp["status"] == "ok":
            QMessageBox.information(self,"OK","Аккаунт создан")

        else:
            QMessageBox.warning(self,"Ошибка","Ник занят")


# ---------------- MAIN MESSENGER ----------------

class Messenger(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Проект Разгром")
        self.resize(900,600)
        self.setStyleSheet(STYLE)

        layout = QHBoxLayout(self)

        # ---- LEFT PANEL ----

        left = QVBoxLayout()

        self.search = QLineEdit()
        self.search.setPlaceholderText("Найти пользователя")

        self.search_btn = QPushButton("Поиск")
        self.search_btn.clicked.connect(self.search_user)

        self.chat_list = QListWidget()
        self.chat_list.itemClicked.connect(self.select_chat)

        left.addWidget(self.search)
        left.addWidget(self.search_btn)
        left.addWidget(self.chat_list)

        # ---- RIGHT PANEL ----

        right = QVBoxLayout()

        self.chat_title = QLabel("Чат")

        self.messages = QTextEdit()
        self.messages.setReadOnly(True)

        self.message = QLineEdit()
        self.message.setPlaceholderText("Сообщение")

        send = QPushButton("Отправить")
        img = QPushButton("Фото")

        send.clicked.connect(self.send_message)
        img.clicked.connect(self.send_image)

        right.addWidget(self.chat_title)
        right.addWidget(self.messages)
        right.addWidget(self.message)
        right.addWidget(send)
        right.addWidget(img)

        layout.addLayout(left,1)
        layout.addLayout(right,3)

        self.current_chat = None

        threading.Thread(target=self.receive, daemon=True).start()

    # -------- SEARCH USER --------

    def search_user(self):

        username = self.search.text()

        if username == "":
            return

        self.chat_list.addItem(username)

    # -------- SELECT CHAT --------

    def select_chat(self, item):

        self.current_chat = item.text()
        self.chat_title.setText("Чат с " + self.current_chat)
        self.messages.clear()

    # -------- SEND TEXT --------

    def send_message(self):

        if not self.current_chat:
            return

        text = self.message.text()

        data = {
            "type":"message",
            "to":self.current_chat,
            "text":text
        }

        sock.send(json.dumps(data).encode())

        self.messages.append(f"Я: {text}")
        self.message.clear()

    # -------- SEND IMAGE --------

    def send_image(self):

        if not self.current_chat:
            return

        file = QFileDialog.getOpenFileName(
            self,
            "Выберите фото",
            "",
            "Images (*.png *.jpg *.jpeg)"
        )

        if file[0]:

            with open(file[0],"rb") as f:
                img = base64.b64encode(f.read()).decode()

            data = {
                "type":"image",
                "to":self.current_chat,
                "image":img
            }

            sock.send(json.dumps(data).encode())

            self.messages.append("📷 Фото отправлено")

    # -------- RECEIVE --------

    def receive(self):

        while True:

            try:

                data = json.loads(sock.recv(10000000).decode())

                if data["type"] == "message":

                    if data["from"] == self.current_chat:
                        self.messages.append(
                            f'{data["from"]}: {data["text"]}'
                        )

                if data["type"] == "image":

                    if data["from"] == self.current_chat:
                        self.messages.append(
                            f'{data["from"]}: 📷 изображение'
                        )

            except:
                break


# ---------------- RUN APP ----------------

app = QApplication(sys.argv)

window = Login()
window.show()

sys.exit(app.exec())