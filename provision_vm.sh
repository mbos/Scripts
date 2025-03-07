#!/bin/bash
# Debian 12 VM Hardening Script
# Dit script voert uitgebreide hardening uit op een Debian VM
# - Kopieert SSH public key naar de opgegeven gebruiker
# - Hardens SSH config (alleen key authentication, geen root login)
# - Configureert firewall (UFW) met basis beveiliging
# - Stelt automatische beveiligingsupdates in
# - Installeert en configureert Fail2ban tegen brute force aanvallen
# - Configureert systeem logging

# Controleert of alle benodigde argumenten zijn opgegeven
if [ "$#" -lt 5 ]; then
    echo "Gebruik: $0 <remote_ip> <username> <password> <ssh_public_key_path> <mike_password>"
    echo "Voorbeeld: $0 192.168.1.100 admin P@ssw0rd ~/.ssh/id_rsa.pub MikeSecurePass123"
    exit 1
fi

REMOTE_IP="$1"
USERNAME="$2"
PASSWORD="$3"
SSH_PUBLIC_KEY_PATH="$4"
MIKE_PASSWORD="$5"

# Controleert of het SSH public key bestand bestaat
if [ ! -f "$SSH_PUBLIC_KEY_PATH" ]; then
    echo "Fout: SSH public key bestand '$SSH_PUBLIC_KEY_PATH' bestaat niet."
    exit 1
fi

# Installeren van benodigde tools als ze nog niet bestaan
if ! command -v sshpass &> /dev/null; then
    echo "sshpass is niet geïnstalleerd. Installeren..."
    
    # Detecteer OS type
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS systeem
        if ! command -v brew &> /dev/null; then
            echo "Homebrew is niet geïnstalleerd. Installeer eerst Homebrew via https://brew.sh/"
            exit 1
        fi
        brew install sshpass
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux systeem
        if command -v apt-get &> /dev/null; then
            # Debian/Ubuntu
            sudo apt-get update && sudo apt-get install -y sshpass
        elif command -v yum &> /dev/null; then
            # CentOS/RHEL/Fedora
            sudo yum install -y sshpass
        elif command -v dnf &> /dev/null; then
            # Nieuwere Fedora versies
            sudo dnf install -y sshpass
        elif command -v pacman &> /dev/null; then
            # Arch Linux
            sudo pacman -S --noconfirm sshpass
        else
            echo "Niet-ondersteund Linux distributie. Installeer sshpass handmatig."
            exit 1
        fi
    else
        echo "Niet-ondersteund besturingssysteem. Installeer sshpass handmatig."
        exit 1
    fi
fi

echo "Beginnen met hardening van de VM op $REMOTE_IP..."

# Controleert of er al een entry is in known_hosts voor deze host en verwijdert deze indien nodig
if ssh-keygen -F "$REMOTE_IP" &>/dev/null; then
    echo "Bestaande host key voor $REMOTE_IP gevonden in known_hosts, wordt verwijderd..."
    ssh-keygen -R "$REMOTE_IP" &>/dev/null
    if [ $? -ne 0 ]; then
        echo "Fout bij verwijderen van host key. Controleer rechten op ~/.ssh/known_hosts"
        exit 1
    fi
    echo "Host key is verwijderd."
fi

# Test of de SSH-verbinding werkt
echo "Testen van SSH-verbinding..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$USERNAME@$REMOTE_IP" "echo 'SSH-verbinding geslaagd.'" &>/dev/null
if [ $? -ne 0 ]; then
    echo "Fout: Kan geen SSH-verbinding maken met $REMOTE_IP"
    echo "Controleer of:"
    echo "  - Het IP-adres correct is"
    echo "  - De opgegeven gebruikersnaam en wachtwoord correct zijn"
    echo "  - De SSH-service draait op de remote machine"
    echo "  - Er geen firewall is die SSH-verkeer blokkeert"
    exit 1
fi

# SSH configuratie hardening
echo "SSH configuratie voorbereiden..."

SSH_CONFIG_HARDENING=$(cat <<EOF
# Aangepaste SSH hardening configuratie
PermitRootLogin no
PubkeyAuthentication yes
PasswordAuthentication no
ChallengeResponseAuthentication no
UsePAM yes
X11Forwarding no
AllowAgentForwarding no
AllowTcpForwarding no
PrintMotd no
AcceptEnv LANG LC_*
# Subsystem sftp is al gedefinieerd in het hoofdconfiguratiebestand
EOF
)

# Kopieert de SSH public key naar de remote server
echo "Kopieren van SSH public key naar de remote server..."
sshpass -p "$PASSWORD" ssh-copy-id -o StrictHostKeyChecking=no -i "$SSH_PUBLIC_KEY_PATH" "$USERNAME@$REMOTE_IP"

SSH_COPY_RESULT=$?
if [ $SSH_COPY_RESULT -ne 0 ]; then
    echo "Fout bij het kopiëren van de SSH key. Foutcode: $SSH_COPY_RESULT"
    echo "Mogelijk oorzaken:"
    echo "  - Het wachtwoord is incorrect"
    echo "  - De SSH-sleutel bestaat al op de server"
    echo "  - Problemen met rechten op de ~/.ssh directory"
    exit 1
fi

# Controleert of de SSH-sleutel correct is gekopieerd
echo "Controleren of de SSH-sleutel correct is gekopieerd..."
if ! ssh -o PasswordAuthentication=no -o BatchMode=yes -o ConnectTimeout=10 "$USERNAME@$REMOTE_IP" "echo 'SSH key auth werkt.'" &>/dev/null; then
    echo "Fout: SSH-sleutel is niet correct geïnstalleerd."
    echo "Probeer het script opnieuw uit te voeren of controleer de sleutel handmatig."
    exit 1
fi

# Maak de gebruiker 'mike' aan op de remote server
echo "Aanmaken van gebruiker 'mike'..."
ssh "$USERNAME@$REMOTE_IP" "
    # Nieuwe gebruiker 'mike' aanmaken
    echo 'Gebruiker mike aanmaken...'
    sudo useradd -m -s /bin/bash mike || { echo 'Fout bij aanmaken van gebruiker mike.'; exit 1; }
    echo \"mike:$MIKE_PASSWORD\" | sudo chpasswd || { echo 'Fout bij instellen van wachtwoord voor mike.'; exit 1; }
    
    # Mike toevoegen aan sudo-groep
    sudo usermod -aG sudo mike || { echo 'Fout bij toevoegen van mike aan sudo groep.'; exit 1; }
    
    # Sudo configuratie zodat mike geen wachtwoord nodig heeft
    echo 'mike ALL=(ALL) NOPASSWD:ALL' | sudo tee /etc/sudoers.d/mike > /dev/null || { echo 'Fout bij configureren van sudoers.'; exit 1; }
    sudo chmod 440 /etc/sudoers.d/mike || { echo 'Fout bij instellen van permissies op sudoers file.'; exit 1; }
    
    # Maak .ssh directory voor mike met juiste permissies
    sudo mkdir -p /home/mike/.ssh || { echo 'Fout bij aanmaken van .ssh directory.'; exit 1; }
    sudo chmod 700 /home/mike/.ssh || { echo 'Fout bij instellen van permissies op .ssh directory.'; exit 1; }
    sudo touch /home/mike/.ssh/authorized_keys || { echo 'Fout bij aanmaken van authorized_keys file.'; exit 1; }
    sudo chmod 600 /home/mike/.ssh/authorized_keys || { echo 'Fout bij instellen van permissies op authorized_keys.'; exit 1; }
    sudo chown -R mike:mike /home/mike/.ssh || { echo 'Fout bij instellen van eigendomsrechten op .ssh directory.'; exit 1; }
" || {
    echo "Fout: Kan gebruiker 'mike' niet aanmaken of configureren."
    exit 1
}

# Kopieert de SSH public key naar de mike gebruiker
echo "Kopieren van SSH public key naar de mike gebruiker..."
# We moeten eerst de key kopiëren naar een temporair bestand op de remote server
echo "Voorbereiden van temporaire map voor SSH key overdracht..."
ssh "$USERNAME@$REMOTE_IP" "mkdir -p /tmp/ssh-setup" || {
    echo "Fout: Kan geen temporaire map aanmaken op de remote server."
    exit 1
}

echo "Kopiëren van SSH key naar temporaire locatie..."
scp -o StrictHostKeyChecking=no "$SSH_PUBLIC_KEY_PATH" "$USERNAME@$REMOTE_IP:/tmp/ssh-setup/authorized_keys" || {
    echo "Fout: Kan de SSH key niet naar de remote server kopiëren."
    exit 1
}

# Nu kunnen we de key naar mike's .ssh directory verplaatsen met juiste permissies
echo "Installeren van SSH key voor mike gebruiker..."
ssh "$USERNAME@$REMOTE_IP" "sudo cp /tmp/ssh-setup/authorized_keys /home/mike/.ssh/ && sudo chown mike:mike /home/mike/.ssh/authorized_keys && sudo chmod 600 /home/mike/.ssh/authorized_keys && sudo rm -rf /tmp/ssh-setup" || {
    echo "Fout: Kan de SSH key niet configureren voor de mike gebruiker."
    echo "Controleer of de remote gebruiker sudo-rechten heeft."
    exit 1
}

# Test de SSH toegang voor mike
echo "Testen van SSH-toegang voor gebruiker mike..."
if ! ssh -o PasswordAuthentication=no -o BatchMode=yes -o ConnectTimeout=10 "mike@$REMOTE_IP" "echo 'SSH key auth werkt voor mike.'" &>/dev/null; then
    echo "Waarschuwing: SSH-sleutel voor mike lijkt niet correct te werken."
    echo "Je kunt misschien inloggen met wachtwoord en het handmatig controleren."
    echo "Het hardening-proces gaat wel door."
else
    echo "SSH key authenticatie voor mike werkt correct."
fi

# Remote commando's uitvoeren om hardening toe te passen
echo "Uitvoeren van hardening maatregelen..."
ssh "$USERNAME@$REMOTE_IP" "
    # Random wachtwoord genereren voor root
    echo 'Root wachtwoord wijzigen naar willekeurige string...'
    ROOT_RANDOM_PASSWORD=\$(openssl rand -base64 32)
    echo \"root:\$ROOT_RANDOM_PASSWORD\" | sudo chpasswd || { echo 'Fout bij wijzigen van root wachtwoord.'; exit 1; }
    echo 'Root wachtwoord is gewijzigd naar een willekeurige string.'
    
    # Backup maken van de originele SSH configuratie
    sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak || { echo 'Fout bij maken van backup van SSH configuratie.'; exit 1; }
    
    # Controleren of de sshd_config.d map bestaat, indien niet aanmaken
    if [ ! -d /etc/ssh/sshd_config.d ]; then
        sudo mkdir -p /etc/ssh/sshd_config.d || { echo 'Fout bij aanmaken van sshd_config.d directory.'; exit 1; }
    fi
    
    # Controleren of 'Include' regel in hoofdconfiguratie staat
    if ! grep -q "Include /etc/ssh/sshd_config.d/\\*.conf" /etc/ssh/sshd_config; then
        echo "Include /etc/ssh/sshd_config.d/*.conf" | sudo tee -a /etc/ssh/sshd_config > /dev/null || { echo 'Fout bij toevoegen van Include regel aan sshd_config.'; exit 1; }
    fi
    
    # Nieuwe SSHD config schrijven
    echo \"$SSH_CONFIG_HARDENING\" | sudo tee /etc/ssh/sshd_config.d/hardening.conf > /dev/null || { echo 'Fout bij schrijven van SSH config.'; exit 1; }
    
    # Test de configuratie vóór het herstarten
    echo 'SSH configuratie controleren...'
    sudo sshd -t || { 
        echo 'Fout gedetecteerd in SSH configuratie. Herstellen van backup...'; 
        sudo cp /etc/ssh/sshd_config.bak /etc/ssh/sshd_config;
        sudo rm -f /etc/ssh/sshd_config.d/hardening.conf;
        exit 1; 
    }
    
    # 1. Firewall (UFW) installeren en configureren
    echo 'Firewall installeren en configureren...'
    sudo apt-get update
    sudo apt-get install -y ufw
    
    # UFW basis regels instellen
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw allow ssh
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    
    # UFW inschakelen met automatische bevestiging
    echo 'y' | sudo ufw enable
    echo 'Firewall is geconfigureerd.'
    
    # 2. Automatische beveiligingsupdates instellen
    echo 'Automatische beveiligingsupdates instellen...'
    sudo apt-get install -y unattended-upgrades apt-listchanges
    
    # Configuratie van unattended-upgrades voor Debian
    sudo tee /etc/apt/apt.conf.d/20auto-upgrades > /dev/null << EOF
APT::Periodic::Update-Package-Lists \"1\";
APT::Periodic::Unattended-Upgrade \"1\";
APT::Periodic::AutocleanInterval \"7\";
APT::Periodic::Download-Upgradeable-Packages \"1\";
EOF
    
    # Debian-specifieke configuratie
    sudo tee -a /etc/apt/apt.conf.d/50unattended-upgrades > /dev/null << EOF
Unattended-Upgrade::Origins-Pattern {
    \"origin=Debian,codename=bookworm,label=Debian-Security\";
    \"origin=Debian,codename=bookworm,label=Debian\";
    \"origin=Debian,codename=bookworm-updates\";
};
Unattended-Upgrade::Remove-Unused-Dependencies \"true\";
Unattended-Upgrade::Automatic-Reboot \"false\";
EOF
    
    # Unattended-upgrades service herstarten
    sudo systemctl restart unattended-upgrades
    echo 'Automatische beveiligingsupdates zijn ingesteld.'
    
    # 3. Fail2ban installeren en configureren
    echo 'Fail2ban installeren en configureren...'
    sudo apt-get install -y fail2ban
    
    # Fail2ban configuratie voor SSH
    sudo tee /etc/fail2ban/jail.local > /dev/null << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
EOF
    
    # Fail2ban herstarten
    sudo systemctl enable fail2ban
    sudo systemctl restart fail2ban
    echo 'Fail2ban is geïnstalleerd en geconfigureerd.'
    
    # 4. Systeem logging configureren
    echo 'Systeem logging configureren...'
    sudo apt-get install -y rsyslog auditd
    
    # Rsyslog configureren voor betere logging
    sudo tee /etc/rsyslog.d/10-hardening.conf > /dev/null << EOF
# Verhoog de logging voor authenticatie events
auth,authpriv.*                 /var/log/auth.log
# Log alle kritieke meldingen naar een apart bestand
*.=crit;*.=alert;*.=emerg       /var/log/critical.log
EOF
    
    # Auditd configureren voor security monitoring
    sudo tee /etc/audit/rules.d/audit.rules > /dev/null << EOF
# Monitoren van systeem aanroepen
-w /etc/passwd -p wa -k identity
-w /etc/group -p wa -k identity
-w /etc/shadow -p wa -k identity
-w /etc/sudoers -p wa -k sudoers
-w /etc/ssh/sshd_config -p wa -k sshd_config

# Monitoren van netwerkveranderingen
-a exit,always -F arch=b64 -S socket -F a0=2 -k network_socket
EOF
    
    # Rsyslog en auditd herstarten
    sudo systemctl restart rsyslog
    sudo systemctl restart auditd
    echo 'Systeem logging is geconfigureerd.'
    
    # 5. Kernel hardening parameters instellen via sysctl
    echo 'Kernel hardening parameters instellen...'
    
    # Sysctl configuratiebestand aanmaken
    sudo tee /etc/sysctl.d/99-security.conf > /dev/null << EOF
# Kernel hardening parameters

# Bescherming tegen IP spoofing
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# Bescherming tegen SYN flood aanvallen
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_synack_retries = 2

# Uitschakelen van IPv4 forwarding
net.ipv4.ip_forward = 0

# Bescherming tegen ICMP redirects
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.default.secure_redirects = 0

# Uitschakelen van ICMP broadcast requests
net.ipv4.icmp_echo_ignore_broadcasts = 1

# Bescherming tegen 'bad error messages'
net.ipv4.icmp_ignore_bogus_error_responses = 1

# Uitschakelen van source routing
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0
net.ipv6.conf.default.accept_source_route = 0

# Uitschakelen van IPv6 router advertisements
net.ipv6.conf.all.accept_ra = 0
net.ipv6.conf.default.accept_ra = 0

# Verhogen van de limiet voor TCP Wqueue memory
net.ipv4.tcp_wmem = 4096 65536 16777216

# Tijd tussen keepalive probes verminderen
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 60
net.ipv4.tcp_keepalive_probes = 5

# ASLR (Address Space Layout Randomization) inschakelen 
kernel.randomize_va_space = 2

# Core dumps beperken
fs.suid_dumpable = 0

# Kernel pointer leakage verhinderen
kernel.kptr_restrict = 1

# dmesg toegang beperken tot root
kernel.dmesg_restrict = 1

# Bescherming tegen hardlinks/symlinks
fs.protected_hardlinks = 1
fs.protected_symlinks = 1

# Kernel messages beperken voor niet-root
kernel.printk = 3 4 1 3

# Bescherming tegen geheugenuitbuiting
vm.mmap_min_addr = 65536

# Swap waarde instellen - minder swappen betekent minder schrijven naar schijf
vm.swappiness = 10
EOF
    
    # Sysctl parameters toepassen
    sudo sysctl -p /etc/sysctl.d/99-security.conf
    echo 'Kernel hardening parameters zijn ingesteld.'
    
    # SSHD parameters toepassen met veiligheidscheck
    echo 'SSH service herstarten...'
    
    # Creëer een beveiligingsvangnet - script dat de ssh config terugzet na 2 minuten
    # tenzij expliciet gestopt. Dit voorkomt dat je buitengesloten raakt als er een probleem is.
    cat > /tmp/ssh_rollback.sh << 'ROLLBACKSCRIPT'
#!/bin/bash
echo "SSH veiligheidsmonitor start. Wacht 2 minuten voor eventuele rollback..."
sleep 120
echo "Uitvoeren van rollback omdat er geen bevestiging is ontvangen..."
cp /etc/ssh/sshd_config.bak /etc/ssh/sshd_config
rm -f /etc/ssh/sshd_config.d/hardening.conf
systemctl restart sshd
echo "Rollback compleet. Originele SSH configuratie is hersteld."
ROLLBACKSCRIPT
    
    sudo chmod +x /tmp/ssh_rollback.sh
    sudo nohup /tmp/ssh_rollback.sh >/tmp/ssh_rollback.log 2>&1 &
    ROLLBACK_PID=$!
    echo "Veiligheids-rollback ingesteld (PID: $ROLLBACK_PID)."
    
    # SSHD herstarten
    sudo systemctl restart sshd
    
    # Als we tot hier komen, annuleer de rollback
    sudo kill $ROLLBACK_PID || true
    sudo rm -f /tmp/ssh_rollback.sh
    
    echo 'SSH hardening is voltooid!'
"

echo "Hardening script is voltooid!"
echo "Je kunt nu inloggen met: ssh mike@$REMOTE_IP"
echo "Let op: Passwordauthenticatie is uitgeschakeld. Je moet je private key gebruiken."
echo "De gebruiker 'mike' heeft sudo-rechten zonder wachtwoord."
echo "Het root-wachtwoord is gewijzigd naar een willekeurige string."

# Extra veiligheidstips tonen
echo ""
echo "Uitgevoerde hardening maatregelen:"
echo "✓ Nieuwe gebruiker 'mike' aangemaakt met sudo-rechten (zonder wachtwoord nodig)"
echo "✓ SSH public key authenticatie ingesteld voor beide gebruikers"
echo "✓ Root wachtwoord veranderd naar willekeurige string"
echo "✓ SSH configuratie beveiligd (geen root login, alleen key auth)"
echo "✓ Firewall (UFW) geïnstalleerd en geconfigureerd"
echo "✓ Automatische beveiligingsupdates ingesteld"
echo "✓ Fail2ban geïnstalleerd tegen brute force aanvallen"
echo "✓ Systeem logging verbeterd (rsyslog + auditd)"
echo "✓ Kernel hardening parameters ingesteld via sysctl"
echo ""
echo "Aanbevolen aanvullende hardening stappen:"
echo "- Niet-essentiële services uitschakelen"
echo "- TLS/SSL configureren voor web services indien van toepassing"
echo "- AppArmor profielen toepassen op kritieke services"