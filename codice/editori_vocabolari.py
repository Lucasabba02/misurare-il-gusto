# -*- coding: utf-8 -*-
"""
Quale linguaggio usa ciascuna casa editrice nelle descrizioni dei suoi libri?

Lo script produce un grafico interattivo (file HTML): una mappa di calore con
  - una RIGA per ogni casa editrice (campo "editore" del CSV);
  - una COLONNA per ogni categoria del dizionario (premi, novità, coinvolgimento...).
Ogni cella mostra le occorrenze ogni 100 parole di quella categoria nelle descrizioni
dei libri della casa editrice. Il COLORE indica quanto la casa editrice si discosta dalla
media di tutti i libri: rosso = usa quel linguaggio PIÙ della media, blu = MENO.
Passando il mouse su una cella si vedono i numeri precisi.

L'editore è una categoria (un nome), non un numero: per questo non si calcola un
coefficiente di correlazione, ma si confronta il profilo di ogni casa editrice con la media.

Requisiti:  pip install plotly matplotlib
Va messo nella stessa cartella di grafico_occorrenze.py (da cui riusa le funzioni di
conteggio), di dizionario.json e del CSV della classifica.

Uso:
    python editori_vocabolari.py
"""

# ---------------------------------------------------------------------
# IMPORTAZIONI
# ---------------------------------------------------------------------
import csv                                   # lettura del CSV
import os                                    # per controllare se un file esiste
import textwrap                              # per mandare a capo i nomi lunghi
from collections import Counter              # contatore: {chiave: numero di volte}

import plotly.graph_objects as go            # grafici interattivi

# Riuso le funzioni del grafico precedente, così il conteggio è identico.
from grafico_occorrenze import (
    COLONNA_DESCRIZIONE, FILE_DIZIONARIO, SEPARATORE_CSV,
    carica_categorie, conta_termini, tokenizza,
)


# ---------------------------------------------------------------------
# 1. IMPOSTAZIONI
# ---------------------------------------------------------------------
FILE_CSV = "classifica_libri.csv"            # nome indicato nella richiesta
FILE_CSV_ALTERNATIVO = "classifica_ibs.csv"  # nome usato dagli script precedenti (se il primo non esiste)
FILE_HTML = "editori_vocabolari.html"
COLONNA_EDITORE = "editore"

# Si mostrano solo le case editrici con almeno questo numero di libri: con uno o due libri
# la "media" di un editore dipende troppo dal caso. Si può abbassare se i libri sono pochi.
MIN_LIBRI_EDITORE = 3

# Facoltativo: per unire sotto un unico nome editori scritti in modo diverso o marchi dello
# stesso gruppo. Esempio:  {"Einaudi Stile Libero": "Einaudi", "Mondadori Libri": "Mondadori"}
ACCORPAMENTI = {}
ACCORPAMENTI_MINUSCOLI = {k.lower(): v for k, v in ACCORPAMENTI.items()}

SATURAZIONE_COLORE = 100                     # oltre ±100% rispetto alla media il colore non cambia più


# ---------------------------------------------------------------------
# 2. LETTURA DEI DATI
# ---------------------------------------------------------------------
def normalizza_editore(nome):
    """Toglie spazi in più e applica gli accorpamenti scelti."""
    nome = " ".join(nome.split())
    return ACCORPAMENTI_MINUSCOLI.get(nome.lower(), nome)


def leggi_libri(percorso):
    """
    Legge il CSV e restituisce una lista di (editore, descrizione).
    Scarta i libri senza editore o senza descrizione e dice quanti sono.
    """
    libri, senza_editore, senza_descrizione = [], 0, 0
    with open(percorso, newline="", encoding="utf-8-sig") as file:
        for riga in csv.DictReader(file, delimiter=SEPARATORE_CSV):
            editore = normalizza_editore(riga.get(COLONNA_EDITORE) or "")
            testo = (riga.get(COLONNA_DESCRIZIONE) or "").strip()
            if not editore:
                senza_editore += 1
            elif not testo:
                senza_descrizione += 1
            else:
                libri.append((editore, testo))
    return libri, senza_editore, senza_descrizione


# ---------------------------------------------------------------------
# 3. CONTEGGIO PER CASA EDITRICE
# ---------------------------------------------------------------------
def occorrenze_per_categoria(testo, categorie):
    """Restituisce (Counter {categoria: occorrenze}, numero di parole) per una descrizione."""
    parole_minuscole = tokenizza(testo)
    parole_originali = tokenizza(testo, minuscolo=False)     # serve per le testate (maiuscole)

    occorrenze = Counter()
    for nome, gruppi in categorie.items():
        for termini, lunghezza_max, sensibile in gruppi:
            parole = parole_originali if sensibile else parole_minuscole
            occorrenze[nome] += sum(conta_termini(parole, termini, lunghezza_max).values())
    return occorrenze, len(parole_minuscole)


def raggruppa_per_editore(libri, categorie):
    """
    Somma, per ogni casa editrice, libri, parole e occorrenze di ogni categoria.
    Restituisce (dati per editore, totale di tutti i libri). Il totale è la "media" di confronto.
    """
    nuova_scheda = lambda nome: {"nome": nome, "n_libri": 0, "n_parole": 0, "occorrenze": Counter()}
    editori = {}
    totale = nuova_scheda("Tutti i libri")

    for editore, testo in libri:
        occorrenze, n_parole = occorrenze_per_categoria(testo, categorie)
        # Lo stesso editore scritto con maiuscole diverse ("einaudi", "Einaudi") è lo stesso.
        scheda = editori.setdefault(editore.lower(), nuova_scheda(editore))
        for s in (scheda, totale):
            s["n_libri"] += 1
            s["n_parole"] += n_parole
            s["occorrenze"].update(occorrenze)
    return editori, totale


def per_100_parole(occorrenze, n_parole):
    """Occorrenze ogni 100 parole."""
    return 100 * occorrenze / n_parole if n_parole else 0.0


# ---------------------------------------------------------------------
# 4. GRAFICO INTERATTIVO
# ---------------------------------------------------------------------
def disegna_grafico(editori, totale, categorie, percorso):
    """Costruisce la mappa di calore interattiva e la salva in un file HTML."""
    # Editori da mostrare: almeno MIN_LIBRI_EDITORE libri, dal più rappresentato al meno.
    righe = sorted((s for s in editori.values() if s["n_libri"] >= MIN_LIBRI_EDITORE),
                   key=lambda s: (-s["n_libri"], s["nome"]))
    nomi_categorie = list(categorie)

    # Valore medio di ogni categoria su TUTTI i libri (la linea di confronto).
    medie = {c: per_100_parole(totale["occorrenze"][c], totale["n_parole"]) for c in nomi_categorie}

    colori, testi, dettagli = [], [], []
    for scheda in righe:
        riga_colori, riga_testi, riga_dettagli = [], [], []
        for c in nomi_categorie:
            valore = per_100_parole(scheda["occorrenze"][c], scheda["n_parole"])
            if medie[c] > 0:
                scostamento = (valore / medie[c] - 1) * 100       # +50 = usa il 50% in più della media
                riga_colori.append(scostamento)
                riga_testi.append(f"{valore:.2f}")
            else:                                                 # categoria mai presente: nessun confronto
                riga_colori.append(None)
                riga_testi.append("–")
            riga_dettagli.append([valore, medie[c], scheda["occorrenze"][c], scheda["n_parole"]])
        colori.append(riga_colori)
        testi.append(riga_testi)
        dettagli.append(riga_dettagli)

    etichette_x = [textwrap.fill(c.replace("_", " "), 16).replace("\n", "<br>") for c in nomi_categorie]
    etichette_y = [f"{s['nome']} (n={s['n_libri']})" for s in righe]     # n = libri dell'editore

    fig = go.Figure(go.Heatmap(
        z=colori, x=etichette_x, y=etichette_y,
        text=testi, texttemplate="%{text}",                   # numero scritto dentro ogni cella
        customdata=dettagli,
        hovertemplate=("<b>%{y}</b><br>Categoria: %{x}<br>"
                       "Occorrenze ogni 100 parole: %{customdata[0]:.2f}<br>"
                       "Media di tutti i libri: %{customdata[1]:.2f}<br>"
                       "Scostamento dalla media: %{z:+.0f}%<br>"
                       "Occorrenze: %{customdata[2]} su %{customdata[3]} parole"
                       "<extra></extra>"),
        zmin=-SATURAZIONE_COLORE, zmax=SATURAZIONE_COLORE, zmid=0,
        colorscale=[[0, "#2166AC"], [0.5, "#F7F7F7"], [1, "#B2182B"]],   # blu - bianco - rosso
        colorbar=dict(title="Scostamento<br>dalla media", ticksuffix="%"),
        xgap=2, ygap=2,
    ))

    fig.update_layout(
        title=dict(text="Linguaggio delle descrizioni per casa editrice", x=0.5, y=0.96),
        xaxis=dict(title="Categoria di vocabolario", side="top"),
        yaxis=dict(title="Casa editrice (n = libri in classifica)", autorange="reversed"),
        height=max(450, 220 + 45 * len(righe)),
        margin=dict(t=170, b=90, l=60, r=40),
        plot_bgcolor="white",
        annotations=[dict(
            xref="paper", yref="paper", x=0, y=-0.04, xanchor="left", yanchor="top", showarrow=False,
            font=dict(size=11),
            text=("Numeri nelle celle: occorrenze ogni 100 parole. Colore: scostamento dalla media di tutti i libri "
                  "(rosso = più della media, blu = meno).<br>"
                  f"Solo case editrici con almeno {MIN_LIBRI_EDITORE} libri."))],
    )
    # include_plotlyjs=True inserisce la libreria nel file: l'HTML funziona anche senza connessione.
    fig.write_html(percorso, include_plotlyjs=True)


# ---------------------------------------------------------------------
# 5. PROGRAMMA PRINCIPALE
# ---------------------------------------------------------------------
def main():
    percorso_csv = FILE_CSV
    if not os.path.exists(percorso_csv) and os.path.exists(FILE_CSV_ALTERNATIVO):
        percorso_csv = FILE_CSV_ALTERNATIVO
        print(f"{FILE_CSV} non trovato: uso {FILE_CSV_ALTERNATIVO}")

    categorie = carica_categorie(FILE_DIZIONARIO)
    libri, senza_editore, senza_descrizione = leggi_libri(percorso_csv)
    if not libri:
        print("Nessun libro con editore e descrizione trovato nel CSV.")
        return

    editori, totale = raggruppa_per_editore(libri, categorie)
    mostrati = [s for s in editori.values() if s["n_libri"] >= MIN_LIBRI_EDITORE]

    print(f"Libri analizzati: {len(libri)} (esclusi {senza_editore} senza editore, "
          f"{senza_descrizione} senza descrizione)")
    print(f"Case editrici: {len(editori)} in totale, {len(mostrati)} con almeno "
          f"{MIN_LIBRI_EDITORE} libri (mostrate nel grafico)")
    if not mostrati:
        piu_grandi = sorted(editori.values(), key=lambda s: -s["n_libri"])[:5]
        print("Nessuna casa editrice raggiunge la soglia. Le più rappresentate sono: "
              + ", ".join(f"{s['nome']} ({s['n_libri']})" for s in piu_grandi))
        print("Abbassa MIN_LIBRI_EDITORE all'inizio dello script.")
        return

    disegna_grafico(editori, totale, categorie, FILE_HTML)
    print(f"Grafico salvato in {FILE_HTML} (aprilo con un browser)")


if __name__ == "__main__":
    main()