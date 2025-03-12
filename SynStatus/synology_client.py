import paramiko
import os
import socket
from dotenv import load_dotenv


class SynologyClient:
    def __init__(self, hostname, username, password=None, key_filename=None, port=22):
        """
        Initialiseer de Synology SSH client

        Args:
            hostname (str): Het IP adres of hostname van het Synology systeem
            username (str): SSH gebruikersnaam
            password (str, optional): SSH wachtwoord
            key_filename (str, optional): Pad naar SSH private key bestand
            port (int): SSH poort nummer (standaard 22)
        """
        self.hostname = hostname
        self.username = username
        self.password = password
        self.key_filename = key_filename
        self.port = port
        self.client = None

    def connect(self):
        # Maak verbinding met het Synology systeem
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            if self.key_filename:
                self.client.connect(
                    self.hostname,
                    port=self.port,
                    username=self.username,
                    key_filename=self.key_filename
                )
            else:
                self.client.connect(
                    self.hostname,
                    port=self.port,
                    username=self.username,
                    password=self.password
                )
            return True
        except paramiko.AuthenticationException as e:
            print(f"Authenticatie mislukt: {str(e)}")
            return False
        except paramiko.SSHException as e:
            print(f"SSH fout bij verbinding: {str(e)}")
            return False
        except socket.gaierror as e:
            print(f"Adres fout: Kan hostname '{self.hostname}' niet vinden: {str(e)}")
            return False
        except socket.error as e:
            print(f"Socket fout bij verbinding: {str(e)}")
            return False
        except ConnectionError as e:
            print(f"Verbindingsfout: {str(e)}")
            return False
        except TimeoutError as e:
            print(f"Timeout bij verbinding: {str(e)}")
            return False
        except FileNotFoundError as e:
            print(f"Key-bestand niet gevonden: {str(e)}")
            return False
        except PermissionError as e:
            print(f"Geen toestemming voor sleutelbestand: {str(e)}")
            return False
        except Exception as e:
            # Fallback voor onverwachte fouten
            print(f"Onverwachte fout bij verbinding: {str(e)}")
            return False

    def is_connected(self):
        # Controleer of er een actieve verbinding is
        if not self.client:
            return False
        try:
            # Voer een simpel command uit om te testen of de verbinding nog werkt
            self.client.exec_command('echo 1')
            return True
        except paramiko.SSHException as e:
            print(f"SSH fout bij verbindingscheck: {str(e)}")
            return False
        except socket.error as e:
            print(f"Socket fout bij verbindingscheck: {str(e)}")
            return False
        except Exception as e:
            print(f"Onverwachte fout bij verbindingscheck: {str(e)}")
            return False

    def execute_command(self, command):
        """
        Voer een command uit op het Synology systeem

        Args:
            command (str): Het command dat uitgevoerd moet worden

        Returns:
            tuple: (stdout, stderr) van het uitgevoerde command
        """
        if not self.client:
            raise ConnectionError("Niet verbonden met Synology systeem")

        try:
            stdin, stdout, stderr = self.client.exec_command(command)
            return stdout.read().decode(), stderr.read().decode()
        except paramiko.SSHException as e:
            raise paramiko.SSHException(f"SSH fout bij uitvoeren command: {str(e)}")
        except socket.error as e:
            raise ConnectionError(f"Verbindingsfout bij uitvoeren command: {str(e)}")
        except UnicodeDecodeError as e:
            raise UnicodeDecodeError(e.encoding, e.object, e.start, e.end,
                                     f"Decodering fout bij lezen command uitvoer: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Onverwachte fout bij uitvoeren command: {str(e)}")

    def get_log_content(self, log_path):
        """
        Lees de inhoud van een logbestand

        Args:
            log_path (str): Pad naar het logbestand

        Returns:
            str: Inhoud van het logbestand
        """
        try:
            command = f"cat {log_path}"
            stdout, stderr = self.execute_command(command)
            if stderr:
                raise FileNotFoundError(f"Fout bij het lezen van log: {stderr}")
            return stdout
        except paramiko.SSHException as e:
            raise paramiko.SSHException(f"SSH fout bij lezen logbestand: {str(e)}")
        except ConnectionError as e:
            raise ConnectionError(f"Verbindingsfout bij lezen logbestand: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Onverwachte fout bij lezen logbestand: {str(e)}")

    def disconnect(self):
        # Verbreek de verbinding met het Synology systeem
        if self.client:
            try:
                self.client.close()
                self.client = None
            except paramiko.SSHException as e:
                print(f"SSH fout bij verbreken verbinding: {str(e)}")
            except Exception as e:
                print(f"Onverwachte fout bij verbreken verbinding: {str(e)}")