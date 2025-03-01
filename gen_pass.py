#! /usr/bin/env python3.9
# (C) Mike Bos 2025
# License: GPL-3.0
# Version: 0.1
# uses https://github.com/OpenTaal/opentaal-wordlist
# This script generates a secure password based on Dutch words with hyphens.

import random
import string
import requests

def download_woordenlijst(url):
    """Download de OpenTaal woordenlijst en filter op geschikte woorden."""
    try:
        response = requests.get(url)
        response.raise_for_status()  # Controleer of de download succesvol is
        
        # Haal alle woorden op en zet om naar een lijst
        alle_woorden = response.text.splitlines()
        
        # Filter woorden (verwijder te korte of te lange woorden en woorden met speciale tekens)
        geschikte_woorden = [woord for woord in alle_woorden 
                             if 4 <= len(woord) <= 8 and  # Niet te kort of te lang
                             woord.isalpha() and          # Alleen letters
                             "'" not in woord]            # Geen apostrofs
        
        return geschikte_woorden
    except Exception as e:
        print(f"Fout bij het downloaden van de woordenlijst: {e}")
        # Gebruik een beperkte fallback lijst als het downloaden mislukt
        return [
            "fiets", "tulp", "kaas", "klompen", "windmolen", "stroopwafel", "oranje", 
            "water", "polder", "bloem", "koning", "stamppot", "gracht", "gezellig", 
            "dijk", "markt", "museum", "trein", "strand", "tuin", "school", "brood"
        ]

def is_veilig_wachtwoord(wachtwoord):
    """Controleert of het wachtwoord voldoet aan alle veiligheidseisen."""
    if len(wachtwoord) < 10:
        return False
    if not any(c.isupper() for c in wachtwoord):  # Minstens 1 hoofdletter
        return False
    if not any(c.isdigit() for c in wachtwoord):  # Minstens 1 cijfer
        return False
    if not any(c in string.punctuation for c in wachtwoord):  # Minstens 1 speciaal teken
        return False
    return True

def genereer_wachtwoord(woordenlijst):
    """Genereert een wachtwoord gebaseerd op Nederlandse woorden met koppeltekens."""
    # Kies 3-4 willekeurige Nederlandse woorden
    aantal_woorden = random.randint(3, 4)
    gekozen_woorden = random.sample(woordenlijst, aantal_woorden)
    
    # Voeg hoofdletter toe aan het begin van een willekeurig woord
    woord_index = random.randint(0, aantal_woorden - 1)
    gekozen_woorden[woord_index] = gekozen_woorden[woord_index].capitalize()
    
    # Voeg een cijfer toe op een willekeurige positie
    cijfer = str(random.randint(0, 9))
    
    # Kies een speciaal teken
    speciale_tekens = "!@#$%^&*()_+=[]{}:;,./<>?"
    speciaal_teken = random.choice(speciale_tekens)
    
    # Combineer de woorden met koppeltekens
    wachtwoord_basis = "-".join(gekozen_woorden)
    
    # Beslis waar het cijfer en het speciale teken komen
    positie_opties = ["begin", "midden", "eind", "tussen_woorden"]
    gekozen_positie = random.choice(positie_opties)
    
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
    if len(wachtwoord) < 10:
        # Voeg extra cijfers toe indien nodig
        extra_cijfers = "".join(str(random.randint(0, 9)) for _ in range(10 - len(wachtwoord)))
        wachtwoord += extra_cijfers
    
    return wachtwoord

def genereer_meerdere_wachtwoorden(woordenlijst, aantal=5):
    """Genereert een opgegeven aantal wachtwoorden."""
    wachtwoorden = []
    for _ in range(aantal):
        wachtwoord = genereer_wachtwoord(woordenlijst)
        while not is_veilig_wachtwoord(wachtwoord):
            wachtwoord = genereer_wachtwoord(woordenlijst)
        wachtwoorden.append(wachtwoord)
    return wachtwoorden

# Hoofdprogramma
if __name__ == "__main__":
    # OpenTaal woordenlijst URL
    # Main site: https://github.com/OpenTaal/opentaal-wordlist
    url = "https://raw.githubusercontent.com/OpenTaal/opentaal-wordlist/refs/heads/master/wordlist.txt"
    
    # Download en filter de woordenlijst
    woordenlijst = download_woordenlijst(url)
    
    # Aantal te genereren wachtwoorden
    aantal = 1
    
    wachtwoorden = genereer_meerdere_wachtwoorden(woordenlijst, aantal)
    
    for i, wachtwoord in enumerate(wachtwoorden, 1):
        print(f"{wachtwoord}")
  