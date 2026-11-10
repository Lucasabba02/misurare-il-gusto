# -*- coding: utf-8 -*-
"""
Premi e posizione in classifica: grafico a barre per fasce di posizione.

Per ogni libro lo script stabilisce due cose:
  1. se la DESCRIZIONE cita il linguaggio dei premi (almeno un termine della categoria
     "premi" di dizionario.json);
  2. se l'AUTORE è molto premiato (almeno SOGLIA_AUTORE_PREMIATO premi diversi in
     premi_arricchiti.json).

Poi divide la classifica in fasce (1-10, 11-20, ...) e, per ogni fascia, disegna la
percentuale di libri che:
  - hanno premi citati nella descrizione;
  - hanno un autore molto premiato;
  - hanno almeno una delle due cose.
Se questi libri sono più frequenti nelle fasce alte, le barre scendono da sinistra a destra.

Requisiti:  pip install matplotlib
Va messo nella stessa cartella di grafico_occorrenze.py (da cui riusa le funzioni di
conteggio), di dizionario.json, classifica_ibs.csv e premi_arricchiti.json.

Uso:
    python distribuzione_premi.py
"""

# ---------------------------------------------------------------------
# IMPORTAZIONI
# ---------------------------------------------------------------------
import csv                                   # lettura del CSV
import json                                  # lettura del JSON dei premi

import matplotlib.pyplot as plt              # grafico

# Riuso funzioni e impostazioni del grafico precedente: così il linguaggio dei
# premi è misurato esattamente come prima.
from grafico_occorrenze import (
    COLONNA_DESCRIZIONE, FILE_CSV, FILE_DIZIONARIO, SEPARATORE_CSV,
    carica_categorie, conta_termini, tokenizza,
)


# ---------------------------------------------------------------------
# 1. IMPOSTAZIONI
# ---------------------------------------------------------------------
FILE_PREMI = "premi_arricchiti.json"
FILE_GRAFICO = "distribuzione_premi.png"
COLONNA_POSIZIONE = "posizione"
COLONNA_AUTORE = "autore"

AMPIEZZA_FASCIA = 10             # quante posizioni per fascia (1-10, 11-20, ...)
SOGLIA_AUTORE_PREMIATO = 5       # premi diversi necessari per dire che un autore è "molto premiato"


# ---------------------------------------------------------------------
# 2. LETTURA DEI DATI
# ---------------------------------------------------------------------
def leggi_libri(percorso):
    """
    Legge il CSV e restituisce una lista di (posizione, [autori], descrizione).
    Se una cella autore contiene più nomi ("A; B") vengono separati.
    Scarta i libri senza posizione numerica; conta quelli senza descrizione.
    """
    libri, senza_descrizione = [], 0
    with open(percorso, newline="", encoding="utf-8-sig") as file:
        for riga in csv.DictReader(file, delimiter=SEPARATORE_CSV):
            try:
                posizione = int(riga[COLONNA_POSIZIONE])
            except (KeyError, ValueError):
                continue
            testo = (riga.get(COLONNA_DESCRIZIONE) or "").strip()
            if not testo:
                senza_descrizione += 1
                continue
            autori = [a.strip() for a in (riga.get(COLONNA_AUTORE) or "").split(";") if a.strip()]
            libri.append((posizione, autori, testo))
    return libri, senza_descrizione


def carica_premi_per_autore(percorso):
    """
    Legge premi_arricchiti.json e restituisce {autore: numero di premi DIVERSI}.
    Conto i nomi diversi (non le singole voci) perché lo stesso premio può comparire
    in più anni. Gli autori senza premi nel file valgono 0.
    """
    with open(percorso, encoding="utf-8") as file:
        dati = json.load(file)
    premi = {}
    for record in dati:
        nomi = {p["premio"].strip().lower() for p in (record.get("premi") or []) if p.get("premio")}
        premi[record["autore"]] = len(nomi)
    return premi


# ---------------------------------------------------------------------
# 3. CLASSIFICAZIONE DEI LIBRI
# ---------------------------------------------------------------------
def descrizione_cita_premi(testo, gruppi_premi):
    """True se la descrizione contiene almeno un termine della categoria "premi"."""
    parole = tokenizza(testo)                                # parole in minuscolo
    for termini, lunghezza_max, _ in gruppi_premi:
        if sum(conta_termini(parole, termini, lunghezza_max).values()) > 0:
            return True
    return False


def premi_dell_autore(autori, premi_per_autore):
    """Numero di premi dell'autore più premiato del libro (un libro può avere più autori)."""
    return max((premi_per_autore.get(a, 0) for a in autori), default=0)


def indice_fascia(posizione):
    """Numero della fascia di una posizione: 1-10 -> 0, 11-20 -> 1, ..."""
    return (posizione - 1) // AMPIEZZA_FASCIA


# ---------------------------------------------------------------------
# 4. CALCOLO PER FASCIA
# ---------------------------------------------------------------------
def calcola_fasce(libri, gruppi_premi, premi_per_autore):
    """
    Per ogni fascia di posizioni restituisce un dizionario con:
      etichetta, n (libri della fascia), n_descrizione, n_autore, n_almeno_uno.
    """
    fasce = {}
    posizione_massima = max(pos for pos, _, _ in libri)

    for posizione, autori, testo in libri:
        i = indice_fascia(posizione)
        if i not in fasce:
            inizio = i * AMPIEZZA_FASCIA + 1
            fine = min((i + 1) * AMPIEZZA_FASCIA, posizione_massima)
            fasce[i] = {"etichetta": f"{inizio}–{fine}", "n": 0,
                        "n_descrizione": 0, "n_autore": 0, "n_almeno_uno": 0}
        f = fasce[i]

        cita_premi = descrizione_cita_premi(testo, gruppi_premi)
        autore_premiato = premi_dell_autore(autori, premi_per_autore) >= SOGLIA_AUTORE_PREMIATO

        f["n"] += 1
        f["n_descrizione"] += cita_premi
        f["n_autore"] += autore_premiato
        f["n_almeno_uno"] += (cita_premi or autore_premiato)

    return [fasce[i] for i in sorted(fasce)]                 # in ordine di posizione


# ---------------------------------------------------------------------
# 5. RISULTATI
# ---------------------------------------------------------------------
def stampa_tabella(fasce):
    """Stampa i conteggi per fascia."""
    print(f"\n{'fascia':>8}{'libri':>7}{'premi in descr.':>17}{'autore premiato':>17}{'almeno uno':>12}")
    for f in fasce:
        print(f"{f['etichetta']:>8}{f['n']:>7}{f['n_descrizione']:>17}{f['n_autore']:>17}{f['n_almeno_uno']:>12}")


def stampa_autori_piu_premiati(libri, premi_per_autore, quanti=8):
    """Stampa gli autori più premiati presenti in classifica, con la loro posizione migliore."""
    migliore = {}                                            # {autore: posizione migliore}
    for posizione, autori, _ in libri:
        for autore in autori:
            migliore[autore] = min(posizione, migliore.get(autore, posizione))
    ordinati = sorted(migliore, key=lambda a: premi_per_autore.get(a, 0), reverse=True)[:quanti]
    print("\nAutori più premiati presenti in classifica (premi diversi nel JSON):")
    for autore in ordinati:
        print(f"  {premi_per_autore.get(autore, 0):3} premi  -  {autore}  (posizione migliore: {migliore[autore]})")


def disegna_grafico(fasce, percorso):
    """Grafico a barre raggruppate: tre barre (percentuali) per ogni fascia di posizioni."""
    etichette = [f"{f['etichetta']}\n(n={f['n']})" for f in fasce]        # n = libri della fascia
    serie = [
        ("Premi citati nella descrizione", "n_descrizione", "#4C78A8"),
        (f"Autore molto premiato (≥{SOGLIA_AUTORE_PREMIATO} premi)", "n_autore", "#F58518"),
        ("Almeno uno dei due", "n_almeno_uno", "#54A24B"),
    ]

    larghezza = 0.27                                         # larghezza di ogni barra
    fig, ax = plt.subplots(figsize=(10, 6))
    for k, (nome, chiave, colore) in enumerate(serie):
        # Le tre barre di una fascia sono affiancate: la prima a sinistra, l'ultima a destra.
        posizioni_x = [i + (k - 1) * larghezza for i in range(len(fasce))]
        percentuali = [100 * f[chiave] / f["n"] for f in fasce]
        barre = ax.bar(posizioni_x, percentuali, larghezza, label=nome, color=colore)
        ax.bar_label(barre, fmt="%.0f%%", padding=2, fontsize=8)

    ax.set_xticks(range(len(fasce)))
    ax.set_xticklabels(etichette)
    ax.set_xlabel("Fascia di posizione in classifica")
    ax.set_ylabel("Libri della fascia (%)")
    ax.set_title("Premi e posizione in classifica: quota di libri per fascia di posizione")
    ax.set_ylim(0, 110)
    ax.legend(loc="upper right", frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.99, 0.01, "Autori senza premi nel JSON contati come non molto premiati",
             ha="right", fontsize=8)

    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(percorso, dpi=200)
    plt.close(fig)


# ---------------------------------------------------------------------
# 6. PROGRAMMA PRINCIPALE
# ---------------------------------------------------------------------
def main():
    gruppi_premi = carica_categorie(FILE_DIZIONARIO)["premi"]
    premi_per_autore = carica_premi_per_autore(FILE_PREMI)
    libri, senza_descrizione = leggi_libri(FILE_CSV)
    if not libri:
        print("Nessun libro con descrizione trovato nel CSV.")
        return

    print(f"Libri analizzati: {len(libri)} (esclusi {senza_descrizione} senza descrizione)")
    fasce = calcola_fasce(libri, gruppi_premi, premi_per_autore)

    stampa_tabella(fasce)
    stampa_autori_piu_premiati(libri, premi_per_autore)
    disegna_grafico(fasce, FILE_GRAFICO)
    print(f"\nGrafico salvato in {FILE_GRAFICO}")


if __name__ == "__main__":
    main()