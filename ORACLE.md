# Oracle Cloud — besplatna VM za `rental_watch.py`

Vodič za **Always Free** instancu (najčešće **ARM Ampere A1**) sa Ubuntu-om, Pythonom i `cron`-om. Skripta ostaje na disku → `state.json` radi kako treba → mejl samo za nove oglase.

Zvanična ponuda: [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/).

---

## 1. Nalog i „home region“

1. Otvori [cloud.oracle.com](https://cloud.oracle.com), napravi **Free Tier** nalog (kartica se traži, ali Always Free resursi ne bi trebalo da se naplaćuju ako ostaneš u okviru besplatnog — pročitaj uslove na Oracle sajtu).
2. Pri prvom ulasku izaberi **region** (npr. `Frankfurt`, `Amsterdam`). Kasnije je bolje ne skakati između regiona.

Ako Oracle kaže da nema kapaciteta za VM u tom regionu, probaj drugi region ili drugi dan.

---

## 2. SSH ključ (na Windowsu, PowerShell)

```powershell
ssh-keygen -t rsa -b 4096 -f $env:USERPROFILE\.ssh\oracle_rental -N '""'
```

Javni ključ za Oracle konzolu:

```powershell
Get-Content $env:USERPROFILE\.ssh\oracle_rental.pub
```

Kopiraj **ceo** red koji počinje sa `ssh-rsa ...`.

---

## 3. Pravljenje VM (Compute)

1. Meni **Compute → Instances → Create instance**.
2. **Name:** npr. `rental-watch`.
3. **Image:** **Canonical Ubuntu 22.04** (ili noviji LTS).
4. **Shape:** klik **Change shape** → **Ampere A1.Flex** (Always Free ARM).
   - **OCPU:** `1`
   - **Memory (GB):** `6` je u okviru free „paketa“ zajedno sa drugim A1 instancama u tenancy-ju; za ovu skriptu često je dovoljno i `1` OCPU / `1` GB ako hoćeš minimalno (proveri trenutna Oracle pravila za Always Free).
5. **Networking:** ostavi default VCN/subnet ako ti Oracle ponudi.
6. **Primary VNIC → Assign public IPv4 address:** **Yes** (da možeš SSH spolja).
7. **Add SSH keys:** **Paste SSH keys** → nalepi sadržaj `.pub` fajla.
8. **Create** i sačekaj status **RUNNING**. Zapiši **Public IP address**.

---

## 4. Sigurnosna lista (ingress) — port 22

Ako se ne možeš spojiti SSH-om:

1. **Networking → Virtual Cloud Networks** → otvori svoju VCN.
2. **Security Lists** (ili **Network Security Groups** ako ih instanca koristi) → **Ingress Rules**.
3. Dodaj pravilo: **Source** = tvoja kućna IP (najbolje) ili privremeno `0.0.0.0/0` (slabije), **IP protocol** TCP, **Destination port** `22`.

---

## 5. Prvi SSH

```powershell
ssh -i $env:USERPROFILE\.ssh\oracle_rental ubuntu@JAVNA_IP
```

Korisnik je obično **`ubuntu`** na Canonical Ubuntu image-u.

---

## 6. Python i folder skripte

Na serveru:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
mkdir -p ~/apartment-monitor && cd ~/apartment-monitor
```

### Kako da staviš fajlove

**A)** Ako imaš git repo:

```bash
git clone URL_TVOG_REPOA .
# ili samo podfolder apartment-monitor iz repoa
```

**B)** Sa laptopa (PowerShell, iz foldera gde ti je `apartment-monitor`):

```powershell
scp -i $env:USERPROFILE\.ssh\oracle_rental -r .\apartment-monitor\* ubuntu@JAVNA_IP:~/apartment-monitor/
```

Zatim na serveru u `~/apartment-monitor`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

(Poslednji red je potreban ako koristiš **Woonzeker** izvor u `rental_watch.py` — koristi Playwright.)

---

## 7. `.env` na serveru

```bash
nano ~/apartment-monitor/.env
```

Isti sadržaj kao na laptopu (`SMTP_*`, `EMAIL_TO`, itd.). Sačuvaj (`Ctrl+O`, Enter, `Ctrl+X`).

```bash
chmod 600 ~/apartment-monitor/.env
```

Test jednom:

```bash
cd ~/apartment-monitor && source .venv/bin/activate && python rental_watch.py
```

Očekuj prvu poruku tipa **inicijalno: N oglasa** (bez mejla za sve postojeće). Drugi run tek onda javlja nove.

---

## 8. Cron — svakih 15 minuta

```bash
crontab -e
```

Dodaj red (prilagodi putanje ako su drugačije):

```cron
*/15 * * * * cd /home/ubuntu/apartment-monitor && /home/ubuntu/apartment-monitor/.venv/bin/python /home/ubuntu/apartment-monitor/rental_watch.py >> /home/ubuntu/rental-watch.log 2>&1
```

Provera loga:

```bash
tail -f ~/rental-watch.log
```

---

## 9. Kontinuirana petlja (opciono)

Ako ipak želiš `--watch` umesto `cron`, koristi **systemd** ili `screen`/`tmux` da proces preživi odjavljivanje:

```bash
sudo apt install -y tmux
tmux new -s rental
cd ~/apartment-monitor && source .venv/bin/activate
python rental_watch.py --watch 300
# Ctrl+B pa D da odvojiš sesiju
```

Za „uvek radi u pozadini“ pouzdanije je **cron** ili systemd timer.

---

## Česti problemi

| Problem | Šta uraditi |
|--------|-------------|
| Nema kapaciteta za A1 | Drugi region / manji shape / probaj kasnije |
| SSH timeout | Ingress 22, tačna IP, instanca RUNNING |
| Gmail odbija login | App password, 2FA, `SMTP_USER` = pun mejl |
| Svaki cron šalje iste mejlove | Proveri da li se briše `state.json` ili radi iz pogrešnog foldera |

---

## Napomena o naplati

Oracle Free Tier i Always Free pravila menjaju se retko, ali **uvek** proveri aktuelnu dokumentaciju i limite na svom nalogu. Ne ostavljaj „Always Free“ instance upaljene ako ti više ne trebaju — manje iznenađenja.
