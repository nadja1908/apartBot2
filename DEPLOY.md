# Praćenje kad je laptop ugašen

Skripta mora da radi na uređaju koji je **stalno uključen i na mreži**. Laptop u sleep/ugasen = nema procesa = nema mejla.

Za **Oracle Cloud Always Free** korak-po-korak (VM, SSH, cron): vidi **`ORACLE.md`** u istom folderu.

## Najjednostavnije: mali VPS + cron

1. Iznajmi najjeftiniji Linux VPS (npr. Hetzner CX22, DigitalOcean droplet, ili Oracle Cloud „Always Free“ ARM ako hoćeš 0 € uz malo podešavanja).
2. Na serveru: `git clone` tvog repoa (ili `scp` celog `apartment-monitor` foldera).
3. Na serveru: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
4. Na serveru napravi `.env` (isti kao na laptopu — **nikad** ga ne commit-uj u git).
5. Zakazi **cron** (npr. svakih 15 minuta):

```cron
*/15 * * * * cd /PUTANJA/do/apartment-monitor && . .venv/bin/activate && python rental_watch.py >> /tmp/rental-watch.log 2>&1
```

`state.json` ostaje na disku servera — zato mejlovi idu samo za **nove** oglase.

## Zašto ne „samo GitHub Actions“

Periodičan job u oblaku je moguć, ali mora negde da **čuva `state.json`** između pokretanja (GitHub Actions po defaultu nema trajni disk za taj fajl). VPS rešava to prirodno jednim folderom.

## Bezbednost

- `.env` samo na serveru, prava `chmod 600 .env`.
- App lozinka za Gmail samo za ovu skriptu; rotiraj ako je negde curkla.
