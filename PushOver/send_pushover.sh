#!/usr/bin/env bash
#
# send_pushover.sh - Verstuur Pushover notificaties vanuit bash
#
# Beschrijving:
#   Dit script verstuurt notificaties via de Pushover service met behulp van
#   curl. Het ondersteunt alle basis Pushover parameters en handelt fouten af.
#
# Gebruik:
#   ./send_pushover.sh -t TOKEN -u USER -m "Bericht" [opties]
#
# Parameters:
#   -t, --token TOKEN     : Pushover API token (vereist)
#   -u, --user USER       : Pushover user key (vereist)
#   -m, --message MSG     : Bericht van de notificatie (vereist)
#   -T, --title TITLE     : Titel van de notificatie (optioneel)
#   -p, --priority PRIO   : Prioriteit (-2 tot 2, standaard 0)
#   -s, --sound SOUND     : Notificatie geluid (optioneel)
#   -d, --device DEVICE   : Verstuur naar specifiek apparaat (optioneel)
#   -U, --url URL         : URL om toe te voegen aan notificatie (optioneel)
#   -L, --url-title TITLE : Titel voor de URL (optioneel)
#   -h, --help            : Toon deze hulp tekst
#
# Error codes:
#   0 : Succes
#   1 : Ontbrekende vereiste parameters (token, user, message)
#   2 : Ongeldige parameter waarde(n)
#   3 : Fout bij het versturen van de aanvraag (curl fout)
#   4 : Pushover API fout
#   5 : Curl command niet beschikbaar
#
# Voorbeelden:
#   ./send_pushover.sh -t abc123 -u user123 -m "Server restarted" -T "Alert"
#   ./send_pushover.sh --token abc123 --user user123 --message "Backup voltooid" --priority 1
#
# Auteur: Created on 15 maart 2025
#

set -o errexit  # Exit bij fouten
set -o nounset  # Exit bij gebruik van ongedeclareerde variabelen
set -o pipefail # Pipe faalt als één commando faalt

# Functie om help tekst te tonen
show_help() {
    grep '^#' "$0" | grep -v '#!/' | sed 's/^# \?//'
    exit 0
}

# Functie om foutmelding te tonen en te stoppen
die() {
    local code=$1
    shift
    echo "FOUT: $*" >&2
    exit "$code"
}

# Controleer of curl beschikbaar is
command -v curl >/dev/null 2>&1 || die 5 "curl commando niet gevonden. Installeer curl om dit script te gebruiken."

# Standaard waarden
TOKEN=""
USER=""
MESSAGE=""
TITLE=""
PRIORITY="0"
SOUND=""
DEVICE=""
URL=""
URL_TITLE=""
TIMESTAMP=$(date +%s)

# Verwerk command line parameters
while [[ $# -gt 0 ]]; do
    case "$1" in
        -t|--token)
            TOKEN="$2"
            shift 2
            ;;
        -u|--user)
            USER="$2"
            shift 2
            ;;
        -m|--message)
            MESSAGE="$2"
            shift 2
            ;;
        -T|--title)
            TITLE="$2"
            shift 2
            ;;
        -p|--priority)
            PRIORITY="$2"
            if ! [[ "$PRIORITY" =~ ^-?[0-2]$ ]]; then
                die 2 "Ongeldige prioriteit: $PRIORITY. Moet tussen -2 en 2 zijn."
            fi
            shift 2
            ;;
        -s|--sound)
            SOUND="$2"
            shift 2
            ;;
        -d|--device)
            DEVICE="$2"
            shift 2
            ;;
        -U|--url)
            URL="$2"
            shift 2
            ;;
        -L|--url-title)
            URL_TITLE="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            ;;
        *)
            die 2 "Onbekende optie: $1"
            ;;
    esac
done

# Controleer verplichte parameters
[[ -z "$TOKEN" ]] && die 1 "Token (-t, --token) is vereist"
[[ -z "$USER" ]] && die 1 "User key (-u, --user) is vereist"
[[ -z "$MESSAGE" ]] && die 1 "Bericht (-m, --message) is vereist"

# Bouw de curl commando op
CURL_CMD="curl -s -f -X POST https://api.pushover.net/1/messages.json"
CURL_CMD="$CURL_CMD --form-string token=$TOKEN"
CURL_CMD="$CURL_CMD --form-string user=$USER"
CURL_CMD="$CURL_CMD --form-string message=$MESSAGE"
CURL_CMD="$CURL_CMD --form-string timestamp=$TIMESTAMP"

# Voeg optionele parameters toe
[[ -n "$TITLE" ]] && CURL_CMD="$CURL_CMD --form-string title=$TITLE"
[[ -n "$PRIORITY" ]] && CURL_CMD="$CURL_CMD --form-string priority=$PRIORITY"
[[ -n "$SOUND" ]] && CURL_CMD="$CURL_CMD --form-string sound=$SOUND"
[[ -n "$DEVICE" ]] && CURL_CMD="$CURL_CMD --form-string device=$DEVICE"
[[ -n "$URL" ]] && CURL_CMD="$CURL_CMD --form-string url=$URL"
[[ -n "$URL_TITLE" ]] && CURL_CMD="$CURL_CMD --form-string url_title=$URL_TITLE"

# Emergency prioriteit (2) vereist extra parameters
if [[ "$PRIORITY" == "2" ]]; then
    CURL_CMD="$CURL_CMD --form-string retry=30 --form-string expire=3600"
fi

# Voer het commando uit
response=$(eval "$CURL_CMD" 2>&1) || {
    err_code=$?
    if [[ $err_code -eq 22 ]]; then
        # HTTP error van curl (status 40x)
        die 4 "Pushover API fout: $response"
    else
        die 3 "Fout bij het versturen van de aanvraag: $response"
    fi
}

# Controleer of de respons succesvol was
if echo "$response" | grep -q '"status":1'; then
    echo "Notificatie succesvol verstuurd!"
    exit 0
else
    error=$(echo "$response" | grep -o '"errors":\[[^]]*\]' | sed 's/"errors":\["\(.*\)"\]/\1/')
    if [[ -n "$error" ]]; then
        die 4 "Pushover API fout: $error"
    else
        die 4 "Onbekende Pushover API fout"
    fi
fi
