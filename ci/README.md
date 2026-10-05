# Jenkins e GitHub

La pipeline del [Jenkinsfile](../Jenkinsfile) usa l'agent Linux ARM64 con etichette `raspberry-pi && docker`. Git, Docker Engine, Docker Compose v2.24.4+ e `flock` devono essere disponibili all'utente dell'agent. Node, pnpm, Python, Ruff e Pytest girano nelle immagini Docker. Non serve un registry né una nuova chiave SSH.

## Job Gravia

- **Definition:** Pipeline script from SCM; **SCM:** Git.
- **Repository URL:** `https://github.com/elfo399/Gravia.git`, senza credenziali per il repository pubblico.
- **Branch:** `*/main`; **Script Path:** `Jenkinsfile`; lightweight checkout attivo.
- **GitHub project:** `https://github.com/elfo399/Gravia`.
- **Trigger:** GitHub hook trigger for GITScm polling. Niente polling periodico.
- Le build sono serializzate, conservate per le ultime 20 esecuzioni e hanno timeout di 45 minuti.

La prima esecuzione può essere avviata con **Build Now**. I parametri del Jenkinsfile vengono registrati durante quella build; poi compare **Build with Parameters**.

## Webhook del repository

In GitHub → Settings → Webhooks:

- **Payload URL:** `https://jenkins.elfo3.dev/github-webhook/` (slash finale).
- **Content type:** `application/json`.
- **Events:** Just the push event; **Active:** attivo; verifica SSL attiva.

Il webhook avvia il polling SCM: il job controlla `main`, quindi i push senza nuove modifiche su quel branch non generano un deploy. Non abilitare il trigger remoto con token. Se Jenkins ha un webhook secret configurato, usare lo stesso secret nel webhook; cambiarlo globalmente richiede coordinamento con gli altri repository. Vedi [plugin GitHub ufficiale Jenkins](https://plugins.jenkins.io/github/).

## Prima installazione sul Raspberry

Il percorso vuoto di `DEPLOY_DIRECTORY` usa `$HOME/gravia` dell'agent: nell'installazione corrente **`/home/elfo/gravia`**, fuori dal checkout Jenkins. La cartella deve essere vuota oppure contenere un'installazione già configurata con `.env` e Compose. Il bootstrap crea Compose, `.env` privato e `/data` persistente con permessi per il runtime. Non sovrascrive la configurazione delle installazioni esistenti.

I parametri iniziali sono `BOARD_MAC=00:24:44:6C:0D:A2`, modalità **real**, `HTTP_PORT=8081`. Il MAC è configurazione della prima installazione. La porta 8080 del Raspberry è già occupata da Jenkins; il bootstrap verifica che la porta scelta sia libera prima di scrivere i file. Gli aggiornamenti conservano `.env`: per cambiare MAC/porta successivamente, modificare quel file sul Raspberry.

`GRAVIA_HTTP_PORT` determina la porta interna del processo HTTP, default 8080. In rete host quella è anche la porta del Raspberry. `GRAVIA_PORT` controlla solo la pubblicazione del Compose bridge. Il healthcheck e le verifiche CI leggono `GRAVIA_HTTP_PORT`.

La board usa la rete host del Raspberry, senza capability aggiunte. Se l'hardware è spento, l'app resta healthy e mostra la board offline: il job non pretende una pesata fisica. Accendere/SYNC la board e verificare `connected=true` prima di pesare.

Per Nginx Proxy Manager, inoltrare all'IP LAN del Raspberry, porta **8081**, con Websockets Support. Se si usa il nome `gravia`, occorre il mapping `gravia:host-gateway` nel servizio NPM come spiegato nel [README](../README.md). La pipeline non modifica il proxy degli altri servizi.

## Test e deploy

1. Checkout `main` e verifica Docker ARM64.
2. Ruff + Pytest backend (JUnit in `reports/backend.xml`).
3. Build frontend, Biome + Vitest (JUnit in `reports/frontend.xml`).
4. Build runtime ARM64 con tag `gravia:<commit abbreviato>-<build>` e label del commit.
5. Bootstrap quando necessario; lock sul percorso di deploy.
6. Prima di sostituire un container attivo, attesa della pesata corrente e backup SQLite consistente in `/data/jenkins-backups`. I backup restano sul Raspberry e non sono pubblicati come artifact.
7. Tag dell'immagine sul nome usato dal Compose dell'installazione e `compose up --no-build --pull never --wait` del solo servizio `gravia`.
8. Verifica HTTP health, stato board e snapshot WebSocket. Se fallisce, ripristino dell'immagine precedente e build rossa. Alla prima installazione non esiste un'immagine precedente da ripristinare.

Gli aggiornamenti preservano database, configurazione e bind mount. Il ripristino automatico riguarda l'immagine; non ripristina il database sopra dati nuovi. Migrazioni future incompatibili richiedono un piano specifico. Conservare i backup e le immagini di release secondo lo spazio disponibile: non è previsto un prune globale, che coinvolgerebbe altri progetti.

Per eseguire localmente le stesse suite su Linux, dalla radice del repository:

```sh
sh ci/test.sh backend gravia-ci-local-1
sh ci/test.sh frontend gravia-ci-local-1
```

Per il deploy manuale di un'immagine già costruita sul Raspberry:

```sh
sh ci/deploy.sh deploy /home/elfo/gravia gravia:COMMIT-BUILD
```

La cartella di deploy deve essere accessibile allo stesso utente del job e al daemon Docker del Raspberry. I dati e `.env` non vanno nel workspace Jenkins né in Git.
