# -*- coding: utf-8 -*-
"""
Arricchimento del CSV della classifica IBS con i premi letterari degli autori.

Per ogni autore presente in "classifica_ibs.csv" lo script:
  1. costruisce l'indirizzo della sua pagina su it.wikipedia.org;
  2. scarica la pagina (se non esiste o la richiesta fallisce, registra
     l'autore con i campi a null e passa al successivo);
     SE la pagina italiana non esiste o non contiene premi, prova anche la
     pagina di en.wikipedia.org (stesso procedimento, stessa pausa di 1 secondo);
  3. cerca la sezione dei premi ("Riconoscimenti", "Premi", ...) ed estrae
     nome del premio e anno di vittoria;
  4. salva tutto in "premi_arricchiti.json";
  5. stampa un breve sommario finale.

Come si usa (stessa cartella di classifica_ibs.csv):
    python premi_wikipedia.py
"""

# ---------------------------------------------------------------------
# IMPORTAZIONI
# ---------------------------------------------------------------------
import copy                           # per copiare un pezzo di pagina senza modificare l'originale
import csv                            # lettura del CSV
import json                           # scrittura del file JSON
import re                             # espressioni regolari (ricerca di "schemi" nel testo)
import time                           # pause tra una richiesta e l'altra
from urllib.parse import quote        # per trasformare accenti e apostrofi nel formato degli URL

import requests                       # scarica le pagine web
from bs4 import BeautifulSoup         # legge e interroga l'HTML


# ---------------------------------------------------------------------
# 1. IMPOSTAZIONI
# ---------------------------------------------------------------------
FILE_CSV_INPUT = "classifica_ibs.csv"          # il file prodotto da scraping_ibs.py
FILE_JSON_OUTPUT = "premi_arricchiti.json"     # il file che verrà creato
SEPARATORE_CSV = ";"                           # lo stesso usato nel CSV di input

PREFISSO_WIKIPEDIA = "https://it.wikipedia.org/wiki/"
PAUSA_SECONDI = 1                              # pausa tra una richiesta e la successiva

# Wikipedia chiede che chi scarica pagine con un programma si presenti con un
# User-Agent descrittivo e un recapito. SOSTITUISCI l'indirizzo con il tuo.
INTESTAZIONI = {
    "User-Agent": "RicercaUmanistica/1.0 (progetto universitario di analisi dati; "
                  "contatto: tua.email@example.com)",
    "Accept-Language": "it-IT,it;q=0.9",
}

# Titoli di sezione in cui Wikipedia italiana elenca di solito i premi (in minuscolo).
TITOLI_SEZIONE_PREMI = {
    "riconoscimenti",
    "premi",
    "premi e riconoscimenti",
    "riconoscimenti e premi",
    "premi letterari",
    "premi e onorificenze",
    "riconoscimenti e onorificenze",
}

# ---------------------------------------------------------------------
# "SCHEMI" DI RICERCA (espressioni regolari)
# ---------------------------------------------------------------------
# Un anno tra il 1900 e il 2099.
RE_ANNO = re.compile(r"\b(19\d{2}|20\d{2})\b")

# Il punto in cui, dopo il nome del premio, inizia il titolo dell'opera:
# "Premio Strega 2019 per M. Il figlio del secolo" -> si taglia prima di " per M."
# (si taglia solo se dopo "per/con" c'è una maiuscola o un virgolettato, così
# "Premio Nazionale per la Traduzione" non viene spezzato).
RE_PER_CON = re.compile(r"\s+(?:per|con|grazie a)\s+(?=[\"«“‘'A-ZÀ-Ý])")

# Separatori che chiudono il nome del premio: due punti, virgola, parentesi, trattino con spazi.
RE_SEPARATORI = re.compile(r"\s[–—-]\s|[:;,(\[]")

# Voci che NON sono vittorie (candidature, finali...): vengono scartate.
RE_NON_VITTORIA = re.compile(
    r"\b(?:finalist\w*|candidat\w*|nominat\w*|nomination|shortlist|cinquina|"
    r"selezionat\w*|menzion\w*|segnalat\w*|secondo posto|terzo posto)\b",
    re.IGNORECASE,
)

# Onorificenze di Stato: non sono premi letterari.
RE_ONORIFICENZA = re.compile(
    r"^(?:Cavaliere|Commendatore|Grande Ufficiale|Ufficiale)\b|"
    r"\bOrdine (?:al merito|della Stella|equestre)",
    re.IGNORECASE,
)

# La parola "premio" (anche minuscola, anche in mezzo a una frase).
RE_PAROLA_PREMIO = re.compile(r"\bpremio\b", re.IGNORECASE)

# Parole minuscole che possono comparire DENTRO il nome di un premio, ma solo se
# seguite da una parola con la maiuscola ("Premio Città di Palermo",
# "Premio Nazionale per la Traduzione").
CONNETTIVI = {"di", "del", "dello", "della", "dei", "degli", "delle", "de",
              "la", "il", "lo", "le", "l'", "per"}

# Qualificatori minuscoli che fanno parte del nome ("Premio Campiello opera prima").
# Ogni voce è una sequenza di parole. Puoi aggiungerne altri.
QUALIFICATORI_MINUSCOLI = [
    ("opera", "prima"), ("opera", "seconda"), ("alla", "carriera"),
    ("della", "critica"), ("della", "giuria"),
    ("giovani",), ("speciale",), ("internazionale",), ("nazionale",), ("letterario",),
]

# Ambiti che compaiono dopo "di" nel nome di un premio ("Premio internazionale di giornalismo").
# Valgono solo nella forma "di <ambito>" (o del/della/dello).
AMBITI_MINUSCOLI = {"giornalismo", "poesia", "narrativa", "saggistica", "letteratura", "teatro",
                    "cultura", "critica", "traduzione", "storia", "filosofia", "scienza",
                    "arte", "musica", "cinema", "pace", "giustizia"}

# Elisioni come "d'Oro", "dell'Aquila": iniziano con la minuscola ma fanno parte del nome.
RE_ELISIONE = re.compile(r"^(?:d|dell|dall|all|nell|sull)['’]\w+", re.IGNORECASE)

# Frasi del tipo "Nel 2019 riceve il ..." / "vince lo ...": servono per i premi
# che NON contengono la parola "premio" (es. "Nel 1990 vince la Palma d'oro").
RE_VERBO_ASSEGNAZIONE = re.compile(
    r"^.*?\b(?:riceve|ricevette|ricevendo|ha ricevuto|vince|vinse|ha vinto|ottiene|"
    r"ottenne|ha ottenuto|si aggiudica|si aggiudicò|conquista|conquistò|consegue|"
    r"conseguì|è insignit[oa] d\w+|viene premiat[oa] con|"
    r"gli viene (?:assegnat|conferit)\w+)\s+"
    r"(?:(?:il|lo|la|l'|un|una|i|gli|le|del|dello|della|dell')\s*)?",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------
# COSTANTI PER WIKIPEDIA INGLESE (usata solo come seconda scelta)
# ---------------------------------------------------------------------
PREFISSO_WIKIPEDIA_EN = "https://en.wikipedia.org/wiki/"

# Titoli di sezione inglesi che elencano i premi (in minuscolo).
# Non includo "Honours"/"Honors" da soli: per sportivi e politici elencano trofei e onorificenze.
TITOLI_SEZIONE_PREMI_EN = {
    "awards", "awards and honors", "awards and honours", "honors and awards",
    "honours and awards", "awards and recognition", "awards and recognitions",
    "recognition", "accolades", "prizes", "literary awards", "awards and nominations",
    "awards and achievements", "prizes and awards", "awards and prizes", "major awards",
}

# Voci inglesi che NON sono vittorie (candidature, finali...).
RE_NON_VITTORIA_EN = re.compile(
    r"\b(?:nominee|nominated|nominations?|short-?listed|shortlist|long-?listed|longlist|"
    r"finalist|runner-?up|honou?rable mention|second place|third place|lost)\b",
    re.IGNORECASE,
)

# Lauree honoris causa, ordini cavallereschi ecc.: non sono premi letterari.
RE_ONORIFICENZA_EN = re.compile(
    r"\bhonou?rary\b|\bdoctorate\b|\bdoctor of\b|\border of\b|\bknight\b|\bchevalier\b|"
    r"\blegion of honou?r\b|\blégion d'honneur\b",
    re.IGNORECASE,
)

# Frasi del tipo "Won the Edgar Award ...", "Recipient of the ...".
RE_PREFISSO_VERBO_EN = re.compile(
    r"^(?:won|winner|winners|awarded|received|recipient|honou?red)\b(?:\s+of)?\s+(?:the\s+)?",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------
# 2. LETTURA DEL CSV
# ---------------------------------------------------------------------
def leggi_csv(percorso):
    """Legge il CSV e restituisce una lista di dizionari (uno per riga)."""
    with open(percorso, newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file, delimiter=SEPARATORE_CSV))


def costruisci_elenco_autori(righe):
    """
    Dalle righe del CSV ricava un dizionario {nome autore: libro e editore}.
    - Se una cella contiene più autori separati da ";", ognuno è trattato a parte.
    - Se un autore compare in più libri, tengo il primo (il meglio piazzato).
    Restituisce anche il numero di libri senza autore, che vengono saltati.
    """
    autori = {}
    senza_autore = 0
    for riga in righe:
        nomi = [n.strip() for n in riga.get("autore", "").split(";") if n.strip()]
        if not nomi:
            senza_autore += 1
            continue
        for nome in nomi:
            if nome not in autori:
                autori[nome] = {
                    "libro": riga.get("titolo", ""),
                    "editore": riga.get("editore", ""),
                }
    return autori, senza_autore


# ---------------------------------------------------------------------
# 3. RECUPERO DELLA PAGINA
# ---------------------------------------------------------------------
def costruisci_url(nome_autore, prefisso=PREFISSO_WIKIPEDIA):
    """
    Costruisce l'URL secondo la convenzione di Wikipedia:
    spazi sostituiti da "_", dopo il prefisso https://it.wikipedia.org/wiki/
    quote() codifica accenti e apostrofi (es. "Giménez" -> "Gim%C3%A9nez").
    """
    titolo = nome_autore.strip().replace(" ", "_")
    return prefisso + quote(titolo, safe="_")


def scarica_pagina(url):
    """
    Scarica la pagina. Non solleva mai eccezioni: restituisce una coppia
    (pagina, errore). Se tutto va bene errore è None; altrimenti pagina è None
    e errore contiene il motivo. Così lo script non si ferma al primo problema.
    """
    try:
        risposta = requests.get(url, headers=INTESTAZIONI, timeout=20)
    except requests.RequestException as errore:
        return None, f"errore di rete: {errore}"

    if risposta.status_code == 404:
        return None, "pagina non trovata (404)"
    if risposta.status_code != 200:
        return None, f"risposta HTTP {risposta.status_code}"

    soup = BeautifulSoup(risposta.text, "html.parser")
    # Tolgo ciò che sporca il testo: numeri di nota [1], link "modifica", codice.
    for elemento in soup.select("sup.reference, span.mw-editsection, style, script"):
        elemento.decompose()
    return soup, None


def e_pagina_di_disambiguazione(soup):
    """True se la pagina è un elenco di omonimi invece di una persona."""
    categorie = soup.find(id="catlinks")
    if categorie is not None and "disambigua" in categorie.get_text().lower():
        return True
    corpo = soup.find(id="mw-content-text") or soup
    inizio = corpo.get_text(" ")[:600].lower()
    return "può riferirsi a" in inizio or "may refer to" in inizio or "may also refer to" in inizio


# ---------------------------------------------------------------------
# 4. ESTRAZIONE DEI SINGOLI CAMPI
# ---------------------------------------------------------------------
def pulisci_testo(testo):
    """Normalizza spazi e punteggiatura."""
    testo = re.sub(r"\s+", " ", testo).strip()
    testo = re.sub(r"\s+([.,;:!?)])", r"\1", testo)    # "parola ." -> "parola."
    testo = re.sub(r"\(\s+", "(", testo)               # "( 2019" -> "(2019"
    return testo


def testo_proprio(elemento):
    """Testo di un elemento SENZA le liste annidate che contiene."""
    copia = copy.copy(elemento)                        # lavoro su una copia: l'originale resta intatto
    for lista in copia.find_all(["ul", "ol"]):
        lista.decompose()
    return pulisci_testo(copia.get_text(" "))


def livello_titolo(tag):
    """Se il tag è un titolo (h1..h6) restituisce il suo livello (2 per h2), altrimenti None."""
    if tag.name and re.fullmatch(r"h[1-6]", tag.name):
        return int(tag.name[1])
    # Nelle versioni recenti di Wikipedia il titolo è dentro <div class="mw-heading">.
    if tag.name == "div" and "mw-heading" in (tag.get("class") or []):
        interno = tag.find(re.compile(r"^h[1-6]$"))
        if interno is not None:
            return int(interno.name[1])
    return None


def trova_sezioni_premi(soup, titoli=TITOLI_SEZIONE_PREMI):
    """Restituisce i titoli di sezione che sembrano contenere premi."""
    return [
        titolo for titolo in soup.find_all(["h2", "h3", "h4"])
        if pulisci_testo(titolo.get_text()).lower() in titoli
    ]


def elenca_voci_sezione(intestazione):
    """
    Restituisce il testo di ogni voce (elemento di elenco o riga di tabella)
    della sezione che inizia con questo titolo, fino al titolo successivo.
    Per le liste annidate unisco il testo del "genitore" a quello del "figlio":
        * Premio Campiello
            * 2005 per "..."      ->   "Premio Campiello 2005 per ..."
    """
    livello = livello_titolo(intestazione)
    ancora = intestazione
    if intestazione.parent is not None and "mw-heading" in (intestazione.parent.get("class") or []):
        ancora = intestazione.parent

    voci = []
    for fratello in ancora.find_next_siblings():
        livello_fratello = livello_titolo(fratello)
        if livello_fratello is not None and livello_fratello <= livello:
            break                                      # inizia un'altra sezione: mi fermo

        for elemento in fratello.find_all(["li", "tr"]):
            if elemento.name == "tr" and not elemento.find("td"):
                continue                               # riga di intestazione di tabella
            if elemento.name == "li" and elemento.find(["ul", "ol"]):
                continue                               # voce che contiene sotto-voci: fa solo da contesto
            testo = testo_proprio(elemento)
            if elemento.name == "li":
                genitore = elemento.find_parent("li")
                if genitore is not None:
                    testo = f"{testo_proprio(genitore)} {testo}"
            testo = pulisci_testo(testo)
            if testo:
                voci.append(testo)
    return voci


def estrai_anno(voce):
    """Primo anno trovato, cercando prima prima del titolo dell'opera ("per ...")."""
    parte_iniziale = RE_PER_CON.split(voce, maxsplit=1)[0]
    for porzione in (parte_iniziale, voce):
        trovato = RE_ANNO.search(porzione)
        if trovato:
            return int(trovato.group(1))
    return None


def e_parola_con_maiuscola(parola):
    """True se la parola inizia con una maiuscola (ignorando virgolette) o è un'elisione tipo "d'Oro"."""
    base = parola.lstrip("«“\"‘'(")
    return bool(base) and (base[0].isupper() or RE_ELISIONE.match(base) is not None)


def lunghezza_qualificatore(parole, posizione):
    """Se da 'posizione' inizia un qualificatore noto (es. "opera prima", "di giornalismo") ne restituisce la lunghezza, altrimenti 0."""
    for qualificatore in QUALIFICATORI_MINUSCOLI:
        porzione = tuple(p.strip(",.;:)").lower() for p in parole[posizione:posizione + len(qualificatore)])
        if porzione == qualificatore:
            return len(qualificatore)
    # Forma "di giornalismo", "della poesia"...: connettivo + ambito noto.
    if posizione + 1 < len(parole):
        prima = parole[posizione].strip(",.;:)").lower()
        seconda = parole[posizione + 1].strip(",.;:)").lower()
        if prima in {"di", "del", "della", "dello"} and seconda in AMBITI_MINUSCOLI:
            return 2
    return 0


def connettivi_seguiti_da_maiuscola(parole, posizione):
    """True se, saltando i connettivi (di, della, per, la...), si arriva a una parola con la maiuscola."""
    j = posizione
    while j < len(parole) and parole[j].strip(",.;:)").lower() in CONNETTIVI:
        j += 1
    return j < len(parole) and e_parola_con_maiuscola(parole[j])


def prendi_nome_dopo_premio(resto):
    """
    Dato il testo che segue la parola "premio" (es. "Strega per il romanzo M."),
    restituisce solo le parole che formano il nome ("Strega").
    Regola: si raccolgono le parole finché sono maiuscole (o connettivi/qualificatori
    ammessi); alla prima parola minuscola "di frase" (nel, per il, con...) ci si ferma.
    """
    parole = resto.split()
    nome = []
    i = 0
    while i < len(parole):
        parola = parole[i]
        if parola.startswith(("(", "[")):
            break                                      # inizia una parentesi: il nome è finito
        base = parola.strip(",.;:)")

        if e_parola_con_maiuscola(parola):
            nome.append(parola)
            i += 1
        elif lunghezza_qualificatore(parole, i):
            n = lunghezza_qualificatore(parole, i)
            nome.extend(parole[i:i + n])
            i += n
        elif base.lower() in CONNETTIVI and connettivi_seguiti_da_maiuscola(parole, i):
            nome.append(parola)
            i += 1
        else:
            break                                      # parola di frase: fine del nome

        if nome[-1][-1] in ",.;:)":
            break                                      # punteggiatura finale: il nome è finito
    return " ".join(nome)


def nome_senza_parola_premio(testo):
    """Per le voci che non contengono la parola "premio": toglie "Nel ... vince il" e simili."""
    testo = RE_VERBO_ASSEGNAZIONE.sub("", testo, count=1)
    testo = re.sub(r"^(?:nel|nell'|del|dell')\s+", "", testo, flags=re.IGNORECASE)
    testo = testo.lstrip(" :;,.-–—()[]")
    testo = RE_SEPARATORI.split(testo, maxsplit=1)[0]
    testo = re.sub(r"\s+", " ", testo).strip(" :;,.-–—")
    return testo or None


def estrai_nome_premio(voce):
    """
    Restituisce SOLO l'etichetta del premio, nella forma "Premio <Nome>":
        "Nel 2019 riceve il premio Strega per M. Il figlio del secolo" -> "Premio Strega"
        "2015: Premio Viareggio per Il tempo migliore..."             -> "Premio Viareggio"
    """
    testo = RE_PER_CON.split(voce, maxsplit=1)[0]      # via "per <Titolo opera>"
    testo = RE_ANNO.sub(" ", testo)                    # via gli anni
    testo = re.sub(r"\(\s*\)", " ", testo)             # via parentesi rimaste vuote
    testo = re.sub(r"\s+", " ", testo).strip()

    trovato = RE_PAROLA_PREMIO.search(testo)
    if trovato is None:
        return nome_senza_parola_premio(testo)         # premio senza la parola "premio"

    nome = prendi_nome_dopo_premio(testo[trovato.end():])
    nome = re.sub(r"[«»“”\"]", "", nome).strip(" ,.;:)]")
    return f"Premio {nome}" if nome else None          # "Premio" scritto sempre con la maiuscola


def estrai_premi(soup):
    """Restituisce la lista dei premi: [{"premio", "anno", "testo_originale"}, ...]."""
    premi = []
    viste = set()                                      # per evitare doppioni
    for intestazione in trova_sezioni_premi(soup):
        for voce in elenca_voci_sezione(intestazione):
            if voce in viste:
                continue
            viste.add(voce)
            if RE_NON_VITTORIA.search(voce) or RE_ONORIFICENZA.search(voce):
                continue                               # finalista, onorificenza di Stato ecc.
            premi.append({
                "premio": estrai_nome_premio(voce),
                "anno": estrai_anno(voce),
                # Il testo grezzo serve a ricontrollare a mano le estrazioni dubbie.
                "testo_originale": voce[:300],
            })
    return premi


# ---------------------------------------------------------------------
# 5. ELABORAZIONE DI UN AUTORE
# ---------------------------------------------------------------------
def elabora_autore_it(nome, info):
    """
    Costruisce il record JSON di un autore usando la pagina ITALIANA. Stati possibili:
      - "risolto":        pagina trovata, almeno un premio e tutti con nome e anno
      - "campo_mancante": pagina trovata ma nessun premio estratto, o premio senza anno
      - "non_trovato":    pagina assente, ambigua o richiesta fallita
    """
    url = costruisci_url(nome)
    record = {
        "autore": nome,
        "libro": info["libro"],
        "editore": info["editore"],
        "url_wikipedia": url,
        "stato": "non_trovato",
        "nota": None,
        "premi": None,                                 # resta null se non si trova nulla
    }

    soup, errore = scarica_pagina(url)
    if soup is None:
        record["nota"] = errore
        return record

    if e_pagina_di_disambiguazione(soup):
        record["nota"] = "pagina di disambiguazione (omonimi)"
        return record

    # Un errore imprevisto nell'estrazione non deve fermare lo script.
    try:
        premi = estrai_premi(soup)
    except Exception as errore_estrazione:             # noqa: BLE001
        record["stato"] = "campo_mancante"
        record["nota"] = f"errore di estrazione: {errore_estrazione}"
        return record

    if not premi:
        record["stato"] = "campo_mancante"
        record["nota"] = "nessun premio estratto (sezione assente o vuota)"
    elif any(p["anno"] is None or p["premio"] is None for p in premi):
        record["stato"] = "campo_mancante"
        record["nota"] = "almeno un premio senza nome o senza anno"
        record["premi"] = premi
    else:
        record["stato"] = "risolto"
        record["premi"] = premi
    return record


# ---------------------------------------------------------------------
# 5b. PAGINA INGLESE (seconda scelta)
# Sulle pagine inglesi i premi si trovano in tre posti: nel riquadro
# informativo ("Notable awards"), in elenchi puntati e in tabelle
# (Year / Award / Result) all'interno di sezioni tipo "Awards and honors".
# ---------------------------------------------------------------------
def testo_proprio_en(elemento):
    """
    Come testo_proprio, ma toglie anche i corsivi: su Wikipedia i titoli delle
    opere sono in corsivo, e qui ci interessa solo il nome del premio.
    """
    copia = copy.copy(elemento)
    for sotto in reversed(copia.find_all(["ul", "ol", "i"])):   # dal più interno al più esterno
        sotto.decompose()
    return pulisci_testo(copia.get_text(" "))


def nodi_della_sezione(intestazione):
    """Elementi che seguono un titolo, fino al titolo successivo di pari o superiore livello."""
    livello = livello_titolo(intestazione)
    ancora = intestazione
    if intestazione.parent is not None and "mw-heading" in (intestazione.parent.get("class") or []):
        ancora = intestazione.parent
    nodi = []
    for fratello in ancora.find_next_siblings():
        livello_fratello = livello_titolo(fratello)
        if livello_fratello is not None and livello_fratello <= livello:
            break
        nodi.append(fratello)
    return nodi


def numero_da_attributo(valore):
    """Legge i valori di rowspan/colspan (es. "2") restituendo almeno 1."""
    trovato = re.match(r"\d+", str(valore or ""))
    return max(1, int(trovato.group())) if trovato else 1


def espandi_tabella(tabella):
    """
    Trasforma una tabella HTML in una lista di righe (liste di testi).
    Le celle che si estendono su più righe (rowspan, tipico della colonna "Year")
    vengono ripetute nelle righe sotto, così ogni riga è completa.
    """
    griglia = []
    riporti = {}                                       # colonna -> [testo, righe ancora da riempire]
    for tr in tabella.find_all("tr"):
        riga, colonna = [], 0
        celle = iter(tr.find_all(["th", "td"]))
        while True:
            if colonna in riporti:                     # cella "scesa" da una riga precedente
                testo, resto = riporti[colonna]
                riga.append(testo)
                if resto > 1:
                    riporti[colonna] = [testo, resto - 1]
                else:
                    del riporti[colonna]
                colonna += 1
                continue
            cella = next(celle, None)
            if cella is None:
                break
            testo = testo_proprio_en(cella)
            larghezza = numero_da_attributo(cella.get("colspan"))
            altezza = numero_da_attributo(cella.get("rowspan"))
            for _ in range(larghezza):
                riga.append(testo)
                if altezza > 1:
                    riporti[colonna] = [testo, altezza - 1]
                colonna += 1
        griglia.append(riga)
    return griglia


def estrai_anno_en(testo):
    """Primo anno (1900-2099) presente nel testo."""
    trovato = RE_ANNO.search(testo)
    return int(trovato.group(1)) if trovato else None


def voci_da_tabella(tabella):
    """
    Voci di una tabella di premi. Restituisce tuple (testo del premio, anno, testo completo).
    Se c'è una colonna "Result", tengo solo le righe vinte ("Won"); le candidature sono scartate.
    """
    griglia = espandi_tabella(tabella)
    if len(griglia) < 2:
        return []
    intestazioni = [c.lower() for c in griglia[0]]

    def colonna(*gruppi):
        """Indice della prima colonna la cui intestazione contiene una parola del primo gruppo che dà risultati."""
        for parole in gruppi:
            for indice, testo in enumerate(intestazioni):
                if any(p in testo for p in parole):
                    return indice
        return None

    i_anno = colonna(("year",))
    i_premio = colonna(("award", "prize"), ("honor", "honour"), ("association", "organization", "organisation"))
    i_esito = colonna(("result", "outcome"))
    if i_premio is None:
        return []                                      # non è una tabella di premi riconoscibile

    def cella(riga, indice):
        return riga[indice] if indice is not None and indice < len(riga) else ""

    voci = []
    for riga in griglia[1:]:
        if i_esito is not None and not re.search(r"\b(?:won|win|winner|recipient|awarded)\b",
                                                   cella(riga, i_esito), re.IGNORECASE):
            continue                                   # candidatura o esito non vinto
        testo_premio = cella(riga, i_premio)
        if not testo_premio:
            continue
        completo = " | ".join(c for c in riga if c)
        anno = estrai_anno_en(cella(riga, i_anno)) if i_anno is not None else None
        if anno is None:
            anno = estrai_anno_en(completo)
        voci.append((testo_premio, anno, completo))
    return voci


def voci_da_nodo(nodo):
    """Voci (tuple come sopra) contenute in un elemento di una sezione: tabelle ed elenchi puntati."""
    voci = []
    tabelle = [nodo] if nodo.name == "table" else nodo.find_all("table")
    for tabella in tabelle:
        voci.extend(voci_da_tabella(tabella))

    if nodo.name != "table":
        for elemento in nodo.find_all("li"):
            if elemento.find_parent("table") is not None:
                continue                               # già gestita come tabella
            if elemento.find(["ul", "ol"]):
                continue                               # voce con sotto-voci: fa solo da contesto
            testo = testo_proprio_en(elemento)
            genitore = elemento.find_parent("li")
            if genitore is not None:
                testo = f"{testo_proprio_en(genitore)} {testo}"
            testo = pulisci_testo(testo)
            if testo:
                voci.append((testo, estrai_anno_en(testo), testo))
    return voci


def voci_da_infobox(soup):
    """
    Premi elencati nel riquadro informativo a destra (riga "Notable awards"/"Awards").
    Le voci sono separate da a-capo, elenchi puntati o punto e virgola.
    """
    voci = []
    riquadro = soup.select_one("table.infobox")
    if riquadro is None:
        return voci
    for riga in riquadro.find_all("tr"):
        etichetta, contenuto = riga.find("th"), riga.find("td")
        if etichetta is None or contenuto is None:
            continue
        if not re.search(r"award|prize|honou?rs?\b", etichetta.get_text(), re.IGNORECASE):
            continue
        copia = copy.copy(contenuto)
        for corsivo in reversed(copia.find_all("i")):
            corsivo.decompose()
        for a_capo in copia.find_all("br"):
            a_capo.replace_with("\n")
        for punto_elenco in copia.find_all("li"):
            punto_elenco.insert_after("\n")
        for parte in re.split(r"[\n;]+", copia.get_text(" ")):
            parte = pulisci_testo(parte)
            if parte:
                voci.append((parte, estrai_anno_en(parte), parte))
    return voci


def estrai_nome_premio_en(testo):
    """
    Ricava solo il nome del premio da una voce inglese, mantenendolo in inglese:
        "Won the Edgar Award for Best Novel (1990)" -> "Edgar Award for Best Novel"
        "Pulitzer Prize for Fiction, 2019"          -> "Pulitzer Prize for Fiction"
    """
    testo = RE_ANNO.sub(" ", testo)                    # via gli anni
    testo = re.sub(r"\([^)]*\)", " ", testo)           # via tutto ciò che è tra parentesi
    testo = re.sub(r"\s+", " ", testo).strip()
    testo = RE_PREFISSO_VERBO_EN.sub("", testo, count=1)   # via "Won the ..." iniziale
    testo = testo.lstrip(" :;,.-–—")
    testo = re.split(r"\s+(?:from|by)\s+", testo, maxsplit=1)[0]   # via "from the ... Trust"
    testo = RE_SEPARATORI.split(testo, maxsplit=1)[0]  # taglio al primo separatore
    testo = re.sub(r"\s+", " ", testo).strip(" :;,.-–—")
    # Tolgo parole di collegamento rimaste in fondo ("... Best Novel for").
    while True:
        nuovo = re.sub(r"\s+(?:for|with|from|by|and|of|in|at|the)$", "", testo, flags=re.IGNORECASE)
        if nuovo == testo:
            break
        testo = nuovo
    return testo or None


def estrai_premi_en(soup):
    """Premi dalla pagina inglese: [{"premio", "anno", "testo_originale"}, ...]."""
    candidati = list(voci_da_infobox(soup))
    for intestazione in trova_sezioni_premi(soup, TITOLI_SEZIONE_PREMI_EN):
        for nodo in nodi_della_sezione(intestazione):
            candidati.extend(voci_da_nodo(nodo))

    premi = []
    viste = set()                                      # per evitare doppioni (infobox + sezione)
    for testo_premio, anno, originale in candidati:
        if RE_NON_VITTORIA_EN.search(originale) or RE_ONORIFICENZA_EN.search(originale):
            continue
        premio = estrai_nome_premio_en(testo_premio)
        chiave = ((premio or originale).lower(), anno)
        if chiave in viste:
            continue
        viste.add(chiave)
        premi.append({"premio": premio, "anno": anno, "testo_originale": originale[:300]})
    return premi


def elabora_autore_en(nome, info):
    """Stessa logica di elabora_autore_it, ma sulla pagina di en.wikipedia.org."""
    url = costruisci_url(nome, PREFISSO_WIKIPEDIA_EN)
    record = {
        "autore": nome,
        "libro": info["libro"],
        "editore": info["editore"],
        "url_wikipedia": url,
        "stato": "non_trovato",
        "nota": None,
        "premi": None,
    }

    soup, errore = scarica_pagina(url)
    if soup is None:
        record["nota"] = errore
        return record

    if e_pagina_di_disambiguazione(soup):
        record["nota"] = "pagina di disambiguazione (omonimi)"
        return record

    try:
        premi = estrai_premi_en(soup)
    except Exception as errore_estrazione:             # noqa: BLE001
        record["stato"] = "campo_mancante"
        record["nota"] = f"errore di estrazione: {errore_estrazione}"
        return record

    if not premi:
        record["stato"] = "campo_mancante"
        record["nota"] = "nessun premio estratto (sezione assente o vuota)"
    elif any(p["anno"] is None or p["premio"] is None for p in premi):
        record["stato"] = "campo_mancante"
        record["nota"] = "almeno un premio senza nome o senza anno"
        record["premi"] = premi
    else:
        record["stato"] = "risolto"
        record["premi"] = premi
    return record


def con_lingua(record, lingua):
    """Restituisce il record con il campo "lingua_pagina" inserito dopo "url_wikipedia"."""
    nuovo = {}
    for chiave, valore in record.items():
        nuovo[chiave] = valore
        if chiave == "url_wikipedia":
            nuovo["lingua_pagina"] = lingua
    return nuovo


def elabora_autore(nome, info):
    """
    Prima la pagina italiana. Solo se non esiste o non dà premi, provo l'inglese
    (con una pausa di un secondo tra le due richieste).
    """
    record_it = elabora_autore_it(nome, info)
    lingua_it = None if record_it["stato"] == "non_trovato" else "it"

    if record_it["stato"] != "non_trovato" and record_it["premi"]:
        return con_lingua(record_it, "it")             # premi già trovati in italiano

    time.sleep(PAUSA_SECONDI)
    record_en = elabora_autore_en(nome, info)
    if record_en["premi"]:
        return con_lingua(record_en, "en")             # l'inglese ha trovato dei premi

    # Nulla nemmeno in inglese: tengo il record italiano e annoto anche l'esito inglese.
    nota_en = record_en["nota"] or "nessun premio estratto"
    record_it["nota"] = f"{record_it['nota']}; en.wikipedia: {nota_en}"
    return con_lingua(record_it, lingua_it)


# ---------------------------------------------------------------------
# 6. SALVATAGGIO E SOMMARIO
# ---------------------------------------------------------------------
def salva_json(records, percorso):
    """Scrive i record nel file JSON (ensure_ascii=False mantiene le lettere accentate)."""
    with open(percorso, "w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)


def stampa_sommario(records, libri_senza_autore):
    """Stampa quanti autori sono risolti, con campi mancanti, non trovati."""
    risolti = sum(1 for r in records if r["stato"] == "risolto")
    mancanti = sum(1 for r in records if r["stato"] == "campo_mancante")
    non_trovati = sum(1 for r in records if r["stato"] == "non_trovato")
    ambigui = sum(1 for r in records if r["nota"] and "disambiguazione" in r["nota"])
    da_inglese = sum(1 for r in records if r.get("lingua_pagina") == "en")

    print()
    print("=== SOMMARIO ===")
    print(f"Autori elaborati       : {len(records)}")
    print(f"Risolti                : {risolti}")
    print(f"Con campo mancante     : {mancanti}")
    print(f"Non trovati            : {non_trovati}  (di cui omonimi/disambigua: {ambigui})")
    print(f"Premi trovati su Wikipedia inglese: {da_inglese} autori")
    if libri_senza_autore:
        print(f"Libri senza autore nel CSV (saltati): {libri_senza_autore}")
    print(f"Risultato salvato in {FILE_JSON_OUTPUT}")


# ---------------------------------------------------------------------
# 7. PROGRAMMA PRINCIPALE
# ---------------------------------------------------------------------
def main():
    try:
        righe = leggi_csv(FILE_CSV_INPUT)
    except FileNotFoundError:
        print(f"File {FILE_CSV_INPUT} non trovato: mettilo nella stessa cartella dello script.")
        return

    autori, libri_senza_autore = costruisci_elenco_autori(righe)
    print(f"Autori da cercare su Wikipedia: {len(autori)}")

    records = []
    for indice, (nome, info) in enumerate(autori.items()):
        if indice > 0:
            time.sleep(PAUSA_SECONDI)                  # pausa tra una richiesta e l'altra
        record = elabora_autore(nome, info)
        print(f"  [{indice + 1}/{len(autori)}] {nome}: {record['stato']} [{record['lingua_pagina'] or '-'}]"
              + (f" ({record['nota']})" if record["nota"] else ""))
        records.append(record)

    salva_json(records, FILE_JSON_OUTPUT)
    stampa_sommario(records, libri_senza_autore)


if __name__ == "__main__":
    main()