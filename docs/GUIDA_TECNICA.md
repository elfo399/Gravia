# Gravia · Guida tecnica

**Weight. Balance. Insight.** Una web app locale che trasforma la Nintendo Wii Balance Board in una bilancia smart. La v0.2 integra la board reale su Raspberry Pi Linux; la modalità demo resta disponibile senza hardware, Bluetooth o account.

Per **Power ON/OFF senza SYNC**, usare `bluez` e la [guida Power lifecycle](POWER_LIFECYCLE.md).
Le istruzioni wiibalance/L2CAP in questa pagina riguardano il fallback `direct`.

## Avvio rapido

Prerequisito: Docker Desktop avviato con container Linux e porta 8080 libera.

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose ps
```

Su macOS/Linux: `cp .env.example .env`. La copia serve solo alla prima configurazione; conserva le modifiche successive al tuo `.env`.

Apri **http://localhost:8080**. Troverai il profilo Alfonso (180 cm). Premi **Inizia misurazione**: in circa 10 secondi il peso si assesta e viene salvato automaticamente. Il grafico e lo storico si aggiornano. I dati non includono pesate storiche inventate.

**Su questo computer Gravia è avviata su http://localhost:8081**, perché ORIO occupa già la porta 8080. Il `.env` locale contiene `GRAVIA_PORT=8081`; `.env.example` mantiene 8080 come default. Se la porta è occupata, cambia `GRAVIA_PORT` nel `.env` e usa lo stesso numero nell'URL. La porta interna del container resta 8080.

```bash
docker compose down              # arresto, senza eliminare i dati
docker compose up -d            # riavvio
docker compose logs --tail=100   # log
```

L'applicazione espone la porta soltanto su `127.0.0.1`. Non richiede autenticazione ed è progettata per l'uso sul computer locale.

## Cosa contiene la v0.2

- Dashboard responsive: sidebar desktop, navigazione mobile, peso live, mappa SVG di pressione, grafico Recharts con intervalli 7/30/90 giorni.
- Profili locali: creazione, modifica, selezione ed eliminazione. Eliminare un profilo elimina anche le sue sessioni e misurazioni, dopo conferma nell'interfaccia.
- Sessioni persistite: attesa, misurazione, stabilizzazione, completamento, cancellazione ed errore. Una sola sessione può usare la board alla volta, anche con più schede del browser.
- Storico con filtro per profilo e date, variazione rispetto alla pesata precedente, note modificabili e cancellazione.
- Statistiche: peso attuale, variazione, media, BMI dinamico, numero di misurazioni, intervallo del peso e stabilità media.
- REST, WebSocket nativo con riconnessione e ripristino dello stato live, errori leggibili, SQLite persistente e migration Alembic.
- Board reale con connessione persistente, lettura in background, reconnect, stato hardware e diagnostica Python.

## Stack

Frontend: React, TypeScript, Vite, React Router, Tailwind CSS, una primitiva Button basata su shadcn/ui e Radix, Lucide React, Recharts. Comunicazione con `fetch` e `WebSocket` nativi. Vitest, Testing Library e Biome.

Backend: Python 3.12, FastAPI, Pydantic / Pydantic Settings, SQLModel, SQLite, Alembic e `wiibalance==1.4.1`. Pytest e Ruff. Dipendenze dichiarate in `pyproject.toml`, versioni verificate bloccate da `requirements.lock`; frontend con pnpm e `pnpm-lock.yaml`. Il Python 3.11 dell'host Raspberry non viene usato dal container.

Un unico container esegue FastAPI e serve il frontend compilato. Non servono proxy aggiuntivi. L'avvio esegue `alembic upgrade head` prima di Uvicorn, con un singolo worker perché la board e il broadcast WebSocket sono locali al processo.

## Struttura

```text
frontend/src/
  pages/          Dashboard, Storico, Statistiche, Profili, Impostazioni
  components/     Card peso, mappa pressione, grafico, navigazione, Button
  api/            REST, WebSocket, calcolo delle statistiche
  hooks/          Dati condivisi React Context e stato della sessione live
  types/          Contratti TypeScript del dominio
backend/app/
  api/            Validazione e delega ai service
  models/         Tabelle SQLModel e schemi API Pydantic
  services/       Profili, pesate, sessioni e rilevamento della stabilità
  balance_board/  Protocollo, DemoBoard, RealBoard e client wiibalance
  database/       Engine SQLite e configurazione delle connessioni
  websocket/      Broadcast e snapshot per riconnessione
backend/alembic/  Migration versionate
backend/tests/    Test di comportamento su database migrati temporanei
backend/scripts/  Verifica end-to-end demo e diagnostica hardware reale
docker/           Dockerfile multi-stage e Compose per la qualità
data/             Database persistente, escluso da Git
```

## Test e qualità

Puoi eseguire tutti i controlli senza installare Python, Node o pnpm sul computer:

```bash
docker compose -f docker/quality.compose.yml run --build --rm backend
docker compose -f docker/quality.compose.yml run --build --rm frontend
```

Il primo comando esegue Ruff (lint e formato) e Pytest. Il secondo installa con lockfile, esegue Biome, Vitest e la build TypeScript/Vite. Le dipendenze frontend dei controlli sono conservate in un volume Docker separato.

Con Gravia già avviata, verifica il flusso reale simulato:

```bash
docker compose exec gravia python scripts/verify_demo.py
```

Il comando verifica tutti e quattro gli stati, i campioni via WebSocket, i sensori, il centro di pressione e il risultato salvato via REST. Conserva una nuova pesata demo nello storico.

Per sviluppo nativo, da `backend`:

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -c requirements.lock ".[dev]"
# Imposta GRAVIA_DATABASE_URL=sqlite:///./gravia.db
alembic upgrade head
uvicorn app.main:app --reload --port 8080
pytest -q
ruff check .
ruff format --check .
```

Da `frontend`, con Node 22 e pnpm 10.11:

```bash
pnpm install --frozen-lockfile
pnpm dev
pnpm lint
pnpm test
pnpm build
```

Vite espone il frontend sulla porta 5173 e inoltra `/api` e `/ws` al backend sulla 8080. Se hai già usato Docker per installare nella cartella `frontend/node_modules`, reinstalla le dipendenze per la piattaforma nativa prima dello sviluppo fuori da Docker.

## Demo mode e stabilità

`DemoBoard` produce circa 10 campioni al secondo: attesa iniziale, salita progressiva, oscillazioni smorzate e assestamento. Ogni campione contiene quattro carichi in kg; il loro totale determina il peso. Il centro di pressione è normalizzato tra -1 e +1: x positivo a destra, y positivo davanti.

`StabilityService` richiede almeno cinque campioni su una finestra di un secondo. Lo score è `max(0, 100 - 5 * max(range / stability_range_kg, deviazione_standard / stability_stddev_kg))`, visualizzato con un decimale; il confronto usa il valore non arrotondato. Con soglia 95, i limiti predefiniti sono **0,8 kg di range** e **0,3 kg di deviazione standard** nella finestra. Sono tolleranze del segnale, non una percentuale di accuratezza della bilancia. La vecchia scala ammetteva solo 50 g di range e 20 g di deviazione, impedendo il completamento in presenza delle oscillazioni osservate sulla board reale. La soglia deve essere mantenuta per la durata configurata. Un'oscillazione oltre soglia o la discesa sotto il peso minimo interrompe la tenuta. Il peso finale è la media della finestra stabile; i sensori vengono scalati insieme per conservarne la distribuzione. Stato COMPLETED e Measurement vengono salvati nella stessa transazione. Nessun risultato parziale è salvato; una sessione senza stabilità termina con errore al timeout.

La sessione può essere annullata e va in errore al timeout, anche se l'adapter smette di inviare campioni. Dopo un riavvio, le sessioni rimaste attive vengono marcate ERROR; i risultati completati rimangono disponibili. IDLE è implicito e non viene persistito.

## Configurazione

| Variabile | Default Compose | Significato |
| --- | --- | --- |
| `GRAVIA_BOARD_MODE` | `demo` | `demo` oppure `real` |
| `GRAVIA_BOARD_MAC` | vuoto | Obbligatorio in modalità real; formato AA:BB:CC:DD:EE:FF |
| `GRAVIA_BOARD_SAMPLE_TIMEOUT` | `2` | Secondi senza nuovi pacchetti prima di dichiarare la board offline |
| `GRAVIA_BOARD_LOCK_PATH` | `/data/real-board.lock` | Lock locale condiviso da app e diagnostica; per sviluppo nativo scegli una cartella scrivibile |
| `COMPOSE_FILE` | non impostato | Sul Raspberry: `docker-compose.yml:docker-compose.raspberry.yml` |
| `GRAVIA_PORT` | `8080` | Porta pubblicata su localhost (8081 su questo computer) |
| `GRAVIA_HTTP_PORT` | `8080` | Porta del processo HTTP; in rete host è la porta del Raspberry |
| `GRAVIA_DATABASE_URL` | `sqlite:////data/gravia.db` | SQLite nel container |
| `GRAVIA_MINIMUM_WEIGHT` | `20` | Peso minimo rilevato, kg |
| `GRAVIA_REQUIRED_STABILITY` | `95` | Score richiesto, 0–100 |
| `GRAVIA_STABILITY_RANGE_KG` | `0.8` | Range massimo della finestra allo score 95, in kg |
| `GRAVIA_STABILITY_STDDEV_KG` | `0.3` | Deviazione standard massima allo score 95, in kg |
| `GRAVIA_STABLE_DURATION` | `2.5` | Tenuta stabile continua, secondi |
| `GRAVIA_SESSION_TIMEOUT` | `60` | Durata massima sessione, secondi |
| `GRAVIA_DEMO_SEED` | `true` | Crea Alfonso se non esistono profili |

Le impostazioni sono mostrate nell'app e si modificano nel `.env`. Applica le modifiche con `docker compose up -d --force-recreate`. Il profilo iniziale non viene duplicato; con seed attivo, un database senza profili riceve nuovamente Alfonso al successivo avvio. Nessuna pesata viene generata automaticamente all'avvio.

## Database e migration

Il bind mount `./data:/data` conserva il database in **data/gravia.db** sul computer. `docker compose down` e i riavvii non lo cancellano. Per un backup consistente, arresta Gravia e copia la cartella `data`, inclusi eventuali file WAL. Le date sono UTC nel database e ISO 8601 con suffisso Z nell'API; l'interfaccia usa il fuso del browser. Il BMI non è memorizzato e si aggiorna quando cambia l'altezza.

```bash
docker compose exec gravia alembic current
docker compose exec gravia alembic upgrade head
docker compose exec gravia alembic check
```

Per una nuova modifica allo schema, crea una migration con Alembic nell'ambiente di sviluppo, revisiona il file generato, poi applicala. La migration iniziale crea `profiles`, `measurement_sessions` e `measurements`, con chiavi esterne, indici e unicità di `session_id` nel risultato. Non viene usato `create_all()`.

## API

Documentazione interattiva: **http://localhost:8080/docs**. JSON in camelCase; Python in snake_case. Errori con proprietà `message`, più `fields` per validazione.

- CRUD profili: `/api/v1/profiles` e `/api/v1/profiles/{id}`.
- Sessioni: POST `/api/v1/sessions` con `{ "profileId": "…" }`, GET `/api/v1/sessions/{id}`, POST `/api/v1/sessions/{id}/cancel`. GET `/api/v1/sessions/active` restituisce la sessione attiva o null.
- Misurazioni: GET `/api/v1/measurements?profileId=…&from=2026-10-01T00:00:00Z&to=2026-10-31T23:59:59Z`, GET/PATCH/DELETE `/api/v1/measurements/{id}`. PATCH modifica solo le note. Gli estremi sono inclusivi; timestamp senza fuso sono interpretati come UTC.
- GET `/api/v1/settings`, `/api/v1/health` e `/api/v1/board/status`.
- WebSocket `/ws/live`: `session_status`, `live_measurement`, `measurement_completed`, `error`, `board_connected`, `board_disconnected`. Al collegamento vengono ripristinati stato hardware e snapshot dell'ultima sessione nel processo corrente. I dati persistenti restano sempre consultabili via REST. I nuovi eventi hardware contengono `board` (lo stesso oggetto REST) e non hanno `sessionId`.

## RealBoard: acquisizione e lifecycle

```text
DemoBoard ─┐
           ├─ BoardSample → SessionService → StabilityService → WebSocket → React
RealBoard ─┘                      ↓
                              SQLite
```

Il contratto `samples()` e il tipo `BoardSample` rimangono identici. Il protocollo aggiunge solo `start()`, `get_status()` e `shutdown()` per lifecycle e disponibilità comuni. La configurazione seleziona l'adapter; sessioni, algoritmo di stabilità e persistenza rimangono condivisi.

`RealBoard` avvia un task in background, senza aspettare il Bluetooth durante lo startup. Connessione, `read_state()` e disconnessione avvengono tramite `asyncio.to_thread()`. Una sola connessione persistente legge circa 10 snapshot al secondo. Non si riconnette a ogni campione o pesata. Annullare una pesata libera il consumatore, mantenendo il lettore disponibile.

L'API verificata nel wheel **wiibalance 1.4.1** è `create_balance_board(address=MAC, use_daemon=False)`, `read_state()`, `disconnect()`. Nessuna CLI `wiibalance` viene invocata. L'indirizzo esplicito evita anche la ricerca con `bluetoothctl`. I valori calibrati della libreria sono in `state.weights`, con `total` e `center_of_pressure` come **tupla (x, y)**. Il solo punto di mapping è `map_board_state()` in `real_board.py`: top_left/right → front_left/right; bottom_left/right → rear_left/right. Totale e centro di pressione sono le medesime formule del contratto esistente. Nessun offset, scala o compensazione termica aggiunti. La configurazione units=imperial della libreria viene rifiutata, per garantire kg.

`read_state()` restituisce uno snapshot: nella versione verificata, ogni pacchetto DATA crea un nuovo oggetto `Weights`. Uno snapshot con lo stesso oggetto viene scartato; dopo `GRAVIA_BOARD_SAMPLE_TIMEOUT` senza aggiornamenti la board passa offline. Questo evita misurazioni completate usando valori vecchi. Errori, sensori non validi e perdita di connessione interrompono la pesata senza salvare un risultato parziale. Anche una riconnessione rapida invalida la sessione precedente; occorre avviarne una nuova.

I retry attendono **2, 5, 10, 10… secondi dopo il fallimento del tentativo**. La durata del tentativo si aggiunge alla pausa: la libreria usa timeout socket di 5 secondi e inizializzazione sincrona. I log riportano modalità, connessione, disconnessione e retry, senza un log per campione.

Alla chiusura si interrompono i retry, si chiudono i socket con `disconnect()` e si attende il thread interno della libreria (che 1.4.1 non attende autonomamente). Viene gestito anche il suo errore di costruzione dopo l'apertura dei socket: un workaround limitato al costruttore della versione fissata recupera l'istanza dal traceback per chiuderla. Un tentativo di connessione già in corso non viene abbandonato: lo shutdown lo attende e chiude il risultato. L'override Raspberry concede **120 secondi** all'arresto, poiché una sequenza completa di inizializzazione può richiedere circa 100 secondi nel caso peggiore.

`GET /api/v1/board/status` restituisce `mode`, `connected`, `macAddress`, `lastSampleAt` UTC, `lastError`, `battery`. Batteria in passi del 25%, oppure null se ignota. Healthcheck e Bluetooth sono indipendenti: board spenta → app healthy. Un avvio pesata offline restituisce **503** prima di creare una sessione nel database. La UI distingue la connessione hardware dalla connessione realtime del browser.

## Docker Bluetooth e Nginx Proxy Manager

Il Compose standard conserva la rete bridge e la pubblicazione localhost configurabile (8081 su questo computer). Per il Raspberry Linux usa **docker-compose.raspberry.yml**: rete host, nessuna pubblicazione `ports`, `cap_drop: ALL`, arresto con 120 secondi di tolleranza. Il runtime resta un solo container, porta predefinita **8080** configurabile con `GRAVIA_HTTP_PORT`, Python 3.12 e frontend compilato. Le immagini ufficiali Python e Node supportano ARM64.

La scelta della rete host deriva dal [codice del kernel Linux](https://raw.githubusercontent.com/torvalds/linux/v6.12/net/bluetooth/af_bluetooth.c): `bt_sock_create()` rifiuta namespace diversi da `init_net` con EAFNOSUPPORT. La libreria crea socket **AF_BLUETOOTH / SOCK_SEQPACKET / L2CAP** diretti; non usa D-Bus, socket raw HCI o comandi di amministrazione dell'adattatore. Nel [codice L2CAP](https://raw.githubusercontent.com/torvalds/linux/v6.12/net/bluetooth/l2cap_sock.c), CAP_NET_RAW è richiesto per SOCK_RAW, non per questo socket; la libreria non fa bind a PSM riservati. Perciò non aggiungiamo NET_ADMIN, NET_RAW, dispositivi, mount D-Bus, bluez/libbluetooth, un secondo bluetoothd, privileged o seccomp unconfined. Restano il BlueZ dell'host per il pairing, lo stack Bluetooth del kernel e il [seccomp predefinito Docker](https://docs.docker.com/engine/security/seccomp/). Sono scelte motivate dal codice, **da verificare sul kernel e Docker del Raspberry reale**.

La [rete host Docker](https://docs.docker.com/engine/network/drivers/host/) elimina il DNS di servizio sulla rete bridge. Per usare il nome `gravia`, il container Nginx Proxy Manager deve avere il mapping persistente `gravia:host-gateway`. Se NPM è gestito con Compose, aggiungilo al suo servizio:

```yaml
services:
  app: # usa il vero nome del tuo servizio NPM
    extra_hosts:
      - "gravia:host-gateway"
```

L'installazione corrente usa il container standalone `Proxy_Manager`, con `ExtraHosts=["gravia:host-gateway"]`, entrambe le reti originali e gli stessi volumi. Il Proxy Host usa **Forward Hostname gravia, Forward Port 8081, Websockets Support abilitato**. NPM 2.12.6 richiede anche la configurazione [Advanced per Gravia](../ci/npm-gravia-location.conf): il suo inoltro standard usa un resolver DNS che non legge `/etc/hosts`, mentre `proxy_pass http://gravia:8081` risolve il mapping quando Nginx carica la configurazione. Docker Engine 20.10+ supporta host-gateway; NPM deve girare sullo stesso Raspberry. Conserva il mapping quando ricrei NPM e aggiorna anche lo snippet se cambi porta. HTTPS e WebSocket pubblici sono stati verificati sul Raspberry.

Con rete host Gravia ascolta su `0.0.0.0:${GRAVIA_HTTP_PORT:-8080}` del Raspberry; `GRAVIA_PORT` non cambia questa porta. Verifica che sia libera e usa la stessa porta nel proxy e negli URL di diagnostica. Il deploy Jenkins corrente usa **8081**, perché Jenkins occupa già 8080. L'app resta locale e senza account: usa la LAN fidata o il controllo accessi già previsto dal tuo proxy.

## Raspberry Pi real board test

Prerequisiti: Raspberry Pi OS **64 bit / ARM64**, Docker Engine con Compose **v2.24.4+** (`!reset`), Bluetooth Classic funzionante sull'host. Il pairing e l'API Python host sono già stati verificati: non serve reinstallare Python sull'host né ripetere il pairing se Paired è già yes.

1. Verifica sistema, adattatore e MAC sull'host:

   ```bash
   uname -m                    # aarch64
   docker compose version
   bluetoothctl devices Paired # oppure bluetoothctl paired-devices sulle versioni precedenti
   bluetoothctl info 00:24:44:6C:0D:A2
   bluetoothctl show           # Powered: yes
   ```

   Il dispositivo deve essere Nintendo RVL-WBC-01 e Paired: yes. Se necessario: `bluetoothctl power on`. Se il pairing manca, apri `bluetoothctl`, esegui `agent on`, `default-agent`, `scan on`, premi il **pulsante rosso SYNC nel vano batterie**, poi `pair 00:24:44:6C:0D:A2`, `trust 00:24:44:6C:0D:A2`, `scan off`, `quit`. Non usare la CLI wiibalance. Termina qualsiasi script Python host, Wii Fit o altro processo che stia già usando la board.

2. Dalla cartella Gravia copia `.env.example` in `.env` **solo se il file non esiste**. Imposta:

   ```dotenv
   COMPOSE_FILE=docker-compose.yml:docker-compose.raspberry.yml
   GRAVIA_BOARD_MODE=real
   GRAVIA_BOARD_MAC=00:24:44:6C:0D:A2
   GRAVIA_BOARD_SAMPLE_TIMEOUT=2
   GRAVIA_DATABASE_URL=sqlite:////data/gravia.db
   ```

   Conserva gli altri parametri esistenti. Il MAC è configurazione, mai hardcoded nell'adapter. Configura NPM come descritto sopra.

   Prepara anche i permessi del bind mount. Il runtime usa UID 0 **senza capability**: per scrivere SQLite, journal e lock deve possedere la cartella `data` e i suoi file. Sul Raspberry, a container fermo:

   ```bash
   docker compose stop gravia
   mkdir -p data
   sudo chown -R 0:0 data
   ```

   Non aggiungere DAC_OVERRIDE per aggirare i permessi. Per copiare i backup dal Raspberry usa sudo se necessario. Questo passaggio Linux non serve nella modalità demo standard su Docker Desktop.

3. Verifica, costruisci e avvia:

   ```bash
   docker compose config       # network_mode: host; cap_drop: ALL; nessun ports
   docker compose build
   docker compose up -d
   docker compose ps
   docker compose exec gravia python --version # Python 3.12.x
   docker compose logs -f gravia
   ```

   Dopo questa configurazione funziona anche `docker compose up -d --build`. L'app deve partire healthy con la board spenta. Cerca `Board mode: real`, `Connecting to Wii Balance Board ...`, eventuali retry, poi **Wii Balance Board connected**. Lascia la board su una superficie rigida e in piano; premi il pulsante di accensione anteriore. Se rimane irraggiungibile durante il tentativo, premi SYNC e attendi il retry.

4. Da un'altra shell controlla:

   ```bash
   curl -s http://127.0.0.1:8080/api/v1/health
   curl -s http://127.0.0.1:8080/api/v1/board/status
   ```

   `status=ok` deve essere indipendente dall'hardware; poi attendi `connected=true`, `lastSampleAt` aggiornato e `lastError=null`. Apri **http://IP-DEL-RASPBERRY:8080** dal telefono, oppure il dominio NPM. Verifica separatamente “Live connesso” e “Balance Board connessa”.

5. Seleziona il profilo, premi **Inizia misurazione**, sali quando compare **Sali sulla bilancia**, distribuisci il carico e rimani fermo. Controlla che peso e mappa cambino spostando realmente la pressione. Attendi MEASURING → STABILIZING → COMPLETED. Verifica la pesata nello storico e in `/api/v1/measurements`; riavvia il container e verifica che rimanga.

6. Prova la perdita di connessione durante una pesata (interrompi l'alimentazione della board): app healthy, board offline, sessione ERROR, nessuna nuova Measurement parziale. Riaccendila: attendi reconnect e avvia **una nuova** pesata. Confronta un peso noto e controlla la posizione dei quattro sensori prima di modificare threshold o orientamento. Nessuna correzione viene applicata automaticamente.

## Diagnostica Docker sul Raspberry

Controlla la disponibilità del socket senza connetterti alla board:

```bash
docker compose exec gravia python -c 'import socket; s=socket.socket(socket.AF_BLUETOOTH,socket.SOCK_SEQPACKET,socket.BTPROTO_L2CAP); print("L2CAP socket OK"); s.close()'
```

Lo script diagnostico principale usa **la stessa API e lo stesso mapping** dell'adapter. Legge `GRAVIA_BOARD_MAC`, stampa cinque campioni JSON e chiude socket/thread, anche con Ctrl+C:

```bash
docker compose exec gravia python scripts/test_real_board.py
```

App e script condividono un lock in `/data/real-board.lock`, mantenuto per tutta la connessione. **Se Gravia è già connessa, lo script si rifiuta con “già in uso”**: non apre un collegamento concorrente. Se il lettore è offline, lo script può acquisire il lock durante un retry; Gravia riprende i tentativi al termine. Non cancellare il lock file: il lock del kernel si libera automaticamente quando il proprietario esce.

Per un test isolato ripetibile, arresta l'app e usa il container della medesima immagine/configurazione (il comando one-shot non avvia Uvicorn):

```bash
docker compose stop gravia
docker compose run --rm --no-deps gravia python scripts/test_real_board.py --samples 10
docker compose up -d gravia
```

Per provare specificamente `exec` senza il lettore concorrente, configura temporaneamente `GRAVIA_BOARD_MODE=demo` **mantenendo il MAC e l'override Raspberry**, ricrea Gravia, esegui lo script, poi ripristina real e ricrea. La UI non salva queste letture diagnostiche.

| Sintomo | Controllo / intervento |
| --- | --- |
| Paired: yes ma non connected | Pairing non significa connessione attiva. Accendi la board, controlla batterie, termina il test Python host, premi SYNC durante il retry. Non occorre `bluetoothctl connect`: l'API apre direttamente i due canali L2CAP. |
| Socket EAFNOSUPPORT / Address family not supported | `docker compose config` deve mostrare rete host. Serve Linux con Bluetooth; il Bluetooth del PC Windows non viene esposto da Docker Desktop. Verifica supporto kernel sull'host. |
| Socket EPERM / EACCES | Esegui lo stesso test sull'host e conserva errno/log. Controlla rootless Docker, AppArmor/SELinux e profilo seccomp effettivo; non aggiungere NET_ADMIN/NET_RAW o seccomp=unconfined alla cieca. Il socket usato è SEQPACKET, non RAW. |
| ENODEV / ENETDOWN / No route to host | `bluetoothctl show`, `rfkill list bluetooth`, `systemctl status bluetooth`; abilita l'adattatore, rimuovi un eventuale blocco rfkill sull'host e controlla distanza/batterie. |
| Connection refused / timeout | Accensione/SYNC, MAC corretto, board già occupata da un altro programma; attendi inizializzazione e retry. |
| “già in uso” nella diagnostica | Comportamento previsto se il lettore possiede la board. Usa stop + run come sopra; non avviare due connessioni. |
| Disconnessioni / campioni fermi | Controlla batterie e segnale, poi log. Il timeout protegge da dati vecchi. Modifica BOARD_SAMPLE_TIMEOUT solo dopo aver osservato campioni reali; una pesata interrotta va ripetuta. |
| App healthy ma board offline | È previsto: REST/UI/database funzionano mentre il lettore riprova. Controlla `/board/status`, non solo l'healthcheck. |
| NPM restituisce 502 dopo rete host | Conserva extra_hosts gravia:host-gateway nel container NPM e la location Advanced con hostname letterale descritta sopra. Per questa installazione usa gravia:8081 e Websockets Support. |
| Realtime offline ma board connessa | Verifica WebSocket del proxy e `/ws/live`; lo stato hardware e il collegamento browser sono distinti. |

## Pipeline Jenkins

Push GitHub su `main` → test backend/frontend → build ARM64 → deploy sul Raspberry. Configurazione del job, webhook, prima installazione e rollback: [ci/README.md](../ci/README.md).

## Verifiche e limiti

I risultati eseguiti localmente sono in [VERIFICATION.md](../VERIFICATION.md). I test hardware automatici usano fake della libreria e i suoi tipi reali: nessuna Wii è richiesta in CI. Non cambiano le misurazioni dell'app. La diagnostica fisica deve essere eseguita sul Raspberry: accesso L2CAP nel container, permessi del kernel locale, risveglio/SYNC, orientamento, accuratezza, disconnessione reale e il tuo routing NPM non possono essere confermati dal PC Windows.

**Software implementation complete. Final Bluetooth container verification must be performed on the Raspberry Pi.**

Assunzioni: un dispositivo, un processo/worker backend, profili fidati, storico locale senza paginazione e impostazioni nel `.env`. Demo intorno a 72,4 kg indipendentemente dal profilo. Prima di cambiare la versione wiibalance rivalida API, freschezza dei campioni e cleanup del costruttore. [Pacchetto wiibalance 1.4.1](https://pypi.org/project/wiibalance/1.4.1/), [sorgente upstream](https://github.com/bboonstra/wiibalance).

Riferimenti tecnici: [WebSocket FastAPI](https://fastapi.tiangolo.com/advanced/websockets/), [alias Pydantic](https://docs.pydantic.dev/latest/api/config/), [Tailwind con Vite](https://tailwindcss.com/docs/installation/using-vite).
