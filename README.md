# Misurare il gusto: quali caratteristiche della descrizione promozionale dei libri sono associate alle diverse fasce di visibilità commerciale nelle classifiche IBS?

Progetto d'esame per il corso *Tecnologie dei dati e del linguaggio*
(Prof. Alfio Ferrara), [Università degli Studi di Milano, A.A. 2025/26].

## Domanda di ricerca

Quali caratteristiche delle descrizioni promozionali dei libri sono associate alle diverse fasce di visibilità commerciale nelle classifiche di vendita? 

## Dati

- **Fonte**: classifica IBS dei libri "più venduti nell'ultima settimana". Ho scelto IBS e non altre piattaforme (Mondadori, Feltrinelli), per semplice praticità d'uso: nella mia esperienza personale ho usato più frequentemente questa piattaforma di vendita rispetto alle altre. Ho invece escluso a priori Amazon, perché non presenta una vera e propria classifica, ma soltanto una sezione "libri più venduti", che non sarebbe stata funzionale alla nostra ricerca. 
- **Campione**: 100 libri, rilevazione riguardante la settimana specifica in cui è stato elaborato il progetto.
- **Dati raccolti**: posizione in classifica, dati bibliografici e descrizione. Premi vinti dagli autori. 

## Metodo
Come LLM ho deciso di utilizzare Claude (se escludiamo un primo tentativo fatto con ChatGPT, di cui avrò modo di sintetizzare gli esiti in sede d'esame). Per operazioni più "complesse" (nella mia esperienza intendo per esempio la creazione di file Excel con alcune specifiche funzionalità di calcolo) ho avuto una migliore esperienza con Claude rispetto ad altri competitor; ho ritenuto quindi più adatto utilizzarlo anche per un'attività che non avevo mai tentato prima come la programmazione.
Ho seguito con attenzione la dispensa-tutorial pubblicata su Ariel, cercando di applicare i suggerimenti di scrittura di script in essa contenuti. 
Per l'ambiente di lavoro ho usato: Python come interprete del linguaggio e Visaul Studio Code come editor del codice. 


## Fase 1 - Raccolta delle descrizioni
Nella prima fase ho raccolto le descrizioni e i dati bibliografici della TOP100 dei libri più venduti della settimana di IBS.it. Nei dati raccolti nel primo file CSV (contenuto in questo repository nella cartella "dati") ho incluso: posizione in classifica, titolo, autore, data di uscita, casa editrice, descrizione e URL. Il file prodotto, dopo un controllo a campione di alcuni titoli, non presentava particolari errori: tutti i dati erano stati trascritti correttamente. Mancava semplicemente il nome di un autore di una raccolta artistica in cui figurava soltanto il nome del curatore. Dopo una verifica online non ho ritenuto necessario intervenire. 
Nel controllo del file CSV ho prestato particolare attenzione alle descrizioni, dal momento che dovevano contenere tutto ciò che veniva indicato su IBS: non solo la sinossi del libro, ma anche riferimenti a premi vinti dall'autore, critiche e citazioni di giornalisti e qualsiasi elemento che contribuisse alla promozione del libro (pur sempre limitatamente a ciò che era contenuto nel box "descrizione" del prodotto).

## Fase 2 - Arricchimento
Per poter analizzare il contenuto delle descrizioni promozionali dei libri in classifica ho scelto 5 categorie di "vocabolario" (contenute nel file dizionario.json nella cartella Dati). 
1. Valutativi positivi (capolavoro, meraviglioso, magistrale, favoloso, straordinario...)
2. Premi, riconoscimenti, segnali di successo (premio "X", vincitore, bestseller, candidato...)
3. Novità e attesa (nuovo, fenomeno, nuova edizione...)
4. Coinvolgimento del lettore (da non perdersi, da leggere, immergersi, divorare...)
5. Citazioni e critiche da recensioni di giornalisti o affini (generalmente individuati da virgolette)

Il modello ha contribuito a integrare le versioni femminili e plurali dei vocaboli che ho indicato ed eventualmente ad aggiungere alcuni sinonimi. 

In questa fase ho anche deciso di raccogliere in un file JSON (premi_arricchiti.JSON nella cartella Dati) i premi vinti dagli autori in classifica. Con un codice creato dal modello sono state visitate le pagine Wikipedia di tutti gli autori presenti in classifica (almeno quelli che avevano una pagina su Wikipedia, gli altri risultano come "non trovato") e sono stati trascritti i premi letterari e culturali vinti (qualora ce ne fossero, altrimenti viene indicato "campo mancante"). In questo caso, diversamente dal primo file CSV, ho dovuto effettuare un lavoro di pulizia maggiore:
1. Innanzitutto, il codice cercava soltanto sulla pagina Wikipedia italiana, ignorando che molti autori fossero stranieri. Ho integrato il codice con un nuovo script che tenesse in considerazione anche Wikipedia.en, qualora l'autore non risultasse presente su Wikipedia.it. Questo ha aumentato considerevolmente la quantità di premi censiti.
2. Inoltre, spesso i premi venivano trascritti in maniera erronea: e.g. "Nel riceve il Premio Strega - 2019", invece di "Nel 2019 riceve il Premio Strega"; ho deciso di normalizzare la trascrizione chiedendo di indicare soltanto il nome del premio e l'anno, come indicato qui sotto.
         "premio": "Premio Flaiano",
        "anno": 2003,
        "testo_originale": "2003 - Premio Flaiano - consegnato a Pescara"

## Fase 3 - Analisi descrittiva
In questa fase ho iniziato a incrociare i dati a mia disposizione, creando alcuni grafici che mi dessero delle informazioni su ciò che cercavo. 

In primis, ho calcolato le occorrenze delle varie categorie di vocabolario nelle descrizioni, normalizzate per 100 parole. Il grafico è stato salvato come occorrenze.png nella cartella Immagini. 

Successivamente ho incrociato la presenza di un certo tipo di vocabolario con la posizione in classifica dei titoli che contenevano quel vocabolario. Il grafico è stato salvato come correlazione.png nella cartella Immagini. Ne è emerso come il lessico riguardante novità/attesa e le citazioni dei giornalisti siano mediamente correlati a una posizione più alta in classifica. 

Ho poi incrociato la presenza di lessico riguardante i premi e la vittoria di premi da parte di alcuni autori (che avevo estratto nel file JSON premi_arricchiti) con la posizione in classifica. Ne è emerso che nella TOP10 la maggior parte dei libri (80%) è stato scritto da autori vincitori di almeno 5 premi o contiene lessico riguardante i premi. Si tratta della fascia con la percentuale più alta rispetto al resto della classifica. 

Infine, ho creato un file HTML interattivo in cui associo l'utilizzo delle varie categorie di vocabolario con la casa editrice che le usa. La casa editrice con il più alto numero di occorrenze per ogni categoria risulta essere Einaudi; molto forte nello specifico è la presenza di lessico riguardante i premi (d'altronde è ben noto che Einaudi sia riconosciuta come casa editrice di qualità!). 

## Fase 4 - Conclusioni e interpretazione personale
Qualche considerazione personale sui dati raccolti:
1. Nelle occorrenze generali prevale fortemente la presenza di lessico riguardante la novità e l'attesa, concentrato nella parte alta della classifica. Questo potrebbe essere dovuto al fatto che nella parte alta della classifica spesso sono contenuti libri che devono ancora uscire (ma che sono già in preordine) o che sono appena usciti e che normalmente riscuotono un certo successo di vendite. La presenza di lessico riguardante la novità e l'attesa è quindi da correlare al fatto che i libri contenuti in questa parte della classifica siano appena usciti o in procinto di uscire.
2. Nella parte alta della classifica sono molto presenti autori e libri che hanno ricevuto premi. Potrebbe essere interpretato come un segno della fiducia del lettore nei confronti di un autore "che conosce", ovvero di un autore che dovrebbe garantire una certa affidabilità nella scrittura. Tuttavia, è pur vero che anche nel resto della classifica non mancano riferimenti a premi, anche nelle parti finali della classifica, seppur nella maggior parte dei casi si tratti di libri usciti da più tempo rispetto a quelli alti in classifica.
3. In generale, è molto scarso l'utilizzo di vocabolario riguardante il coinvolgimento diretto del lettore. Risulta abbastanza evidente come nella promozione odierna dei libri si punti più sulla qualità del contenuto o su altri fattori, invece di sollecitare il lettore all'acquisto. 

In conclusione, misurare il gusto in maniera oggettiva risulta essere un'operazione inevitabilmente riduttiva. Il gusto è un elemento estremamente personale: dipende dalla storia di lettura di ciascuno, dal contesto culturale, dall'umore e perfino dal momento in cui si sceglie un libro. Per questo, quando si sceglie un libro, non si riflette necessariamente né sulla posizione di un titolo in classifica né sulla descrizione che l'editore ne propone.

La classifica, infatti, registra le vendite, che sono influenzate da molti fattori che nulla hanno a che vedere con il gusto in senso stretto: la notorietà dell'autore, le campagne promozionali, i premi, il prezzo. A sua volta, la sinossi è un testo promozionale scritto per attirare l'attenzione, non una descrizione neutrale del contenuto né una misura di ciò che i lettori apprezzano.

Questo progetto non pretende quindi di misurare il gusto, ma di osservare un suo indicatore indiretto: il modo in cui il linguaggio promozionale si associa alla visibilità commerciale. I risultati vanno letti come un'esplorazione di tendenze; non sono quindi una spiegazione dei motivi per cui i lettori preferiscono un determinato libro.

## Limiti/Caveat finale

- La rilevazione è stata fatta in una specifica settimana: la classifica cambia continuamente e non è detto che i risultati siano sempre uguali.
- Campione di 100 libri: i risultati non sono generalizzabili in quanto il campione di 100 libri, per quanto sufficientemente ampio per i termini della nostra ricerca, non rappresenta efficacemente la mole di libri che vengono pubblicati ogni settimana.

## Un riassunto dei risultati è contenuto nel file report.html nella cartella Report

Luca Sabbadini
