#! /usr/bin/env python3.9
# (C) Mike Bos 2025
# License: GPL-3.0
# Version: 0.3
# uses https://github.com/OpenTaal/opentaal-wordlist
# This script generates a secure password based on Dutch words with hyphens.

import random
import string
import requests
import argparse

# Constanten
OPENTAAL_URL = "https://raw.githubusercontent.com/OpenTaal/opentaal-wordlist/refs/heads/master/wordlist.txt"
MIN_WOORD_LENGTE = 4
MAX_WOORD_LENGTE = 8
MIN_WACHTWOORD_LENGTE = 10
MIN_AANTAL_WOORDEN = 3
MAX_AANTAL_WOORDEN = 4
SPECIALE_TEKENS = "!@#$%^&*()_+=[]{}:;,./<>?"
FALLBACK_WOORDENLIJST = [
    "fiets", "tulp", "kaas", "klompen", "windmolen", "stroopwafel", "oranje", 
    "water", "polder", "bloem", "koning", "stamppot", "gracht", "gezellig", 
    "dijk", "markt", "museum", "trein", "strand", "tuin", "school", "brood"
]
POSITIE_OPTIES = ["begin", "midden", "eind", "tussen_woorden"]

def download_woordenlijst(url, verbose=False):
    """Download de OpenTaal woordenlijst en filter op geschikte woorden."""
    try:
        response = requests.get(url)
        response.raise_for_status()  # Controleer of de download succesvol is
        
        # Haal alle woorden op en zet om naar een lijst
        alle_woorden = response.text.splitlines()
        
        # Filter woorden (verwijder te korte of te lange woorden en woorden met speciale tekens)
        geschikte_woorden = [woord for woord in alle_woorden 
                             if MIN_WOORD_LENGTE <= len(woord) <= MAX_WOORD_LENGTE and  # Niet te kort of te lang
                             woord.isalpha() and          # Alleen letters
                             "'" not in woord]            # Geen apostrofs
        
        if verbose:
            print(f"Aantal woorden gedownload: {len(alle_woorden)}")
            print(f"Aantal geschikte woorden: {len(geschikte_woorden)}")
            
        return geschikte_woorden
    except Exception as e:
        if verbose:
            print(f"Fout bij het downloaden van de woordenlijst: {e}")
            print("Gebruik van fallback woordenlijst.")
        # Gebruik een beperkte fallback lijst als het downloaden mislukt
        return FALLBACK_WOORDENLIJST

def is_veilig_wachtwoord(wachtwoord):
    """Controleert of het wachtwoord voldoet aan alle veiligheidseisen."""
    if len(wachtwoord) < MIN_WACHTWOORD_LENGTE:
        return False
    if not any(c.isupper() for c in wachtwoord):  # Minstens 1 hoofdletter
        return False
    if not any(c.isdigit() for c in wachtwoord):  # Minstens 1 cijfer
        return False
    if not any(c in string.punctuation for c in wachtwoord):  # Minstens 1 speciaal teken
        return False
    return True

def genereer_wachtwoord(woordenlijst, verbose=False):
    """Genereert een wachtwoord gebaseerd op Nederlandse woorden met koppeltekens."""
    # Kies 3-4 willekeurige Nederlandse woorden
    aantal_woorden = random.randint(MIN_AANTAL_WOORDEN, MAX_AANTAL_WOORDEN)
    gekozen_woorden = random.sample(woordenlijst, aantal_woorden)
    
    if verbose:
        print(f"Gekozen woorden: {gekozen_woorden}")
    
    # Voeg hoofdletter toe aan het begin van een willekeurig woord
    woord_index = random.randint(0, aantal_woorden - 1)
    gekozen_woorden[woord_index] = gekozen_woorden[woord_index].capitalize()
    
    # Voeg een cijfer toe op een willekeurige positie
    cijfer = str(random.randint(0, 9))
    
    # Kies een speciaal teken
    speciaal_teken = random.choice(SPECIALE_TEKENS)
    
    # Combineer de woorden met koppeltekens
    wachtwoord_basis = "-".join(gekozen_woorden)
    
    if verbose:
        print(f"Basiswachtwoord: {wachtwoord_basis}")
        print(f"Gekozen cijfer: {cijfer}")
        print(f"Gekozen speciaal teken: {speciaal_teken}")
    
    # Beslis waar het cijfer en het speciale teken komen
    gekozen_positie = random.choice(POSITIE_OPTIES)
    
    if verbose:
        print(f"Gekozen positie voor speciale tekens: {gekozen_positie}")
    
    if gekozen_positie == "begin":
        wachtwoord = cijfer + speciaal_teken + wachtwoord_basis
    elif gekozen_positie == "eind":
        wachtwoord = wachtwoord_basis + cijfer + speciaal_teken
    elif gekozen_positie == "midden":
        # Voeg het cijfer en speciale teken in het midden van een willekeurig woord
        midden_woord_index = random.randint(0, aantal_woorden - 1)
        woord_delen = list(wachtwoord_basis)
        midden_index = len(wachtwoord_basis) // 2
        woord_delen.insert(midden_index, cijfer + speciaal_teken)
        wachtwoord = "".join(woord_delen)
    else:  # tussen_woorden
        # Vervang een koppelteken door het cijfer en speciale teken
        if "-" in wachtwoord_basis:
            koppelteken_posities = [i for i, char in enumerate(wachtwoord_basis) if char == '-']
            vervang_positie = random.choice(koppelteken_posities)
            woord_delen = list(wachtwoord_basis)
            woord_delen[vervang_positie] = cijfer + speciaal_teken
            wachtwoord = "".join(woord_delen)
        else:
            # Fallback als er geen koppeltekens zijn
            wachtwoord = wachtwoord_basis + cijfer + speciaal_teken
    
    # Controleer of het wachtwoord lang genoeg is
    if len(wachtwoord) < MIN_WACHTWOORD_LENGTE:
        # Voeg extra cijfers toe indien nodig
        extra_cijfers = "".join(str(random.randint(0, 9)) for _ in range(MIN_WACHTWOORD_LENGTE - len(wachtwoord)))
        wachtwoord += extra_cijfers
        if verbose:
            print(f"Wachtwoord was te kort, extra cijfers toegevoegd: {extra_cijfers}")
    
    if verbose:
        print(f"Gegenereerd wachtwoord: {wachtwoord}")
        print(f"Wachtwoord lengte: {len(wachtwoord)} tekens")
    
    return wachtwoord

def genereer_meerdere_wachtwoorden(woordenlijst, aantal=1, verbose=False):
    """Genereert een opgegeven aantal wachtwoorden."""
    wachtwoorden = []
    for i in range(aantal):
        if verbose:
            print(f"\nWachtwoord {i+1}/{aantal} genereren...")
        
        wachtwoord = genereer_wachtwoord(woordenlijst, verbose)
        pogingen = 1
        
        while not is_veilig_wachtwoord(wachtwoord):
            if verbose:
                print(f"Wachtwoord voldoet niet aan veiligheidseisen. Nieuwe poging ({pogingen+1})...")
            wachtwoord = genereer_wachtwoord(woordenlijst, verbose)
            pogingen += 1
            
        if verbose:
            print(f"Veilig wachtwoord gegenereerd na {pogingen} poging(en).")
            
        wachtwoorden.append(wachtwoord)
    return wachtwoorden

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Genereer veilige wachtwoorden gebaseerd op Nederlandse woorden.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Toon uitgebreide informatie tijdens generatie')
    parser.add_argument('-n', '--aantal', type=int, default=1, help='Aantal te genereren wachtwoorden (default: 1)')
    return parser.parse_args()

# Hoofdprogramma
if __name__ == "__main__":
    # Parse command line arguments
    args = parse_arguments()
    
    if args.verbose:
        print(f"Genereren van {args.aantal} wachtwoord(en)...")
        print("Woordenlijst downloaden en filteren...")
    
    # Download en filter de woordenlijst
    woordenlijst = download_woordenlijst(OPENTAAL_URL, args.verbose)
    
    # Genereer de wachtwoorden
    wachtwoorden = genereer_meerdere_wachtwoorden(woordenlijst, args.aantal, args.verbose)
    
    # Print alleen de resulterende wachtwoorden
    for wachtwoord in wachtwoorden:
        print(f"{wachtwoord}")
