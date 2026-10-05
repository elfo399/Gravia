# Training — Gravia 0.3.0

Training aggiunge tre esercizi brevi all'installazione esistente. Apri **Training** nel menu,
scegli il profilo e accendi la Balance Board. Avvia un esercizio, sali sulla pedana e attendi
il countdown 3–2–1. I punteggi e i risultati si salvano automaticamente nello storico Training
del profilo, separato dalle pesate. Il record personale usa solo attività completate.

## Esercizi

| Esercizio | Durata | Obiettivo |
| --- | --- | --- |
| Balance Hold | 30 secondi | Mantenere il centro di pressione nella zona centrale |
| Weight Shift | 10 target, fino a circa 40 secondi | Spostare il peso a sinistra, destra, avanti e dietro |
| Symmetry | 30 secondi | Distribuire il peso tra i due lati, nella fascia 45–55% |

Le durate di Balance Hold e Symmetry sono attualmente fissate a 30 secondi.
Il codice permette di estenderle in seguito; non sono disponibili preset aggiuntivi o minigiochi.
Nella modalità demo si usa la stessa DemoBoard delle pesate: oscilla vicino al centro.
Weight Shift può quindi concludersi con dieci target mancati e zero punti. Il risultato non
viene alterato per simulare una prestazione migliore.

## Architettura e campioni

```text
RealBoard / BluezRealBoard → CalibratedBoard → BoardSample → ActivityService → esercizio
DemoBoard ────────────────────────────────→ BoardSample → ActivityService → esercizio
                                                       ↓                  ↓
                                                /ws/live             ActivitySession
                                                       ↓                  ↓
                                           useLiveMeasurement ← API REST / SQLite
                                                       ↓
                                              useActivitySession → UI
```

L'applicazione mantiene un solo adattatore hardware e un solo WebSocket frontend.
I motori ricevono esclusivamente BoardSample e tempi: non conoscono Bluetooth, HID, socket,
database o interfaccia. La calibrazione viene applicata una volta, a monte di pesate e Training.
Il punto SVG usa la stessa proiezione del centro di pressione della dashboard; il disegno
del target è condiviso da Balance Hold e Weight Shift.

ActivityService riusa il lock di SessionService. Avvio di Training, pesata, avvio/reset
calibrazione controllano lo stesso stato sotto lock; una richiesta concorrente restituisce
409 con un messaggio leggibile. Anche un task che sta chiudendo il flusso mantiene l'esclusività.
Una sola istanza Uvicorn deve gestire la board, come nell'installazione attuale: il lock è in memoria.

La presenza richiede almeno il peso minimo delle pesate (20 kg nella configurazione predefinita)
per un secondo continuo, poi il countdown dura tre secondi. Una discesa prima di VIA riporta
all'attesa. Durante l'esercizio una discesa di almeno 0,8 secondi interrompe la sessione;
brevi variazioni sono tollerate e non contribuiscono alle medie. Campioni non finiti,
tempi non monotoni, un intervallo eccessivo o un flusso bloccato interrompono l'attività.
Il timer segue il tempo monotono dei campioni; un timeout complessivo evita attese indefinite.
Disconnessione e Power OFF producono ERROR e liberano la board. Il servizio Bluetooth e le
regole esistenti del pulsante Power non vengono modificati.

## ActivitySession e migration

La migration Alembic **0003**, successiva a **0002**, crea `activity_sessions` e gli indici
su profilo e tipo di attività, senza modificare le tabelle delle pesate o della calibrazione.

| Campo | Significato |
| --- | --- |
| id, profile_id | Identificatore e FK del profilo |
| activity_type | Stringa, estensibile a future attività senza cambiare schema |
| status | WAITING_FOR_USER, COUNTDOWN, ACTIVE, COMPLETED, CANCELLED, ERROR |
| started_at, completed_at, created_at | Date UTC |
| duration_seconds | Durata prevista durante la sessione; durata effettiva alla conclusione |
| score | Punteggio solo per COMPLETED |
| result_json | Metriche aggregate solo per COMPLETED |
| error_message | Motivo dell'interruzione, quando presente |

Non vengono persistiti campioni grezzi. L'annullamento e gli errori conservano una riga di audit
con punteggio e risultato nulli. Al riavvio le sessioni incomplete diventano ERROR.
Eliminare un profilo elimina anche il suo storico Training, come già avviene per le pesate;
il backend rifiuta l'eliminazione se quel profilo ha un'attività in corso.

## API

| Metodo | Endpoint | Uso |
| --- | --- | --- |
| POST | /api/v1/activities | Avvio: profileId, activityType, durationSeconds facoltativo (30) |
| GET | /api/v1/activities | Elenco, filtri facoltativi profileId e activityType |
| GET | /api/v1/activities/active | Ripristino dell'attività in corso dopo navigazione/riconnessione |
| GET | /api/v1/activities/{id} | Sessione e risultato |
| POST | /api/v1/activities/{id}/cancel | Annullamento |

Tipi ammessi: BALANCE_HOLD, WEIGHT_SHIFT, SYMMETRY. Creazione: 201; dati non validi: 422;
profilo/sessione inesistenti: 404; board occupata o sessione già terminata: 409;
board spenta: 503. JSON REST e WebSocket usano camelCase, coerentemente con le API esistenti.

## Eventi sul WebSocket esistente

| Evento | Contenuto |
| --- | --- |
| activity_status | activitySessionId, profileId, activityType, status, countdown, durationSeconds, message |
| activity_live | activitySessionId, elapsed, remaining, score, weight, centerOfPressure, data dell'esercizio |
| activity_completed | activitySessionId, activity completa con score e resultJson salvati |

Alla connessione il server riproduce gli ultimi eventi Training oltre agli snapshot già esistenti.
La UI filtra sessione, esercizio e profilo; i dati della pesata non vengono riutilizzati come letture Training.
Il backend invia i dati live al massimo ogni 100 ms. Il frontend mostra il punteggio ricevuto,
senza ricalcolarlo. Un nuovo avvio cancella lo snapshot del risultato precedente.

## Punteggi backend

**Balance Hold**: `distance = hypot(center_x, center_y)`;
`quality = clamp(1 - distance / 0.75, 0, 1)`;
`score = round(average_quality * 1000)`. Zona centrale: raggio **0.15**.
Le medie sono ponderate per il tempo dei campioni validi, non per il loro numero.
Risultato: averageCenterDistance, maxCenterDistance, centeredPercent.

**Symmetry**: `left_ratio = (front_left + rear_left) / total_weight`;
`quality = clamp(1 - abs(left_ratio - 0.5) / 0.20, 0, 1)`;
`score = round(average_quality * 1000)`. Fascia equilibrata inclusiva: **45–55%**.
Risultato: averageLeftPercent, averageRightPercent, balancedPercent.

**Weight Shift**: dieci target pseudo-casuali senza ripetizioni consecutive.
Coordinate LEFT (-0.45, 0), RIGHT (0.45, 0), FRONT (0, 0.45), REAR (0, -0.45).
Il target è raggiunto solo dopo **0.4 s continui** entro un raggio **0.18**.
Uscire dal target o perdere presenza resetta il mantenimento; nessun singolo campione basta.
Dopo **4 s** il target è mancato e si passa al successivo.
Ogni target raggiunto vale `round(100 + max(0, 50 * (1 - reaction_time / 4)))` punti;
reaction_time include il mantenimento ed è misurato dall'attivazione di quel target.
La somma è al massimo 1500; i target mancati valgono zero.
Risultato: targets, targetsReached, targetsMissed, averageReactionTime, bestReactionTime.
I tempi di reazione sono nulli quando non viene raggiunto alcun target.

## File principali

- Backend: `app/activities/{balance_hold,symmetry,weight_shift}.py`, `services/activity_service.py`,
  `models/activity_session.py`, `api/activities.py`, `alembic/versions/0003_activity_sessions.py`,
  `tests/test_activities.py`.
- Integrazione backend: lifecycle, registrazione router/modelli/Alembic, SessionService,
  BoardCalibrationService, ProfileService, CalibratedBoard e LiveMeasurements.
- Frontend: `pages/TrainingPage.tsx`, `pages/TrainingExercisePage.tsx`, `components/training/`,
  `hooks/useActivitySession.ts`, `types/ActivitySession.ts`, `api/activitiesApi.ts` e relativi test.
- Integrazione frontend: App, sidebar, WebSocket e hook live condivisi, selezione/eliminazione profili,
  blocco pulsanti pesata/calibrazione, proiezione SVG condivisa, CSS e versione.
- Deploy/documentazione: controlli pre-deploy e verifica API Training, README, guida e questo documento.
  La pipeline mantiene gli stessi passaggi semplici di test/build/deploy.

## Verifica e prove fisiche

I test backend usano migrazioni reali SQLite e BoardSample registrati con tempo virtuale,
senza accorciare le durate degli esercizi. Coprono formule, target, hold, timeout, presenza,
countdown, interruzioni, calibrazione applicata una volta, esclusività e API.
I test frontend verificano hub, record e storico, avvio singolo anche con StrictMode,
countdown, timer/punteggio, percentuali, target, risultati, annullamento, errori e payload WebSocket.

Verifiche automatiche: Pytest, Ruff, Biome, TypeScript/Vite, Alembic upgrade/check,
Docker Compose config/build. La prova nel browser usa la modalità demo con le durate reali.
Il deploy Jenkins attende che non ci siano pesate, Training o calibrazioni in corso,
crea il backup SQLite locale e controlla health, API Training e snapshot WebSocket.

Le seguenti prove richiedono una persona sulla **board reale** e restano da eseguire:

1. Con board vuota e spenta, una pressione Power: LED fisso e board connessa.
2. Avvia Balance Hold, sali, verifica countdown 3–2–1, segui il punto per 30 s e controlla
   risultato, storico e record. Ripeti Symmetry, spostando lentamente il peso tra i due piedi.
3. Avvia Weight Shift, segui tutte e quattro le direzioni senza sollevare i piedi. Verifica
   che un passaggio rapido non conti e che una sosta di 0.4 s raggiunga il target.
4. Durante ogni esercizio prova Annulla; verifica punteggio assente e nuova attività avviabile.
5. Scendi durante countdown: deve ripartire l'attesa. Scendi per più di 0.8 s durante ACTIVE:
   deve comparire l'interruzione senza risultato.
6. Premi Power durante ACTIVE: LED spento, ERROR, nessun punteggio; riaccendi con una sola
   pressione e riprova. Verifica anche lo spegnimento quando non ci sono attività.
7. Durante Training verifica che pesata e calibrazione siano bloccate; prova anche il contrario.
8. Controlla dopo il test che una normale pesata si concluda ancora e che la calibrazione
   impostata resti valida. Per valutarne la precisione serve un peso conosciuto.

Le prove con campioni registrati e DemoBoard non costituiscono una verifica fisica
della Wii Balance Board o della precisione della calibrazione.
