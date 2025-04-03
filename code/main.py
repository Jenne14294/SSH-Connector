import sys
import paramiko
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLineEdit, QListWidget, QLabel, QFileDialog, QTextEdit, QStackedWidget, 
                             QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QMessageBox, QInputDialog,
                             QCheckBox, QListWidgetItem, QComboBox, QSystemTrayIcon, QMenu, QAction)
                             
from PyQt5.QtGui import QPixmap, QFont, QIcon
from PyQt5.QtCore import Qt, QSettings, QSize
from cryptography.fernet import Fernet

class SSHClientGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.ssh_client = None
        self.sftp_client = None
        self.current_path = f"/home/{self.user_input.text()}"
        self.current_ip = ""
        self.current_user = ""
        self.encrypt_key = self.load_encryption_key()

        # 設置圖示
        self.tray_icon = QSystemTrayIcon(self)
        icon = QIcon("./icons/icon.png")  # 使用你的圖示路徑
        self.tray_icon.setIcon(icon)

        # 設置右鍵菜單
        self.menu = QMenu(self)
        self.open_action = QAction("開啟", self)
        self.quit_action = QAction("退出", self)
        self.status_action = QAction("連接狀態: 🟥", self)  # 新增顯示狀態的選項
        self.upload_action = QAction("上傳", self)  # 快速上傳選項
        self.logout_action = QAction("登出", self)  # 快速上傳選項

        # 連接右鍵動作
        self.open_action.triggered.connect(self.show)  # 顯示主視窗
        self.quit_action.triggered.connect(self.quit_app)  # 退出應用程式

        self.menu.addAction(self.open_action)
        self.menu.addAction(self.status_action)  # 把狀態選項加入菜單
        self.menu.addAction(self.quit_action)

        # 將菜單設置給系統托盤
        self.tray_icon.setContextMenu(self.menu)

        # 顯示圖示
        self.tray_icon.show()

        self.setGeometry(300, 300, 250, 150)

    def update_menu(self, is_connected):
        """根據是否連接來更新菜單"""
        if is_connected:
            self.upload_action.triggered.connect(self.upload_file)
            self.upload_action.triggered.connect(self.logout)
            
            # 在「退出」之前插入「快速上傳」
            self.menu.insertAction(self.quit_action, self.upload_action)
            self.menu.insertAction(self.quit_action, self.logout_action)
            self.status_action.setText(f"連接狀態: 🟢 ({self.current_ip} - {self.current_user})")
        else:
            self.menu.removeAction(self.upload_action)  # 移除「快速上傳」
            self.menu.removeAction(self.logout_action)  # 移除「快速上傳」
            self.status_action.setText("連接狀態: 🟥")


    def quit_app(self):
        """退出應用程序"""
        QApplication.quit()

    def closeEvent(self, event):
        """當視窗關閉時，將其隱藏到工具列，而不是退出應用"""
        event.ignore()  # 防止視窗關閉
        self.hide()  # 隱藏視窗

    def initUI(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #2e3b4e;
                color: #ffffff;
                font-family: 'Arial';
            }
            QLineEdit {
                background-color: #4a5d72;
                border: 1px solid #3a4c61;
                border-radius: 5px;
                padding: 8px;
                color: #ffffff;
            }
            QLineEdit:focus {
                border-color: #61b9f7;
            }
            QPushButton {
                background-color: #61b9f7;
                border: none;
                padding: 10px;
                border-radius: 5px;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4a9be0;
            }
            QLabel {
                color: #ffffff;
                font-size: 16px;
            }
            QListWidget {
                background-color: #3a4c61;
                border-radius: 5px;
                padding: 10px;
                color: #ffffff;
                width: 400px;  # 增大檔案列表寬度
                font-size: 16px;  # 增大字體
            }
            QTextEdit {
                background-color: #3a4c61;
                border-radius: 5px;
                padding: 10px;
                color: #ffffff;
                height: 300px;  # 增大文字預覽區
            }
            QListWidget::item:hover {
                background-color: #61b9f7;
            }
            QGraphicsView {
                background-color: #3a4c61;
                border-radius: 5px;
                width: 600px;  # 增大圖片預覽區寬度
                height: 400px;  # 增大圖片預覽區高度
            }
            QHBoxLayout {
                margin-top: 20px;
            }
        """)

        self.stacked_widget = QStackedWidget(self)
        
        # 登入畫面
        self.login_widget = QWidget()
        login_layout = QVBoxLayout()

         # 下拉式選單
        self.login_combobox = QComboBox(self)
        self.login_combobox.setPlaceholderText("選擇已儲存的登入資訊")
        self.load_saved_logins()  # 載入已儲存的登入資訊
        self.login_combobox.currentIndexChanged.connect(self.on_combobox_select)

        # 清空紀錄的按鈕
        self.clear_btn = QPushButton("清空儲存的紀錄", self)
        self.clear_btn.setFixedWidth(150)
        self.clear_btn.clicked.connect(self.clear_saved_logins)

        # 創建水平佈局來並排顯示
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.login_combobox)
        h_layout.addWidget(self.clear_btn)

        # 將水平佈局添加到主佈局
        login_layout.addLayout(h_layout)
        
        self.ip_input = QLineEdit(self)
        self.ip_input.setPlaceholderText("輸入伺服器 IP")
        login_layout.addWidget(self.ip_input)
        
        self.user_input = QLineEdit(self)
        self.user_input.setPlaceholderText("輸入使用者名稱")
        login_layout.addWidget(self.user_input)
        
        # 創建密碼輸入框
        self.password_input = QLineEdit(self)
        self.password_input.setPlaceholderText("輸入密碼")
        self.password_input.setEchoMode(QLineEdit.Password)

        # 創建顯示密碼按鈕
        self.show_password_btn = QPushButton(self)
        self.show_icon = QIcon(QPixmap("./icons/show_password.png"))  # 顯示密碼的圖示
        self.hide_icon = QIcon(QPixmap("./icons/hide_password.png"))  # 隱藏密碼的圖示
        self.show_password_btn.setIcon(self.hide_icon)  # 預設為隱藏密碼
        self.show_password_btn.setFixedSize(30, 30)  # 設定按鈕大小
        self.show_password_btn.setStyleSheet("border: none;")  # 移除按鈕邊框
        self.show_password_btn.clicked.connect(self.toggle_password_visibility)
        self.show_password_btn.setIconSize(QSize(40, 40))

        # 建立水平佈局
        password_layout = QHBoxLayout()
        password_layout.addWidget(self.password_input)
        password_layout.addWidget(self.show_password_btn)
        password_layout.setContentsMargins(0, 0, 0, 0)  # 移除內邊距
        password_layout.setSpacing(5)  # 設定元件間距

        login_layout.addLayout(password_layout)

        # 記住資訊勾選框
        self.remember_checkbox = QCheckBox("記住登入資訊", self)
        login_layout.addWidget(self.remember_checkbox)
        
        self.connect_btn = QPushButton("連線", self)
        self.connect_btn.clicked.connect(self.connect_ssh)
        login_layout.addWidget(self.connect_btn)
        
        self.login_widget.setLayout(login_layout)
        self.stacked_widget.addWidget(self.login_widget)
        
        # 主畫面
        self.main_widget = QWidget()
        main_layout = QVBoxLayout()

        # 放置檔案列表和預覽區
        file_preview_layout = QHBoxLayout()
        
        self.file_list = QListWidget(self)
        self.file_list.itemDoubleClicked.connect(self.navigate)
        file_preview_layout.addWidget(self.file_list)
        
        self.preview_area = QGraphicsView(self)  # 使用 QGraphicsView 顯示圖片
        self.scene = QGraphicsScene()
        self.preview_area.setScene(self.scene)
        
        # 文字預覽區
        self.text_preview = QTextEdit(self)
        self.text_preview.setReadOnly(True)
        self.text_preview.setVisible(False)  # 文字預覽區隱藏
        
        file_preview_layout.addWidget(self.preview_area)
        file_preview_layout.addWidget(self.text_preview)

        main_layout.addLayout(file_preview_layout)

        # 放置操作按鈕並排顯示
        button_layout = QHBoxLayout()

        # 顯示當前連線的IP和使用者名稱
        self.connection_label = QLabel("當前連線: 未連線", self)
        self.connection_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.connection_label)

        self.logout_btn = QPushButton("登出", self)
        self.logout_btn.clicked.connect(self.logout)
        button_layout.addWidget(self.logout_btn)

         # 建立資料夾和刪除檔案按鈕並排
        folder_layout = QHBoxLayout()
        self.create_folder_btn = QPushButton("建立資料夾", self)
        self.create_folder_btn.clicked.connect(self.create_folder)
        folder_layout.addWidget(self.create_folder_btn)

        self.delete_file_btn = QPushButton("刪除檔案", self)
        self.delete_file_btn.clicked.connect(self.delete_selected_files)
        folder_layout.addWidget(self.delete_file_btn)

        main_layout.addLayout(folder_layout)

        self.download_btn = QPushButton("下載檔案", self)
        self.download_btn.clicked.connect(self.download_file)
        button_layout.addWidget(self.download_btn)
        
        self.upload_btn = QPushButton("上傳檔案", self)
        self.upload_btn.clicked.connect(self.upload_file)
        button_layout.addWidget(self.upload_btn)
        
        main_layout.addLayout(button_layout)
        
        self.main_widget.setLayout(main_layout)
        self.stacked_widget.addWidget(self.main_widget)
        
        layout = QVBoxLayout()
        layout.addWidget(self.stacked_widget)
        self.setLayout(layout)
        
        self.setWindowTitle("SSH 連接者")
        self.setGeometry(100, 100, 1000, 700)
        self.stacked_widget.setCurrentWidget(self.login_widget)

    def load_encryption_key(self):
        # 加載加密金鑰（此金鑰應該在第一次啟動時生成並保存在某處）
        # 如果您沒有金鑰，可以使用以下方式生成一個：
        # key = Fernet.generate_key()
        # 保存到文件或者應用配置中
        return b'aqFDRxBW0UMR4x7yhgsFdN29-BHvMk2K8xsYcDs3kHI='  # 請替換為您的加密金鑰
    
    def encrypt_password(self, password):
        # 使用加密金鑰加密密碼
        cipher = Fernet(self.encrypt_key)
        encrypted_password = cipher.encrypt(password.encode())
        return encrypted_password
    
    def decrypt_password(self, encrypted_password):
        # 使用加密金鑰解密密碼
        cipher = Fernet(self.encrypt_key)
        decrypted_password = cipher.decrypt(encrypted_password).decode()
        return decrypted_password

    def load_saved_logins(self):
        """從設定檔讀取已儲存的登入資訊，QComboBox 只顯示 IP - 使用者名稱"""
        settings = QSettings("my_app", "login_info")
        saved_logins = settings.allKeys()

        self.login_combobox.clear()  # 清空舊資料

        for key in saved_logins:
            if " - " in key:  # 確保是正確格式的鍵 (IP - 使用者名稱)
                encrypted_password = settings.value(key)  # 取得加密密碼
                self.login_combobox.addItem(key, encrypted_password)  # 顯示 "IP - 使用者名稱"，但存密碼


    def clear_saved_logins(self):
        # 彈出確認提示框
        reply = QMessageBox.question(self, '確認刪除', '確定要清除所有儲存的登入紀錄嗎？', 
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 使用 QSettings 清除儲存的所有登入紀錄
            settings = QSettings("my_app", "login_info")

            # 清除所有的登入紀錄（IP 和使用者名稱的紀錄）
            saved_logins = settings.allKeys()
            for key in saved_logins:
                settings.remove(key)

            # 顯示確認訊息
            QMessageBox.information(self, "清空成功", "所有儲存的登入紀錄已經清除！")
            
            # 刷新 QComboBox，清空並重新載入已儲存的登入紀錄
            self.login_combobox.clear()  # 清空現有選項
            self.load_saved_logins()  # 重新載入已儲存的登入資訊

        else:
            # 如果使用者選擇「否」，則不進行刪除
            QMessageBox.information(self, "取消操作", "您選擇取消清除紀錄。")

    def on_combobox_select(self):
        """當選擇一個登入紀錄時，只填入 IP 和使用者名稱，不填入密碼"""
        selected_index = self.login_combobox.currentIndex()  # 取得當前索引
        selected_text = self.login_combobox.currentText()  # 取得顯示文字 (IP - 使用者名稱)

        if selected_index >= 0 and " - " in selected_text:
            ip, username = selected_text.split(" - ", 1)  # 解析出 IP 和使用者名稱
            stored_encrypt_password = self.login_combobox.itemData(selected_index)
            decrypt_password = self.decrypt_password(stored_encrypt_password)

            self.ip_input.setText(ip)
            self.user_input.setText(username)
            self.password_input.setText(decrypt_password)


    def toggle_password_visibility(self):
        # 切換顯示/隱藏密碼
        if self.password_input.echoMode() == QLineEdit.Password:
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.show_password_btn.setIcon(QIcon(QPixmap("./icons/show_password.png")))  # 眼睛開啟
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.show_password_btn.setIcon(QIcon(QPixmap("./icons/hide_password.png")))  # 眼睛關閉

    def save_login_info(self, ip, user, password):
        """儲存登入資訊 (IP - 使用者名稱 + 加密密碼)，並將資安提示存到獨立的 QSettings"""
        login_settings = QSettings("my_app", "login_info")  # 存登入資訊
        security_settings = QSettings("my_app_security", "settings")  # 存資安提示
        key = f"{ip} - {user}"  # 確保符合存儲格式
        encrypted_password = self.encrypt_password(password)

        # 檢查是否已顯示過資安提示
        if not security_settings.value("security_prompt_shown", False):
            reply = QMessageBox.question(self, "資安提示",
                                        "密碼儲存會有資安風險，請確認要保存登入資訊嗎？",
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                security_settings.setValue("security_prompt_shown", True)  # 存到獨立的 QSettings
                login_settings.setValue(key, encrypted_password)
                QMessageBox.information(self, "成功", "登入資訊已儲存！")
            else:
                self.remember_checkbox.setChecked(False)  # 取消勾選
                return
        else:
            login_settings.setValue(key, encrypted_password)

        # 刷新 QComboBox，清空並重新載入已儲存的登入紀錄
        self.login_combobox.clear()  # 清空現有選項
        self.load_saved_logins()  # 重新載入已儲存的登入資訊

    def connect_ssh(self):
        ip = self.ip_input.text()
        user = self.user_input.text()
        password = self.password_input.text()

        if not ip and not user and not password:
            self.show_error("連線失敗", f"輸入不可為空")
            return

        # try:
            # 嘗試建立 SSH 連線
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh_client.connect(ip, username=user, password=password)
        self.sftp_client = self.ssh_client.open_sftp()

            # 連線成功後更新 UI
        self.current_ip = ip
        self.current_user = user
        self.connection_label.setText(f"當前連線: {self.current_ip} ({self.current_user})")
        self.current_path = f"/home/{user}"
        self.load_directory(self.current_path)
        self.stacked_widget.setCurrentWidget(self.main_widget)
        self.update_menu(True)  # 更新菜單，顯示「快速上傳」

            # 只有當「記住登入資訊」被勾選時，才存儲登入資訊
        if self.remember_checkbox.isChecked():
            self.save_login_info(ip, user, password)

        # except Exception as e:
        #     self.show_error("連線失敗", f"無法連線: {e}")


    def create_folder(self):
        folder_name, ok = QInputDialog.getText(self, "建立資料夾", "輸入資料夾名稱:")
        if ok and folder_name:
            try:
                new_folder_path = f"{self.current_path}/{folder_name}"
                self.sftp_client.mkdir(new_folder_path)
                self.load_directory(self.current_path)
            except Exception as e:
                self.show_error("建立資料夾失敗", f"無法建立資料夾: {e}")

    def delete_selected_files(self):
        checked_items = []

        # 先把所有勾選的檔案儲存起來
        for index in range(self.file_list.count()):
            item = self.file_list.item(index)
            checkbox = self.file_list.itemWidget(item)

            if not checkbox:
                continue

            if checkbox.isChecked():  # 檢查是否被選中
                checked_items.append(item)

        # 提示使用者確認刪除
        reply = QMessageBox.question(
            self, 
            "確認刪除", 
            f"您確定要刪除選中的 {len(checked_items)} 個檔案嗎？", 
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )

        if reply == QMessageBox.No:
            return  # 如果使用者選擇「否」，則不進行刪除

        # 使用 for 迴圈直接遍歷 checked_items
        for item_to_delete in checked_items:
            file_name = item_to_delete.text()
            file_path = f"{self.current_path}/{file_name}"

            try:
                if self.is_directory(file_path):
                    self.sftp_client.rmdir(file_path)
                else:
                    self.sftp_client.remove(file_path)

            except Exception as e:
                # 可以在 GUI 中顯示錯誤訊息給使用者
                self.show_error("刪除檔案失敗", f"無法刪除檔案: {e}")

        # 刪除後重新載入目錄
        self.load_directory(self.current_path)
    
    def load_directory(self, path):
        try:
            self.file_list.clear()
            self.current_path = path
            self.file_list.addItem("上一頁")  # 返回上一層
            for item in self.sftp_client.listdir(path):
                if not item.startswith('.'):  # 不顯示隱藏檔案
                    item_widget = QListWidgetItem(item)
                    font = QFont()  # 創建字體對象
                    font.setPointSize(24)  # 設置字體大小
                    item_widget.setFont(font)  # 設置字體
                    checkbox = QCheckBox(item)  # 每個檔案有勾選框
                    self.file_list.addItem(item_widget)
                    self.file_list.setItemWidget(item_widget, checkbox)
        except Exception as e:
            self.show_error("讀取目錄失敗", f"無法讀取目錄: {e}")


    
    def navigate(self, item):
        selected_item = item.text()
        if selected_item == "上一頁":
            self.scene.clear()  # 清空圖片預覽
            self.text_preview.clear()  # 清空文字預覽
            self.text_preview.setVisible(False)  # 隱藏文字預覽
            self.preview_area.setVisible(False)  # 隱藏圖片預覽
            self.current_path = "/".join(self.current_path.split("/")[:-1]) or "/home/jenne14294"
            self.load_directory(self.current_path)
        else:
            new_path = f"{self.current_path}/{selected_item}"
            try:
                if self.is_directory(new_path):
                    self.current_path = new_path
                    self.load_directory(self.current_path)
                else:
                    self.preview_file(new_path)
            except:
                self.preview_file(new_path)
    
    def is_directory(self, path):
        try:
            self.sftp_client.listdir(path)
            return True
        except:
            return False
    
    def preview_file(self, remote_path):
        try:
            # 檢查是否為圖片格式
            if remote_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                with self.sftp_client.open(remote_path, 'rb') as file:
                    content = file.read()
                    pixmap = QPixmap()
                    if pixmap.loadFromData(content):
                        self.scene.clear()
                        # 設定圖片大小為最大顯示區域的大小，但保持比例
                        pixmap_item = QGraphicsPixmapItem(pixmap.scaled(self.preview_area.width(), self.preview_area.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                        self.scene.addItem(pixmap_item)
                        self.text_preview.setVisible(False)
                        self.preview_area.setVisible(True)
                    else:
                        self.scene.clear()
                        pixmap_item = QGraphicsPixmapItem()
                        self.scene.addItem(pixmap_item)
                        self.show_error("無法顯示圖片", "圖片格式不支持或加載失敗")
            else:
                # 處理非圖片檔案
                with self.sftp_client.open(remote_path, 'r') as file:
                    content = file.read().decode('utf-8', errors='ignore')
                    self.text_preview.setText(content)
                    self.scene.clear()
                    self.text_preview.setVisible(True)
                    self.preview_area.setVisible(False)
        except Exception as e:
            self.show_error("預覽失敗", f"無法預覽檔案: {e}")

    def download_file(self):
        checked_items = []  # 用來儲存勾選的檔案項目

        # 取得所有已勾選的項目
        for row in range(self.file_list.count()):
            item = self.file_list.item(row)
            checkbox = self.file_list.itemWidget(item)  # 取得對應的勾選框

            if isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                checked_items.append(item)  # 如果勾選了，則加入列表

        if not checked_items:
            self.show_error("下載錯誤", "請勾選檔案進行下載")
            return

        # 讓使用者選擇下載位置
        save_dir = QFileDialog.getExistingDirectory(self, "選擇下載資料夾")
        if save_dir:
            # 下載每一個已勾選的檔案
            for item in checked_items:
                file_name = item.text()
                remote_path = f"{self.current_path}/{file_name}"
                local_path = f"{save_dir}/{file_name}"  # 組合成完整的本地儲存路徑
                
                try:
                    self.sftp_client.get(remote_path, local_path)  # 下載檔案
                except Exception as e:
                    self.show_error("下載失敗", f"下載檔案 {file_name} 失敗: {e}")
                    continue  # 如果某個檔案下載失敗，繼續處理下一個檔案

            self.show_info("下載完成", "選擇的檔案已下載完畢。")

    def upload_file(self):
        # 讓使用者選擇多個檔案
        local_paths, _ = QFileDialog.getOpenFileNames(self, "選擇要上傳的檔案")
        
        # 如果沒有選擇檔案
        if not local_paths:
            self.show_error("上傳錯誤", "請選擇檔案進行上傳")
            return
        
        # 上傳每一個選擇的檔案
        for local_path in local_paths:
            remote_path = f"{self.current_path}/{local_path.split('/')[-1]}"  # 生成遠端檔案路徑
            try:
                self.sftp_client.put(local_path, remote_path)  # 上傳檔案
            except Exception as e:
                self.show_error("上傳失敗", f"上傳檔案 {local_path} 失敗: {e}")
                continue  # 如果某個檔案上傳失敗，繼續處理下一個檔案
        
        # 上傳完成後重新載入目錄
        self.load_directory(self.current_path)


    def logout(self):
        if self.ssh_client:
            self.sftp_client.close()
            self.ssh_client.close()
        self.stacked_widget.setCurrentWidget(self.login_widget)
        self.ip_input.clear()
        self.user_input.clear()
        self.password_input.clear()
        self.update_menu(False)  # 更新為已連接狀態

    def show_error(self, title, message):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec_()

    def show_info(self, title, message):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec_()  # 顯示訊息框

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("./icons/icon.png"))
    window = SSHClientGUI()
    window.show()
    sys.exit(app.exec_())
