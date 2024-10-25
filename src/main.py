import subprocess
import os
import zipfile
import threading
import requests
import json
import sys
import enum
import platform
from datetime import datetime

CURRENT_PLATFORM = platform.system()

if CURRENT_PLATFORM == 'Windows':
    import win32com.client

from PyQt6.QtWidgets import QApplication, QMessageBox, QProgressBar, QPushButton, QFileDialog, QCheckBox, QVBoxLayout, QProgressBar, QWidget, QLabel, QSizePolicy, QSpacerItem
from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices

IS_DEV = True

VERSION = '1'

URL = 'http://localhost:3000' if IS_DEV else 'https://waddleforever.com'

class OpenOutcome(enum.IntEnum):
    Success = 0,
    Incompatible = 1,
    Connection = 2

class InstallerApp(QApplication):
    finished = pyqtSignal()

    def __init__(self):
        super().__init__([])
        self.verify_version()
        self.finished.connect(self.close_app)

    def verify_version(self):
        outcome = OpenOutcome.Success
        try:
            response = requests.post(URL + '/api/installer', data = json.dumps({
                'version': VERSION
            }))
            if response.status_code == 200:
                json_outcome = response.json()
                if 'status' in json_outcome:
                    status = json_outcome['status']
                    if (status == 'current'):
                        self.window = Installer(self)
                        self.window.show()
                    else:
                        outcome = OpenOutcome.Incompatible
                else:
                    outcome = OpenOutcome.Incompatible
            else:
                outcome = OpenOutcome.Connection
        except :
            outcome = OpenOutcome.Connection
        
        if (outcome != OpenOutcome.Success):
            warning = QMessageBox()
            warning.setWindowTitle('Error')
            message = 'Cannot start installation process: Check your internet connection or if the Waddle Forever webservice is functioning.' if outcome == OpenOutcome.Connection else 'This installer is not compatible with the latest version, please download the installer again from the Waddle Forever website.'
            warning.setText(message)
            warning.setStandardButtons(QMessageBox.StandardButton.Ok)
            warning.exec()
            self.close_app()

    def close_app(self):
        QApplication.quit()
        sys.exit()

class Installer(QWidget):
    download_finished = pyqtSignal()
    unzip_finished = pyqtSignal()

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setWindowTitle("Waddle Forever installer")
        self.setGeometry(100, 100, 500, 300)

        self.init_directory_picker()

    def init_directory_picker(self):
        message = QLabel(self)
        message.setText('Choose the parent directory to install Waddle Forever')

        self.button = QPushButton("Change Directory", self)
        self.button.clicked.connect(self.open_directory_picker)

        self.default_directory = os.getenv('APPDATA') if CURRENT_PLATFORM == 'Windows' else os.path.expanduser('~')

        self.installation_directory_label = QLabel(self)
        self.install_dir = os.path.join(self.default_directory, "WaddleForever")
        self.installation_directory_label.setText(f'Will be installed in: {self.install_dir}')

        self.confirm_dir_button = QPushButton('Confirm')
        self.confirm_dir_button.clicked.connect(self.open_package_selector)

        layout = QVBoxLayout()
        layout.addWidget(message)
        layout.addWidget(self.installation_directory_label)
        layout.addWidget(self.confirm_dir_button)
        layout.addWidget(self.button)
        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        self.setLayout(layout)

    def open_directory_picker(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.install_dir = os.path.join(directory, "WaddleForever")
            self.confirm_dir_button.setEnabled(True)
            self.installation_directory_label.setText(f'Will be installed in: {self.install_dir}')

    def open_package_selector(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel('Choose what you would like to install: ', self))

        game_checkbox = QCheckBox("Install game (Required)", self)
        game_checkbox.setEnabled(False)
        game_checkbox.setChecked(True)

        response = requests.get(URL + '/api/packages').json()
        packages = response['packages']
        layout.addWidget(game_checkbox)
        self.package_checkboxes = {}
        for package in packages:
            checkbox = QCheckBox(package['name'] + f" (around {package['size']} MB)")
            self.package_checkboxes[package['setting']] = checkbox
            layout.addWidget(checkbox)

        self.confirm_package_button = QPushButton('Confirm')
        self.confirm_package_button.clicked.connect(self.start_download_process)
        layout.addWidget(self.confirm_package_button)
        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        QWidget().setLayout(self.layout())
        self.setLayout(layout)
    
    def start_download_process(self):
        self.settings = {}
        for package in self.package_checkboxes:
            self.settings[package] = self.package_checkboxes[package].checkState() == Qt.CheckState.Checked
        QWidget().setLayout(self.layout())
        layout = QVBoxLayout()
        self.progress_label = QLabel(self)
        self.progress_bar = QProgressBar(self)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        self.setLayout(layout)

        QTimer.singleShot(0, self.start_download)

        
    def download_current_file(self):
        file_info = self.files_to_download[self.current_download]
        file_name = file_info['filename']
        name = file_info['name']
        self.progress_label.setText(f'Downloading files ({self.current_download + 1}/{len(self.files_to_download)})')
        self.download_file(file_name, os.path.join(self.install_dir, f'{name}.zip'))


    def start_download(self):
        self.current_download = 0
        os.makedirs(self.install_dir, exist_ok=True)
        settings_json = json.dumps(self.settings)
        with open(os.path.join(self.install_dir, 'settings.json'), 'w') as f:
            f.write(settings_json)

        platform = {
            'platform': 'win32',
            'arch': 'x64'
        } if CURRENT_PLATFORM == 'Windows' else {
            'platform': 'linux',
            'arch': 'x64'
        }
        
        client_info = requests.post(URL + '/api/client', data = json.dumps(platform)).json()
        media_info = requests.post(URL + '/api/media', settings_json).json()
        server_info = requests.post(URL + '/api/server', data = json.dumps(platform)).json()

        if client_info['exists'] == False or server_info['exists'] == False:
            # TODO handler error
            QApplication.quit()
            sys.exit()
        
        

        self.files_to_download = []
        self.files_to_download.append(client_info)
        self.files_to_download.append(server_info)

        for file in media_info['filenames']:
            self.files_to_download.append(file)
        
        self.download_finished.connect(self.start_unzip)

        self.download_thread = threading.Thread(target=self.download_current_file)
        self.download_thread.start()


    def download_file(self, name, dest_path):
        last_update = datetime.now()
        
        with requests.get(URL + '/' + name, stream=True) as response:
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0

            with open(dest_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        file.write(chunk)
                        downloaded_size += len(chunk)

                        current = datetime.now()
                        delta = current - last_update
                        if delta.seconds >= 1:
                            last_update = current
                            self.progress_bar.setValue(int(downloaded_size / total_size * 100))
                
                self.progress_bar.setValue(100)
                self.current_download += 1
                if (self.current_download < len(self.files_to_download)):
                    self.download_current_file()
                else:
                    self.download_finished.emit()

    def start_unzip(self):
        self.files_to_unzip = []
        media_dir = os.path.join(self.install_dir, 'media')
        os.makedirs(media_dir, exist_ok=True)

        for file in self.files_to_download:
            file_type = file['type']
            zip_dir = os.path.join(self.install_dir, file['name'] + '.zip')
            if (file_type) == 'client':
                self.files_to_unzip.append({
                    'zip': zip_dir,
                    'out': self.install_dir
                })
            elif (file_type) == 'media':
                self.files_to_unzip.append({
                    'zip': zip_dir,
                    'out': os.path.join(media_dir, file['name'])
                })
            elif (file_type) == 'server':
                self.files_to_unzip.append({
                    'zip': zip_dir,
                    'out': self.install_dir
                })  
        
        self.current_unzip = 0
        self.unzip_finished.connect(self.finish_install)
        self.zip_thread = threading.Thread(target=self.unzip_current_file)
        self.zip_thread.start()

    def unzip_current_file(self):
        unzip_info = self.files_to_unzip[self.current_unzip]
        self.progress_label.setText(f'Extracting files ({self.current_unzip + 1}/{len(self.files_to_unzip)})')
        self.unzip_file(unzip_info['zip'], unzip_info['out'])

    def unzip_file(self, zip_path, extract_to):
        os.makedirs(extract_to, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            total_files = len(zip_ref.infolist())
            for i, file in enumerate(zip_ref.infolist()):
                zip_ref.extract(file, extract_to)
                self.progress_bar.setValue(int((i + 1) / total_files * 100))

        os.remove(zip_path)
        self.current_unzip += 1
        if (self.current_unzip < len(self.files_to_unzip)):
            self.unzip_current_file()
        else:
            self.unzip_finished.emit()
    
    def finish_install(self):
        QWidget().setLayout(self.layout())
        layout = QVBoxLayout()
        layout.addWidget(QLabel('Installation complete', self))

        if CURRENT_PLATFORM == 'Windows':
            self.shortcut_checkbox = QCheckBox('Create desktop shortcut', self)
            self.run_game_checkbox = QCheckBox('Run the game now', self)
            self.shortcut_checkbox.setChecked(True)
            self.run_game_checkbox.setChecked(True)
            
            layout.addWidget(self.shortcut_checkbox)
            layout.addWidget(self.run_game_checkbox)
        
        if CURRENT_PLATFORM == 'Linux':
            url = QUrl(URL + '/linux')
            QDesktopServices.openUrl(url)

        self.finish_button = QPushButton('Finish')
        self.finish_button.clicked.connect(self.close_installer)
        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        layout.addWidget(self.finish_button)
        self.setLayout(layout)
    
    def close_installer(self):
        if CURRENT_PLATFORM == 'Windows':
            exe_name = 'WaddleForeverClient.exe'
            if self.shortcut_checkbox.checkState() == Qt.CheckState.Checked:
                create_shortcut(self.install_dir, 'Waddle Forever', exe_name)
            if self.run_game_checkbox.checkState() == Qt.CheckState.Checked:
                subprocess.Popen(os.path.join(self.install_dir, exe_name), cwd=self.install_dir)

        self.app.finished.emit()

def create_shortcut(target_path, shortcut_name, target_name):
    desktop_dir = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')

    shortcut_path = os.path.join(desktop_dir, f"{shortcut_name}.lnk")

    target_dir = os.path.join(target_path, target_name)

    shell = win32com.client.Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.TargetPath = target_dir
    shortcut.IconLocation = target_dir
    shortcut.WorkingDirectory = target_path
    shortcut.save()

def main():
    try:
        app = InstallerApp()
        app.exec()
    except Exception as error:
        print(error)

if __name__ == "__main__":
    main()