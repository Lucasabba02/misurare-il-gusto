# -*- coding: utf-8 -*-
"""
Scraping della classifica settimanale dei libri più venduti su IBS.

Cosa fa lo script, in sintesi:
  1. scarica la pagina della classifica;
  2. per ogni libro ricava posizione, titolo, autore e link alla sua scheda;
  3. visita la scheda di ogni libro e ricava data di uscita, editore e
     descrizione promozionale;
  4. salva tutto in un file CSV, ordinato per posizione in classifica.

Come si usa:
  - installa le librerie (una volta sola, dal terminale):
        pip install requests beautifulsoup4
  - esegui lo script:
        python scraping_ibs.py
"""

# ---------------------------------------------------------------------
# IMPORTAZIONI
# Una "libreria" è codice scritto da altri che possiamo riutilizzare.
# Con "import" la rendiamo disponibile nel nostro script.
# ---------------------------------------------------------------------
import csv                          # per scrivere il file CSV (libreria standard di Python)
import re                           # espressioni regolari: per cercare "schemi" dentro il testo
import time                         # per fare pause tra una richiesta e l'altra
from urllib.parse import urljoin    # per trasformare link relativi in link completi

import requests                     # per scaricare le pagine web
from bs4 import BeautifulSoup       # per "leggere" l'HTML e cercarci dentro


# ---------------------------------------------------------------------
# 1. IMPOSTAZIONI
# Le metto tutte qui in alto: se vuoi cambiare qualcosa, lo fai in un
# punto solo, senza dover cercare nel resto del codice.
# ---------------------------------------------------------------------
URL_CLASSIFICA = "https://www.ibs.it/classifica/libri/1week/sold"
URL_BASE = "https://www.ibs.it"

# Ogni pagina della classifica contiene 40 libri.
# 1 = solo i primi 40; 2 = i primi 80; 3 = i primi 120 (le pagine sono 3).
NUMERO_PAGINE = 3

# Pausa (in secondi) tra una richiesta e l'altra: è buona educazione verso
# il sito e riduce il rischio di essere bloccati.
PAUSA_SECONDI = 1.5

# Nome del file che verrà creato nella stessa cartella dello script.
FILE_CSV = "classifica_ibs.csv"

# Separatore delle colonne. Il punto e virgola ";" fa aprire il file
# correttamente con un doppio clic in Excel italiano.
# Se invece lo leggi con pandas, usa: pd.read_csv("classifica_ibs.csv", sep=";")
SEPARATORE = ";"

# Le "intestazioni" dicono al sito chi siamo. Senza uno User-Agent da browser,
# molti siti rifiutano la richiesta perché sembra quella di un robot.
INTESTAZIONI = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "it-IT,it;q=0.9",
}

# Le colonne del CSV, nell'ordine in cui compariranno.
COLONNE = [
    "posizione",
    "titolo",
    "autore",
    "data_uscita",
    "editore",
    "descrizione",
    "url",          # colonna extra: utile per ricontrollare la fonte
]

# ---------------------------------------------------------------------
# "SCHEMI" DI RICERCA (espressioni regolari)
# Una espressione regolare descrive un "modello" di testo.
# re.compile(...) lo prepara una volta, così lo possiamo riusare.
# ---------------------------------------------------------------------
# Un link a una scheda libro contiene "/e/" seguito da numeri (il codice EAN),
# per esempio: .../e/9788807092220
MODELLO_LINK_LIBRO = re.compile(r"/e/\d+")

# Link alla pagina di un autore, per esempio: /libri/autori/umberto-galimberti
MODELLO_LINK_AUTORE = re.compile(r"/libri/autori/")

# La posizione in classifica appare come "1°", "2°", ..., "40°".
# ^ e $ = il testo deve essere SOLO questo; \d+ = una o più cifre.
MODELLO_POSIZIONE = re.compile(r"^\s*(\d+)\s*[°º]\s*$")

# Nella scheda libro, la descrizione finisce quando incontriamo uno di questi titoli.
MARCATORI_FINE_DESCRIZIONE = {"Argomenti", "Dettagli", "Valutazioni e recensioni"}


# ---------------------------------------------------------------------
# 2. FUNZIONI DI SUPPORTO
# Una "funzione" è un blocco di codice con un nome: si definisce una volta
# con "def" e si può richiamare tutte le volte che serve.
# ---------------------------------------------------------------------
def pulisci_testo(testo):
    """Toglie spazi doppi, a-capo e spazi prima della punteggiatura."""
    testo = re.sub(r"\s+", " ", testo).strip()        # più spazi/a-capo -> uno spazio solo
    testo = re.sub(r"\s+([.,;:!?])", r"\1", testo)    # "parola ." -> "parola."
    return testo


def scarica_pagina(url):
    """Scarica una pagina e restituisce l'HTML già 'interpretato' da BeautifulSoup."""
    risposta = requests.get(url, headers=INTESTAZIONI, timeout=20)
    # Se il sito risponde con un errore (404, 403, 500...) questa riga
    # interrompe il programma con un messaggio chiaro, invece di proseguire
    # con una pagina vuota o sbagliata.
    risposta.raise_for_status()
    # "html.parser" è il lettore HTML incluso in Python: non serve installare altro.
    return BeautifulSoup(risposta.text, "html.parser")


def valore_dopo_etichetta(soup, etichetta):
    """
    Nelle schede libro i dati tecnici sono scritti come coppie
    'etichetta' + 'valore', per esempio:
        Editore:        Feltrinelli
        In commercio dal:   20 ottobre 2026
    Questa funzione trova l'etichetta e restituisce il primo testo che la segue.
    """
    modello = re.compile(r"^\s*" + re.escape(etichetta) + r"\s*:?\s*$", re.IGNORECASE)
    nodo = soup.find(string=modello)          # cerca il testo dell'etichetta
    if nodo is None:
        return ""                             # etichetta assente: restituisco stringa vuota
    # find_all_next scorre i testi che seguono l'etichetta, nell'ordine della pagina.
    for testo in nodo.find_all_next(string=True, limit=10):
        if testo.parent.name in ("script", "style"):
            continue                          # ignoro il codice nascosto nella pagina
        pulito = pulisci_testo(testo)
        if pulito:                            # primo testo non vuoto = il valore cercato
            return pulito
    return ""


def estrai_descrizione(soup):
    """Restituisce il testo della sezione 'Descrizione' della scheda libro."""
    # Cerco il titolo di sezione "Descrizione" (un titolo h2/h3/h4, non il
    # link del menu che porta lo stesso nome).
    titolo = soup.find(["h2", "h3", "h4"], string=re.compile(r"^\s*Descrizione\s*$"))
    if titolo is None:
        return ""

    parti = []
    # Scorro i testi che vengono dopo il titolo, fino al titolo della sezione successiva.
    for testo in titolo.find_all_next(string=True, limit=500):
        if testo.parent.name in ("script", "style", "noscript"):
            continue
        pulito = pulisci_testo(testo)
        if not pulito:
            continue
        if pulito.lower() == "descrizione":
            continue                           # è il titolo della sezione stessa, non il contenuto
        if pulito in MARCATORI_FINE_DESCRIZIONE:
            break                              # fine della descrizione
        if pulito.lower().startswith("leggi di") and len(pulito) < 30:
            continue                           # salto i pulsanti "Leggi di più / meno"
        parti.append(pulito)

    return pulisci_testo(" ".join(parti))


# ---------------------------------------------------------------------
# 3. ESTRAZIONE DEI DATI
# ---------------------------------------------------------------------
def estrai_classifica(soup):
    """
    Dalla pagina della classifica ricava una lista di libri.
    Ogni libro è un dizionario, ad esempio:
        {"posizione": 1, "titolo": "...", "autore": "...", "url": "..."}

    Strategia: nella pagina ogni libro ha scritto "1°", "2°", ecc.
    Parto da quel testo e risalgo nella struttura HTML finché trovo il
    "contenitore" che include anche il link alla scheda del libro.
    Così non dipendo dai nomi delle classi CSS, che il sito può cambiare.
    """
    libri = []
    posizioni_viste = set()                    # per non inserire due volte la stessa posizione

    # Cerco gli elementi il cui testo COMPLESSIVO è una posizione ("1°").
    # Così funziona anche se nell'HTML il numero e il simbolo ° sono in tag separati,
    # per esempio <span>1</span><sup>°</sup>.
    def e_posizione(tag):
        return (tag.name in ("div", "span", "p", "strong", "b", "em", "i", "small", "li")
                and MODELLO_POSIZIONE.match(tag.get_text()) is not None)

    for nodo_posizione in soup.find_all(e_posizione):
        posizione = int(MODELLO_POSIZIONE.match(nodo_posizione.get_text()).group(1))
        if posizione in posizioni_viste:
            continue

        # Risalgo di livello (.parent = elemento "genitore") finché il
        # contenitore contiene un link a una scheda libro.
        scheda = nodo_posizione.parent
        while scheda is not None and scheda.find("a", href=MODELLO_LINK_LIBRO) is None:
            scheda = scheda.parent
        if scheda is None:
            continue

        # Titolo e link: il primo link-libro che contiene del testo.
        # (Il link attorno alla copertina contiene solo un'immagine, quindi ha testo vuoto.)
        titolo, url = "", ""
        for link in scheda.find_all("a", href=MODELLO_LINK_LIBRO):
            testo_link = pulisci_testo(link.get_text())
            if testo_link:
                titolo = testo_link
                url = urljoin(URL_BASE, link["href"])
                break

        # Autori: tutti i link che puntano a pagine-autore.
        # dict.fromkeys elimina i doppioni mantenendo l'ordine.
        autori = [pulisci_testo(a.get_text())
                  for a in scheda.find_all("a", href=MODELLO_LINK_AUTORE)]
        autori = list(dict.fromkeys(a for a in autori if a))

        posizioni_viste.add(posizione)
        libri.append({
            "posizione": posizione,
            "titolo": titolo,
            "autore": "; ".join(autori),       # più autori separati da "; "
            "url": url,
        })

    return libri


def estrai_dettagli(soup):
    """Dalla scheda di un singolo libro ricava data di uscita, editore, descrizione."""
    # Provo più etichette possibili per la data: per i libri non ancora usciti
    # il sito potrebbe usarne una diversa.
    data_uscita = ""
    for etichetta in ("In commercio dal", "Data di uscita", "Data di pubblicazione"):
        data_uscita = valore_dopo_etichetta(soup, etichetta)
        if data_uscita:
            break

    return {
        "data_uscita": data_uscita,
        "editore": valore_dopo_etichetta(soup, "Editore"),
        "descrizione": estrai_descrizione(soup),
    }


# ---------------------------------------------------------------------
# 4. SALVATAGGIO
# ---------------------------------------------------------------------
def salva_csv(libri):
    """Scrive la lista di libri nel file CSV, una riga per libro."""
    # encoding="utf-8-sig": conserva correttamente le lettere accentate in Excel.
    # newline="": evita righe vuote in più su Windows.
    with open(FILE_CSV, "w", newline="", encoding="utf-8-sig") as file:
        scrittore = csv.DictWriter(
            file, fieldnames=COLONNE, delimiter=SEPARATORE, extrasaction="ignore"
        )
        scrittore.writeheader()                # prima riga: i nomi delle colonne
        scrittore.writerows(libri)             # poi un libro per riga


# ---------------------------------------------------------------------
# 5. PROGRAMMA PRINCIPALE
# ---------------------------------------------------------------------
def main():
    # --- Passo 1: la classifica ---
    libri = []
    for numero in range(1, NUMERO_PAGINE + 1):
        url = URL_CLASSIFICA if numero == 1 else f"{URL_CLASSIFICA}?page={numero}"
        print(f"Scarico la pagina {numero} della classifica...")
        soup = scarica_pagina(url)
        libri.extend(estrai_classifica(soup))
        time.sleep(PAUSA_SECONDI)

    if not libri:
        print("Nessun libro trovato: la struttura della pagina potrebbe essere cambiata.")
        # DIAGNOSTICA: salvo l'HTML ricevuto, così puoi aprirlo e vedere cosa ha
        # davvero ricevuto Python (può essere diverso da ciò che vedi nel browser).
        with open("debug_classifica.html", "w", encoding="utf-8") as f:
            f.write(str(soup))
        print("--- Diagnostica ---")
        print("Titolo pagina ricevuta :", soup.title.get_text(strip=True) if soup.title else "(nessuno)")
        print("Caratteri HTML ricevuti:", len(str(soup)))
        print("Link a schede libro    :", len(soup.find_all("a", href=MODELLO_LINK_LIBRO)))
        print("Compare il simbolo '°' :", "°" in soup.get_text())
        print("HTML salvato in debug_classifica.html")
        return

    libri.sort(key=lambda libro: libro["posizione"])   # ordino per posizione
    print(f"Trovati {len(libri)} libri. Ora visito le singole schede...")

    # --- Passo 2: la scheda di ogni libro ---
    for indice, libro in enumerate(libri, start=1):
        print(f"  [{indice}/{len(libri)}] {libro['posizione']}° - {libro['titolo']}")
        try:
            dettagli = estrai_dettagli(scarica_pagina(libro["url"]))
        except requests.RequestException as errore:
            # Se una scheda dà errore, non fermo tutto: lascio i campi vuoti e proseguo.
            print(f"    Problema con questa scheda: {errore}")
            dettagli = {"data_uscita": "", "editore": "", "descrizione": ""}
        libro.update(dettagli)                 # aggiungo i nuovi dati al dizionario del libro
        time.sleep(PAUSA_SECONDI)

    # --- Passo 3: il CSV ---
    salva_csv(libri)
    print(f"Fatto! Dati salvati in {FILE_CSV}")


# Questa riga fa partire main() solo quando esegui direttamente il file
# (e non quando lo importi come libreria in un altro script).
if __name__ == "__main__":
    main()
