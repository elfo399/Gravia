# Balance Board: Power quotidiano

`bluez` attende connessioni avviate dalla board. Il servizio host non apre
socket L2CAP e non chiama Device1.Connect(). `direct` conserva wiibalance 1.4.1
come fallback diagnostico; Demo resta indipendente. SessionService,
StabilityService e il contratto BoardSample non cambiano.

## Ricerca e architettura

Nel daemon wiibalance 1.4.1 `_ensure_board_connected()` crea una board solo
quando self.board è None; se esiste ma connected è False, restituisce ancora
True. Il commento upstream sul reconnect non contiene un'implementazione:
use_daemon=True non risolve il requisito.

Il [plugin Wii di BlueZ 5.66](https://github.com/bluez/bluez/blob/5.66/plugins/wiimote.c)
specifica anche che pairing con SYNC **seguito dalla prima connessione HID**
abilita il reconnect. Paired/Trusted da soli non lo garantiscono. Una sola
Device1.Connect nel setup iniziale è distinta dal loop outbound vietato
nell'uso quotidiano; l'agent runtime non chiama mai Connect.

Raspberry verificato: Bookworm ARM64, BlueZ 5.66, kernel
6.12.47+rpt-rpi-2712. hid_wiimote e hidp sono disponibili; Input1.ReconnectMode
della board è device. Pairing già presente (Paired=yes, Bonded=yes), Trusted=no.
Il setup conserva normalmente il pairing e imposta Trusted. Il vecchio
record di questa installazione ha richiesto il recovery esplicito descritto sotto.

Il servizio Python 3 usa D-Bus per stato e Disconnect, evdev per attivare
il flusso del driver e hidraw read-only per sensori e pulsante Power.
Il kernel espone Power come BTN_A, derivato dallo stesso bit del report HID;
il runtime usa un solo flusso ordinato per gli edge. Mescolare eventi
evdev e hidraw, con code indipendenti, può riapplicare una pressione dopo
il rilascio. Sul Raspberry un evento della prima pressione è arrivato
fino a 6,2 secondi dopo i primi report neutri anche nel solo flusso hidraw:
non basta ignorare il primo report o applicare 500 ms di debounce.
La connessione resta CONNECTING durante una finestra iniziale di 10 secondi
e richiede un rilascio stabile di almeno 500 ms prima di diventare pronta.
Solo dopo questa fase viene accettata una nuova pressione per spegnere.
Una pressione mantenuta durante il setup non diventa mai uno spegnimento.
Durante questa fase il reader riceve i pacchetti ma non pubblica campioni
come pronti per la misura: la UI mostra "Connessione alla Balance Board...".
La calibrazione
0/17/34 kg viene letta dall'attributo bboard_calib del driver Linux;
conversione e orientamento seguono il driver. Evdev filtra valori identici
e variazioni minime: un timer sugli snapshot potrebbe scambiare dati vecchi
per peso stabile. Hidraw distingue nuovi pacchetti identici da dati fermi.
Heartbeat di stato e campioni sono separati; il container verifica MAC,
epoch, sequenza e freschezza sul clock monotonic comune del kernel.

Riferimenti primari:

- [BlueZ Device1](https://github.com/bluez/bluez/blob/master/doc/org.bluez.Device.rst)
- [BlueZ Input1](https://github.com/bluez/bluez/blob/master/doc/org.bluez.Input.rst)
- [Driver Linux 6.12](https://github.com/torvalds/linux/blob/v6.12/drivers/hid/hid-wiimote-modules.c)
- [Input Linux: filtraggio](https://github.com/torvalds/linux/blob/v6.12/drivers/input/input.c)
- [hidraw](https://www.kernel.org/doc/html/latest/hid/hidraw.html)
- [xwiimote](https://github.com/dvdhrm/xwiimote)
- [wiiweigh: solo riferimento lifecycle, senza Python 2 o auto-off](https://github.com/chaosbiber/wiiweigh)

## Installazione amministrativa sul Raspberry

Una volta dal checkout, e successivamente solo quando cambiano i file host:

```sh
sudo sh host/install-board-agent.sh 00:24:44:6C:0D:A2
sudo sh scripts/setup_balance_board.sh 00:24:44:6C:0D:A2
```

Pacchetti apt: python3-dbus, python3-gi, python3-evdev e dipendenze GLib.
Nessun pip di sistema, Python 2, libreria xwiimote o secondo container.
Utente gravia-board dedicato; udev permette solo i nodi input/hidraw del MAC;
la policy D-Bus consente osservazione e solo Disconnect del device su hci0.
Se cambi adattatore, aggiorna la policy per il path reale.
L'installer crea modules-load.d/gravia-wii.conf e gravia-board-agent.service:
carica esplicitamente hid_wiimote e hidp, disponibili ma non caricati
all'inizio della verifica. Non dipende dall'autoload tramite il container.
boot dopo Bluetooth, restart dopo crash, attesa passiva con board spenta,
log di connessioni e disconnessioni senza stampare i pesi. Non modifica ERTM.

Il reader viene chiuso prima di Disconnect. Lo stato resta DISCONNECTING
fino a Connected=false. Edge/debounce evita richieste duplicate; la pressione
usata per accendere non viene interpretata come richiesta di spegnimento.
Non c'è auto-off dopo la misura.

## FIRST PAIR: solo quando manca il pairing

Lo script preserva pairing esistente. Al primo setup apre bluetoothctl con
agent e scansione. Premi una volta SYNC rosso; nello stesso prompt:

```text
power on
agent on
default-agent
scan on
pair 00:24:44:6C:0D:A2
connect 00:24:44:6C:0D:A2
trust 00:24:44:6C:0D:A2
disconnect 00:24:44:6C:0D:A2
scan off
info 00:24:44:6C:0D:A2
quit
```

Verifica Paired=yes e Trusted=yes. BlueZ conserva i dati in
/var/lib/bluetooth; il servizio non fa remove o re-pair all'avvio.

Se un vecchio pairing direct risulta Paired/Trusted ma Power lampeggia e si
spegne, completare la prima connessione HID mantenendo il pairing:
`sudo sh scripts/setup_balance_board.sh MAC --initialize-hid`.
Questo singolo passaggio usa SYNC nel setup/recovery, non a ogni accensione.

Sul Raspberry il vecchio record ha prodotto autenticazione “Invalid exchange
(52)”, con pairing/trust presenti ma chiave rifiutata. È stato necessario
salvare il record e rimuovere **solo quel MAC**, una volta, prima del nuovo
pairing. Lo script non rimuove mai automaticamente associazioni. In caso di
identico errore verificato, eseguire esplicitamente `bluetoothctl remove MAC`
e ripetere FIRST PAIR con agent attivo; Pair deve riuscire prima di Connect.

Le regole udev verificano HID_UNIQ nell'uevent del parent HID: input/uniq
del driver è vuoto. L'assegnazione finale GROUP:= evita che 99-com.rules
di Raspberry ripristini il gruppo input; il servizio non appartiene a input.
Hidraw è leggibile dal gruppo ma non scrivibile (0640).

RuntimeDirectoryPreserve=yes conserva la directory /run/gravia durante
restart dell'agent: Docker monta la directory, quindi deve mantenere il
medesimo inode mentre il socket viene ricreato. /run resta temporaneo e
viene ricreato al boot. Un restart agent non richiede restart di Gravia.

## Docker e migrazione

Copia docker-compose.bluez.yml nella directory persistente conservando data
e configurazione locale. Aggiungi a .env:

```dotenv
GRAVIA_BOARD_MODE=real
GRAVIA_BOARD_TRANSPORT=bluez
GRAVIA_BOARD_MAC=00:24:44:6C:0D:A2
GRAVIA_BOARD_SOCKET=/run/gravia/balance-board.sock
GRAVIA_BOARD_AGENT_GID=990
COMPOSE_FILE=docker-compose.yml:docker-compose.raspberry.yml:docker-compose.bluez.yml
```

Usa il GID stampato dall'installer, non presumere sia sempre 990. Ricrea il
container con la nuova immagine dopo avere terminato le sessioni attive.
Il solo bind aggiunto è /run/gravia:/run/gravia:ro: directory 0750, socket
0660, gruppo dedicato nel container, protocollo JSONL v1 read-only.
Restano unico container, network_mode host, cap_drop ALL, HTTP port e dati.
Non vengono montati D-Bus, /tmp o device nel container. Il socket non richiede
rete host, ma conserviamo il routing NPM funzionante e il fallback direct;
non migriamo la rete prima della verifica hardware.

Jenkins fa test/build/deploy applicativi e non installa il servizio.
Quando host/ cambia, riesegui esplicitamente l'installer dal nuovo checkout
con board OFF e nessuna misura attiva. Aggiornamenti solo UI/API non richiedono
questo passaggio.

## Uso quotidiano

1. Board OFF: app healthy, connected=false, state=WAITING_FOR_POWER.
2. Premi soltanto Power frontale, rilascialo e attendi circa 10 secondi fino
   a “Balance Board connessa”. Non ripremere Power durante la connessione.
3. Inizia misurazione, sali e attendi COMPLETED. Puoi fare più pesate.
4. Premi di nuovo Power: disconnessione, LED blu spento, Gravia offline.
5. Un nuovo Power riconnette. SYNC non serve nell'uso normale.

Spegnere durante una sessione termina ERROR senza Measurement parziale.
Riavviare solo Gravia non spegne la board: l'hardware è gestito dall'agent.

```sh
systemctl status gravia-board-agent
journalctl -u gravia-board-agent --since '10 minutes ago'
bluetoothctl info 00:24:44:6C:0D:A2
busctl get-property org.bluez /org/bluez/hci0/dev_00_24_44_6C_0D_A2 org.bluez.Input1 ReconnectMode
curl http://localhost:8081/api/v1/board/status
```

## Fallback direct

Non eseguire due reader concorrenti. Ferma l'agent, seleziona
GRAVIA_BOARD_TRANSPORT=direct e ricrea Gravia. Mantiene il percorso wiibalance
già verificato, retry/SYNC compresi; non promette il nuovo lifecycle.
Per tornare a bluez avvia l'agent e ricrea Gravia con transport bluez.
Le vecchie istruzioni L2CAP della guida tecnica valgono solo per direct.

I test software non verificano LED/reconnect reali: i test fisici A–H
vengono registrati nel rapporto dopo esecuzione con l'utente.
