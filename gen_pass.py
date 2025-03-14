#! /usr/bin/env python3.9
# (C) Mike Bos 2025
# License: GPL-3.0
# Version: 0.4
#
# uses https://github.com/OpenTaal/opentaal-wordlist
# This script generates a secure password based on Dutch words with hyphens.
#
# Usage:
#   ./gen_pass.py [options]
#
# Options:
#   -h, --help                      Toon deze help informatie
#   -v, --verbose                   Toon uitgebreide informatie tijdens generatie
#   -n, --aantal N                  Aantal te genereren wachtwoorden (default: 1)
#   --min-woord-lengte N            Minimale lengte van een woord (default: 4)
#   --max-woord-lengte N            Maximale lengte van een woord (default: 8)
#   --min-wachtwoord-lengte N       Minimale lengte van een wachtwoord (default: 10)
#   --min-aantal-woorden N          Minimale aantal woorden per wachtwoord (default: 3)
#   --max-aantal-woorden N          Maximale aantal woorden per wachtwoord (default: 4)
#   --speciale-tekens CHARS         Te gebruiken speciale tekens (default: "!@#$%^&*()_+=[]{}:;,./<>?")
#   --url URL                       Aangepaste URL voor de woordenlijst
#
# Voorbeelden:
#   ./gen_pass.py                   Genereer één wachtwoord
#   ./gen_pass.py -n 5              Genereer 5 wachtwoorden
#   ./gen_pass.py -v                Genereer één wachtwoord met uitgebreide informatie
#   ./gen_pass.py -n 3 -v           Genereer 3 wachtwoorden met uitgebreide informatie
#   ./gen_pass.py --min-woord-lengte 5 --max-woord-lengte 7  Gebruik woorden van 5-7 letters
#   ./gen_pass.py --min-wachtwoord-lengte 12  Maak wachtwoorden van minimaal 12 tekens
#   ./gen_pass.py --speciale-tekens "!@#$%"   Gebruik alleen deze speciale tekens

import random
import string
import requests
import argparse

# Default constanten
DEFAULT_OPENTAAL_URL = "https://raw.githubusercontent.com/OpenTaal/opentaal-wordlist/refs/heads/master/wordlist.txt"
DEFAULT_MIN_WOORD_LENGTE = 4
DEFAULT_MAX_WOORD_LENGTE = 8
DEFAULT_MIN_WACHTWOORD_LENGTE = 10
DEFAULT_MIN_AANTAL_WOORDEN = 3
DEFAULT_MAX_AANTAL_WOORDEN = 4
DEFAULT_SPECIALE_TEKENS = "!@#$%^&*()_+=[]{}:;,./<>?"
FALLBACK_WOORDENLIJST = [
    "fiets", "tulp", "kaas", "klompen", "windmolen", "stroopwafel", "oranje", 
    "water", "polder", "bloem", "koning", "stamppot", "gracht", "gezellig", 
    "dijk", "markt", "museum", "trein", "strand", "tuin", "school", "brood"
]
POSITIE_OPTIES = ["begin", "midden", "eind", "tussen_woorden"]

def download_woordenlijst(url, min_woord_lengte, max_woord_lengte, verbose=False):
    """Download de OpenTaal woordenlijst en filter op geschikte woorden."""
    try:
        response = requests.get(url)
        response.raise_for_status()  # Controleer of de download succesvol is
        
        # Haal alle woorden op en zet om naar een lijst
        alle_woorden = response.text.splitlines()
        
        # Filter woorden (verwijder te korte of te lange woorden en woorden met speciale tekens)
        geschikte_woorden = [woord for woord in alle_woorden 
                             if min_woord_lengte <= len(woord) <= max_woord_lengte and  # Niet te kort of te lang
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
        return [w for w in FALLBACK_WOORDENLIJST 
                if min_woord_lengte <= len(w) <= max_woord_lengte]

def is_veilig_wachtwoord(wachtwoord, min_wachtwoord_lengte, speciale_tekens):
    """Controleert of het wachtwoord voldoet aan alle veiligheidseisen."""
    if len(wachtwoord) < min_wachtwoord_lengte:
        return False
    if not any(c.isupper() for c in wachtwoord):  # Minstens 1 hoofdletter
        return False
    if not any(c.isdigit() for c in wachtwoord):  # Minstens 1 cijfer
        return False
    if not any(c in speciale_tekens for c in wachtwoord):  # Minstens 1 speciaal teken
        return False
    return True

def genereer_wachtwoord(woordenlijst, min_aantal_woorden, max_aantal_woorden, 
                        min_wachtwoord_lengte, speciale_tekens, verbose=False):
    """Genereert een wachtwoord gebaseerd op Nederlandse woorden met koppeltekens."""
    # Kies willekeurige Nederlandse woorden
    aantal_woorden = random.randint(min_aantal_woorden, max_aantal_woorden)
    # Beperk het aantal woorden tot wat beschikbaar is in de woordenlijst
    aantal_woorden = min(aantal_woorden, len(woordenlijst))
    gekozen_woorden = random.sample(woordenlijst, aantal_woorden)
    
    if verbose:
        print(f"Gekozen woorden: {gekozen_woorden}")
    
    # Voeg hoofdletter toe aan het begin van een willekeurig woord
    woord_index = random.randint(0, aantal_woorden - 1)
    gekozen_woorden[woord_index] = gekozen_woorden[woord_index].capitalize()
    
    # Voeg een cijfer toe op een willekeurige positie
    cijfer = str(random.randint(0, 9))
    
    # Kies een speciaal teken
    speciaal_teken = random.choice(speciale_tekens) if speciale_tekens else "!"
    
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
    if len(wachtwoord) < min_wachtwoord_lengte:
        # Voeg extra cijfers toe indien nodig
        extra_cijfers = "".join(str(random.randint(0, 9)) for _ in range(min_wachtwoord_lengte - len(wachtwoord)))
        wachtwoord += extra_cijfers
        if verbose:
            print(f"Wachtwoord was te kort, extra cijfers toegevoegd: {extra_cijfers}")
    
    if verbose:
        print(f"Gegenereerd wachtwoord: {wachtwoord}")
        print(f"Wachtwoord lengte: {len(wachtwoord)} tekens")
    
    return wachtwoord

def genereer_meerdere_wachtwoorden(woordenlijst, aantal=1, min_aantal_woorden=DEFAULT_MIN_AANTAL_WOORDEN, 
                                  max_aantal_woorden=DEFAULT_MAX_AANTAL_WOORDEN, 
                                  min_wachtwoord_lengte=DEFAULT_MIN_WACHTWOORD_LENGTE,
                                  speciale_tekens=DEFAULT_SPECIALE_TEKENS, verbose=False):
    """Genereert een opgegeven aantal wachtwoorden."""
    wachtwoorden = []
    for i in range(aantal):
        if verbose:
            print(f"\nWachtwoord {i+1}/{aantal} genereren...")
        
        wachtwoord = genereer_wachtwoord(woordenlijst, min_aantal_woorden, max_aantal_woorden, 
                                        min_wachtwoord_lengte, speciale_tekens, verbose)
        pogingen = 1
        
        while not is_veilig_wachtwoord(wachtwoord, min_wachtwoord_lengte, speciale_tekens):
            if verbose:
                print(f"Wachtwoord voldoet niet aan veiligheidseisen. Nieuwe poging ({pogingen+1})...")
            wachtwoord = genereer_wachtwoord(woordenlijst, min_aantal_woorden, max_aantal_woorden, 
                                            min_wachtwoord_lengte, speciale_tekens, verbose)
            pogingen += 1
            
        if verbose:
            print(f"Veilig wachtwoord gegenereerd na {pogingen} poging(en).")
            
        wachtwoorden.append(wachtwoord)
    return wachtwoorden

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Genereer veilige wachtwoorden gebaseerd op Nederlandse woorden.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('-v', '--verbose', action='store_true', 
                        help='Toon uitgebreide informatie tijdens generatie')
    parser.add_argument('-n', '--aantal', type=int, default=1, 
                        help='Aantal te genereren wachtwoorden')
    parser.add_argument('--min-woord-lengte', type=int, default=DEFAULT_MIN_WOORD_LENGTE, 
                        help='Minimale lengte van een woord')
    parser.add_argument('--max-woord-lengte', type=int, default=DEFAULT_MAX_WOORD_LENGTE, 
                        help='Maximale lengte van een woord')
    parser.add_argument('--min-wachtwoord-lengte', type=int, default=DEFAULT_MIN_WACHTWOORD_LENGTE, 
                        help='Minimale lengte van een wachtwoord')
    parser.add_argument('--min-aantal-woorden', type=int, default=DEFAULT_MIN_AANTAL_WOORDEN, 
                        help='Minimale aantal woorden per wachtwoord')
    parser.add_argument('--max-aantal-woorden', type=int, default=DEFAULT_MAX_AANTAL_WOORDEN, 
                        help='Maximale aantal woorden per wachtwoord')
    parser.add_argument('--speciale-tekens', type=str, default=DEFAULT_SPECIALE_TEKENS, 
                        help='Te gebruiken speciale tekens')
    parser.add_argument('--url', type=str, default=DEFAULT_OPENTAAL_URL, 
                        help='Aangepaste URL voor de woordenlijst')
    return parser.parse_args()

# Hoofdprogramma
if __name__ == "__main__":
    # Parse command line arguments
    args = parse_arguments()
    
    # Validate arguments
    if args.min_woord_lengte > args.max_woord_lengte:
        print("Fout: min-woord-lengte moet kleiner of gelijk zijn aan max-woord-lengte")
        exit(1)
    if args.min_aantal_woorden > args.max_aantal_woorden:
        print("Fout: min-aantal-woorden moet kleiner of gelijk zijn aan max-aantal-woorden")
        exit(1)
    if args.min_woord_lengte < 1:
        print("Fout: min-woord-lengte moet ten minste 1 zijn")
        exit(1)
    if args.min_wachtwoord_lengte < 6:
        print("Waarschuwing: Een wachtwoord korter dan 6 tekens wordt niet aanbevolen")
        
    if args.verbose:
        print(f"Genereren van {args.aantal} wachtwoord(en)...")
        print(f"Instellingen:")
        print(f"  - Woord lengte: {args.min_woord_lengte}-{args.max_woord_lengte} tekens")
        print(f"  - Wachtwoord minimale lengte: {args.min_wachtwoord_lengte} tekens")
        print(f"  - Aantal woorden per wachtwoord: {args.min_aantal_woorden}-{args.max_aantal_woorden}")
        print(f"  - Speciale tekens: {args.speciale_tekens}")
        print("Woordenlijst downloaden en filteren...")
    
    # Download en filter de woordenlijst
    woordenlijst = download_woordenlijst(args.url, args.min_woord_lengte, 
                                         args.max_woord_lengte, args.verbose)
    
    if len(woordenlijst) < args.max_aantal_woorden:
        if args.verbose:
            print(f"Waarschuwing: Slechts {len(woordenlijst)} geschikte woorden gevonden")
            print("Het aantal woorden per wachtwoord wordt aangepast")
        if len(woordenlijst) == 0:
            print("Fout: Geen geschikte woorden gevonden. Probeer andere woord lengtes.")
            exit(1)
    
    # Genereer de wachtwoorden
    wachtwoorden = genereer_meerdere_wachtwoorden(
        woordenlijst, 
        args.aantal, 
        args.min_aantal_woorden, 
        args.max_aantal_woorden, 
        args.min_wachtwoord_lengte,
        args.speciale_tekens,
        args.verbose
    )
    
    # Print alleen de resulterende wachtwoorden
    for wachtwoord in wachtwoorden:
        print(f"{wachtwoord}")
