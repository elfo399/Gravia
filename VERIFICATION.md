# Dashboard e temi · 5 ottobre 2026

Verifica locale con dati demo e database temporaneo, separati dal Raspberry.

| Controllo | Esito |
| --- | --- |
| Frontend Vitest | **60 passati**, inclusi 7 casi dei temi e 5 casi delle letture isolate per profilo |
| Biome / TypeScript / Vite | Lint e build passati |
| Docker runtime | Immagine finale amd64 costruita con la nuova interfaccia |
| Browser desktop | Dashboard a sei card, temi chiaro e scuro, preferenza conservata al ricaricamento |
| Browser mobile 390×844 | Dashboard e navigazione accessibili, nessuno scorrimento orizzontale |
| Pesata demo | Completata e salvata; peso, sensori, grafico e statistiche aggiornati |
| Isolamento dati | Storico sintetico usato soltanto nell'anteprima locale; nessuna pesata di test sul Raspberry |

# Calibrazione Gravia · 5 ottobre 2026

Verifica locale su Docker Desktop / container Linux, con board simulate e database temporanei separati dai dati personali.

| Controllo | Esito |
| --- | --- |
| Backend Pytest | **94 passati**, inclusi 23 nuovi casi di calibrazione e integrazione REST su entrambi i trasporti reali |
| Frontend Vitest | **48 passati**, inclusi 20 casi del wizard/card e il blocco della pesata durante calibrazione |
| Ruff lint e formato | Passati sul backend e sul codice host esistente |
| Biome | Passato, 48 file frontend |
| TypeScript / Vite | Build passata |
| Alembic | `upgrade head` e `check` passati su SQLite temporaneo; nessuna operazione mancante rilevata |
| Docker runtime | Immagine amd64 finale costruita con frontend compilato |
| Browser desktop e mobile 390×844 | Wizard completo, letture di 4 secondi, verifica indipendente e salvataggio su backend di prova |
| Restart applicazione di prova | Calibrazione ancora Attiva, stessa data e fattore; reset con conferma torna a Non configurata |
| Isolamento della verifica | Nessuna calibrazione fittizia o pesata di test scritta sul Raspberry |
| [Jenkins #12](https://jenkins.elfo3.dev/job/Gravia/12/) | **SUCCESS**, 100,277 s: test, build ARM64 e deploy del commit `988c9b1` tramite webhook GitHub |
| Database sul Raspberry dopo deploy | Revision `0002`, `alembic check` valido, integrità SQLite `ok`, una pesata preesistente conservata, zero calibrazioni fittizie |
| API e interfaccia pubbliche | Settings HTTP 200, nuovo bundle frontend, WebSocket WSS con `calibrationActive=false`; board spenta, pulsante Calibra correttamente disabilitato |

La calibrazione interna Nintendo resta invariata. Le prove sopra confermano comportamento e persistenza del software, **non l'accuratezza della board fisica**. La procedura con peso noto, restart e cinque pesate reali è nella [guida tecnica](docs/GUIDA_TECNICA.md#procedura-fisica-sul-raspberry). La warning di deprecazione Starlette/TestClient è preesistente e non causa test falliti.

# Jenkins e deploy Raspberry · 5 ottobre 2026

Verifica eseguita sull'agent nativo `orio-raspberry-pi` di [Jenkins](https://jenkins.elfo3.dev/job/Gravia/), oltre alle prove locali sotto riportate.

| Controllo | Esito |
| --- | --- |
| Agent | Linux ARM64 `aarch64`, utente `elfo`, Docker Compose v2.39.4, `flock` disponibile |
| [Build Jenkins #2](https://jenkins.elfo3.dev/job/Gravia/2/) | **SUCCESS**: 43 test backend + 24 frontend, Ruff, Biome e build ARM64 |
| Prima installazione | `/home/elfo/gravia`, dati persistenti fuori dal workspace Jenkins |
| Runtime | Modalità `real`, porta HTTP **8081** (8080 occupata da Jenkins), rete host, capability rimosse |
| Verifica post-deploy | HTTP health `ok`, snapshot WebSocket `ok`; board configurata ma offline al momento del test |
| Webhook GitHub | Push, JSON, SSL verificato, firma SHA-256 con il secret già configurato su Jenkins; ping firmato **HTTP 200** |
| Ripristino locale con release difettosa | Applicazione invalida rifiutata, immagine precedente ripristinata, HTTP/WebSocket nuovamente validi, integrità backup SQLite `ok` |
| Protezione dati | Nessuna pesata avviata durante la verifica CI; `.env` e database conservati sul Raspberry |
| Proxy NPM con hostname | `gravia:8081`, mapping Docker persistente `gravia:host-gateway`, location Advanced con hostname letterale, `nginx -t` valido |
| Dominio pubblico | `https://gravia.elfo3.dev/` HTTP 200, health `ok`, snapshot WSS valido, UI «Live connesso» |
| Altri Proxy Host dopo ricreazione NPM | Docker, Proxy, Orio e Synapse HTTP 200; Jenkins HTTP 403 previsto senza autenticazione |

La board deve essere accesa/SYNC per verificare la connessione e una pesata fisica. Queste prove confermano la pipeline e l'applicazione, non l'accuratezza della bilancia. Il proxy NPM inoltra a `gravia:8081` per questa installazione.

# Verifica v0.2 locale · 5 ottobre 2026

Verifica eseguita realmente su Windows con Docker Desktop / container Linux. Nessun Raspberry o Bluetooth fisico collegato a questa sessione. La configurazione locale rimane demo su **http://localhost:8081**; gli altri progetti, incluso ORIO, restano invariati.

| Controllo | Esito |
| --- | --- |
| `docker compose config` | Valido: rete bridge, porta localhost 8081, bind data |
| Compose base + `docker-compose.raspberry.yml` | Valido: rete host, ports rimossi, cap_drop ALL, grace period 120s |
| `docker compose build` | Immagine finale amd64 costruita, frontend compilato |
| `docker compose up -d --wait` / ps / logs --tail=200 | App healthy, startup regolare, modalità demo |
| Python / wiibalance runtime | Python 3.12.15 / wiibalance 1.4.1 |
| Ruff lint e formato | Passati; 40 file Python formattati |
| Pytest senza hardware | **43 test passati** |
| Biome | Passato: 42 file, nessuna correzione necessaria nel controllo finale |
| Vitest | **24 test passati** in 5 file |
| TypeScript / Vite | Build passata |
| Demo end-to-end | 97 campioni WebSocket, peso 72.537 kg, Measurement persistita |
| Stati demo | WAITING_FOR_USER → MEASURING → STABILIZING → COMPLETED |
| Persistenza dopo rebuild e restart | Le 5 pesate precedenti sono identiche; 6 totali dopo il test demo |
| SQLite integrity_check | ok |
| Alembic current / check | 0001 head, nessuna nuova operazione di schema |
| Rete Docker in modalità demo | REST + WebSocket raggiungibili da un altro container via **gravia:8080** |
| Modalità real offline nell'immagine finale | Container temporaneo healthy, REST responsive, retry 2/5/10s, EAFNOSUPPORT leggibile |
| Avvio pesata con hardware offline | HTTP 503; zero Session e zero Measurement nel database temporaneo |
| Evento hardware al collegamento WS | board_connected in demo; board_disconnected in real offline |
| Cinque route SPA | HTTP 200 in demo e real offline |
| Browser desktop | DEMO e hardware connesso in demo; REALE, hardware non connesso e pulsante disabilitato in real offline; realtime connesso in entrambi |
| Browser mobile | Verificato a viewport 390×844, larghezza contenuto = scrollWidth = 375, senza overflow orizzontale |
| Build ARM64 | **Immagine completa linux/arm64 costruita** con buildx, tag gravia:0.2-arm64 |
| Avvio ARM64 sotto emulazione | aarch64, Python 3.12.15, wiibalance 1.4.1, cap_drop ALL, health e SQLite ok; REST + WS e cinque route SPA passati |
| Clean shutdown reale offline | Verificato sul container temporaneo; task di retry arrestato e shutdown Uvicorn completato |
| Diagnostica | API, stampa campioni, read error, Ctrl+C e disconnect verificati con fake nei test |

Il wheel wiibalance 1.4.1 è stato scaricato e ispezionato. Confermati nomi dei sensori, centro di pressione come tupla, batterie, sostituzione dell'oggetto Weights a ogni pacchetto, socket diretti L2CAP e assenza di D-Bus nell'adapter diretto. È stata verificata con un fake anche la pulizia del costruttore parzialmente fallito e il join del worker della libreria.

Il test real sul PC ha restituito **[Errno 97] Address family not supported by protocol**, atteso senza Bluetooth del Raspberry. Dimostra robustezza dello startup, disponibilità HTTP e gestione degli errori, **non la connessione Bluetooth nel container**. La build ARM64 usa emulazione: non è una prova radio né una prova del kernel Raspberry.

Pytest segnala la stessa deprecazione Starlette/httpx del TestClient presente in v0.1. Tutti i test passano; il runtime non usa TestClient. Nessuna migrazione aggiunta, nessuna modifica a StabilityService, nessun offset/scale introdotto.

## File della v0.2

| Area | File modificati o aggiunti |
| --- | --- |
| Adapter | backend/app/balance_board/board.py, demo_board.py, real_board.py, **wiibalance_client.py** (nuovo) |
| Stato | **backend/app/models/board_status.py** (nuovo), backend/app/configuration.py, application_lifecycle.py |
| Sessioni/API/realtime | backend/app/services/session_service.py, backend/app/api/application.py, backend/app/websocket/live_measurements.py, backend/app/main.py |
| Dipendenze | backend/pyproject.toml, backend/requirements.lock, frontend/package.json |
| Script | **backend/scripts/test_real_board.py** (nuovo), backend/scripts/verify_demo.py |
| Test backend | backend/tests/test_api.py, test_session_service.py, **test_real_board.py**, **test_real_board_diagnostic.py** (nuovi) |
| Contratto frontend | **frontend/src/types/BoardStatus.ts** (nuovo), frontend/src/api/websocket.ts, websocket.test.ts |
| Hook | frontend/src/hooks/useLiveMeasurement.ts, **useLiveMeasurement.test.ts** (nuovo) |
| UI | frontend/src/components/CurrentWeightCard.tsx, **CurrentWeightCard.test.tsx** (nuovo), AppSidebar.tsx, frontend/src/pages/SettingsPage.tsx, frontend/src/styles.css |
| Container/config | docker/Dockerfile, **docker-compose.raspberry.yml** (nuovo), .env.example |
| Documentazione | README.md, VERIFICATION.md |

Il Compose principale e il `.env` locale mantengono la configurazione v0.1. I file del progetto erano già non tracciati da Git: non sono stati creati commit. Gli script, Compose temporanei e screenshot della verifica si trovano nella cartella artifacts, esclusa da Git.

## Prove visive

- [Dashboard reale offline](artifacts/gravia-v02-real-offline.png)
- [Dashboard demo desktop](artifacts/gravia-v02-demo.png)
- [Dashboard demo mobile](artifacts/gravia-v02-demo-mobile.png)

## Da verificare sul Raspberry

Connessione radio effettiva dal container, cap_drop ALL con il kernel/profili di sicurezza locali, pairing/risveglio/SYNC, orientamento e accuratezza rispetto a un peso noto, letture persistenti, disconnessione fisica e NPM dell'utente. Prima della rete host, configurare extra_hosts gravia:host-gateway nel Compose NPM oppure usare IP LAN:8080; la porta 8080 dell'host deve essere libera. Preparare il proprietario UID 0 della cartella data per il runtime privo di capability. Procedura completa nel README.

**Software implementation complete. Final Bluetooth container verification must be performed on the Raspberry Pi.**

---

# Verifica storica v0.1 · 5 ottobre 2026

Verifica eseguita realmente sul computer locale, con Docker Desktop e container Linux.

| Controllo | Esito |
| --- | --- |
| `docker compose config` | Configurazione valida |
| `docker compose build` | Immagine creata, TypeScript e Vite compilati |
| `docker compose up --build -d --wait` | Avvio riuscito, healthcheck healthy |
| `docker compose ps` | Gravia attiva su 127.0.0.1:8081 |
| Pytest | 17 test passati |
| Ruff lint e formato | Entrambi passati |
| Vitest | 16 test passati, 3 file |
| Biome | Passato, 39 file verificati |
| Alembic current / check | Revision 0001 head; nessuna differenza con i modelli |
| Frontend e cinque route | HTTP 200 |
| API health, settings, profiles, measurements | HTTP 200 |
| Demo end-to-end REST + WebSocket | 97 campioni, risultato persistito |
| Stati sessione via WebSocket | WAITING_FOR_USER → MEASURING → STABILIZING → COMPLETED |
| Browser desktop | Avvio dal pulsante, peso live, completamento, grafico e storico |
| Browser mobile | Dashboard e navigazione inferiore verificate a 390 × 844 |
| Riavvio con `down` / `up` | Identificativi delle quattro pesate conservati |
| SQLite integrity check | ok |

Il database locale contiene Alfonso, altezza 180 cm, e quattro pesate prodotte durante la verifica. I test automatici usano database temporanei creati tramite Alembic e non modificano il database dell'applicazione.

La porta 8080 era occupata da ORIO. Il `.env` locale usa 8081; il progetto mantiene 8080 come default configurabile. ORIO è rimasta in esecuzione.

Pytest segnala una deprecazione di Starlette relativa all'uso di httpx nel TestClient: i test passano e il runtime dell'applicazione non usa TestClient. Nessun errore applicativo è stato rilevato nei log del container o nella console della dashboard.

Bluetooth reale non implementato, come previsto: `RealBoard` restituisce un errore chiaro. La verifica riguarda la DemoBoard; la calibrazione e il comportamento fisico devono essere validati sul Raspberry Pi con la board reale.
