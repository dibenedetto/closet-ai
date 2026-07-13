# ClosetAI — guida per l’esame ufficiale

Questa guida accompagna `ClosetAI-esame-ufficiale.pptx`. Le note del
relatore sono già incorporate in ogni slide; qui trovi le risposte brevi da
memorizzare, le domande probabili e le formulazioni da evitare.

## Apertura consigliata (35–45 secondi)

> ClosetAI non vuole suggerire altri acquisti: vuole rendere visibile quanto
> usiamo ciò che possediamo e trasformare questi segnali in azioni concrete —
> riscoprire, curare, riparare, scambiare o riciclare. Il progetto collega
> quattro informazioni nell’interfaccia: impatto verde, stato dei capi, gap del
> guardaroba e capi fantasma. Durante la presentazione distingueremo sempre ciò
> che abbiamo addestrato noi, ciò che usiamo pre-addestrato e ciò che è una
> regola trasparente.

## La risposta sui capi fantasma

Sì, i ghost garments sono rilevati end-to-end.

Definizione operativa:

```text
ghost = zero wear registrati
        AND posseduto da almeno la soglia scelta (30 giorni di default)
        AND capo non ritirato
```

La data di acquisto è preferita; se manca, si usa la data di inserimento
nell’app. Non è machine learning: è una regola verificabile.

La UI li mostra in:

- `/dashboard`: soglia 30/60/90/180 giorni, conteggio “Capi da riscoprire” e
  lista nominativa;
- `/items/:id`: badge “Poco utilizzato”;
- `/today`: bonus “Riscoperta” negli outfit eleggibili.

Formula corretta da usare: **“mai indossato dopo almeno X giorni”**. Non dire
“non indossato di recente”: un capo indossato una volta anni fa non è ghost
secondo la definizione corrente.

## Mappa tecnica da ricordare

| Componente | Natura | Addestrato da noi? | Stato nel prodotto |
| --- | --- | ---: | --- |
| Fashion-CLIP | modello vision pre-addestrato | No | inferenza categoria + embedding |
| MLP stato del capo | rete neurale su embedding congelati | **Sì** | in uso |
| MLP closet gaps | rete multi-label su 14 feature aggregate | **Sì** | in uso |
| Ghost detector | soglia + wear log | No, regola | in uso |
| Outfit recommender | colore + meteo + ghost + feedback | No, regole pesate | in uso |
| Cost-per-wear | prezzo / utilizzi | No, formula | in uso |
| CO₂eq circolare | media categoria × fattore azione | No, proxy | in uso |
| LLM / diffusion | modelli generativi esterni | No | opzionali |
| Ghost-risk LogisticRegression | esperimento sklearn | Sì, fitting accademico | non collegato alla UI |
| Wear RandomForest | esperimento sklearn | Sì, fitting accademico | non collegato alla UI |
| Style KMeans | esperimento sklearn | Sì, fitting accademico | non collegato alla UI |

## Cinque concetti da spiegare in linguaggio semplice

1. **Transfer learning** — non riaddestriamo tutta la vista artificiale.
   Fashion-CLIP rimane congelato; alleniamo una testa piccola e specifica.
2. **Multi-class** — per lo stato scegliamo una sola classe fra buono, usurato
   e danneggiato.
3. **Multi-label** — per i gap più risposte possono essere vere insieme.
4. **Validation vs test** — la validation decide quando fermare il training; il
   test si apre alla fine per stimare la prestazione.
5. **Fallback** — senza pesi o servizi esterni l’app non deve bloccarsi: usa
   regole o disabilita la funzione opzionale.

## Numeri difendibili

- Condition MLP: 600 immagini locali; 83 nel test; accuracy holdout `0,940`;
  F1 danneggiato `0,981`; circa `164.611` parametri addestrabili.
- Gap MLP: 5.000 guardaroba simulati; 14 feature; 6 label; micro-F1 `0,943`;
  macro-F1 `0,932`; subset accuracy `0,779`; Hamming loss `0,040`.
- Ghost-risk accademico: ROC-AUC `0,713` su dati sintetici; non è evidenza di
  efficacia reale e non alimenta l’app.
- Wear forecast accademico: MAE `0,75` utilizzi su target sintetico; è un sanity
  check della pipeline.

Presenta `0,94` come **holdout del prototipo**, non come validazione esterna. Il
dataset dello stato è stato risuddiviso localmente e non garantisce che ogni
sorgente correlata sia isolata fra train e test.

## Come parlare della sostenibilità

Usa:

- “stima di CO₂ equivalente”;
- “proxy per categoria e azione”;
- “scenario di sostituzione”;
- “ordine di grandezza motivazionale”.

Evita:

- “abbiamo risparmiato davvero X kg di CO₂”;
- “questa riparazione elimina il 70% delle emissioni”;
- “la dashboard misura l’impatto reale”.

La formula corrente è trasparente ma semplificata. Prima della produzione
servono LCA per materiale, range d’incertezza e una verifica dell’ipotesi che
riuso o riparazione evitino effettivamente un nuovo acquisto.

## Domande probabili del professore

### “Perché usare una rete per i gap se le label derivano da regole?”

> Oggi è un dimostratore tecnico controllabile: la rete apprende una funzione
> multi-label da esempi simulati e il fallback resta la regola. Il passo
> scientificamente importante è sostituire o integrare quelle label con
> feedback reale, poi confrontare rete e baseline su un test esterno.

### “Il 94% vale su utenti reali?”

> No. È il risultato di un holdout locale della pipeline. Per parlare di
> generalizzazione servono split per sorgente, foto di utenti reali e test per
> camera, luce, sfondo e tipo di difetto.

### “Perché non addestrare Fashion-CLIP?”

> Il dataset locale non è abbastanza grande. Congelare l’estrattore riduce dati,
> costo e rischio di overfitting; concentriamo il training sulla testa specifica.

### “Il recommender impara dal feedback?”

> Il feedback modifica leggermente il ranking con un termine fino a ±4%; non
> riaddestra un modello. Meteo, colore e riscoperta restano spiegabili e
> dominanti.

### “Quali dati personali conservate?”

> Nell’MVP: immagini dei capi, metadata, utilizzi e azioni, tutti in locale e in
> modalità single-user. In produzione servono autenticazione, isolamento per
> utente, cifratura, cancellazione/retention, EXIF stripping e una valutazione
> GDPR/DPIA perché una foto può includere corpo e ambiente domestico.

### “Cosa succede se un modello non è disponibile?”

> La condition e la gap analysis hanno fallback; meteo, LLM e try-on sono
> opzionali. Il nucleo CRUD, wear log, ghost, cost-per-wear e circolarità resta
> utilizzabile.

## Possiamo farne un’app smartphone?

Sì. Oggi è una web app responsive, già usabile dal browser mobile e con hint
per la fotocamera posteriore. Il backend FastAPI è separato e versionato, quindi
un client mobile non richiede di riscrivere la logica di dominio.

Percorso consigliato:

1. **PWA** — massima riusabilità della UI. Aggiungere manifest, icone, HTTPS,
   service worker e coda offline. [MDN descrive manifest e requisiti di
   installabilità](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable).
2. **Capacitor** — riusa quasi tutta l’app Vite e aggiunge plugin per camera,
   notifiche e packaging nativo. [La documentazione ufficiale conferma che può
   entrare in un progetto JavaScript esistente](https://capacitorjs.com/docs).
3. **Expo / React Native** — migliore se mobile diventa il prodotto principale.
   Si riusano API, tipi e logica dati; si ricostruiscono componenti DOM, CSS e
   navigazione. Expo supporta Android/iOS, accesso a camera/libreria con
   [ImagePicker](https://docs.expo.dev/versions/latest/sdk/imagepicker/) e
   persistenza con [SQLite](https://docs.expo.dev/versions/latest/sdk/sqlite/).

Prima di un rilascio mobile reale servono: autenticazione multiutente, HTTPS,
Postgres + object storage, immagini firmate, compressione/orientamento/EXIF,
sincronizzazione offline idempotente, notifiche opt-in e job asincroni per il
try-on.

Risposta orale breve:

> Sì. L’architettura API-first rende il mobile un nuovo client, non una
> riscrittura del backend. La via più breve è una PWA; Capacitor riusa la UI per
> gli store; Expo ha senso se camera, push e offline-first diventano centrali.
> Prima della produzione servono auth, storage multiutente, HTTPS e una policy
> rigorosa per le immagini.

## Regole di comunicazione durante l’esame

- Per ogni feature: **input → trasformazione → output → beneficio → limite**.
- Dire “il modello stima una probabilità”, non “l’AI capisce”.
- Dire “abbiamo addestrato la testa MLP”, non “abbiamo addestrato
  Fashion-CLIP”.
- Separare sempre funzionalità runtime ed esperimenti dei notebook.
- Non leggere le slide: usare il titolo come tesi e il diagramma come prova.
- Quando non sai un dettaglio, dichiarare l’assunzione e indicare come la
  verificheresti.
- Se il professor contesta una metrica sintetica, concordare sul limite e
  riportare la discussione al piano di validazione esterna.

## Checklist del giorno dell’esame

- Aprire prima `/dashboard`, un dettaglio `/items/:id`, `/today` e Swagger.
- Verificare che ci siano almeno un ghost, un capo usurato/danneggiato e un gap.
- Fare una prova completa della demo con timer: obiettivo `3:30`.
- Disattivare notifiche e aggiornamenti automatici.
- Portare deck, PDF di backup se prodotto localmente e notebook su due supporti.
- Non promettere servizi LLM/try-on se le credenziali non sono configurate.
