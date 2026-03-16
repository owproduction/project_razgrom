import socket, sys, json, base64, threading
from PySide6.QtWidgets import *
from PySide6.QtGui import QTextCursor
from PySide6.QtCore import Qt

SERVER = "192.168.133.20"
PORT = 5555

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((SERVER, PORT))

STYLE = """
QWidget{background:#0f0f0f;color:white;font-size:14px;}
QLineEdit{background:#1e1e1e;border:1px solid #333;padding:6px;}
QPushButton{background:#aa0000;border:none;padding:8px;}
QListWidget{background:#151515;border:none;}
QTextBrowser{background:#121212;border:none;}
"""

WELCOME_TEXT = "❝ «Проект Разгром» спасет мир. Наступит ледниковый период для культуры. Искусственно вызванные темные века. «Проект Разгром» вынудит человечество погрузиться в спячку и ограничить свои аппетиты на время, необходимое Земле для восстановления ресурсов. ❞"

# ---------------- LOGIN ----------------
class Login(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Проект Разгром v3")
        self.resize(300,200)
        self.setStyleSheet(STYLE)
        layout = QVBoxLayout()
        self.user = QLineEdit()
        self.user.setPlaceholderText("Ник")
        self.password = QLineEdit()
        self.password.setPlaceholderText("Пароль")
        self.password.setEchoMode(QLineEdit.Password)
        login_btn = QPushButton("Войти")
        reg_btn = QPushButton("Регистрация")
        login_btn.clicked.connect(self.login)
        reg_btn.clicked.connect(self.register)
        layout.addWidget(self.user)
        layout.addWidget(self.password)
        layout.addWidget(login_btn)
        layout.addWidget(reg_btn)
        self.setLayout(layout)

    def login(self):
        data = {"type":"login","username":self.user.text(),"password":self.password.text()}
        sock.send(json.dumps(data).encode())
        resp = json.loads(sock.recv(1024).decode())
        if resp["status"]=="ok":
            self.chat = MessengerV3(self.user.text())
            self.chat.show()
            self.close()
        else:
            QMessageBox.warning(self,"Ошибка","Неверный логин")

    def register(self):
        data = {"type":"register","username":self.user.text(),"password":self.password.text()}
        sock.send(json.dumps(data).encode())
        resp = json.loads(sock.recv(1024).decode())
        if resp["status"]=="ok":
            QMessageBox.information(self,"OK","Аккаунт создан")
        else:
            QMessageBox.warning(self,"Ошибка","Ник занят")

# ---------------- MAIN MESSENGER ----------------
class MessengerV3(QWidget):
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.setWindowTitle("Проект Разгром v3")
        self.resize(1000,600)
        self.setStyleSheet(STYLE)
        layout = QHBoxLayout(self)

        # LEFT PANEL - chats + favorite
        left = QVBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Найти пользователя")
        self.search_btn = QPushButton("Поиск")
        self.search_btn.clicked.connect(self.search_user)
        self.chat_list = QListWidget()
        self.chat_list.itemClicked.connect(self.select_chat)
        self.favorite_btn = QPushButton("Избранное")
        self.favorite_btn.clicked.connect(self.show_favorites)
        left.addWidget(self.search)
        left.addWidget(self.search_btn)
        left.addWidget(self.chat_list)
        left.addWidget(self.favorite_btn)

        # RIGHT PANEL - chat
        right = QVBoxLayout()
        self.chat_title = QLabel("Чат")
        self.messages = QTextBrowser()
        self.message = QLineEdit()
        self.message.setPlaceholderText("Введите сообщение")
        self.send_btn = QPushButton("Отправить")
        self.send_btn.clicked.connect(self.send_message)
        self.img_btn = QPushButton("Фото")
        self.img_btn.clicked.connect(self.send_image)
        right.addWidget(self.chat_title)
        right.addWidget(self.messages)
        right.addWidget(self.message)
        right.addWidget(self.send_btn)
        right.addWidget(self.img_btn)

        layout.addLayout(left,1)
        layout.addLayout(right,3)

        self.current_chat = None
        threading.Thread(target=self.receive_messages, daemon=True).start()

        # показываем приветственное сообщение
        self.messages.append(f"<i>{WELCOME_TEXT}</i>")

    # -------- SEARCH --------
    def search_user(self):
        username = self.search.text()
        if username=="":
            return
        if username not in [self.chat_list.item(i).text() for i in range(self.chat_list.count())]:
            self.chat_list.addItem(username)

    # -------- SELECT CHAT --------
    def select_chat(self, item):
        self.current_chat = item.text()
        self.chat_title.setText("Чат с " + self.current_chat)
        self.messages.clear()
        # запрос истории
        data = {"type":"get_history","with":self.current_chat}
        sock.send(json.dumps(data).encode())
        resp = json.loads(sock.recv(10000000).decode())
        for msg in resp.get("messages",[]):
            self.append_message(msg["sender"], msg.get("text"), msg.get("image"), msg.get("favorite",0))

    # -------- APPEND MESSAGE --------
    def append_message(self, sender, text=None, image=None, favorite=0):
        cursor = self.messages.textCursor()
        cursor.movePosition(QTextCursor.End)
        fav_mark = "⭐ " if favorite else ""
        if text:
            self.messages.append(f"{fav_mark}<b>{sender}:</b> {text}")
        if image:
            self.messages.append(f'{fav_mark}<b>{sender}:</b><br><img src="data:image/png;base64,{image}" width="200"/>')

    # -------- SEND TEXT --------
    def send_message(self):
        if not self.current_chat:
            return
        text = self.message.text()
        if text=="":
            return
        data = {"type":"message","to":self.current_chat,"text":text}
        sock.send(json.dumps(data).encode())
        self.append_message("Я", text)
        self.message.clear()
        # добавляем чат в боковую панель если новый
        if self.current_chat not in [self.chat_list.item(i).text() for i in range(self.chat_list.count())]:
            self.chat_list.addItem(self.current_chat)

    # -------- SEND IMAGE --------
    def send_image(self):
        if not self.current_chat:
            return
        file = QFileDialog.getOpenFileName(self,"Выберите фото","","Images (*.png *.jpg *.jpeg)")
        if file[0]:
            with open(file[0],"rb") as f:
                img = base64.b64encode(f.read()).decode()
            data = {"type":"image","to":self.current_chat,"image":img}
            sock.send(json.dumps(data).encode())
            self.append_message("Я", image=img)
            if self.current_chat not in [self.chat_list.item(i).text() for i in range(self.chat_list.count())]:
                self.chat_list.addItem(self.current_chat)

    # -------- SHOW FAVORITES --------
    def show_favorites(self):
        data = {"type":"get_favorites"}
        sock.send(json.dumps(data).encode())
        resp = json.loads(sock.recv(10000000).decode())
        self.messages.clear()
        self.chat_title.setText("Избранное")
        for msg in resp.get("messages",[]):
            self.append_message(msg["sender"], msg.get("text"), msg.get("image"), 1)

    # -------- RECEIVE --------
    def receive_messages(self):
        while True:
            try:
                data = json.loads(sock.recv(10000000).decode())
                sender = data.get("from")
                # добавляем чат в боковую панель если новый
                if sender != self.current_chat:
                    if sender not in [self.chat_list.item(i).text() for i in range(self.chat_list.count())]:
                        self.chat_list.addItem(sender)
                self.append_message(sender, data.get("text"), data.get("image"), data.get("favorite",0))
            except:
                break

# ---------------- RUN ----------------
app = QApplication(sys.argv)
window = Login()
window.show()
sys.exit(app.exec())