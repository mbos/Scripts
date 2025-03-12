import json
import locale
import os
import re
import subprocess
import sys
from datetime import datetime

import keyring  # type: ignore
import paramiko  # Toegevoegd voor SSH exceptions
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QTextEdit, QGroupBox, QMessageBox, QSizePolicy,
                             QProgressBar)
from dotenv import load_dotenv

from synology_client import SynologyClient

# Constanten voor log paden om hard-coded waarden te vermijden
LOG_PATHS = {
    'backup': '/var/services/homes/Mike/backup.log',
    'deurbel': '/var/services/homes/Mike/deurbel_cleanup.log'
}

# Lokalisatie strings
TRANSLATIONS = {
    'nl_NL': {
        'window_title': "Synology Onderhoud",
        'edit_credentials': "Verbindingsgegevens wijzigen",
        'hostname_label': "Hostname:",
        'username_label': "Username:",
        'password_label': "Password:",
        'connect_btn': "Verbinden",
        'disconnect_btn': "Verbinding verbreken",
        'connection_broken': "Verbinding verbroken",
        'open_ssh': "Open SSH Sessie",
        'backup_label': "Backup",
        'backup_no_log': "Backup (geen log)",
        'backup_error': "Backup (error)",
        'doorbell_label': "Deurbel",
        'doorbell_no_log': "Deurbel (geen log)",
        'storage_unavailable': "Storage informatie niet beschikbaar",
        'storage_used': "Gebruikt: {} van {} (Vrij: {})",
        'error_title': "Fout",
        'error_credentials': "Vul alle verbindingsgegevens in",
        'error_connection': "Kon geen verbinding maken",
        'warning_title': "Waarschuwing",
        'warning_save_config': "Kon configuratie niet opslaan: {}",
        'warning_iterm': "Kon iTerm sessie niet openen: {}"
    },
    'en_US': {
        'window_title': "Synology Maintenance",
        'edit_credentials': "Edit Connection Details",
        'hostname_label': "Hostname:",
        'username_label': "Username:",
        'password_label': "Password:",
        'connect_btn': "Connect",
        'disconnect_btn': "Disconnect",
        'connection_broken': "Connection Lost",
        'open_ssh': "Open SSH Session",
        'backup_label': "Backup",
        'backup_no_log': "Backup (no log)",
        'backup_error': "Backup (error)",
        'doorbell_label': "Doorbell",
        'doorbell_no_log': "Doorbell (no log)",
        'storage_unavailable': "Storage information unavailable",
        'storage_used': "Used: {} of {} (Free: {})",
        'error_title': "Error",
        'error_credentials': "Please fill in all connection details",
        'error_connection': "Could not establish connection",
        'warning_title': "Warning",
        'warning_save_config': "Could not save configuration: {}",
        'warning_iterm': "Could not open iTerm session: {}"
    }
}


# Configuratieklasse om configuratieparameters te bundelen
class SynologyConfig:
    def __init__(self):
        self.config_file = os.path.expanduser('~/.synology_maintenance.json')
        self.keyring_service = 'synology_maintenance'
        self.keyring_username = 'synology_user'
        self.temp_dir = os.path.expanduser('~/.synology_maintenance_temp')
        self.config_data = {}

    def load(self):
        """Laadt configuratie uit bestand"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    try:
                        self.config_data = json.load(f)
                    except json.JSONDecodeError as e:
                        print(f"Ongeldige JSON in configuratiebestand: {e}")
                        self.config_data = {}
            else:
                self.config_data = {}
        except (FileNotFoundError, PermissionError) as e:
            print(f"Fout bij toegang tot configuratiebestand: {e}")
            self.config_data = {}
        except IOError as e:
            print(f"I/O fout bij lezen configuratie: {e}")
            self.config_data = {}

    def save(self):
        """Slaat configuratie op in bestand"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config_data, f)
            return True, ""
        except (FileNotFoundError, PermissionError) as e:
            return False, f"Toegangsfout: {str(e)}"
        except IOError as e:
            return False, f"I/O fout: {str(e)}"
        except TypeError as e:
            return False, f"Ongeldige data: {str(e)}"

    def has_saved_credentials(self):
        """Controleert of er opgeslagen gegevens zijn"""
        return 'hostname' in self.config_data and 'username' in self.config_data

    def get_credentials(self):
        """Haalt opgeslagen gegevens op"""
        if not self.has_saved_credentials():
            return None, None, None

        hostname = self.config_data.get('hostname')
        username = self.config_data.get('username')
        password = keyring.get_password(self.keyring_service, self.keyring_username)
        return hostname, username, password

    def save_credentials(self, hostname, username, password):
        """Slaat verbindingsgegevens op"""
        self.config_data['hostname'] = hostname
        self.config_data['username'] = username
        success, error_msg = self.save()
        if success:
            keyring.set_password(self.keyring_service, self.keyring_username, password)
        return success, error_msg


def get_system_language():
    # Bepaal de systeem taal en return de juiste taal code
    try:
        # Voor macOS, gebruik defaults om de systeem taal op te halen
        if sys.platform == 'darwin':
            try:
                # Haal de voorkeurstalen op via defaults
                result = subprocess.run(['defaults', 'read', '.GlobalPreferences', 'AppleLanguages'],
                                        capture_output=True, text=True)
                languages = result.stdout.strip()

                # Check voor Nederlands in de talen lijst
                if 'nl' in languages.lower():
                    return 'nl_NL'

            except subprocess.SubprocessError as e:
                print(f"Fout bij ophalen taalinstellingen: {e}")

            try:
                # Alternatieve methode: check de locale settings
                result = subprocess.run(['defaults', 'read', '.GlobalPreferences', 'AppleLocale'], capture_output=True,
                                        text=True)
                locale_setting = result.stdout.strip()

                if locale_setting.startswith('nl'):
                    return 'nl_NL'

            except subprocess.SubprocessError as e:
                print(f"Fout bij ophalen locale instellingen: {e}")

        # Fallback naar locale detectie
        system_lang = locale.getdefaultlocale()[0]

        # Check of de taal ondersteund wordt
        if system_lang in TRANSLATIONS:
            return system_lang

        # Als de taal niet ondersteund wordt maar wel Nederlands is
        if system_lang and system_lang.lower().startswith('nl'):
            return 'nl_NL'

    except locale.Error as e:
        print(f"Locale fout: {e}")
    except (TypeError, IndexError) as e:
        print(f"Fout bij verwerken taalinstellingen: {e}")

    return 'en_US'


def format_size(size_bytes):
    # Converteer bytes naar leesbaar formaat
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def safe_write_file(filepath, content):
    """Schrijft content naar een bestand met goede error handling."""
    # Zorg dat de directory bestaat
    directory = os.path.dirname(filepath)
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
        except (FileNotFoundError, PermissionError, IOError) as e:
            return False, f"Kan directory niet aanmaken: {str(e)}"

    # Schrijf het bestand
    try:
        with open(filepath, 'w') as f:
            f.write(content)
        return True, ""
    except (FileNotFoundError, PermissionError) as e:
        return False, f"Toegangsfout: {str(e)}"
    except IOError as e:
        return False, f"I/O fout: {str(e)}"


class StatusButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setMinimumWidth(150)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("color: #e74c3c; font-weight: bold; padding: 5px;")

    def set_status(self, text, is_ok):
        self.setText(text)
        color = "#2ecc71" if is_ok else "#e74c3c"  # Groen of rood
        self.setStyleSheet(f"color: {color}; font-weight: bold; padding: 5px;")


class StorageIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(5)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Labels voor details
        self.details_label = QLabel()
        self.details_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.progress)
        layout.addWidget(self.details_label)

    def update_storage(self, used_bytes, total_bytes, lang):
        if total_bytes > 0:
            percentage = (used_bytes / total_bytes) * 100
            self.progress.setValue(int(percentage))

            used_str = format_size(used_bytes)
            total_str = format_size(total_bytes)
            free_str = format_size(total_bytes - used_bytes)

            self.details_label.setText(TRANSLATIONS[lang]['storage_used'].format(used_str, total_str, free_str))
        else:
            self.progress.setValue(0)
            self.details_label.setText(TRANSLATIONS[lang]['storage_unavailable'])


class SynologyMaintenanceApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.lang = get_system_language()
        self.setWindowTitle(TRANSLATIONS[self.lang]['window_title'])
        self.setGeometry(100, 100, 400, 300)

        # Configuratie
        self.config = SynologyConfig()
        self.temp_dir = self.config.temp_dir

        # Zorg ervoor dat de temp directory bestaat
        if not os.path.exists(self.temp_dir):
            try:
                os.makedirs(self.temp_dir)
            except (FileNotFoundError, PermissionError, IOError) as e:
                print(f"Fout bij aanmaken temp directory: {e}")

        # Laad environment variables en configuratie
        load_dotenv()
        self.config.load()

        self.synology_client = None

        # Maak de output_text aan voordat init_ui wordt aangeroepen
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)

        self.init_ui()

        # Timer voor status updates
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(30000)  # Update elke 30 seconden

        # Automatisch verbinden als er opgeslagen gegevens zijn
        if self.config.has_saved_credentials():
            self.connect_with_saved_credentials()

    def init_ui(self):
        # Maak central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)  # Voeg wat ruimte toe tussen elementen

        # Connectie groep
        self.conn_group = QGroupBox("")  # Lege titel
        self.conn_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.conn_layout = QVBoxLayout()
        self.conn_layout.setSpacing(5)  # Verminder verticale ruimte

        # Verborgen modus (alleen knop)
        self.hidden_layout = QHBoxLayout()
        self.edit_conn_btn = QPushButton(TRANSLATIONS[self.lang]['edit_credentials'])
        self.edit_conn_btn.clicked.connect(self.show_connection_details)
        self.hidden_layout.addWidget(self.edit_conn_btn)
        self.conn_layout.addLayout(self.hidden_layout)

        # Details widgets
        self.details_widget = QWidget()
        details_layout = QVBoxLayout(self.details_widget)

        # Hostname
        hostname_layout = QHBoxLayout()
        hostname_label = QLabel(TRANSLATIONS[self.lang]['hostname_label'])
        self.hostname_input = QLineEdit()
        hostname_layout.addWidget(hostname_label)
        hostname_layout.addWidget(self.hostname_input)
        details_layout.addLayout(hostname_layout)

        # Username
        username_layout = QHBoxLayout()
        username_label = QLabel(TRANSLATIONS[self.lang]['username_label'])
        self.username_input = QLineEdit()
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_input)
        details_layout.addLayout(username_layout)

        # Password
        password_layout = QHBoxLayout()
        password_label = QLabel(TRANSLATIONS[self.lang]['password_label'])
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        details_layout.addLayout(password_layout)

        # Connect button
        self.connect_btn = QPushButton(TRANSLATIONS[self.lang]['connect_btn'])
        self.connect_btn.clicked.connect(self.handle_connection)
        details_layout.addWidget(self.connect_btn)

        self.conn_layout.addWidget(self.details_widget)
        self.conn_group.setLayout(self.conn_layout)
        main_layout.addWidget(self.conn_group)

        # Status gebied
        status_group = QGroupBox()
        status_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        status_layout = QHBoxLayout()
        status_layout.setSpacing(20)
        status_layout.setContentsMargins(5, 5, 5, 5)

        # Status labels en SSH knop
        self.connection_btn = QPushButton(TRANSLATIONS[self.lang]['disconnect_btn'])
        self.connection_btn.setStyleSheet("color: #e74c3c; font-weight: bold; padding: 5px;")
        self.connection_btn.clicked.connect(self.open_ssh_session)

        self.backup_status = StatusButton(TRANSLATIONS[self.lang]['backup_label'])
        self.backup_status.clicked.connect(lambda: self.open_log_file('backup.log'))

        self.deurbel_status = StatusButton(TRANSLATIONS[self.lang]['doorbell_label'])
        self.deurbel_status.clicked.connect(lambda: self.open_log_file('deurbel_cleanup.log'))

        status_layout.addWidget(self.connection_btn)
        status_layout.addWidget(self.backup_status)
        status_layout.addWidget(self.deurbel_status)

        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)

        # Storage indicator
        storage_group = QGroupBox()
        storage_layout = QVBoxLayout()
        self.storage_indicator = StorageIndicator()
        storage_layout.addWidget(self.storage_indicator)
        storage_group.setLayout(storage_layout)
        main_layout.addWidget(storage_group)

        # Update UI based on saved credentials
        self.update_connection_ui()

    def update_connection_ui(self):
        # Update de UI gebaseerd op opgeslagen gegevens
        if self.config.has_saved_credentials():
            hostname, username, _ = self.config.get_credentials()
            self.hostname_input.setText(hostname)
            self.username_input.setText(username)
            self.details_widget.hide()
            self.edit_conn_btn.show()
        else:
            self.details_widget.show()
            self.edit_conn_btn.hide()

    def show_connection_details(self):
        # Toon de verbindingsgegevens voor bewerking
        self.password_input.clear()  # Wachtwoord moet opnieuw worden ingevoerd
        self.details_widget.show()
        self.edit_conn_btn.hide()

    def connect_with_saved_credentials(self):
        # Verbind met opgeslagen gegevens
        hostname, username, password = self.config.get_credentials()
        if all([hostname, username, password]):
            self.synology_client = SynologyClient(hostname, username, password)
            if self.synology_client.connect():
                self.connect_btn.setText(TRANSLATIONS[self.lang]['disconnect_btn'])
                self.update_status()  # Update status indicators
                return True
        return False

    def handle_connection(self):
        if self.synology_client and self.connect_btn.text() == TRANSLATIONS[self.lang]['disconnect_btn']:
            self.synology_client.disconnect()
            self.synology_client = None
            self.connect_btn.setText(TRANSLATIONS[self.lang]['connect_btn'])
            self.update_status()  # Update status indicators
            return

        hostname = self.hostname_input.text()
        username = self.username_input.text()
        password = self.password_input.text()

        if not all([hostname, username, password]):
            QMessageBox.critical(self, TRANSLATIONS[self.lang]['error_title'],
                                 TRANSLATIONS[self.lang]['error_credentials'])
            return

        self.synology_client = SynologyClient(hostname, username, password)

        if self.synology_client.connect():
            # Sla gegevens op
            success, error_msg = self.config.save_credentials(hostname, username, password)
            if not success:
                QMessageBox.warning(self, TRANSLATIONS[self.lang]['warning_title'],
                                    TRANSLATIONS[self.lang]['warning_save_config'].format(error_msg))

            self.connect_btn.setText(TRANSLATIONS[self.lang]['disconnect_btn'])
            self.update_status()  # Update status indicators
            self.update_connection_ui()  # Verberg details na succesvolle verbinding
        else:
            self.synology_client = None
            QMessageBox.critical(self, TRANSLATIONS[self.lang]['error_title'],
                                 TRANSLATIONS[self.lang]['error_connection'])

    def open_ssh_session(self):
        # Open een SSH sessie in iTerm
        if not self.synology_client or not self.synology_client.is_connected():
            return

        hostname, username, password = self.config.get_credentials()
        if not all([hostname, username, password]):
            return

        # iTerm AppleScript om een nieuwe tab te openen met SSH sessie
        apple_script = '''
        -- Check of iTerm al draait
        tell application "System Events"
            set isRunning to (exists (processes where name is "iTerm"))
        end tell

        -- Start iTerm als deze nog niet draait
        if not isRunning then
            tell application "iTerm"
                activate
                -- Wacht even tot iTerm volledig is opgestart
                delay 1
            end tell
        end if

        tell application "iTerm"
            activate
            -- Check of er een window is, zo niet maak er een
            if not (exists window 1) then
                create window with default profile
                delay 1
            end if

            tell current window
                create tab with default profile
                tell current session
                    -- Start SSH verbinding
                    write text "ssh ''' + username + '@' + hostname + '''"
                    -- Wacht even tot de password prompt verschijnt
                    delay 1.5
                    -- Vul wachtwoord in
                    write text "''' + password + '''"
                end tell
            end tell
        end tell
        '''

        try:
            subprocess.run(['osascript', '-e', apple_script])
        except subprocess.SubprocessError as e:
            print(f"Fout bij uitvoeren Apple Script: {str(e)}")
            QMessageBox.warning(self, TRANSLATIONS[self.lang]['warning_title'],
                                TRANSLATIONS[self.lang]['warning_iterm'].format(f"Subprocess fout: {str(e)}"))
        except FileNotFoundError as e:
            print(f"osascript commando niet gevonden: {str(e)}")
            QMessageBox.warning(self, TRANSLATIONS[self.lang]['warning_title'],
                                TRANSLATIONS[self.lang]['warning_iterm'].format("osascript commando niet gevonden"))

    def update_status(self):
        # Update alle status indicators
        if not self.synology_client or not self.synology_client.is_connected():
            self.connection_btn.setText(TRANSLATIONS[self.lang]['connection_broken'])
            self.connection_btn.setStyleSheet("color: #e74c3c; font-weight: bold; padding: 5px;")
            self.backup_status.set_status(TRANSLATIONS[self.lang]['backup_no_log'], False)
            self.deurbel_status.set_status(TRANSLATIONS[self.lang]['doorbell_no_log'], False)
            self.storage_indicator.update_storage(0, 0, self.lang)
            return

        # Update verbinding status
        self.connection_btn.setText(TRANSLATIONS[self.lang]['open_ssh'])
        self.connection_btn.setStyleSheet("color: #2ecc71; font-weight: bold; padding: 5px;")

        # Update storage, backup en deurbel status
        self.update_storage_status()
        self.update_backup_status()
        self.update_deurbel_status()

    def update_storage_status(self):
        """Update de opslagstatus-indicator met actuele gegevens."""
        try:
            stdout, _ = self.synology_client.execute_command("df -B1 /volume1")
            lines = stdout.strip().split('\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                if len(parts) >= 4:
                    total_bytes = int(parts[1])
                    used_bytes = int(parts[2])
                    self.storage_indicator.update_storage(used_bytes, total_bytes, self.lang)
                    return
        except (ConnectionError, TimeoutError) as e:
            print(f"Verbindingsfout bij storage check: {str(e)}")
        except ValueError as e:
            print(f"Fout bij parsen van storage data: {str(e)}")
        except paramiko.SSHException as e:
            print(f"SSH fout bij storage check: {str(e)}")
        except Exception as e:
            print(f"Onverwachte fout bij storage check: {str(e)}")

        # Als we hier komen, is er iets misgegaan
        self.storage_indicator.update_storage(0, 0, self.lang)

    def get_date_info(self):
        """Haal de datum-informatie op in Engels formaat."""
        try:
            original_locale = locale.getlocale(locale.LC_TIME)
            locale.setlocale(locale.LC_TIME, 'en_US.UTF-8')

            today = datetime.now()
            date_info = {
                'weekday': today.strftime("%a"),
                'month': today.strftime("%b"),
                'day': today.strftime("%d"),
                'year': today.strftime("%Y")
            }

            # Zet locale terug naar de oorspronkelijke waarde
            locale.setlocale(locale.LC_TIME, original_locale)
            return date_info
        except locale.Error as e:
            print(f"Locale fout bij datum formatteren: {str(e)}")
            # Fallback naar Engelse afkortingen
            today = datetime.now()
            return {
                'weekday': today.strftime("%a"),
                'month': today.strftime("%b"),
                'day': today.strftime("%d"),
                'year': today.strftime("%Y")
            }

    def update_backup_status(self):
        """Update de backup status indicator."""
        try:
            # Controleer eerst of het logbestand bestaat
            stdout = self.synology_client.execute_command(
                f"test -f {LOG_PATHS['backup']} && echo 'exists' || echo 'not found'")[0]
            if "not found" in stdout:
                print("Backup logbestand niet gevonden")
                self.backup_status.set_status(TRANSLATIONS[self.lang]['backup_no_log'], False)
                return

            stdout = self.synology_client.execute_command(f"cat {LOG_PATHS['backup']}")[0]

            # Haal de datuminformatie op
            date_info = self.get_date_info()

            # Zoek naar de datum van vandaag in de backup started regel
            try:
                date_pattern = f"###### Backup started: {date_info['weekday']} {date_info['month']} {date_info['day']} \\d{{2}}:\\d{{2}}:\\d{{2}} CET {date_info['year']} ######"
                has_backup_today = bool(re.search(date_pattern, stdout, re.IGNORECASE))

                # Zoek naar "This archive" en controleer of er bytes zijn gebackupt
                has_archive = "This archive:" in stdout and "GB" in stdout

                is_backup_ok = has_backup_today and has_archive

                self.backup_status.set_status(TRANSLATIONS[self.lang]['backup_label'], is_backup_ok)
            except re.error as e:
                print(f"Regex fout bij backup check: {str(e)}")
                self.backup_status.set_status(TRANSLATIONS[self.lang]['backup_error'], False)
        except (ConnectionError, TimeoutError) as e:
            print(f"Verbindingsfout bij backup check: {str(e)}")
            self.backup_status.set_status(TRANSLATIONS[self.lang]['backup_error'], False)
        except paramiko.SSHException as e:
            print(f"SSH fout bij backup check: {str(e)}")
            self.backup_status.set_status(TRANSLATIONS[self.lang]['backup_error'], False)
        except Exception as e:
            print(f"Onverwachte fout bij backup check: {str(e)}")
            self.backup_status.set_status(TRANSLATIONS[self.lang]['backup_error'], False)

    def update_deurbel_status(self):
        """Update de deurbel status indicator."""
        try:
            # Controleer eerst of het logbestand bestaat
            stdout = self.synology_client.execute_command(
                f"test -f {LOG_PATHS['deurbel']} && echo 'exists' || echo 'not found'")[0]
            if "not found" in stdout:
                print("Deurbel logbestand niet gevonden")
                self.deurbel_status.set_status(TRANSLATIONS[self.lang]['doorbell_no_log'], False)
                return

            stdout = self.synology_client.execute_command(f"cat {LOG_PATHS['deurbel']}")[0]
            is_deurbel_ok = "error" not in stdout.lower()
            self.deurbel_status.set_status(TRANSLATIONS[self.lang]['doorbell_label'], is_deurbel_ok)
        except (ConnectionError, TimeoutError) as e:
            print(f"Verbindingsfout bij deurbel check: {str(e)}")
            self.deurbel_status.set_status(TRANSLATIONS[self.lang]['doorbell_no_log'], False)
        except paramiko.SSHException as e:
            print(f"SSH fout bij deurbel check: {str(e)}")
            self.deurbel_status.set_status(TRANSLATIONS[self.lang]['doorbell_no_log'], False)
        except Exception as e:
            print(f"Onverwachte fout bij deurbel check: {str(e)}")
            self.deurbel_status.set_status(TRANSLATIONS[self.lang]['doorbell_no_log'], False)

    def open_log_file(self, log_name):
        # Download en open een logbestand in VSCode
        if not self.synology_client or not self.synology_client.is_connected():
            return

        try:
            # Controleer eerst of VSCode beschikbaar is
            try:
                subprocess.run(['which', 'code'], check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                QMessageBox.warning(
                    self,
                    TRANSLATIONS[self.lang]['warning_title'],
                    "Visual Studio Code (command 'code') is niet beschikbaar. Installeer VSCode en zorg dat het 'code' commando beschikbaar is in het PATH."
                )
                return
            except FileNotFoundError as e:
                QMessageBox.warning(
                    self,
                    TRANSLATIONS[self.lang]['warning_title'],
                    "'which' commando niet gevonden. Dit is onverwacht op een UNIX-achtig systeem."
                )
                return

            # Haal het logbestand op
            log_path = LOG_PATHS.get(log_name.split('.')[0], f"/var/services/homes/Mike/{log_name}")
            
            try:
                stdout, _ = self.synology_client.execute_command(f"cat {log_path}")
            except (ConnectionError, TimeoutError) as e:
                QMessageBox.warning(self, TRANSLATIONS[self.lang]['warning_title'],
                                    f"Verbindingsfout bij ophalen logbestand: {str(e)}")
                return
            except paramiko.SSHException as e:
                QMessageBox.warning(self, TRANSLATIONS[self.lang]['warning_title'],
                                    f"SSH fout bij ophalen logbestand: {str(e)}")
                return
            except Exception as e:
                QMessageBox.warning(self, TRANSLATIONS[self.lang]['warning_title'],
                                    f"Onverwachte fout bij ophalen logbestand: {str(e)}")
                return

            # Sla het bestand lokaal op
            temp_file = os.path.join(self.temp_dir, log_name)

            # Schrijf het bestand naar de tijdelijke locatie
            success, error_msg = safe_write_file(temp_file, stdout)
            if not success:
                QMessageBox.warning(self, TRANSLATIONS[self.lang]['warning_title'], error_msg)
                return

            # Open het bestand in VSCode
            try:
                subprocess.run(['code', temp_file])
            except subprocess.SubprocessError as e:
                QMessageBox.warning(self, TRANSLATIONS[self.lang]['warning_title'],
                                    f"Fout bij starten VSCode: {str(e)}")
            except FileNotFoundError as e:
                QMessageBox.warning(self, TRANSLATIONS[self.lang]['warning_title'],
                                    "VSCode 'code' commando niet gevonden in PATH")
        except Exception as e:
            # Algemene fallback exception die we toch behouden voor onverwachte fouten
            QMessageBox.warning(self, TRANSLATIONS[self.lang]['warning_title'],
                                f"Onverwachte fout: {str(e)}")

    def cleanup_temp_files(self):
        # Verwijder alle tijdelijke bestanden en de tijdelijke directory
        try:
            if os.path.exists(self.temp_dir):
                for file in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, file)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                    except (FileNotFoundError, PermissionError) as e:
                        print(f"Toegangsfout bij verwijderen van {file_path}: {e}")
                    except IOError as e:
                        print(f"I/O fout bij verwijderen van {file_path}: {e}")
                try:
                    os.rmdir(self.temp_dir)
                except (FileNotFoundError, PermissionError) as e:
                    print(f"Toegangsfout bij verwijderen van temp map: {e}")
                except IOError as e:
                    print(f"I/O fout bij verwijderen van temp map: {e}")
        except (FileNotFoundError, PermissionError) as e:
            print(f"Toegangsfout bij cleanup van tijdelijke bestanden: {e}")
        except IOError as e:
            print(f"I/O fout bij cleanup van tijdelijke bestanden: {e}")

    def closeEvent(self, event):
        # Override de closeEvent om cleanup uit te voeren bij het sluiten van het programma
        self.cleanup_temp_files()
        event.accept()

if __name__ == "__main__":
    # Zet de locale op basis van systeem instellingen
    try:
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error as e:
        print(f"Fout bij instellen locale: {e}")
    except Exception as e:
        print(f"Onverwachte fout bij instellen locale: {e}")

    app = QApplication(sys.argv)
    window = SynologyMaintenanceApp()
    window.show()
    sys.exit(app.exec())