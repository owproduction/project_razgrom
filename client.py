import socket, sys, json, base64
from PySide6.QtWidgets import *
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

SERVER = "192.168.133.20"
PORT = 5555

sock = socket.socket()
sock.connect((SERVER, PORT))

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

        self.input = QLineEdit()

        send = QPushButton("Отправить")
        send.clicked.connect(self.send_text)

        img = QPushButton("Фото")
        img.clicked.connect(self.send_image)

        file = QPushButton("Файл")
        file.clicked.connect(self.send_file)

        right.addWidget(self.chat)
        right.addWidget(self.input)
        right.addWidget(send)
        right.addWidget(img)
        right.addWidget(file)

        layout.addWidget(self.users)
        layout.addLayout(right)

        self.current = None

    # ---------- ОТКРЫТИЕ ЧАТА ----------
    def open_chat(self, item):
        self.current = item.text()
        self.chat.clear()

        sock.send(json.dumps({"type":"get_history","with":self.current}).encode())
        resp = json.loads(sock.recv(1000000).decode())

        for m in resp["messages"]:
            self.show_msg(m)

    # ---------- ВЫВОД ----------
    def show_msg(self, m):
        sender = m["sender"]

        if m.get("text"):
            self.chat.append(f"<b>{sender}:</b> {m['text']}")

        if m.get("image"):
            self.chat.append(f"""
<b>{sender}:</b><br>
<a href="img://{m['image']}">
<img src="data:image/png;base64,{m['image']}" width="200">
</a>
""")

        if m.get("file"):
            self.chat.append(f"""
<b>{sender}:</b>
<a href="file://{m['filename']}::{m['file']}">
📁 {m['filename']}
</a>
""")

    # ---------- КЛИК ПО ССЫЛКЕ ----------
    def mousePressEvent(self, event):
        cursor = self.chat.cursorForPosition(event.pos())
        href = cursor.charFormat().anchorHref()

        if href.startswith("img://"):
            img_data = href.replace("img://","")
            self.open_image(img_data)

        if href.startswith("file://"):
            name,data = href.replace("file://","").split("::")
            self.save_file(name,data)

    # ---------- УВЕЛИЧЕНИЕ КАРТИНКИ ----------
    def open_image(self, img_data):
        dlg = QDialog(self)
        dlg.setWindowTitle("Фото")
        layout = QVBoxLayout(dlg)

        pix = QPixmap()
        pix.loadFromData(base64.b64decode(img_data))

        lbl = QLabel()
        lbl.setPixmap(pix.scaled(800,600,Qt.KeepAspectRatio))

        btn = QPushButton("Скачать")
        btn.clicked.connect(lambda: self.save_file("image.png", img_data))

        layout.addWidget(lbl)
        layout.addWidget(btn)

        dlg.exec()

    # ---------- СОХРАНЕНИЕ ----------
    def save_file(self, name, data):
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить", name)
        if path:
            with open(path,"wb") as f:
                f.write(base64.b64decode(data))

    # ---------- ОТПРАВКА ----------
    def send_text(self):
        text = self.input.text()
        sock.send(json.dumps({"type":"message","to":self.current,"text":text}).encode())
        self.input.clear()

    def send_image(self):
        file,_ = QFileDialog.getOpenFileName(self,"Фото","","Images (*.png *.jpg)")
        if file:
            with open(file,"rb") as f:
                data = base64.b64encode(f.read()).decode()
            sock.send(json.dumps({"type":"image","to":self.current,"image":data}).encode())

    def send_file(self):
        file,_ = QFileDialog.getOpenFileName(self,"Файл","")
        if file:
            with open(file,"rb") as f:
                data = base64.b64encode(f.read()).decode()
            name = file.split("/")[-1]
            sock.send(json.dumps({
                "type":"file",
                "to":self.current,
                "file":data,
                "filename":name
            }).encode())

# ---------- RUN ----------
app = QApplication(sys.argv)
w = Messenger()
w.show()
sys.exit(app.exec())