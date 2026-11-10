# -*- coding: utf-8 -*-
"""
Correlazione tra il linguaggio delle descrizioni e la posizione in classifica.

Per ogni libro lo script calcola le occorrenze ogni 100 parole di ciascuna categoria
del dizionario (la stessa misura di grafico_occorrenze.py), poi calcola per ogni
categoria la correlazione di Spearman tra quella misura e la posizione in classifica.

Come leggere il risultato:
  - rho è un numero tra -1 e +1.
        rho positivo: i libri con più linguaggio di quella categoria stanno più in alto in classifica.
        rho negativo: stanno più in basso.
        rho vicino a 0: nessuna relazione.
  - p dice quanto è probabile ottenere un rho così per puro caso. Se p è sotto 0,05
    la correlazione si considera "significativa" (poco probabile che sia casuale).

Requisiti:  pip install scipy matplotlib
Va messo nella stessa cartella di grafico_occorrenze.py (da cui riusa le funzioni di
conteggio), di dizionario.json e di classifica_ibs.csv.

Uso:
    python correlazione_classifica.py
"""

# ---------------------------------------------------------------------
# IMPORTAZIONI
# ---------------------------------------------------------------------
import csv                                   # lettura/scrittura CSV
import textwrap                              # nomi lunghi sull'asse x
from collections import Counter              # contatore dei termini

import matplotlib.pyplot as plt              # grafico
from scipy.stats import spearmanr            # correlazione di Spearman

# Riuso le funzioni e le impostazioni del grafico precedente, così la misura è identica.
from grafico_occorrenze import (
    COLONNA_DESCRIZIONE, FILE_CSV, FILE_DIZIONARIO, SEPARATORE_CSV,
    carica_categorie, conta_termini, tokenizza,
)


# ---------------------------------------------------------------------
# 1. IMPOSTAZIONI
# ---------------------------------------------------------------------
COLONNA_POSIZIONE = "posizione"
FILE_RISULTATI = "correlazioni.csv"          # tabella dei risultati
FILE_GRAFICO = "correlazioni.png"            # grafico delle correlazioni
SOGLIA_P = 0.05                              # sotto questo valore la correlazione è "significativa"
MIN_LIBRI = 10                               # con meno libri la correlazione non è affidabile


# ---------------------------------------------------------------------
# 2. LETTURA DEI DATI
# ---------------------------------------------------------------------
def leggi_libri(percorso):
    """
    Legge il CSV e restituisce una lista di (posizione, descrizione).
    Scarta i libri senza descrizione o senza posizione numerica.
    """
    libri = []
    with open(percorso, newline="", encoding="utf-8-sig") as file:
        for riga in csv.DictReader(file, delimiter=SEPARATORE_CSV):
            testo = (riga.get(COLONNA_DESCRIZIONE) or "").strip()
            try:
                posizione = int(riga[COLONNA_POSIZIONE])
            except (KeyError, ValueError):
                continue
            if testo:
                libri.append((posizione, testo))
    return libri


# ---------------------------------------------------------------------
# 3. MISURA: OCCORRENZE OGNI 100 PAROLE PER LIBRO
# ---------------------------------------------------------------------
def occorrenze_per_100_parole(testo, categorie):
    """
    Restituisce {categoria: occorrenze ogni 100 parole} per UNA descrizione.
    Occorrenze ogni 100 parole = (occorrenze della categoria / parole del testo) * 100.
    """
    parole_minuscole = tokenizza(testo)
    parole_originali = tokenizza(testo, minuscolo=False)    # serve per le testate (maiuscole)
    n_parole = len(parole_minuscole)

    valori = {}
    for nome, gruppi in categorie.items():
        conteggio = Counter()                               # {termine: quante volte compare}
        for termini, lunghezza_max, sensibile in gruppi:
            parole = parole_originali if sensibile else parole_minuscole
            conteggio.update(conta_termini(parole, termini, lunghezza_max))
        valori[nome] = 100 * sum(conteggio.values()) / n_parole if n_parole else 0.0
    return valori


# ---------------------------------------------------------------------
# 4. CORRELAZIONE
# ---------------------------------------------------------------------
def calcola_correlazione(nome, valori, posizioni):
    """
    Correlazione di Spearman tra le occorrenze (una per libro) e la posizione in classifica.
    Uso -posizione al posto di posizione: così il 1° posto vale più del 40°, e una
    correlazione POSITIVA significa "più linguaggio di questo tipo, posizione più alta".
    """
    risultato = {
        "categoria": nome,
        "libri_con_termini": sum(1 for v in valori if v > 0),   # libri con almeno un termine
        "rho": None,
        "p": None,
    }
    # Se la categoria non compare mai (o compare sempre uguale) la correlazione non esiste.
    if len(set(valori)) > 1:
        rho, p = spearmanr(valori, [-pos for pos in posizioni])
        risultato["rho"], risultato["p"] = float(rho), float(p)
    return risultato


def commenta(r):
    """Frase di sintesi per una categoria."""
    if r["rho"] is None:
        return "correlazione non calcolabile (nessuna variazione tra i libri)"
    if r["p"] >= SOGLIA_P:
        return "correlazione non significativa (può essere dovuta al caso)"
    if r["rho"] > 0:
        return "correlazione positiva significativa: più linguaggio di questo tipo, posizione più alta"
    return "correlazione negativa significativa: più linguaggio di questo tipo, posizione più bassa"


# ---------------------------------------------------------------------
# 5. RISULTATI: TABELLA, CSV, GRAFICO
# ---------------------------------------------------------------------
def formatta_p(p):
    """Scrive i valori p molto piccoli come '<0.001' invece di '0.000'."""
    if p is None:
        return "-"
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def stampa_risultati(risultati, n_libri):
    """Stampa la tabella dei risultati."""
    print(f"\nLibri analizzati: {n_libri}\n")
    print(f"{'categoria':32}{'libri con termini':>19}{'rho':>9}{'p':>9}")
    for r in risultati:
        rho = "-" if r["rho"] is None else f"{r['rho']:+.3f}"
        print(f"{r['categoria']:32}{r['libri_con_termini']:>19}{rho:>9}{formatta_p(r['p']):>9}")
    print()
    for r in risultati:
        print(f"- {r['categoria']}: {commenta(r)}")


def salva_csv(risultati, percorso):
    """Salva i risultati in un CSV (separatore ';', apribile in Excel)."""
    colonne = ["categoria", "libri_con_termini", "rho", "p"]
    with open(percorso, "w", newline="", encoding="utf-8-sig") as file:
        scrittore = csv.DictWriter(file, fieldnames=colonne, delimiter=SEPARATORE_CSV)
        scrittore.writeheader()
        for r in risultati:
            scrittore.writerow({c: ("" if r[c] is None else r[c]) for c in colonne})


def disegna_grafico(risultati, n_libri, percorso):
    """Grafico a barre di rho per ogni categoria (asterisco = correlazione significativa)."""
    nomi = [textwrap.fill(r["categoria"].replace("_", " "), 14) for r in risultati]
    valori = [r["rho"] or 0.0 for r in risultati]            # categoria non calcolabile -> nessuna barra
    colori = ["#4C78A8" if v >= 0 else "#E45756" for v in valori]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    barre = ax.bar(nomi, valori, color=colori)

    # Scrivo il valore di rho vicino a ogni barra, con * se significativo.
    for barra, r in zip(barre, risultati):
        if r["rho"] is None:
            testo = "n.c."
        else:
            testo = f"{r['rho']:+.2f}" + ("*" if r["p"] < SOGLIA_P else "")
        altezza = barra.get_height()
        ax.annotate(testo, (barra.get_x() + barra.get_width() / 2, altezza),
                    xytext=(0, 4 if altezza >= 0 else -4), textcoords="offset points",
                    ha="center", va="bottom" if altezza >= 0 else "top")

    ax.axhline(0, color="black", linewidth=0.8)             # linea dello zero (nessuna correlazione)
    ax.set_xlabel("Categorie di vocabolario")
    ax.set_ylabel("Correlazione di Spearman (rho)\npositiva = posizione più alta in classifica")
    ax.set_title(f"Linguaggio delle descrizioni e posizione in classifica ({n_libri} libri)")
    limite = max(0.3, max(abs(v) for v in valori) * 1.25)
    ax.set_ylim(-limite, limite)
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.99, 0.01, "* correlazione significativa (p < 0,05); n.c. = non calcolabile",
             ha="right", fontsize=8)

    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(percorso, dpi=200)
    plt.close(fig)


# ---------------------------------------------------------------------
# 6. PROGRAMMA PRINCIPALE
# ---------------------------------------------------------------------
def main():
    categorie = carica_categorie(FILE_DIZIONARIO)
    libri = leggi_libri(FILE_CSV)
    if len(libri) < MIN_LIBRI:
        print(f"Libri utilizzabili: {len(libri)}. Ne servono almeno {MIN_LIBRI}.")
        return

    posizioni = [posizione for posizione, _ in libri]
    valori_libri = [occorrenze_per_100_parole(testo, categorie) for _, testo in libri]

    # Una correlazione per ogni categoria del dizionario.
    risultati = [calcola_correlazione(nome, [v[nome] for v in valori_libri], posizioni)
                 for nome in categorie]

    stampa_risultati(risultati, len(libri))
    salva_csv(risultati, FILE_RISULTATI)
    disegna_grafico(risultati, len(libri), FILE_GRAFICO)
    print(f"\nRisultati salvati in {FILE_RISULTATI} e {FILE_GRAFICO}")


if __name__ == "__main__":
    main()