# ClosetAI — tutorial utente e traccia per la dimostrazione

Questo documento spiega ClosetAI dal punto di vista di chi lo usa. Può essere
letto come manuale operativo oppure seguito come copione durante la demo
dell'esame. I nomi tra virgolette corrispondono alle etichette presenti
nell'interfaccia.

## 1. L'idea in una frase

ClosetAI è un prototipo di guardaroba digitale che aiuta a usare meglio i capi
già posseduti: cataloga le fotografie, registra gli utilizzi, propone outfit,
segnala capi dimenticati e gap funzionali e rende visibili le azioni di cura e
seconda vita.

Non è un negozio e non decide al posto della persona. Offre indicatori e
suggerimenti che l'utente può verificare, correggere o ignorare.

### Cosa mostrare

Aprire `http://localhost:5173` e lasciare visibili il titolo «Vesti meglio.
Compra meno.», la card «Impatto verde» e i tre segnali «Uso reale», «Stato dei
capi» e «Gap del guardaroba».

### Cosa dire

> «ClosetAI parte da un principio semplice: il capo più sostenibile è quello
> che possediamo già. L'applicazione trasforma il guardaroba in dati utili per
> scegliere cosa indossare, capire cosa usiamo davvero e intervenire prima di
> comprare o buttare.»

### Risultato atteso

Chi ascolta comprende subito il beneficio per l'utente e il filo logico della
demo: **aggiungi → indossa → combina → cura → valuta → rigenera**.

## 2. Primo accesso e navigazione

Per usare il prototipo locale devono essere attivi sia il backend sia il
frontend. Non è prevista una schermata di registrazione o di login: la versione
attuale è locale e a utente singolo.

Nel menu principale sono disponibili:

- «Guardaroba»: home, ricerca, filtri e griglia dei capi;
- «Cosa metto?»: proposte di outfit per la giornata;
- «Impatto»: utilizzi, stato, capi fantasma, gap e azioni circolari;
- «Aggiungi un capo»: inserimento di un nuovo elemento;
- «ML Lab» e «Specchio»: prototipi dimostrativi, non necessari nell'uso
  quotidiano.

Su uno schermo piccolo le voci principali sono nella barra in basso. Il
pulsante `+` nell'intestazione apre «Aggiungi un capo».

### Cosa fare e mostrare

1. Selezionare «Guardaroba».
2. Scorrere la sezione «Il ciclo del tuo guardaroba».
3. Nella griglia provare la ricerca per nome, categoria o colore.
4. Provare il filtro per categoria e i pulsanti «Attivi», «Tutti» e «Seconda
   vita».

### Cosa dire

> «La home non è solo un catalogo fotografico. Riassume uso, stato e possibili
> gap, poi consente di trovare un capo per nome, categoria o colore. I capi
> ancora utilizzabili e quelli già destinati a una seconda vita rimangono
> distinguibili.»

### Risultato atteso

La griglia mostra soltanto i capi compatibili con i filtri. «Azzera filtri»
ripristina la vista iniziale quando una ricerca non restituisce risultati.

## 3. Aggiungere il primo capo

Selezionare «Aggiungi un capo». La fotografia e il nome sono obbligatori;
categoria, colore, prezzo e data di acquisto sono facoltativi.

### Procedura utente

1. In «Fotografa il capo», scegliere «Scatta o scegli una foto».
2. Usare un'immagine JPG, PNG o WebP non superiore a 10 MB. Una fotografia
   frontale, con luce naturale e sfondo semplice, rende più leggibile il capo.
3. Controllare l'anteprima; «Cambia foto» e «Rimuovi» permettono di correggere
   la scelta prima del salvataggio.
4. Inserire un nome riconoscibile, per esempio “T-shirt bordeaux”.
5. Lasciare vuoti categoria e colore per farli stimare automaticamente dalla
   fotografia, oppure compilarli manualmente.
6. Se disponibili, aggiungere prezzo e data di acquisto. Servono per
   cost-per-wear, anzianità del capo e identificazione dei capi fantasma.
7. Selezionare «Salva nel guardaroba».

La condizione del capo non viene stimata in questo passaggio: viene
diagnosticata nella pagina di dettaglio.

### Cosa mostrare

Compilare solo foto, nome, prezzo e data; lasciare vuoti categoria e colore.
Mostrare l'anteprima, quindi salvare.

### Cosa dire

> «L'utente fornisce il minimo indispensabile: una foto e un nome. Se categoria
> e colore non sono indicati, ClosetAI prova a ricavarli dall'immagine. Prezzo e
> data non sono obbligatori, ma rendono più significative le statistiche.»

### Risultato atteso

Dopo «Salva nel guardaroba» si apre il dettaglio del nuovo capo. Categoria,
colore e confidenza della classificazione sono visibili nella «Carta
d'identità». Una confidenza bassa invita a verificare il risultato: non indica
un errore certo.

## 4. Controllare e correggere il dettaglio

La pagina del capo riunisce fotografia, identità, utilizzi e azioni di cura.
Mostra anche «Utilizzi», «Cost-per-wear» e «Ultimo uso».

### Procedura utente

1. Controllare categoria, colore e «Confidenza classificazione».
2. Usare «Modifica» per correggere nome, categoria, colore, prezzo o data.
3. Usare «Rianalizza foto» per chiedere una nuova stima automatica di categoria
   e colore. Questa azione non sostituisce la fotografia.
4. Nella sezione «Cura e seconda vita», verificare lo stato proposto e, se
   necessario, correggerlo nel menu «Stato del capo».

Lo stato ha tre livelli: «In buono stato», «Da curare» e «Danneggiato». La
diagnosi può provenire dalla rete neurale oppure dal fallback a regole esperte;
l'interfaccia indica la fonte. Rimane un supporto alla decisione, non una
certificazione della qualità tessile.

### Cosa mostrare

Indicare la percentuale di confidenza, aprire «Modifica» senza cambiare pagina
definitivamente, quindi tornare indietro e mostrare «Rianalizza foto» e «Stato
del capo».

### Cosa dire

> «L'automazione non nasconde l'incertezza. L'app mostra la confidenza e lascia
> sempre all'utente l'ultima parola: si possono correggere i metadati e lo stato
> del capo.»

### Risultato atteso

Le correzioni salvate aggiornano il dettaglio e alimentano le analisi
successive. «Rianalizza foto» aggiorna categoria, colore e confidenza.

## 5. Registrare l'uso reale

Un utilizzo può essere registrato in tre punti:

- «Indossato» sulla card del capo nella home;
- «Indossato oggi» nel dettaglio;
- «Indosso questo» su una proposta nella pagina «Cosa metto oggi?».

L'ultimo comando registra insieme tutti i capi dell'outfit. Nel dettaglio, «La
sua storia» mostra gli utilizzi più recenti e consente di rimuovere una
registrazione errata.

Il cost-per-wear è calcolato solo quando sono presenti sia il prezzo sia almeno
un utilizzo. È il rapporto fra prezzo di acquisto e numero di utilizzi
registrati: più il capo viene usato, più il costo attribuito a ogni uso
diminuisce. Un capo in
«Seconda vita» non può ricevere nuovi utilizzi.

### Cosa mostrare

Premere «Indossato oggi» su un capo con prezzo, poi osservare l'aumento di
«Utilizzi», l'aggiornamento di «Ultimo uso» e del «Cost-per-wear».

### Cosa dire

> «Questa è l'informazione più importante che l'utente aggiunge nel tempo. Non
> misuriamo soltanto quanti capi possiede, ma quali entrano davvero nella sua
> vita. Il cost-per-wear rende visibile il valore d'uso, non il valore di
> mercato.»

### Risultato atteso

Compare il messaggio «Utilizzo di oggi registrato. Il cost-per-wear è stato
aggiornato.» e la nuova riga appare nello storico.

## 6. Ottenere una proposta con «Cosa metto oggi?»

La pagina costruisce combinazioni con i capi attivi del guardaroba e le ordina
in base a compatibilità dei colori, adeguatezza al meteo, capi fantasma e un
piccolo segnale ricavato dai feedback precedenti.

### Procedura utente

1. Selezionare una città tra Pisa, Milano, Roma, Torino e Napoli.
2. Scegliere 2, 3 o 4 proposte.
3. Se utile, indicare l'occasione «Lavoro», «Tempo libero» o «Sera».
4. Premere «Nuove proposte».
5. Leggere la motivazione e le barre «Palette», «Meteo» ed eventualmente
   «Anti-fantasma».
6. Usare il cuore o la `X` per esprimere un feedback.
7. Se si sceglie la combinazione, premere «Indosso questo».

Nella versione attuale l'occasione viene salvata insieme al feedback e agli
utilizzi, ma non filtra direttamente la generazione iniziale degli outfit. La
città determina invece il contesto meteo. Se Open-Meteo non è raggiungibile,
l'app mostra l'avviso «Meteo live non disponibile» e usa condizioni miti di
riferimento.

La percentuale dentro «Compatibilità» è un punteggio relativo usato per
ordinare le proposte, non la probabilità che l'outfit piaccia a ogni persona.
Il feedback modifica leggermente i ranking futuri e non riaddestra una rete
neurale.

### Cosa mostrare

Cambiare città, chiedere tre proposte, aprire con il cursore una fotografia,
indicare il punteggio e le sue componenti, quindi salvare un feedback. Se i dati
della demo possono essere modificati, premere «Indosso questo» sulla prima
proposta.

### Cosa dire

> «Il sistema non genera vestiti nuovi: ricombina quelli presenti nel
> guardaroba. Il punteggio è trasparente, perché separa palette, meteo e bonus
> anti-fantasma. Il feedback dell'utente pesa poco e personalizza l'ordine senza
> sostituire gli altri criteri.»

### Risultato atteso

Appaiono proposte complete ordinate per punteggio. Per generarne una servono
almeno un top e un pantalone, oppure un vestito. «Indosso questo» registra un
utilizzo per ogni capo della combinazione.

## 7. Riconoscere e recuperare i capi fantasma

Un **capo fantasma** è un capo attivo che:

1. non ha alcun utilizzo registrato;
2. è posseduto da almeno la soglia scelta, 30 giorni per impostazione
   predefinita.

Per calcolare il tempo di possesso si usa la data di acquisto; se manca, si usa
la data di inserimento in ClosetAI. Questa è una regola deterministica, non una
predizione di machine learning.

Il segnale è visibile in tre punti:

- «Impatto»: metrica «Capi fantasma», selettore 30/60/90/180 giorni e lista
  «Capi da riscoprire»;
- dettaglio del capo: badge «Fantasma · mai indossato da 30+ giorni»;
- «Cosa metto oggi?»: componente «Anti-fantasma» quando una proposta contiene
  un capo mai indossato da almeno 30 giorni.

### Cosa mostrare

Aprire «Impatto», cambiare la soglia da 30 a 60 giorni e indicare come cambiano
conteggio e lista. Aprire uno degli elementi di «Capi da riscoprire», quindi
tornare alle proposte outfit e cercare la barra «Anti-fantasma».

### Cosa dire

> «Fantasma non significa semplicemente poco usato: significa mai indossato e
> posseduto da abbastanza tempo. La soglia è esplicita e modificabile. Lo scopo
> non è giudicare l'utente, ma far riemergere un capo prima di un nuovo
> acquisto.»

### Risultato atteso

Registrando il primo utilizzo, il capo esce dalla lista dei fantasmi. Cambiare
la soglia modifica l'analisi visualizzata, non elimina né modifica il capo.

## 8. Leggere «Impatto»: stato, gap e sostenibilità

La pagina «Impatto» riunisce quattro domande dell'utente.

### Quanto uso ciò che possiedo?

Le metriche «Capi attivi», «Utilizzi registrati», «Cost-per-wear medio» e «Capi
fantasma» descrivono il guardaroba attivo. «I capi che lavorano di più» mostra i
più indossati. Sono indicatori descrittivi, non valutazioni finanziarie.

### In che stato sono i capi?

«Cosa richiede cura?» divide i capi attivi in «In buono stato», «Da curare»,
«Danneggiati» e «Da verificare». Aprendo il singolo capo si può controllare e
correggere lo stato.

### Ho davvero un gap nel guardaroba?

«Cosa manca davvero?» analizza categorie, varietà cromatica, presenza di colori
neutri e rapporto dei capi fantasma. Può indicare, per esempio, un capospalla
mancante oppure troppe t-shirt. In fondo alla card è dichiarata la fonte:
«rete neurale addestrata» quando i pesi sono disponibili, altrimenti «regole
esperte».

Il risultato è un consiglio, non un ordine di acquisto. «Nessun acquisto
necessario» è un risultato valido e coerente con l'obiettivo del progetto.

### Quale impatto ho registrato?

«Da azione a CO₂ evitata» somma riparazioni e azioni di seconda vita registrate
dall'utente. Il valore in kg CO₂eq è una **stima di scenario** basata sul tipo
di capo e di azione; non è una misurazione diretta né un'analisi completa del
ciclo di vita. Anche gli equivalenti in chilometri, voli o superficie di
foresta sono confronti indicativi.

### Cosa mostrare

Scorrere nell'ordine: metriche, «Cosa manca davvero?», «Cosa richiede cura?»,
«Da azione a CO₂ evitata», «I capi che lavorano di più» e «Capi da
riscoprire».

### Cosa dire

> «Questa pagina trasforma i dati in quattro decisioni: cosa rimettere in
> rotazione, cosa curare, se esiste davvero un vuoto funzionale e quali azioni
> circolari ho già compiuto. L'impatto ambientale è presentato con unità e
> limiti espliciti: è una stima, non una misura fisica.»

### Risultato atteso

L'utente trova nello stesso punto rotazione, stato, gap e impatto. Premendo
«Aggiorna dati» ricarica tutte le analisi; se un servizio opzionale non risponde,
l'app può mantenere disponibili i dati principali e segnalare un aggiornamento
parziale.

## 9. Curare un capo o dargli una seconda vita

Aprire il dettaglio di un capo e raggiungere «Cura e seconda vita».

### Procedura utente

1. Controllare «Stato del capo».
2. Aggiungere, se utile, una «Nota per la prossima azione».
3. Leggere «Azioni suggerite», motivazione e CO₂eq stimata.
4. Premere «Registra» accanto a «Ripara», «Scambia», «Vendi», «Dona» o
   «Ricicla» e confermare.
5. Controllare l'azione nello «Storico circolare».

«Ripara» mantiene il capo attivo. «Scambia», «Vendi», «Dona» e «Ricicla» lo
spostano in «Seconda vita» e impediscono nuovi utilizzi. Rimuovendo l'ultima
azione che lo aveva ritirato, il capo viene riattivato. Rimuovere un'azione
ricalcola anche l'impatto.

«Elimina capo», nella «Zona delicata», è diverso: elimina definitivamente
capo, foto, utilizzi e azioni associate e va usato soltanto per correggere un
inserimento indesiderato.

### Cosa mostrare

Scegliere un capo «Da curare», aggiungere una breve nota e registrare
«Ripara». In alternativa, per mostrare «Seconda vita», registrare «Dona» su un
capo preparato per la demo e poi trovarlo con il filtro «Seconda vita» nella
home.

### Cosa dire

> «La diagnosi diventa utile solo quando conduce a un gesto. Riparare prolunga
> l'uso; scambio, vendita, donazione e riciclo chiudono l'uso personale ma
> conservano la storia dell'azione e il suo impatto stimato.»

### Risultato atteso

Compare una conferma con la CO₂eq stimata, lo storico si aggiorna e la pagina
«Impatto» include la nuova azione. Un capo ritirato compare con il badge «In
seconda vita».

## 10. Funzioni opzionali e prototipi

Queste funzioni possono non essere visibili: dipendono dalla configurazione
locale e non sono necessarie per completare il flusso principale.

- «AI · descrizione» genera o rigenera un breve testo sul capo soltanto quando
  è configurato un modello linguistico.
- «AI · try-on virtuale» appare soltanto quando il backend generativo è
  disponibile. Accetta un ritratto JPG/PNG/WebP fino a 10 MB e su CPU può
  richiedere alcuni minuti. Il risultato è un'anteprima generata, non una prova
  affidabile di vestibilità o taglia.
- Il coach nella pagina «Impatto» appare quando è configurato il modello
  linguistico; usa statistiche del guardaroba e azioni già registrate.
- «ML Lab» è un'area tecnica: mostra disponibilità e metriche dei due modelli,
  consente di provare lo stato su una foto senza salvare un capo e di simulare
  un guardaroba immaginario per la gap analysis. Non modifica il guardaroba.
- «Specchio» è una vista kiosk a schermo intero con ora, meteo e una proposta;
  si aggiorna ogni cinque minuti. È un prototipo per uno smart mirror, non una
  funzione richiesta per il normale utilizzo web.

### Cosa dire

> «Il percorso principale continua a funzionare senza i moduli generativi. Il
> Lab e lo Specchio servono a rendere ispezionabili due estensioni del
> prototipo, ma non vanno confusi con le attività quotidiane dell'utente.»

### Risultato atteso

Se una funzione opzionale non è configurata, il relativo controllo è nascosto
oppure viene indicata chiaramente la sua indisponibilità; il guardaroba resta
utilizzabile.

## 11. Routine consigliata

Una spiegazione semplice dell'uso nel tempo può essere questa:

1. **Una volta:** fotografare i capi e verificare categoria, colore, prezzo e
   data.
2. **Ogni giorno:** registrare i capi indossati oppure scegliere «Indosso
   questo» da una proposta.
3. **Ogni settimana:** controllare «Capi da riscoprire», stato e gap.
4. **Quando serve:** registrare riparazione o seconda vita e osservare
   l'impatto aggregato.

### Cosa dire per chiudere la demo

> «ClosetAI non chiede di comprare tecnologia per comprare altri vestiti. Chiede
> pochi dati, restituisce decisioni comprensibili e mantiene l'utente al centro:
> usare di più, curare prima e acquistare soltanto quando emerge un bisogno
> reale.»

## 12. Risoluzione dei problemi più comuni

| Problema visibile | Controllo o soluzione |
| --- | --- |
| La pagina non si apre | Verificare che frontend e backend siano entrambi attivi e aprire `http://localhost:5173`, non la porta delle API. |
| «Alcuni indicatori non sono aggiornati» | Aggiornare la pagina o usare «Aggiorna dati». Il catalogo può restare disponibile anche se un'analisi secondaria fallisce. |
| La foto viene rifiutata | Usare JPG, PNG o WebP e restare sotto 10 MB. |
| Categoria o colore sono errati | Usare «Modifica» per la correzione manuale oppure «Rianalizza foto». |
| Non appare alcun outfit | Inserire almeno un top e un pantalone, oppure un vestito. Usare categorie riconosciute come `t-shirt`, `camicia`, `felpa`, `maglione`, `jeans`, `pantaloni`, `shorts`, `gonna` o `vestito`. |
| Il meteo non è live | Il banner segnala il fallback; le proposte usano condizioni miti di riferimento. |
| Il cost-per-wear è «—» | Aggiungere il prezzo e registrare almeno un utilizzo. |
| Un capo non diventa fantasma | Verificare che sia attivo, senza utilizzi e posseduto da almeno la soglia scelta. Senza data di acquisto, il conteggio parte dall'inserimento nell'app. |
| L'impatto verde resta a zero | Registrare almeno una riparazione o un'azione di seconda vita: i semplici utilizzi non vengono convertiti in CO₂eq evitata. |
| Non si può registrare «Indossato oggi» | Il capo è probabilmente in «Seconda vita». Rimuovere l'ultima azione di ritiro solo se era stata registrata per errore. |
| Descrizione AI, coach o try-on non compaiono | Sono moduli opzionali e vengono mostrati soltanto quando il relativo backend è configurato. |
| «ML Lab» indica «da addestrare» | I pesi del modello non sono presenti. La gap analysis principale può comunque usare il fallback a regole esperte. |

## 13. Scaletta compatta per l'esame (6–8 minuti)

| Tempo | Mostrare | Messaggio principale | Risultato visibile |
| --- | --- | --- | --- |
| 0:00–0:40 | Home, «Vesti meglio. Compra meno.» | Usare meglio ciò che si possiede | Visione complessiva |
| 0:40–1:40 | «Aggiungi un capo» | Foto e nome; categoria e colore stimati ma correggibili | Nuovo dettaglio con confidenza |
| 1:40–2:20 | «Indossato oggi» | L'uso reale alimenta storia e cost-per-wear | Metriche aggiornate |
| 2:20–3:30 | «Cosa metto oggi?» | Ranking trasparente: palette, meteo, anti-fantasma e feedback leggero | Outfit e registrazione batch |
| 3:30–4:20 | «Capi fantasma» | Regola: zero utilizzi + anzianità minima + capo attivo | Conteggio, lista e badge |
| 4:20–5:30 | «Impatto» | Stato, gap e CO₂eq stimata guidano decisioni diverse | Quadro sintetico del guardaroba |
| 5:30–6:40 | «Cura e seconda vita» | Dalla diagnosi a un gesto registrato | Storico e impatto aggiornati |
| 6:40–7:10 | Chiusura | L'utente verifica e mantiene il controllo | Ritorno al ciclo in sei tappe |

Durante la prova è preferibile usare un guardaroba già popolato con fotografie,
prezzi, date, utilizzi e almeno un'azione circolare. Prima dell'esame verificare
anche che esistano le categorie necessarie per generare un outfit. Non affidare
la riuscita della demo ai moduli opzionali.
