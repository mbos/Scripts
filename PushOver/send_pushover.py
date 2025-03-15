#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
send_pushover.py - Stuur een Pushover notificatie

Beschrijving:
    Dit script stuurt een notificatie via de Pushover service. Het ondersteunt
    alle basis Pushover parameters zoals titel, bericht, prioriteit en geluid.

Gebruik:
    ./send_pushover.py --token TOKEN --user USER_KEY --message "Bericht" [opties]

Parameters:
    --token, -t       : Pushover API token (vereist)
    --user, -u        : Pushover user key (vereist)
    --message, -m     : Bericht van de notificatie (vereist)
    --title           : Titel van de notificatie (optioneel)
    --priority, -p    : Prioriteit (-2 tot 2, standaard 0)
    --sound, -s       : Notificatie geluid (optioneel)
    --device, -d      : Verstuur naar specifiek apparaat (optioneel)
    --url             : URL om toe te voegen aan notificatie (optioneel)
    --url-title       : Titel voor de URL (optioneel)
    --timestamp       : Unix timestamp (optioneel, standaard huidige tijd)
    --help, -h        : Toon deze hulp tekst

Error codes:
    0 : Succes
    1 : Ontbrekende vereiste parameters (token, user, message)
    2 : Ongeldige parameter waarde(n)
    3 : Fout bij het versturen van de aanvraag
    4 : Pushover API fout
    5 : Onverwachte fout

Voorbeelden:
    ./send_pushover.py --token abc123 --user user123 --message "Server restart" --title "Alert"
    ./send_pushover.py -t abc123 -u user123 -m "Server restart" -p 1 -s "cosmic"

Auteur: Created on 15 maart 2025
"""

import argparse
import sys
import time
import requests
import json

def parse_arguments():
    """Verwerk command line argumenten."""
    parser = argparse.ArgumentParser(
        description='Stuur een Pushover notificatie',
        formatter_class=argparse.RawTextHelpFormatter)
        
    # Verplichte parameters
    parser.add_argument('--token', '-t', required=True, help='Pushover API token')
    parser.add_argument('--user', '-u', required=True, help='Pushover gebruiker key')
    parser.add_argument('--message', '-m', required=True, help='Bericht inhoud')
    
    # Optionele parameters
    parser.add_argument('--title', help='Titel van de notificatie')
    parser.add_argument('--priority', '-p', type=int, default=0, 
                       choices=[-2, -1, 0, 1, 2], help='Prioriteit (-2 tot 2, standaard 0)')
    parser.add_argument('--sound', '-s', help='Notificatie geluid')
    parser.add_argument('--device', '-d', help='Verstuur naar specifiek apparaat')
    parser.add_argument('--url', help='URL om toe te voegen aan notificatie')
    parser.add_argument('--url-title', help='Titel voor de URL')
    parser.add_argument('--timestamp', type=int, help='Unix timestamp (standaard huidige tijd)')
    
    return parser.parse_args()

def send_pushover_notification(params):
    """
    Stuur een Pushover notificatie met de gegeven parameters.
    
    Args:
        params (dict): De parameters voor het Pushover API verzoek
        
    Returns:
        tuple: (Success Boolean, Response Object)
    """
    try:
        response = requests.post(
            "https://api.pushover.net/1/messages.json", 
            data=params, 
            timeout=10
        )
        
        if response.status_code != 200:
            response_data = response.json()
            error_msg = response_data.get('errors', ['Onbekende API fout'])[0]
            print(f"Pushover API fout: {error_msg}", file=sys.stderr)
            return False, response
        
        return True, response
        
    except requests.exceptions.RequestException as e:
        print(f"Fout bij het versturen van de aanvraag: {e}", file=sys.stderr)
        return False, None
    except json.JSONDecodeError:
        print("Fout bij het verwerken van de API response", file=sys.stderr)
        return False, None

def main():
    """Hoofdfunctie van het script."""
    try:
        args = parse_arguments()
        
        # Bouw de parameters voor de API aanvraag
        params = {
            'token': args.token,
            'user': args.user,
            'message': args.message,
        }
        
        # Voeg optionele parameters toe als ze aanwezig zijn
        if args.title:
            params['title'] = args.title
        if args.priority is not None:
            params['priority'] = args.priority
        if args.sound:
            params['sound'] = args.sound
        if args.device:
            params['device'] = args.device
        if args.url:
            params['url'] = args.url
        if args.url_title:
            params['url_title'] = args.url_title
        if args.timestamp:
            params['timestamp'] = args.timestamp
        else:
            params['timestamp'] = int(time.time())
        
        # Valideer prioriteit (dit wordt ook door argparse gedaan maar voor zekerheid)
        if args.priority not in [-2, -1, 0, 1, 2]:
            print("Ongeldige prioriteit. Moet tussen -2 en 2 zijn.", file=sys.stderr)
            return 2
            
        # Stuur de notificatie
        success, response = send_pushover_notification(params)
        
        if success:
            print("Notificatie succesvol verstuurd!")
            return 0
        elif response:
            return 4  # Pushover API fout
        else:
            return 3  # Verzoek fout
            
    except Exception as e:
        print(f"Onverwachte fout: {e}", file=sys.stderr)
        return 5

if __name__ == "__main__":
    sys.exit(main())
