# -*- coding: utf-8 -*-
"""
Genera report.html: una pagina di sintesi del progetto "Misurare il gusto".

La pagina contiene:
  1. titolo e breve introduzione;
  2. una sezione "Numeri" con tabelle riassuntive (classifica IBS, occorrenze,
     correlazioni, premi, uso dei vocabolari per casa editrice);
  3. una sezione "Grafici" con le immagini già prodotte dagli altri script;
  4. una sezione "Editori" con il link alla mappa interattiva.

L'HTML è scritto come stringa Python (f-string): niente librerie di template e
nessun JavaScript. Il file si apre con un doppio clic in qualunque browser, a condizione
che le immagini e editori_vocabolari.html restino nella STESSA cartella di report.html.

Prima di lanciarlo devono essere stati eseguiti gli altri script, che creano le immagini
(grafico_occorrenze.py, correlazione_classifica.py, distribuzione_premi.py) e la
mappa degli editori (editori_vocabolari.py).

Requisiti:  pip install scipy matplotlib plotly
Va messo nella stessa cartella degli script del progetto (riusa le loro funzioni, così i
numeri del report coincidono con quelli dei grafici), di dizionario.json,
premi_arricchiti.json e del CSV della classifica.

Uso:
    python crea_report.py
"""

# ---------------------------------------------------------------------
# IMPORTAZIONI
# ---------------------------------------------------------------------
import csv                                    # lettura del CSV
import html                                   # html.escape: rende sicuro il testo da inserire nell'HTML
import os                                     # per controllare se un file esiste
from datetime import datetime                 # data di generazione del report

# Riuso funzioni e impostazioni degli script già scritti.
from grafico_occorrenze import (
    COLONNA_DESCRIZIONE, FILE_DIZIONARIO, SEPARATORE_CSV, carica_categorie,
)
from editori_vocabolari import (
    COLONNA_EDITORE, FILE_CSV, FILE_CSV_ALTERNATIVO, MIN_LIBRI_EDITORE,
    normalizza_editore, occorrenze_per_categoria, per_100_parole, raggruppa_per_editore,
)
from distribuzione_premi import (
    COLONNA_AUTORE, COLONNA_POSIZIONE, FILE_PREMI, SOGLIA_AUTORE_PREMIATO,
    carica_premi_per_autore, premi_dell_autore,
)
from correlazione_classifica import calcola_correlazione, formatta_p


# ---------------------------------------------------------------------
# 1. IMPOSTAZIONI
# ---------------------------------------------------------------------
FILE_REPORT = "report.html"
FILE_EDITORI_HTML = "editori_vocabolari.html"

# Grafici da inserire nel report, nell'ordine: (file immagine, didascalia).
# Per cambiare ordine o testo basta modificare questa lista.
FIGURE = [
    ("correlazioni.png",
     "Correlazione di Spearman tra l'uso di ciascun vocabolario e la posizione in classifica. "
     "Valori positivi: più linguaggio di quel tipo nelle posizioni alte. "
     "L'asterisco indica le correlazioni significative (p &lt; 0,05)."),
    ("distribuzione_premi.png",
     "Per ogni fascia di posizioni, quota di libri che citano premi nella descrizione, "
     "che hanno un autore molto premiato o che hanno almeno una delle due caratteristiche."),
    ("occorrenze.png",
     "Occorrenze ogni 100 parole di ciascun vocabolario nelle descrizioni dell'intera classifica."),
]

# Il CSS è in una stringa normale (non f-string): le sue parentesi graffe { } si
# confonderebbero con quelle dei campi dinamici dell'f-string della pagina.
CSS = """
body { font-family: Arial, Helvetica, sans-serif; max-width: 800px; margin: 2rem auto;
       padding: 0 1rem; line-height: 1.6; color: #222; }
h1 { margin-bottom: 0.2rem; }
h2 { margin-top: 2.5rem; border-bottom: 1px solid #ccc; padding-bottom: 0.3rem; }
.sottotitolo { color: #555; margin-top: 0; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: 0.9rem; }
th, td { border: 1px solid #bbb; padding: 0.4rem 0.6rem; text-align: left; vertical-align: top; }
th { background: #f0f0f0; }
td.num { text-align: right; white-space: nowrap; }
img { width: 100%; height: auto; }
figure { margin: 1.5rem 0; }
figcaption { font-size: 0.9rem; color: #555; margin-top: 0.4rem; }
.nota { font-size: 0.85rem; color: #555; }
"""


# ---------------------------------------------------------------------
# 2. FUNZIONI DI FORMATTAZIONE
# ---------------------------------------------------------------------
def num(valore, cifre=2, segno=False):
    """Numero con la virgola decimale all'italiana ('-' se manca)."""
    if valore is None:
        return "–"
    formato = f"{valore:+.{cifre}f}" if segno else f"{valore:.{cifre}f}"
    return formato.replace(".", ",")


def intero(valore):
    """Numero intero con il punto come separatore delle migliaia (1440 -> 1.440)."""
    return f"{valore:,}".replace(",", ".")


def percentuale(parte, totale):
    """'18 (45%)'."""
    return f"{intero(parte)} ({100 * parte / totale:.0f}%)" if totale else "–"


def p_italiano(p):
    """Valore p con la virgola: '0,012' oppure '<0,001' ('–' se manca)."""
    return "–" if p is None else formatta_p(p).replace(".", ",")


# Nomi da mostrare nelle tabelle (le chiavi del JSON non hanno accenti).
NOMI_CATEGORIE = {
    "premi": "Premi",
    "novita": "Novità",
    "coinvolgimento_lettore": "Coinvolgimento del lettore",
    "valutativi_positivi": "Valutativi positivi",
    "citazioni_critiche_giornalisti": "Citazioni e critiche di giornalisti",
}


def nome_leggibile(categoria):
    """Nome mostrato nella tabella; se la categoria non è nell'elenco, si ripulisce la chiave."""
    return NOMI_CATEGORIE.get(categoria, categoria.replace("_", " ").capitalize())


# ---------------------------------------------------------------------
# 3. LETTURA DEI DATI E CALCOLO DEI NUMERI
# ---------------------------------------------------------------------
def leggi_libri(percorso):
    """
    Legge il CSV e restituisce (lista di libri, numero di righe del CSV).
    Ogni libro è un dizionario con posizione, autori, editore e descrizione.
    Si tengono solo i libri con posizione numerica e descrizione non vuota.
    """
    libri, righe_totali = [], 0
    with open(percorso, newline="", encoding="utf-8-sig") as file:
        for riga in csv.DictReader(file, delimiter=SEPARATORE_CSV):
            righe_totali += 1
            testo = (riga.get(COLONNA_DESCRIZIONE) or "").strip()
            try:
                posizione = int(riga[COLONNA_POSIZIONE])
            except (KeyError, ValueError):
                continue
            if not testo:
                continue
            libri.append({
                "posizione": posizione,
                "autori": [a.strip() for a in (riga.get(COLONNA_AUTORE) or "").split(";") if a.strip()],
                "editore": normalizza_editore(riga.get(COLONNA_EDITORE) or ""),
                "testo": testo,
            })
    return libri, righe_totali


def calcola_numeri(libri, righe_totali, categorie, premi_per_autore):
    """Calcola tutti i numeri che finiscono nelle tabelle e li restituisce in un dizionario."""
    # Occorrenze di ogni categoria in ogni descrizione (stessa funzione dei grafici).
    for libro in libri:
        libro["occ"], libro["parole"] = occorrenze_per_categoria(libro["testo"], categorie)
    parole_totali = sum(l["parole"] for l in libri)
    posizioni = [l["posizione"] for l in libri]

    # Case editrici (solo libri con editore noto) e relative occorrenze.
    editori, _ = raggruppa_per_editore(
        [(l["editore"], l["testo"]) for l in libri if l["editore"]], categorie)
    visibili = [s for s in editori.values() if s["n_libri"] >= MIN_LIBRI_EDITORE]

    # Una riga per categoria: occorrenze, correlazione con la posizione, editore che la usa di più.
    vocabolari = []
    for nome in categorie:
        occorrenze = sum(l["occ"][nome] for l in libri)
        tassi = [100 * l["occ"][nome] / l["parole"] if l["parole"] else 0.0 for l in libri]
        correlazione = calcola_correlazione(nome, tassi, posizioni)

        migliore = max(visibili, key=lambda s: per_100_parole(s["occorrenze"][nome], s["n_parole"]),
                       default=None)
        valore = per_100_parole(migliore["occorrenze"][nome], migliore["n_parole"]) if migliore else 0
        vocabolari.append({
            "categoria": nome,
            "occorrenze": occorrenze,
            "per_100": per_100_parole(occorrenze, parole_totali),
            "rho": correlazione["rho"], "p": correlazione["p"],
            # Se nessun editore ha il vocabolario (valore 0) non indico alcun editore.
            "editore_top": (migliore["nome"], migliore["n_libri"], valore) if migliore and valore > 0 else None,
        })

    # Numeri sui premi: descrizioni che li citano e autori molto premiati.
    premi_autori = [premi_dell_autore(l["autori"], premi_per_autore) for l in libri]
    correlazione_premi = calcola_correlazione(
        "premi_autore", [float(p) for p in premi_autori], posizioni)

    return {
        "righe_csv": righe_totali, "n_libri": len(libri), "parole_totali": parole_totali,
        "pos_min": min(posizioni), "pos_max": max(posizioni),
        "n_autori": len({a for l in libri for a in l["autori"]}),
        "n_editori": len(editori), "n_editori_visibili": len(visibili),
        "n_cita_premi": sum(1 for l in libri if l["occ"]["premi"] > 0),
        "n_autore_premiato": sum(1 for p in premi_autori if p >= SOGLIA_AUTORE_PREMIATO),
        "correlazione_premi": correlazione_premi,
        "vocabolari": vocabolari,
    }


# ---------------------------------------------------------------------
# 4. COSTRUZIONE DELL'HTML
# ---------------------------------------------------------------------
def riga(celle, intestazione=False):
    """Una riga di tabella. Le celle sono testi già pronti; quelle numeriche vanno allineate a destra."""
    tag = "th" if intestazione else "td"
    html_celle = ""
    for testo, e_numero in celle:
        classe = ' class="num"' if (e_numero and not intestazione) else ""
        html_celle += f"<{tag}{classe}>{testo}</{tag}>"
    return f"<tr>{html_celle}</tr>"


def tabella_generale(n):
    """Tabella 'Indicatore / Valore' con i dati della classifica IBS e dei premi."""
    cp = n["correlazione_premi"]
    if cp["rho"] is None:
        corr_premi = "non calcolabile"
    else:
        corr_premi = f"rho = {num(cp['rho'], 2, segno=True)}; p = {p_italiano(cp['p'])}"

    righe = [
        '<tr><th colspan="2">Classifica IBS</th></tr>',
        riga([("Libri nel CSV", False), (intero(n["righe_csv"]), True)]),
        riga([("Libri analizzati (con descrizione)", False), (intero(n["n_libri"]), True)]),
        riga([("Posizioni in classifica", False), (f"da {n['pos_min']} a {n['pos_max']}", True)]),
        riga([("Parole totali nelle descrizioni", False), (intero(n["parole_totali"]), True)]),
        riga([("Autori diversi", False), (intero(n["n_autori"]), True)]),
        riga([("Case editrici diverse", False),
              (f"{intero(n['n_editori'])} (con almeno {MIN_LIBRI_EDITORE} libri: "
               f"{intero(n['n_editori_visibili'])})", True)]),
        '<tr><th colspan="2">Premi</th></tr>',
        riga([("Libri con premi citati nella descrizione", False),
              (percentuale(n["n_cita_premi"], n["n_libri"]), True)]),
        riga([(f"Libri con autore molto premiato (almeno {SOGLIA_AUTORE_PREMIATO} premi diversi)", False),
              (percentuale(n["n_autore_premiato"], n["n_libri"]), True)]),
        riga([("Correlazione tra premi dell'autore e posizione (Spearman)", False), (corr_premi, True)]),
    ]
    return "<table>\n" + "\n".join(righe) + "\n</table>"


def tabella_vocabolari(n):
    """Tabella con una riga per vocabolario: occorrenze, correlazione, editore che lo usa di più."""
    intestazione = riga([("Vocabolario", False), ("Occorrenze", False), ("Ogni 100 parole", False),
                         ("rho", False), ("p", False),
                         (f"Editore che lo usa di più (almeno {MIN_LIBRI_EDITORE} libri)", False)],
                        intestazione=True)
    righe = [intestazione]
    for v in n["vocabolari"]:
        if v["editore_top"]:
            nome, n_libri, valore = v["editore_top"]
            editore = f"{html.escape(nome)} (n={n_libri}): {num(valore)} ogni 100 parole"
        else:
            editore = "–"
        righe.append(riga([
            (html.escape(nome_leggibile(v["categoria"])), False),
            (intero(v["occorrenze"]), True),
            (num(v["per_100"]), True),
            (num(v["rho"], 2, segno=True), True),
            (p_italiano(v["p"]), True),
            (editore, False),
        ]))
    return "<table>\n" + "\n".join(righe) + "\n</table>"


def sezione_figure():
    """Un blocco <figure> per ogni immagine, con la sua didascalia."""
    blocchi = []
    for file, didascalia in FIGURE:
        blocchi.append(f'<figure>\n<img src="{file}" alt="{file}">\n'
                       f"<figcaption>{didascalia}</figcaption>\n</figure>")
    return "\n".join(blocchi)


def costruisci_pagina(n):
    """Assembla la pagina HTML completa (una grande f-string) e la restituisce come testo."""
    introduzione = (
        "Questo report riassume il progetto «Misurare il gusto». Partendo dalla classifica dei libri "
        "più venduti di IBS, misura quanto le descrizioni promozionali usano cinque tipi di linguaggio "
        "(premi, novità, coinvolgimento del lettore, giudizi positivi, citazioni di giornalisti) e lo "
        "mette in relazione con la posizione in classifica, con i premi degli autori e con le case "
        f"editrici. L'analisi riguarda {intero(n['n_libri'])} libri in un'unica rilevazione: i risultati "
        "descrivono associazioni, non rapporti di causa ed effetto."
    )
    nota_tabella = (
        "rho è la correlazione di Spearman tra l'uso del vocabolario e la posizione in classifica: "
        "positivo = più linguaggio di quel tipo nelle posizioni alte (vicine al primo posto), "
        "negativo = nelle posizioni basse. Se p è inferiore a 0,05 la correlazione si considera "
        "significativa. Le occorrenze sono sommate su tutte le descrizioni."
    )
    testo_editori = (
        f"Nel campione compaiono {intero(n['n_editori'])} case editrici; "
        f"{intero(n['n_editori_visibili'])} hanno almeno {MIN_LIBRI_EDITORE} libri e sono nella mappa. "
        "La mappa mostra, per ciascuna, quanto usa ogni vocabolario rispetto alla media di tutti i libri. "
        "Con pochi libri per editore le differenze possono essere dovute al caso."
    )
    data = datetime.now().strftime("%d/%m/%Y")

    return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Misurare il gusto – Report di sintesi</title>
<style>
{CSS}
</style>
</head>
<body>

<h1>Misurare il gusto</h1>
<p class="sottotitolo">Il linguaggio delle descrizioni e la classifica dei libri più venduti di IBS</p>
<p>{introduzione}</p>

<h2>Numeri</h2>
<h3>Quadro generale</h3>
{tabella_generale(n)}
<h3>Vocabolari</h3>
{tabella_vocabolari(n)}
<p class="nota">{nota_tabella}</p>

<h2>Grafici</h2>
{sezione_figure()}

<h2>Editori</h2>
<p>{testo_editori}</p>
<p><a href="{FILE_EDITORI_HTML}">Apri la tabella interattiva editori e vocabolari</a>
(si apre nel browser; il file deve stare nella stessa cartella di questo report).</p>

<p class="nota">Report generato il {data}.</p>

</body>
</html>
"""


# ---------------------------------------------------------------------
# 5. PROGRAMMA PRINCIPALE
# ---------------------------------------------------------------------
def main():
    # File indispensabili per calcolare i numeri.
    percorso_csv = FILE_CSV if os.path.exists(FILE_CSV) else FILE_CSV_ALTERNATIVO
    mancanti = [f for f in (percorso_csv, FILE_DIZIONARIO, FILE_PREMI) if not os.path.exists(f)]
    if mancanti:
        print("File mancanti, impossibile creare il report: " + ", ".join(mancanti))
        return

    # File da collegare nella pagina: se mancano il report si crea, ma i link non funzionano.
    for file in [f for f, _ in FIGURE] + [FILE_EDITORI_HTML]:
        if not os.path.exists(file):
            print(f"Attenzione: {file} non trovato. Lancia prima lo script che lo crea, "
                  "altrimenti nel report mancherà.")

    categorie = carica_categorie(FILE_DIZIONARIO)
    premi_per_autore = carica_premi_per_autore(FILE_PREMI)
    libri, righe_totali = leggi_libri(percorso_csv)
    if not libri:
        print("Nessun libro con descrizione e posizione trovato nel CSV.")
        return

    numeri = calcola_numeri(libri, righe_totali, categorie, premi_per_autore)
    with open(FILE_REPORT, "w", encoding="utf-8") as file:
        file.write(costruisci_pagina(numeri))
    print(f"Report salvato in {FILE_REPORT} ({numeri['n_libri']} libri analizzati)")


if __name__ == "__main__":
    main()