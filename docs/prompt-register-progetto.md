# ClosetAI — registro degli strumenti e prompt riproducibili

Questo documento soddisfa la richiesta di consegna relativa a **tool e prompt
usati nel workflow**. I prompt sono versioni consolidate e riproducibili delle
attività svolte durante il progetto: non costituiscono una trascrizione
automatica e parola-per-parola di ogni conversazione. Ogni output generato deve
essere verificato con fonti, test o revisione umana prima di entrare nel
prodotto o nella presentazione.

## Strumenti impiegati

| Ambito | Strumento | Impiego | Controllo umano |
| --- | --- | --- | --- |
| Ideazione, codice e documentazione | OpenAI ChatGPT/Codex | problem setting, requisiti, architettura, implementazione, test, documenti e note orali | revisione del codice, build, test automatici e confronto con la UI reale |
| Logo e visuali | AI generativa per immagini e assistenza generativa SVG | concept gruccia + foglia, iterazioni visuali e immagini illustrative | rimozione di testo/loghi estranei, controllo leggibilità, implementazione finale come SVG editabile |
| Presentazione | OpenAI Codex + artifact-tool + PowerPoint | struttura narrativa, grafica, esportazione PPTX e note orali native | render di tutte le slide, controllo layout e verifica dei contenuti |
| Machine learning | Python, Jupyter, PyTorch, Fashion-CLIP | dataset, addestramento e valutazione dei modelli per stato e gap | notebook riproducibili, metriche su holdout e dichiarazione dei limiti |
| Prodotto | React, FastAPI, SQLite | web app, API, persistenza e flussi utente | build frontend, test backend e prova locale end-to-end |

## Regola comune per prompt affidabili

Ogni prompt include cinque elementi:

1. **contesto verificabile**;
2. **obiettivo singolo**;
3. **vincoli e cose da non inventare**;
4. **formato dell’output**;
5. **controlli finali richiesti al modello**.

## P01 — ideazione del prodotto eco-sostenibile

**Strumento:** ChatGPT/Codex  
**Obiettivo:** definire il problema e il valore del prodotto.

```text
Agisci come product designer esperto di economia circolare. Dobbiamo ideare un
prodotto digitale eco-sostenibile per studenti universitari: deve integrare una
componente di machine learning realmente funzionale, non soltanto un chatbot.

Proponi un concept che aiuti le persone a ridurre acquisti tessili impulsivi e
ad allungare la vita dei capi già posseduti. Descrivi: problema, utente, user
story completa, decisioni supportate, dati necessari, possibili rischi e una
metrica osservabile per ogni beneficio. Non inventare dati ambientali: indica
quali affermazioni richiedono una fonte esterna. Concludi con una frase di
valore di massimo 15 parole e una tabella problema → funzione → risultato.
```

**Verifica:** il concept deve poter funzionare senza AI generativa e non deve
trasformarsi in un negozio che incentiva nuovi acquisti.

## P02 — requisiti e user story della web app

**Strumento:** ChatGPT/Codex  
**Obiettivo:** tradurre il concept in requisiti verificabili.

```text
Partendo dal concept ClosetAI, scrivi i requisiti di una web app locale a
utente singolo. Il flusso deve essere: fotografare un capo, correggere i
metadati, registrare gli utilizzi, ottenere outfit, riconoscere capi fantasma,
valutare lo stato, analizzare i gap e registrare riparazione o seconda vita.

Per ogni funzione specifica: input, output visibile, regola o modello usato,
fallback, errore comprensibile e criterio di accettazione. Distingui sempre
machine learning, regole deterministiche e AI generativa. Non dichiarare come
implementata una funzione soltanto pianificata. Restituisci user story,
requisiti funzionali e checklist di test.
```

**Verifica:** ogni requisito deve essere riconducibile a una schermata o a un
endpoint reale.

## P03 — architettura logica e scaffold del progetto

**Strumento:** OpenAI Codex  
**Obiettivo:** progettare un’architettura semplice e dimostrabile.

```text
Progetta l’architettura di ClosetAI con frontend React/TypeScript, backend
FastAPI/Python, database SQLite, immagini locali e checkpoint PyTorch.

Mostra il flusso dati per: creazione capo, registrazione utilizzo, suggerimento
outfit, diagnosi dello stato, gap analysis e azione circolare. Per ogni
componente assegna una responsabilità unica. Mantieni i modelli ML dietro
servizi sostituibili e prevedi fallback deterministici. Non introdurre
microservizi, code o cloud se non servono al prototipo. Produci: albero delle
cartelle, contratti API, rischi, test minimi e percorso di evoluzione verso
autenticazione, PostgreSQL e object storage.
```

**Verifica:** l’architettura deve essere eseguibile su un normale portatile e
deve separare UI, logica applicativa, dati e modelli.

## P04 — modello per lo stato del capo

**Strumento:** ChatGPT/Codex + Python/PyTorch  
**Obiettivo:** creare un notebook riproducibile per la classificazione.

```text
Crea un notebook Python autosufficiente per classificare lo stato di un capo
in buono, usurato o danneggiato. Usa Fashion-CLIP pre-addestrato e congelato
come estrattore di embedding e addestra soltanto una piccola MLP.

Il notebook deve includere: obiettivo, provenienza e limiti dei dati, split
train/validation/test, seed, preprocessing, architettura, training, curve,
confusion matrix, accuracy per split, error analysis, salvataggio checkpoint e
una cella di inferenza. Non presentare i dati sintetici come equivalenti a foto
reali e non usare il test set per scegliere gli iperparametri. Commenta ogni
sezione per un pubblico non informatico.
```

**Verifica:** il notebook deve poter essere eseguito dall’inizio alla fine e
deve dichiarare l’assenza di validazione esterna.

## P05 — modello per i gap del guardaroba

**Strumento:** ChatGPT/Codex + Python/PyTorch  
**Obiettivo:** documentare la classificazione multi-label.

```text
Crea un notebook Python autosufficiente per una gap analysis multi-label del
guardaroba. L’input contiene 14 indicatori aggregati; l’output può attivare sei
gap funzionali. Usa una MLP con sigmoid e binary cross-entropy.

Spiega come vengono simulati 5.000 guardaroba e come le etichette sono derivate
da regole esperte. Includi split riproducibile, standardizzazione, training,
threshold, micro-F1, macro-F1, hamming loss, metriche per etichetta, esempi di
errore e confronto con il fallback a regole. Evidenzia che una metrica elevata
su label generate da regole non dimostra efficacia su utenti reali.
```

**Verifica:** separare chiaramente validazione tecnica e validità esterna.

## P06 — progettazione UI/UX

**Strumento:** ChatGPT/Codex  
**Obiettivo:** creare un’esperienza comprensibile durante l’esame.

```text
Progetta la UI di ClosetAI per una persona non tecnica. La navigazione primaria
deve contenere Guardaroba, Cosa metto?, Impatto e Aggiungi un capo. Mantieni il
ML Lab come approfondimento separato.

Per ogni schermata definisci gerarchia, call to action, stati vuoti, errori,
mobile layout e microcopy. Rendi visibili: utilizzi, cost-per-wear, ghost,
stato, gap e impatto stimato. Evita nomenclature interne, percorsi di file,
comandi di training e percentuali presentate come certezze. Restituisci una
specifica implementabile in React e una checklist di accessibilità.
```

**Verifica:** build TypeScript, controllo responsive e corrispondenza tra
etichette documentate e UI reale.

## P07 — concept e realizzazione del logo

**Strumento:** AI generativa per immagini / assistenza generativa SVG  
**Obiettivo:** rappresentare guardaroba e sostenibilità senza marchi esistenti.

```text
Create an original minimal vector logo for a sustainable digital wardrobe
called ClosetAI. Combine a clothes hanger with one sprouting leaf. Use a deep
forest-green rounded-square background, white hanger lines and a light
yellow-green leaf. Flat geometry, strong silhouette, accessible contrast,
recognizable at 32 px, no gradients that disappear at small size, no mockup,
no text, no letters, no human figure, no shopping bag, no recycling cliché,
no resemblance to existing fashion or technology brands. Provide one primary
concept and three concise variation directions suitable for redrawing as SVG.
```

**Verifica:** ricerca visiva di somiglianze, prova a 32/48/128 px, contrasto e
ridisegno finale come SVG editabile. Il logo usato nell’app è una gruccia con
foglia, implementata come componente SVG e revisionata manualmente.

## P08 — analisi di sostenibilità e fattibilità

**Strumento:** ChatGPT/Codex  
**Obiettivo:** evitare green claim non dimostrati.

```text
Valuta ClosetAI come prodotto eco-sostenibile senza trasformare stime in fatti.
Separa: beneficio potenziale, impatto digitale del sistema, ipotesi, limiti e
dati necessari per una futura LCA.

Analizza riduzione degli acquisti evitabili, aumento dell’uso, riparazione e
seconda vita. Considera anche energia per training/inferenza, storage immagini
e servizi generativi esterni. Proponi mitigazioni coerenti con il prototipo:
modello pre-addestrato congelato, MLP piccole, inferenza CPU, caching, servizi
generativi opzionali e nessun hardware dedicato. Aggiungi fattibilità tecnica,
materiali/dispositivi, costi qualitativi e percorso di scalabilità. Non
inventare kg di CO2 o prezzi: segnala i dati che richiedono fonte o misura.
```

**Verifica:** usare sempre “stima di scenario” per la CO₂eq dell’app e citare
le fonti dei dati di contesto.

## P09 — audit di errori e allucinazioni

**Strumento:** ChatGPT/Codex  
**Obiettivo:** controllare contenuti generati e implementazione.

```text
Esegui un audit avversariale di ClosetAI. Cerca affermazioni non supportate,
funzioni documentate ma non implementate, metriche senza dataset, confusione
tra regole e machine learning, output generativi presentati come dati e
greenwashing.

Per ogni problema restituisci: affermazione, evidenza nel codice o nei dati,
gravità, correzione minima e test di regressione. Verifica in particolare:
definizione ghost, formula cost-per-wear, ranking outfit, origine delle label
del gap, limiti del modello di stato, significato della CO₂eq, disponibilità
LLM/try-on e differenza tra demo locale e studio utenti. Se non trovi evidenza,
scrivi “non verificato” invece di completare per plausibilità.
```

**Verifica:** ricerca nel repository, chiamate API locali, test automatici e
confronto fra documentazione, slide e UI.

## P10 — presentazione ufficiale con note orali

**Strumento:** OpenAI Codex + artifact-tool + PowerPoint  
**Obiettivo:** costruire una narrazione adatta a un esame non informatico.

```text
Crea una presentazione in italiano per un esame universitario su ClosetAI.
Apri con una user story completa e passa poi alle scelte tecniche. La struttura
deve coprire: problem setting, workflow di AI generativa con tool/prompt e
allucinazioni, machine learning con notebook Python, architettura logica,
fattibilità e analisi di sostenibilità.

Distingui sempre: modello pre-addestrato, modelli addestrati da noi, regole,
AI generativa usata per progetto/logo/presentazione. Usa una sola idea per
slide, pochi testi sul canvas e note orali native scritte come copione dello
studente. Non inventare metriche; mostra limiti e fonti vicino ai claim.
```

**Verifica:** render di tutte le slide, controllo layout, conteggio note e
confronto con la checklist della consegna.

## P11 — preparazione alle domande del professore

**Strumento:** ChatGPT/Codex  
**Obiettivo:** allenare un’esposizione trasparente.

```text
Simula una commissione universitaria che valuta ClosetAI. Formula 15 domande
progressive su sostenibilità, workflow generativo, allucinazioni, modelli ML,
dataset, metriche, fattibilità e scalabilità. Per ogni domanda crea una risposta
orale di 20-40 secondi basata esclusivamente sui fatti forniti. Inserisci almeno
cinque domande critiche che obblighino a dichiarare un limite. Non suggerire di
nascondere errori o di presentare stime come misure.
```

## Tentativi scartati e correzioni rilevanti

| Tentativo o rischio | Perché era debole | Correzione adottata |
| --- | --- | --- |
| Quattro stati del capo, incluso “nuovo” | “Nuovo” e “buono” erano difficili da distinguere visivamente | tre classi: buono, usurato, danneggiato |
| VLM con tutorial di riparazione | complessità alta e valore limitato per il nucleo del prodotto | rimosso; stato + azione trasparente |
| Gap con metriche elevate | label derivate da regole possono gonfiare la validazione interna | limite dichiarato e futura validazione con utenti |
| Virtual try-on generativo | può sembrare una prova reale di taglia o vestibilità | funzione opzionale e disabilitata nella demo ufficiale |
| CO₂eq mostrata come impatto reale | rischio di greenwashing e falsa precisione | etichetta “stima di scenario”, formula e ipotesi visibili |
| Testi generati sull’implementazione | rischio di descrivere funzioni pianificate come già presenti | verifica con codice, API, build e test prima della consegna |

## Checklist prima della consegna

- [ ] Sostituire eventuali nomi di tool generativi se il gruppo ha usato un
  prodotto diverso da quello indicato.
- [ ] Conservare soltanto prompt pertinenti e realmente difendibili.
- [ ] Verificare che metriche e quantità coincidano fra notebook, app e slide.
- [ ] Dichiarare chiaramente dataset sintetici, stime e moduli opzionali.
- [ ] Non includere dati personali, chiavi API o immagini senza autorizzazione.
