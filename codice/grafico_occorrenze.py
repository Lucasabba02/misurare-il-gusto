# -*- coding: utf-8 -*-
"""
Grafico a barre delle occorrenze ogni 100 parole per ciascuna categoria del dizionario.

Cosa fa lo script:
  1. legge le categorie e i termini da dizionario.json;
  2. legge le descrizioni dei libri da classifica_ibs.csv;
  3. conta, con collections.Counter, quante volte compaiono i termini di ogni
     categoria in tutte le descrizioni;
  4. calcola le occorrenze ogni 100 parole:
         (occorrenze totali della categoria / parole totali di tutte le descrizioni) * 100
  5. disegna il grafico (asse x: categorie, asse y: occorrenze ogni 100 parole)
     e lo salva in occorrenze.png.

Uso (stessa cartella di dizionario.json e classifica_ibs.csv):
    python grafico_occorrenze.py
"""

# ---------------------------------------------------------------------
# IMPORTAZIONI
# ---------------------------------------------------------------------
import csv                            # lettura del CSV
import json                           # lettura del dizionario
import re                             # per spezzare i testi in parole
import textwrap                       # per mandare a capo i nomi lunghi sull'asse x
from collections import Counter       # contatore: dizionario {termine: numero di volte}

import matplotlib.pyplot as plt       # libreria per i grafici


# ---------------------------------------------------------------------
# 1. IMPOSTAZIONI
# ---------------------------------------------------------------------
FILE_DIZIONARIO = "dizionario.json"
FILE_CSV = "classifica_ibs.csv"
SEPARATORE_CSV = ";"
COLONNA_DESCRIZIONE = "descrizione"        # colonna del CSV con il testo da analizzare
FILE_GRAFICO = "occorrenze.png"


# ---------------------------------------------------------------------
# 2. LETTURA DEI DATI
# ---------------------------------------------------------------------
def tokenizza(testo, minuscolo=True):
    """
    Spezza un testo in parole. Una "parola" è una sequenza di lettere o cifre:
    spazi, punteggiatura e apostrofi la separano ("dell'anno" diventa "dell" + "anno").
    Con minuscolo=True tutto viene scritto in minuscolo, così "Premio" e "premio"
    sono la stessa parola.
    """
    if minuscolo:
        testo = testo.lower()
    return re.findall(r"\w+", testo)


def prepara_termini(termini, sensibile_maiuscole):
    """
    Trasforma una lista di termini in una coppia (insieme di termini, lunghezza massima).
    Ogni termine diventa una tupla di parole: "nuova edizione" -> ("nuova", "edizione").
    Uso la stessa funzione tokenizza() sia per i testi sia per i termini, così
    apostrofi e punteggiatura vengono trattati allo stesso modo.
    """
    insieme = {tuple(tokenizza(t, minuscolo=not sensibile_maiuscole)) for t in termini}
    insieme.discard(())                                   # scarto eventuali termini vuoti
    lunghezza_max = max(len(t) for t in insieme)
    return insieme, lunghezza_max


def carica_categorie(percorso):
    """
    Legge dizionario.json e restituisce {categoria: [gruppi]}, dove ogni gruppo è
    (insieme di termini, lunghezza massima, sensibile alle maiuscole).
    Quasi tutte le categorie hanno un solo gruppo. L'ultima è divisa in due:
      - "testate" (nomi di giornali): si cercano rispettando maiuscole e minuscole;
      - "espressioni": si cercano senza distinguere maiuscole e minuscole.
    """
    with open(percorso, encoding="utf-8") as file:
        dizionario = json.load(file)

    categorie = {}
    for nome, contenuto in dizionario.items():
        if isinstance(contenuto, dict):                   # categoria con sottoliste
            gruppi = []
            for sotto_nome, termini in contenuto.items():
                sensibile = (sotto_nome == "testate")
                gruppi.append((*prepara_termini(termini, sensibile), sensibile))
        else:                                             # categoria con una lista semplice
            gruppi = [(*prepara_termini(contenuto, False), False)]
        categorie[nome] = gruppi
    return categorie


def leggi_descrizioni(percorso):
    """Legge il CSV e restituisce la lista dei testi delle descrizioni non vuote."""
    with open(percorso, newline="", encoding="utf-8-sig") as file:
        righe = csv.DictReader(file, delimiter=SEPARATORE_CSV)
        descrizioni = [r.get(COLONNA_DESCRIZIONE, "") or "" for r in righe]
    return [d for d in descrizioni if d.strip()]


# ---------------------------------------------------------------------
# 3. CONTEGGIO
# ---------------------------------------------------------------------
def conta_termini(parole, termini, lunghezza_max):
    """
    Conta i termini del dizionario in una lista di parole e restituisce un Counter
    {termine: quante volte compare}.
    Si scorre il testo da sinistra a destra: a ogni posizione si prova prima il termine
    più lungo possibile. Così "nuova edizione" conta UNA volta (come "nuova edizione")
    e non due (come "nuova" più "nuova edizione"), e ogni parola viene contata una volta sola.
    """
    trovati = Counter()
    i = 0
    while i < len(parole):
        # Provo da lunghezza_max parole fino a 1 parola.
        for n in range(min(lunghezza_max, len(parole) - i), 0, -1):
            candidato = tuple(parole[i:i + n])
            if candidato in termini:
                trovati[" ".join(candidato)] += 1
                i += n                                    # salto le parole appena riconosciute
                break
        else:                                             # nessun termine trovato qui
            i += 1                                        # passo alla parola successiva
    return trovati


def calcola_occorrenze(categorie, descrizioni):
    """
    Conta le occorrenze di ogni categoria in tutte le descrizioni.
    Restituisce (Counter per categoria, numero totale di parole).
    """
    occorrenze = {nome: Counter() for nome in categorie}  # un Counter per ogni categoria
    parole_totali = 0

    for testo in descrizioni:
        parole_minuscole = tokenizza(testo)               # per i termini senza distinzione di maiuscole
        parole_originali = tokenizza(testo, minuscolo=False)   # per le testate
        parole_totali += len(parole_minuscole)

        for nome, gruppi in categorie.items():
            for termini, lunghezza_max, sensibile in gruppi:
                parole = parole_originali if sensibile else parole_minuscole
                # Counter.update() somma i conteggi nuovi a quelli già presenti.
                occorrenze[nome].update(conta_termini(parole, termini, lunghezza_max))

    return occorrenze, parole_totali


# ---------------------------------------------------------------------
# 4. GRAFICO
# ---------------------------------------------------------------------
def disegna_grafico(valori, n_descrizioni, parole_totali, percorso):
    """Disegna il grafico a barre e lo salva in un file immagine."""
    # Nomi leggibili sull'asse x: via i trattini bassi e a capo ogni 14 caratteri.
    etichette = [textwrap.fill(nome.replace("_", " "), 14) for nome in valori]
    altezze = list(valori.values())

    fig, ax = plt.subplots(figsize=(9, 5.5))
    barre = ax.bar(etichette, altezze, color="#4C78A8")
    ax.bar_label(barre, fmt="%.2f", padding=3)            # scrive il valore sopra ogni barra

    ax.set_xlabel("Categorie di vocabolario")
    ax.set_ylabel("Occorrenze ogni 100 parole")
    ax.set_title(f"Occorrenze ogni 100 parole nelle descrizioni "
                 f"({n_descrizioni} libri, {parole_totali} parole)")
    ax.set_ylim(0, (max(altezze) * 1.15) or 1)            # spazio sopra la barra più alta
    ax.spines[["top", "right"]].set_visible(False)        # bordo più pulito

    fig.tight_layout()
    fig.savefig(percorso, dpi=200)                        # dpi = risoluzione dell'immagine
    plt.close(fig)


# ---------------------------------------------------------------------
# 5. PROGRAMMA PRINCIPALE
# ---------------------------------------------------------------------
def main():
    categorie = carica_categorie(FILE_DIZIONARIO)
    descrizioni = leggi_descrizioni(FILE_CSV)
    if not descrizioni:
        print(f"Nessuna descrizione trovata nella colonna '{COLONNA_DESCRIZIONE}' di {FILE_CSV}.")
        return

    occorrenze, parole_totali = calcola_occorrenze(categorie, descrizioni)

    # Occorrenze ogni 100 parole = occorrenze totali / parole totali * 100.
    # sum(contatore.values()) è il numero totale di occorrenze della categoria.
    per_100 = {nome: 100 * sum(c.values()) / parole_totali for nome, c in occorrenze.items()}

    print(f"Descrizioni analizzate: {len(descrizioni)} | parole totali: {parole_totali}")
    for nome, c in occorrenze.items():
        print(f"  {nome}: {sum(c.values())} occorrenze -> {per_100[nome]:.2f} ogni 100 parole")

    disegna_grafico(per_100, len(descrizioni), parole_totali, FILE_GRAFICO)
    print(f"Grafico salvato in {FILE_GRAFICO}")


if __name__ == "__main__":
    main()