# ClosetAI — spiegazione tecnica ad alto livello

Questo documento è una traccia per spiegare ClosetAI durante l’esame
ufficiale. È pensato per un pubblico con una preparazione tecnica generale,
ma non necessariamente informatica. Il percorso principale richiede circa
sette minuti; i paragrafi «se il professore chiede» servono per approfondire
senza appesantire l’introduzione.

## Apertura consigliata — 40 secondi

> ClosetAI è un prototipo che trasforma un guardaroba fisico in un inventario
> digitale e usa i dati d’uso per aiutare la persona a valorizzare ciò che
> possiede già. L’architettura separa l’interfaccia, le API, la logica di
> dominio e i modelli di machine learning. Quando l’utente fotografa un capo,
> il sistema ne ricava categoria e colore; quando registra gli utilizzi,
> calcola costo per utilizzo, capi fantasma e andamento del guardaroba. Su
> questi dati costruisce outfit, diagnosi dello stato, gap funzionali e stime
> di impatto circolare. Per correttezza distinguiamo sempre quattro cose:
> modelli preaddestrati, modelli addestrati da noi, regole deterministiche e
> funzioni generative opzionali.

La tesi da mantenere durante tutta la spiegazione è:

> **ClosetAI non automatizza una singola classificazione: collega foto,
> inventario, uso nel tempo e azioni circolari in un unico ciclo misurabile.**

## 1. La struttura del sistema

ClosetAI è un’applicazione web **API-first**, organizzata in quattro livelli:

```text
Persona
   │
   ▼
Interfaccia React + TypeScript
   │  richieste HTTP/JSON e caricamento immagini
   ▼
API FastAPI
   │
   ├── servizi di dominio: utilizzi, ghost, outfit, stato, gap, circolarità
   ├── modelli ML: Fashion-CLIP, MLP stato, MLP gap
   └── servizi opzionali: meteo, LLM, diffusion try-on
   │
   ▼
SQLite per i dati ── filesystem per le immagini ── ChromaDB per gli embedding
```

- Il **frontend React** presenta il guardaroba, raccoglie le azioni
  dell’utente e visualizza i risultati. Non contiene il cuore delle regole.
- Il **backend FastAPI** espone API versionate sotto `/api/v1`, valida gli
  input e orchestra la logica applicativa.
- I **servizi di dominio** calcolano statistiche, propongono outfit, rilevano
  ghost garment e gestiscono le azioni circolari.
- Il livello **ML** esegue l’inferenza dei modelli, ma non controlla tutto il
  prodotto: molte funzioni sono formule o regole esplicite.
- Nell’MVP i metadati sono salvati in **SQLite**, mentre foto e immagini
  generate restano nel filesystem locale. Gli embedding visivi sono
  indicizzati separatamente in **ChromaDB**.

Questa separazione è importante perché consente di cambiare l’interfaccia —
per esempio creando un’app mobile — senza riscrivere la logica del backend.

## 2. Primo flusso: dalla fotografia al capo digitale

Si può spiegare il flusso seguendo un singolo capo.

1. L’utente inserisce nome, fotografia e, se disponibili, prezzo e data di
   acquisto. Può anche specificare manualmente categoria e colore.
2. Il backend accetta JPEG, PNG o WebP, verifica tipo ed estensione e applica
   un limite di 10 MB. Il file viene rinominato con un identificatore casuale,
   così non si usa direttamente il nome fornito dall’utente.
3. **Fashion-CLIP**, un modello vision preaddestrato, trasforma la foto in un
   vettore numerico di 512 valori, chiamato *embedding*. Confrontando il
   vettore con prompt testuali inglesi, sceglie una fra 14 categorie del
   progetto. Il colore dominante viene invece ricavato con quantizzazione
   dell’immagine e associazione a una palette: non è un modello addestrato.
4. Categoria o colore inseriti dall’utente hanno priorità sul risultato
   automatico. La correzione umana rimane quindi possibile.
5. Il record viene salvato in SQLite, la foto nel filesystem e l’embedding in
   ChromaDB. Se classificazione o indice vettoriale non sono disponibili, il
   salvataggio del capo non deve bloccarsi.

Una precisazione utile all’esame: lo **stato di conservazione non viene
imposto automaticamente al salvataggio**. La diagnosi è un’operazione
separata, richiamabile dal dettaglio del capo, e può essere corretta
manualmente.

### Come spiegare l’embedding senza gergo

> L’embedding è una rappresentazione numerica compatta della fotografia.
> Immagini semanticamente simili tendono ad avere rappresentazioni vicine.
> Nel prototipo lo salviamo per ricerche di similarità e sviluppi futuri; il
> recommender di outfit corrente non lo usa nel proprio punteggio.

## 3. Secondo flusso: dall’utilizzo ai capi fantasma

Quando l’utente preme «Indossato», il backend crea un evento con il capo e la
data. Da questa cronologia derivano metriche semplici ma verificabili:

- numero di utilizzi;
- ultimo utilizzo;
- giorni dall’ultimo utilizzo;
- **cost-per-wear**, cioè `prezzo / numero di utilizzi`, se entrambi i dati
  sono disponibili;
- capi più utilizzati e media degli utilizzi per capo.

Il rilevamento operativo dei **capi fantasma** è una regola condivisa da
statistiche, gap analysis e recommender:

```text
ghost = capo attivo
        AND zero utilizzi registrati
        AND posseduto da almeno X giorni
```

La soglia predefinita è 30 giorni, ma nella dashboard può essere scelta fra
30, 60, 90 e 180 giorni. Per misurare il possesso si usa prima la data di
acquisto; se manca, la data di inserimento nell’app.

Non è corretto dire che «un ghost è un capo non indossato recentemente». Nel
prototipo, un capo indossato almeno una volta non è ghost, anche se
l’utilizzo è molto lontano nel tempo. Non è neppure corretto presentare
questa funzione come machine learning: è una regola deterministica,
trasparente e modificabile.

Il risultato è visibile in tre punti:

- nella dashboard, con soglia, conteggio e lista;
- nel dettaglio del capo, con il badge «Fantasma»;
- nella pagina «Cosa metto?», come bonus «Anti-fantasma» quando una proposta
  include un capo eleggibile.

## 4. Come vengono costruite le proposte di outfit

Il recommender corrente è un sistema di **generazione di combinazioni e
ranking a regole**, non una rete neurale.

1. Considera soltanto i capi attivi e li divide per ruolo. Le combinazioni
   correnti usano top, bottom, vestito, capospalla e scarpe; il ruolo
   accessorio è riconosciuto ma non entra ancora nella generazione.
2. Interroga Open-Meteo per temperatura e precipitazioni. Se il servizio non
   risponde, usa condizioni miti di fallback e lo dichiara nella risposta.
3. Esclude combinazioni palesemente inadeguate alla temperatura e genera
   candidati validi, limitando il numero di capi per ruolo.
4. Assegna a ogni candidato un punteggio comprensibile:

```text
punteggio = 55% compatibilità dei colori
          + 35% adeguatezza al meteo
          + bonus ghost fino a 15%
          + preferenza da feedback fino a ±4%
```

5. Ordina i risultati e applica un criterio di diversità, per evitare tre
   proposte quasi identiche.

Il like o dislike dell’utente modifica leggermente i ranking successivi, ma
**non riaddestra un modello**. Questo è un esempio di personalizzazione
incrementale e spiegabile. L’occasione selezionata nell’interfaccia viene
salvata con feedback e utilizzi, ma nella versione attuale non modifica il
ranking: non va quindi presentata come un filtro già operativo.

## 5. I due modelli addestrati e usati dal prodotto

### 5.1 Stato di conservazione del capo

Il primo modello risponde alla domanda: «dalla foto, il capo appare buono,
usurato o danneggiato?».

```text
foto → Fashion-CLIP congelato → embedding 512D → MLP → 3 probabilità
```

Fashion-CLIP rimane congelato: non ne modifichiamo i pesi. Abbiamo addestrato
soltanto una piccola rete *MLP* con livelli `512 → 256 → 128 → 3`, circa 165
mila parametri. È un’applicazione di **transfer learning**: si riusa una
rappresentazione visiva generale e si addestra una testa per il compito
specifico.

Nel notebook d’esame il test locale ha ottenuto accuracy circa `0,94`. Questo
numero descrive un holdout del prototipo, non una validazione clinica o
industriale. Il dataset contiene 600 esempi e include degradazioni
sintetiche: illuminazione, sfondo, tessuti e danni di utenti reali potrebbero
produrre risultati diversi.

Se il checkpoint non è disponibile o la foto non è leggibile, il sistema usa
un’euristica basata su età e numero di utilizzi. La risposta riporta la
propria sorgente (`clip-mlp` oppure `heuristic`) e l’utente può sempre
correggere lo stato.

### 5.2 Gap funzionali del guardaroba

Il secondo modello non guarda direttamente le fotografie. Riceve 14
caratteristiche aggregate, per esempio:

- quantità di top, bottom, capispalla, scarpe, vestiti e accessori;
- proporzioni di t-shirt, capi invernali e formali;
- numero di colori e presenza di un colore neutro;
- rapporto fra capi ghost e capi attivi.

Una MLP `14 → 64 → 32 → 6` produce sei probabilità indipendenti. È un
problema **multi-label**: possono essere contemporaneamente veri «manca un
capospalla» e «poca varietà di colori».

Il notebook riproducibile usa 5.000 guardaroba simulati e ottiene micro-F1
circa `0,945`. Il limite centrale è che le etichette di training derivano da
regole esperte: il risultato dimostra la pipeline multi-label, ma non prova
che i gap corrispondano ai bisogni reali di una popolazione. Per una
validazione esterna servirebbero inventari e feedback di utenti diversi.

Anche qui esiste un fallback: senza checkpoint, il backend applica
direttamente le regole esperte. La dashboard mostra se la fonte è
«rete neurale addestrata» oppure «regole esperte».

## 6. Stato, azioni circolari e impatto verde

La diagnosi dello stato non è il punto finale. Il servizio circolare la
trasforma in azioni coerenti con una gerarchia di riuso:

- un capo in buono stato può essere scambiato, venduto o donato;
- un capo usurato privilegia riparazione e poi riuso;
- un capo danneggiato privilegia riparazione e, come ultima scelta, riciclo.

Quando l’utente conferma un’azione, il sistema la salva. Vendita, swap,
donazione e riciclo ritirano il capo dal guardaroba attivo; la riparazione lo
mantiene disponibile. I capi ritirati non partecipano più a outfit, wear log,
conteggio ghost e gap attivi.

L’**impatto verde** è calcolato con una formula trasparente:

```text
CO₂eq evitata stimata = media di produzione della categoria × fattore azione
```

Per esempio, la riparazione usa un fattore `0,70`, il riuso tramite vendita,
swap o donazione `1,00`, il riciclo `0,30`. I valori di partenza sono medie
indicative per categoria.

La formulazione corretta è «stima di scenario in kg di CO₂ equivalente».
Non si tratta di una misurazione fisica né di una Life Cycle Assessment
completa. Il calcolo non conosce materiale, filiera, trasporto, durata reale
aggiuntiva o se l’azione abbia davvero evitato un nuovo acquisto. Il suo valore
nell’MVP è rendere esplicita l’ipotesi e motivare il comportamento; una versione
scientificamente più forte dovrebbe mostrare intervalli d’incertezza e usare
dati LCA per materiale.

## 7. Tassonomia: che tipo di “intelligenza” usa ClosetAI?

Questa distinzione è essenziale per non attribuire al progetto più di ciò che
fa realmente.

| Componente | Natura | Addestrato da noi? | Uso nel prodotto |
| --- | --- | ---: | --- |
| Fashion-CLIP | modello vision preaddestrato | No | categoria ed embedding dalla foto |
| MLP stato | rete neurale su embedding congelati | **Sì** | diagnosi buono/usurato/danneggiato |
| MLP gap | rete tabellare multi-label | **Sì** | gap funzionali del guardaroba |
| Colore dominante | quantizzazione e palette | No | attributo del capo |
| Ghost detector | soglia su possesso e wear log | No | dashboard, dettaglio e outfit |
| Cost-per-wear | formula aritmetica | No | statistiche d’uso |
| Outfit recommender | regole e score pesato | No | proposte «Cosa metto?» |
| Impatto CO₂eq | tabella e fattori d’azione | No | dashboard e azioni circolari |
| Descrizioni e coach | LLM esterno o locale via LiteLLM | No | opzionale |
| Try-on | diffusion/inpainting locale | No | opzionale, disabilitato di default |

I tre notebook su regressione logistica del rischio ghost, random forest per
gli utilizzi e K-means per lo stile sono **esperimenti accademici
autosufficienti**. Eseguono realmente un fitting, ma non alimentano le API o
l’interfaccia corrente. In particolare, non bisogna confondere il K-means
didattico con l’estrazione colore usata dall’app.

## 8. Affidabilità e degradazione controllata

Un criterio progettuale dell’MVP è mantenere utilizzabile il flusso principale
quando un modello o un servizio esterno manca:

- la classificazione fallita non impedisce di salvare e correggere un capo;
- diagnosi stato e gap analysis hanno fallback deterministici;
- il meteo non disponibile viene sostituito da condizioni di riferimento,
  marcate come fallback;
- LLM e try-on restituiscono indisponibilità senza bloccare guardaroba,
  utilizzi, ghost o circolarità;
- il try-on è disabilitato di default per evitare download di modelli pesanti e
  tempi CPU non compatibili con un normale flusso interattivo.

Questo consente di dire che l’AI **arricchisce** il prodotto, ma il nucleo del
guardaroba digitale non dipende da una singola chiamata esterna.

## 9. Dati, privacy e sicurezza: cosa è pronto e cosa no

Il prototipo è progettato per una demo locale single-user:

- dati e foto restano normalmente sulla macchina che esegue il backend;
- la telemetria anonima di ChromaDB è disattivata;
- sono presenti validazione dei formati, limite upload e difese contro nomi di
  file non sicuri;
- il frontend di sviluppo comunica con origini locali autorizzate.

Queste misure non rendono però l’MVP pronto per utenti pubblici. Mancano
autenticazione, separazione dei dati per account, autorizzazione sulle
immagini, HTTPS obbligatorio, cifratura e una politica di conservazione e
cancellazione. Occorrerebbe inoltre rimuovere i metadati EXIF, applicare rate
limit, introdurre migrazioni DB formali e processare i task pesanti in coda.

Le foto del corpo o dell’ambiente domestico, soprattutto nel try-on, sono dati
sensibili dal punto di vista pratico. Prima di un rilascio servirebbero
consenso informato, minimizzazione, valutazione GDPR/DPIA e una policy chiara
sui provider esterni. Un LLM cloud può ricevere il testo del prompt; un
servizio try-on cloud potrebbe ricevere anche immagini. Questi flussi devono
essere dichiarati e configurabili. Anche il controllo di sicurezza del
contenuto generativo andrebbe attivato in una versione pubblica.

## 10. Prontezza per smartphone

ClosetAI può diventare un’app smartphone perché il backend non dipende dal
browser. L’interfaccia attuale è già responsive, usa una navigazione mobile e
l’input fotografico richiede preferibilmente la fotocamera posteriore.

Il percorso più realistico è:

1. **PWA**: aggiungere manifest, service worker, HTTPS, icone e una coda
   offline. È la soluzione con il massimo riuso del frontend.
2. **Capacitor**: impacchettare la web app per gli store e integrare camera,
   notifiche e funzioni native.
3. **React Native/Expo**: ricostruire l’interfaccia se il prodotto diventa
   davvero mobile-first, riusando però API, schemi e logica di dominio.

Prima del rilascio occorrerebbero un backend multiutente, PostgreSQL, object
storage protetto, URL firmati, compressione e orientamento delle immagini,
sincronizzazione offline idempotente, notifiche opt-in e job asincroni per il
try-on.

Risposta orale breve:

> Sì. L’architettura API-first rende lo smartphone un nuovo client, non una
> riscrittura del sistema. La via breve è una PWA; Capacitor permette la
> distribuzione negli store; Expo è indicato se camera, notifiche e offline
> diventano centrali. Prima della produzione dobbiamo però aggiungere identità,
> isolamento dei dati e protezione delle immagini.

## 11. Sequenza consigliata per una spiegazione di sette minuti

1. **Problema e obiettivo — 40 s:** rendere visibile l’uso reale per comprare
   meno e prolungare la vita dei capi.
2. **Architettura — 50 s:** React, API FastAPI, servizi, modelli e storage.
3. **Foto e catalogazione — 60 s:** validazione, Fashion-CLIP preaddestrato,
   colore, persistenza e correzione umana.
4. **Wear log e ghost — 60 s:** eventi, cost-per-wear e definizione esatta del
   ghost.
5. **Outfit — 50 s:** meteo, combinazioni, score spiegabile e feedback.
6. **Modelli nostri — 90 s:** MLP stato e MLP gap, con dataset, metrica e
   limite principale.
7. **Circolarità — 50 s:** diagnosi, azione, ritiro e stima CO₂eq.
8. **Limiti e futuro — 40 s:** validazione reale, privacy e mobile.

Per ogni funzione usare sempre lo schema:

> **input → trasformazione → output → beneficio → limite**

Esempio:

> L’input del ghost detector è la data di possesso e la cronologia degli
> utilizzi; la trasformazione è una regola a soglia; l’output è un flag; il
> beneficio è far riemergere un capo dimenticato; il limite è che l’assenza di
> wear log può significare mancata registrazione, non mancato utilizzo reale.

## 12. Formulazioni corrette e formulazioni da evitare

| Dire | Evitare |
| --- | --- |
| «Abbiamo addestrato la testa MLP» | «Abbiamo addestrato Fashion-CLIP» |
| «Il modello stima una probabilità» | «L’AI sa che il capo è danneggiato» |
| «Il ghost è una regola su zero wear e anzianità» | «L’AI scopre i ghost» |
| «Il recommender ordina combinazioni con uno score» | «La rete genera gli outfit» |
| «Stima di scenario in kg CO₂eq» | «CO₂ realmente risparmiata» |
| «Risultato su holdout locale o dati simulati» | «Accuratezza garantita su utenti reali» |
| «Try-on dimostrativo basato su inpainting» | «Simulazione fedele della vestibilità» |

## Chiusura consigliata — 25 secondi

> Il contributo del progetto non è usare AI ovunque. È scegliere il meccanismo
> adatto a ogni problema: un modello preaddestrato per interpretare la foto,
> due reti leggere per stato e gap, regole trasparenti per uso, ghost, outfit e
> impatto, e componenti generative soltanto opzionali. In questo modo il
> sistema resta spiegabile e utilizzabile, e rende espliciti anche i propri
> limiti prima di una validazione su utenti reali.
