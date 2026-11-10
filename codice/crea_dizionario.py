# -*- coding: utf-8 -*-
"""
Genera il file dizionario.json con i termini delle cinque categorie:
  1. premi
  2. novita
  3. coinvolgimento_lettore
  4. valutativi_positivi
  5. citazioni_critiche_giornalisti

Lo script fa solo questo: non legge altri file e non analizza testi.
Per ogni categoria ci sono due liste:
  - *_FORNITI : i termini che mi hai dato (invariati);
  - *_AGGIUNTI: i termini che ho aggiunto perché coerenti con la categoria.
Nel JSON finale le due liste sono unite (prima i tuoi, poi i miei, senza doppioni).
Per togliere un'aggiunta che non ti convince basta cancellarla dalla lista *_AGGIUNTI
e rilanciare lo script.

Uso:
    python crea_dizionario.py
"""

import json   # libreria standard di Python per scrivere file JSON

FILE_USCITA = "dizionario.json"


# ---------------------------------------------------------------------
# 1. PREMI
# ---------------------------------------------------------------------
PREMI_FORNITI = [
    "premio", "premi", "premiata", "premiato", "premiati", "premiate",
    "vincitore", "vincitrice", "vincitori", "vincitrici",
    "finalista", "finalisti", "finaliste",
    "candidato", "candidata", "candidati", "candidate",
    "selezionato", "selezionata", "selezionati", "selezionate",
    "successo", "bestseller", "best seller",
    "libro dell'anno", "romanzo dell'anno",
]

PREMI_AGGIUNTI = [
    # tipi di premio e principali premi letterari
    "premio letterario", "premi letterari", "premio internazionale", "premio speciale",
    "premio strega", "premio campiello", "premio viareggio", "premio bancarella",
    "premio nobel", "premio pulitzer", "premio goncourt", "premio booker",
    "booker prize", "nobel", "pulitzer", "goncourt",
    # riconoscimenti e selezioni
    "riconoscimento", "riconoscimenti", "semifinalista", "semifinalisti",
    "shortlist", "longlist", "cinquina", "in lizza", "menzione speciale",
    # successo commerciale (nella tua lista rientrano già "successo" e "bestseller")
    "best-seller", "bestsellers", "caso editoriale", "milioni di copie",
    "in vetta alle classifiche", "in testa alle classifiche", "primo in classifica",
]


# ---------------------------------------------------------------------
# 2. ELEMENTI DI NOVITÀ
# ---------------------------------------------------------------------
NOVITA_FORNITI = [
    "nuovo", "nuova", "nuovi", "nuove", "novità",
    "atteso", "attesa", "attesissimo", "attesissima",
    "fenomeno", "appena uscito", "appena pubblicato",
    "nuova edizione", "nuovo romanzo",
]

NOVITA_AGGIUNTI = [
    "nuovissimo", "nuovissima", "nuovissimi", "nuovissime",
    "attesi", "attesissimi", "attesissime", "tanto atteso", "tanto attesa",
    "inedito", "inedita", "inediti", "inedite",
    "ultimo romanzo", "ultimo libro", "ultima fatica", "ultimo capitolo",
    "nuovo libro", "nuovo capitolo", "nuova uscita", "nuova traduzione", "nuova veste",
    "novità editoriale", "novità editoriali", "novità assoluta",
    "in libreria", "arriva in libreria", "torna in libreria", "in uscita", "appena arrivato",
    "debutto", "esordio",
]


# ---------------------------------------------------------------------
# 3. COINVOLGIMENTO DEL LETTORE
# ---------------------------------------------------------------------
COINVOLGIMENTO_FORNITI = [
    "da leggere", "da non perdere", "da scoprire", "da amare", "da divorare",
    "ti farà", "vi farà", "scoprirete", "immergersi", "perdersi",
]

COINVOLGIMENTO_AGGIUNTI = [
    # rivolgersi direttamente al lettore
    "scoprirai", "se amate", "se ami", "se avete amato", "se hai amato",
    "per chi ama", "per chi ha amato",
    # promesse di coinvolgimento (seconda persona)
    "ti conquisterà", "vi conquisterà", "ti catturerà", "vi catturerà",
    "ti appassionerà", "vi appassionerà", "ti emozionerà", "vi emozionerà",
    "ti sorprenderà", "vi sorprenderà", "ti travolgerà", "vi travolgerà",
    "ti terrà incollato", "vi terrà incollati",
    "ti lascerà senza fiato", "vi lascerà senza fiato", "senza fiato",
    "non riuscirai a smettere", "non riuscirete a smettere",
    "non riuscirai a staccarti", "non riuscirete a staccarvi",
    "tutto d'un fiato",
    # inviti
    "lasciatevi", "lasciarsi trasportare", "lasciarsi catturare", "lasciarsi rapire",
    "immergetevi", "immergiti", "perdetevi",
    "da non lasciarsi sfuggire", "da non lasciarsi scappare",
    "da regalare", "da consigliare", "da gustare", "da assaporare",
]


# ---------------------------------------------------------------------
# 4. VALUTATIVI POSITIVI
# ---------------------------------------------------------------------
VALUTATIVI_FORNITI = [
    "capolavoro", "capolavori", "straordinario", "straordinaria", "magistrale",
    "avvincente", "sorprendente", "indimenticabile", "brillante",
    "meraviglioso", "meravigliosa", "emozionante", "incredibile", "favoloso",
    "magnifico", "bellissimo", "bellissima", "coinvolgente", "appassionante",
    "imperdibile",
]

VALUTATIVI_AGGIUNTI = [
    # forme che mancano per i tuoi termini (plurali e femminili)
    "straordinari", "straordinarie", "magistrali", "avvincenti", "sorprendenti",
    "indimenticabili", "brillanti", "meravigliosi", "meravigliose", "emozionanti",
    "incredibili", "favolosa", "favolosi", "favolose", "magnifica", "magnifici",
    "magnifiche", "bellissimi", "bellissime", "coinvolgenti", "appassionanti",
    "imperdibili",
    # altri aggettivi di valutazione positiva
    "eccezionale", "eccezionali", "eccellente", "eccellenti",
    "splendido", "splendida", "splendidi", "splendide",
    "stupendo", "stupenda", "stupendi", "stupende",
    "sublime", "sublimi", "formidabile", "formidabili",
    "memorabile", "memorabili", "spettacolare", "spettacolari",
    "affascinante", "affascinanti", "toccante", "toccanti",
    "commovente", "commoventi", "travolgente", "travolgenti",
    "irresistibile", "irresistibili", "entusiasmante", "entusiasmanti",
    "esilarante", "esilaranti", "ammaliante", "ammalianti",
    "intramontabile", "intramontabili", "mozzafiato", "senza pari",
]


# ---------------------------------------------------------------------
# 5. CITAZIONI E CRITICHE DI GIORNALISTI (tutta proposta mia)
# Divisa in due parti, perché vanno cercate in modo diverso:
#   - testate: nomi propri; vanno cercati rispettando maiuscole/minuscole
#     ("La Stampa" è il giornale, "la stampa" no);
#   - espressioni: frasi di critica o recensione, in minuscolo.
# Non ho inserito "giornalista", "secondo", "scrive" e testate che sono anche parole
# comuni (Libero, Domani, Internazionale): scatterebbero troppo spesso a vuoto.
# ---------------------------------------------------------------------
TESTATE = [
    # italiane
    "Corriere della Sera", "la Repubblica", "La Repubblica", "La Stampa",
    "Il Sole 24 Ore", "Il Messaggero", "Il Fatto Quotidiano", "Il Foglio",
    "L'Espresso", "L'Unità", "Il Manifesto", "Avvenire", "Famiglia Cristiana",
    "La Lettura", "TuttoLibri", "Il Venerdì", "Vanity Fair", "Io Donna",
    "Il Post", "Wired", "Rolling Stone", "Panorama", "Il Resto del Carlino",
    "Il Gazzettino", "Il Secolo XIX", "Il Riformista", "La Gazzetta dello Sport",
    # straniere
    "The New York Times", "New York Times", "The Guardian", "The Times",
    "The Sunday Times", "The Washington Post", "The Independent", "The Telegraph",
    "The Observer", "The Economist", "The New Yorker", "Financial Times",
    "Los Angeles Times", "USA Today", "The Wall Street Journal", "Wall Street Journal",
    "Publishers Weekly", "Kirkus Reviews", "Kirkus", "Booklist", "Library Journal",
    "Entertainment Weekly", "Daily Mail", "Time Magazine",
    "Le Monde", "Le Figaro", "Libération", "L'Express", "El País",
    "Der Spiegel", "Die Zeit", "Süddeutsche Zeitung", "Frankfurter Allgemeine",
]

ESPRESSIONI_CRITICA = [
    "acclamato dalla critica", "acclamata dalla critica",
    "acclamato dalla stampa", "acclamata dalla stampa",
    "elogiato dalla critica", "elogiata dalla critica",
    "lodato dalla critica", "lodata dalla critica",
    "celebrato dalla critica", "celebrata dalla critica",
    "amato dalla critica", "amata dalla critica",
    "applaudito dalla critica", "applaudita dalla critica",
    "apprezzato dalla critica", "apprezzata dalla critica",
    "elogiato da", "elogiata da", "lodato da", "lodata da",
    "consenso della critica", "consensi della critica",
    "plauso della critica", "plauso dei critici",
    "successo di critica", "successo di pubblico e di critica",
    "la critica internazionale", "dalla critica internazionale",
    "la stampa internazionale", "stampa internazionale",
    "secondo la critica", "secondo i critici", "secondo la stampa",
    "i critici", "critici letterari", "i giornali", "recensori",
    "recensione", "recensioni", "recensito", "recensita",
    "salutato come", "salutata come",
    "è stato definito", "è stata definita", "hanno definito", "ha definito",
    "definito dal", "definita dal", "definito dalla", "definita dalla",
    "definito da", "definita da", "definito dai", "definita dai",
]


# ---------------------------------------------------------------------
# COSTRUZIONE DEL DIZIONARIO
# ---------------------------------------------------------------------
def unisci(*liste):
    """Unisce le liste mantenendo l'ordine e togliendo i doppioni."""
    risultato = []
    for lista in liste:
        for termine in lista:
            if termine not in risultato:
                risultato.append(termine)
    return risultato


DIZIONARIO = {
    "premi": unisci(PREMI_FORNITI, PREMI_AGGIUNTI),
    "novita": unisci(NOVITA_FORNITI, NOVITA_AGGIUNTI),
    "coinvolgimento_lettore": unisci(COINVOLGIMENTO_FORNITI, COINVOLGIMENTO_AGGIUNTI),
    "valutativi_positivi": unisci(VALUTATIVI_FORNITI, VALUTATIVI_AGGIUNTI),
    "citazioni_critiche_giornalisti": {
        "testate": unisci(TESTATE),
        "espressioni": unisci(ESPRESSIONI_CRITICA),
    },
}


def main():
    # ensure_ascii=False mantiene le lettere accentate; indent=2 rende il file leggibile.
    with open(FILE_USCITA, "w", encoding="utf-8") as file:
        json.dump(DIZIONARIO, file, ensure_ascii=False, indent=2)

    print(f"Dizionario salvato in {FILE_USCITA}")
    for categoria, contenuto in DIZIONARIO.items():
        if isinstance(contenuto, dict):
            parti = ", ".join(f"{nome}: {len(termini)}" for nome, termini in contenuto.items())
            print(f"  {categoria}: {parti}")
        else:
            print(f"  {categoria}: {len(contenuto)} termini")


if __name__ == "__main__":
    main()