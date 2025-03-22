#! /usr/bin/env python3.9
# (C) Mike Bos 2025
# License: GPL-3.0
# Version: 0.7.1
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
#   --max-woord-lengte N            Maximale lengte van een woord (default: 10)
#   --min-wachtwoord-lengte N       Minimale lengte van een wachtwoord (default: 10)
#   --min-aantal-woorden N          Minimale aantal woorden per wachtwoord (default: 3)
#   --max-aantal-woorden N          Maximale aantal woorden per wachtwoord (default: 4)
#   --speciale-tekens CHARS         Te gebruiken speciale tekens (default: "!@#$%^&*()_+=[]{}:;,./<>?")
#   --url URL                       Aangepaste URL voor de woordenlijst
#   --database DB                   Naam van de SQLite database voor woorden (default: "opentaal_woorden.db")
#   --max-pogingen N                Maximaal aantal pogingen per wachtwoord (default: 20)
#
# Voorbeelden:
#   ./gen_pass.py                   Genereer één wachtwoord
#   ./gen_pass.py -n 5              Genereer 5 wachtwoorden
#   ./gen_pass.py -v                Genereer één wachtwoord met uitgebreide informatie
#   ./gen_pass.py -n 3 -v           Genereer 3 wachtwoorden met uitgebreide informatie
#   ./gen_pass.py --min-woord-lengte 5 --max-woord-lengte 7  Gebruik woorden van 5-7 letters
#   ./gen_pass.py --min-wachtwoord-lengte 12  Maak wachtwoorden van minimaal 12 tekens
#   ./gen_pass.py --speciale-tekens "!@#$%"   Gebruik alleen deze speciale tekens
#   ./gen_pass.py --database "mijn_woorden.db"  Gebruik een aangepaste database naam
#   ./gen_pass.py --max-pogingen 30  Probeer maximaal 30 keer per wachtwoord

import random
import requests
import argparse
import os
import sqlite3

# Default constanten
DEFAULT_OPENTAAL_URL = "https://raw.githubusercontent.com/OpenTaal/opentaal-wordlist/refs/heads/master/wordlist.txt"
DEFAULT_MIN_WOORD_LENGTE = 4
DEFAULT_MAX_WOORD_LENGTE = 10
DEFAULT_MIN_WACHTWOORD_LENGTE = 10
DEFAULT_MIN_AANTAL_WOORDEN = 3
DEFAULT_MAX_AANTAL_WOORDEN = 4
DEFAULT_SPECIALE_TEKENS = "!@#$%^&*()_+=[]{}:;,./<>?"
# Maak het database pad absoluut, relatief aan de locatie van dit script
DEFAULT_DB_NAAM = os.path.join(os.path.dirname(os.path.abspath(__file__)), "opentaal_woorden.db")
DEFAULT_MAX_POGINGEN = 20
POSITIE_OPTIES = ["begin", "midden", "eind", "tussen_woorden"]

def init_database(db_naam):
    """Initialiseer de SQLite database."""
    conn = sqlite3.connect(db_naam)
    cursor = conn.cursor()
    
    # Maak de tabel voor woorden aan als deze nog niet bestaat
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS woorden (
        id INTEGER PRIMARY KEY,
        woord TEXT UNIQUE,
        lengte INTEGER
    )
    ''')
    
    # Maak een index aan op de lengte kolom voor snellere queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_lengte ON woorden(lengte)')
    
    conn.commit()
    return conn

def check_database_exists(db_naam):
    """Controleer of de database bestaat en woorden bevat."""
    if not os.path.exists(db_naam):
        return False
    
    try:
        with sqlite3.connect(db_naam) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM woorden")
            count = cursor.fetchone()[0]
            return count > 0
    except sqlite3.Error:
        return False

def check_and_repair_database(db_naam, verbose=False):
    """Controleer de database integriteit en repareer indien nodig."""
    if not os.path.exists(db_naam):
        return False
    
    try:
        with sqlite3.connect(db_naam) as conn:
            cursor = conn.cursor()
            
            # Controleer de integriteit van de database
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]
            
            if result != "ok":
                if verbose:
                    print(f"Database integriteitscontrole mislukt: {result}")
                    print("Database wordt verwijderd en opnieuw aangemaakt.")
                
                # Sluit de verbinding en verwijder de corrupte database
                conn.close()
                os.remove(db_naam)
                return False
            
            # Controleer of de tabel bestaat en woorden bevat
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='woorden'")
            if not cursor.fetchone():
                if verbose:
                    print("Tabel 'woorden' niet gevonden in database.")
                return False
            
            cursor.execute("SELECT COUNT(*) FROM woorden")
            count = cursor.fetchone()[0]
            
            if verbose and count > 0:
                print(f"Database integriteitscontrole geslaagd. {count} woorden gevonden.")
            
            return count > 0
    except sqlite3.Error as e:
        if verbose:
            print(f"Fout bij het controleren van de database: {e}")
            print("Database wordt verwijderd en opnieuw aangemaakt.")
        
        # Verwijder de corrupte database
        try:
            os.remove(db_naam)
        except OSError:
            pass
        
        return False

def download_and_create_database(url, db_naam, verbose=False):
    """Download de OpenTaal woordenlijst en sla deze op in een SQLite database."""
    try:
        if verbose:
            print("Woordenlijst downloaden...")
        
        response = requests.get(url, timeout=30)  # Voeg timeout toe
        response.raise_for_status()  # Controleer of de download succesvol is
        
        # Haal alle woorden op
        alle_woorden = response.text.splitlines()
        
        if verbose:
            print(f"Aantal woorden gedownload: {len(alle_woorden)}")
            print("Database aanmaken...")
        
        # Initialiseer de database
        conn = init_database(db_naam)
        cursor = conn.cursor()
        
        # Filter woorden en voeg ze toe aan de database
        toegevoegde_woorden = 0
        for woord in alle_woorden:
            if woord.isalpha() and "'" not in woord:  # Alleen letters, geen apostrofs
                try:
                    cursor.execute("INSERT INTO woorden (woord, lengte) VALUES (?, ?)", 
                                  (woord, len(woord)))
                    toegevoegde_woorden += 1
                except sqlite3.IntegrityError:
                    # Woord bestaat al in de database
                    pass
        
        conn.commit()
        
        if verbose:
            print(f"Aantal woorden toegevoegd aan database: {toegevoegde_woorden}")
        
        # Optimaliseer de database na het toevoegen van alle woorden
        optimize_database(conn, verbose)
        
        return conn
    except (requests.exceptions.RequestException, sqlite3.Error) as e:
        error_msg = f"Fout bij het downloaden of verwerken van de woordenlijst: {e}"
        if verbose:
            print(error_msg)
        # Verwijder de mogelijk gedeeltelijk aangemaakte database
        if os.path.exists(db_naam):
            try:
                os.remove(db_naam)
            except OSError:
                if verbose:
                    print(f"Kon database bestand {db_naam} niet verwijderen")
        raise RuntimeError(error_msg)

def get_woorden_from_database(conn, min_woord_lengte, max_woord_lengte, verbose=False):
    """Haal geschikte woorden op uit de database."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT woord FROM woorden WHERE lengte >= ? AND lengte <= ?",
        (min_woord_lengte, max_woord_lengte)
    )
    
    woorden = [row[0] for row in cursor.fetchall()]
    
    if verbose:
        print(f"Aantal geschikte woorden uit database: {len(woorden)}")
    
    return woorden

def optimize_database(conn, verbose=False):
    """Optimaliseer de database voor betere prestaties."""
    if verbose:
        print("Database optimaliseren...")
    
    cursor = conn.cursor()
    cursor.execute("PRAGMA optimize")
    cursor.execute("VACUUM")
    conn.commit()
    
    if verbose:
        print("Database geoptimaliseerd.")
    
    return conn

def download_woordenlijst(url, min_woord_lengte, max_woord_lengte, db_naam=DEFAULT_DB_NAAM, verbose=False):
    """Download de OpenTaal woordenlijst of gebruik de database als deze bestaat."""
    # Controleer of de database al bestaat en geldig is
    if check_and_repair_database(db_naam, verbose):
        if verbose:
            print(f"Bestaande database '{db_naam}' gevonden, deze wordt gebruikt.")
        
        with sqlite3.connect(db_naam) as conn:
            woorden = get_woorden_from_database(conn, min_woord_lengte, max_woord_lengte, verbose)
    else:
        if verbose:
            print(f"Geen database gevonden of database is ongeldig. Nieuwe database wordt aangemaakt.")
        
        with download_and_create_database(url, db_naam, verbose) as conn:
            woorden = get_woorden_from_database(conn, min_woord_lengte, max_woord_lengte, verbose)
    
    return woorden

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
    # Controleer of er voldoende woorden zijn
    if len(woordenlijst) < min_aantal_woorden:
        if verbose:
            print("Niet genoeg woorden in de lijst om aan de minimale woordvereiste te voldoen.")
        return None
    
    # Kies willekeurige Nederlandse woorden
    aantal_woorden = random.randint(min_aantal_woorden, min(max_aantal_woorden, len(woordenlijst)))
    
    if verbose:
        print(f"Aantal woorden voor dit wachtwoord: {aantal_woorden}")
    
    gekozen_woorden = random.sample(woordenlijst, aantal_woorden)
    
    if verbose:
        print(f"Gekozen woorden: {gekozen_woorden}")
    
    # Voeg hoofdletter toe aan het begin van een willekeurig woord
    woord_index = random.randint(0, aantal_woorden - 1)
    gekozen_woorden[woord_index] = gekozen_woorden[woord_index].capitalize()
    
    # Voeg een cijfer toe op een willekeurige positie
    cijfer = str(random.randint(0, 9))
    
    # Kies een speciaal teken
    if not speciale_tekens:
        # Fallback als speciale tekens leeg is (zou niet moeten gebeuren door eerdere validatie)
        speciaal_teken = "!"
    else:
        speciaal_teken = random.choice(speciale_tekens)
    
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
        woord = gekozen_woorden[midden_woord_index]
        midden_index = max(1, len(woord) // 2)  # Zorg ervoor dat midden_index minstens 1 is
        gekozen_woorden[midden_woord_index] = woord[:midden_index] + cijfer + speciaal_teken + woord[midden_index:]
        wachtwoord = "-".join(gekozen_woorden)
    else:  # tussen_woorden
        # Vervang een koppelteken door het cijfer en speciale teken
        if "-" in wachtwoord_basis and aantal_woorden > 1:
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
                                  speciale_tekens=DEFAULT_SPECIALE_TEKENS, verbose=False,
                                  max_pogingen=10):
    """Genereert een opgegeven aantal wachtwoorden."""
    wachtwoorden = []
    for i in range(aantal):
        if verbose:
            print(f"\nWachtwoord {i+1}/{aantal} genereren...")
        
        wachtwoord = genereer_wachtwoord(woordenlijst, min_aantal_woorden, max_aantal_woorden, 
                                        min_wachtwoord_lengte, speciale_tekens, verbose)
        # Als het wachtwoord None is, betekent dit dat er niet genoeg woorden in de lijst zijn
        if wachtwoord is None:
            if verbose:
                print("Wachtwoord generatie mislukt (niet genoeg woorden).")
            continue
            
        pogingen = 1
        
        while not is_veilig_wachtwoord(wachtwoord, min_wachtwoord_lengte, speciale_tekens):
            if pogingen >= max_pogingen:
                if verbose:
                    print(f"Maximaal aantal pogingen ({max_pogingen}) bereikt. Wachtwoord generatie gestopt.")
                break
                
            if verbose:
                print(f"Wachtwoord voldoet niet aan veiligheidseisen. Nieuwe poging ({pogingen+1})...")
            
            wachtwoord = genereer_wachtwoord(woordenlijst, min_aantal_woorden, max_aantal_woorden, 
                                            min_wachtwoord_lengte, speciale_tekens, verbose)
            if wachtwoord is None:
                if verbose:
                    print("Wachtwoord generatie mislukt (niet genoeg woorden).")
                break
            
            pogingen += 1
            
        if wachtwoord is not None and is_veilig_wachtwoord(wachtwoord, min_wachtwoord_lengte, speciale_tekens):
            if verbose:
                print(f"Veilig wachtwoord gegenereerd na {pogingen} poging(en).")
            wachtwoorden.append(wachtwoord)
        elif verbose:
            print("Kon geen veilig wachtwoord genereren, deze wordt overgeslagen.")
    
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
    parser.add_argument('--database', type=str, default=DEFAULT_DB_NAAM,
                        help='Naam van de SQLite database voor woorden')
    parser.add_argument('--max-pogingen', type=int, default=DEFAULT_MAX_POGINGEN,
                        help='Maximaal aantal pogingen per wachtwoord')
    return parser.parse_args()

# Hoofdprogramma
if __name__ == "__main__":
    # Initialize random seed met een veiligere methode
    try:
        random.seed(os.urandom(32))
    except NotImplementedError:
        # Fallback voor systemen zonder os.urandom
        random.seed()
    
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
    if not args.speciale_tekens:
        print("Fout: speciale-tekens mag niet leeg zijn")
        exit(1)
        
    if args.verbose:
        print(f"Genereren van {args.aantal} wachtwoord(en)...")
        print(f"Instellingen:")
        print(f"  - Woord lengte: {args.min_woord_lengte}-{args.max_woord_lengte} tekens")
        print(f"  - Wachtwoord minimale lengte: {args.min_wachtwoord_lengte} tekens")
        print(f"  - Aantal woorden per wachtwoord: {args.min_aantal_woorden}-{args.max_aantal_woorden}")
        print(f"  - Speciale tekens: {args.speciale_tekens}")
        print(f"  - Database: {args.database}")
        print(f"  - Max pogingen per wachtwoord: {args.max_pogingen}")
        print("Woordenlijst ophalen uit database of downloaden...")
    
    # Download en filter de woordenlijst of gebruik de database
    woordenlijst = download_woordenlijst(args.url, args.min_woord_lengte, 
                                         args.max_woord_lengte, args.database, args.verbose)
    
    if len(woordenlijst) < args.min_aantal_woorden:
        print(f"Fout: Slechts {len(woordenlijst)} geschikte woorden gevonden, maar {args.min_aantal_woorden} nodig.")
        print("Probeer andere woord lengtes of een andere woordenlijst.")
        exit(1)

    if len(woordenlijst) < args.max_aantal_woorden and args.verbose:
        print(f"Waarschuwing: Slechts {len(woordenlijst)} geschikte woorden gevonden")
        print(f"Het maximum aantal woorden per wachtwoord wordt aangepast naar {len(woordenlijst)}")

    # Genereer de wachtwoorden
    wachtwoorden = genereer_meerdere_wachtwoorden(
        woordenlijst,
        args.aantal,
        args.min_aantal_woorden,
        args.max_aantal_woorden,
        args.min_wachtwoord_lengte,
        args.speciale_tekens,
        args.verbose,
        max_pogingen=args.max_pogingen
    )

    # Print alleen de resulterende wachtwoorden
    for wachtwoord in wachtwoorden:
        if wachtwoord is not None:
            print(f"{wachtwoord}")
