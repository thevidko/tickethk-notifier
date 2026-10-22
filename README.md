# tickethk-notifier

Hlídá stránku akce na [tickethk.cz](https://tickethk.cz) a pošle push notifikaci přes [ntfy](https://ntfy.sh), když se uvolní vstupenky (a znovu, když jsou zase vyprodané).

Stránka je Inertia.js aplikace, takže data o zónách (cena, zbývající kapacita, `is_sellable`) se čtou přímo z JSONu v atributu `data-page`. Bez prohlížeče, bez závislostí.

## Spuštění

```bash
git clone https://github.com/thevidko/tickethk-notifier.git
cd tickethk-notifier
cp .env.example .env    # a nastav NTFY_URL
docker compose up -d --build
docker compose logs -f
```

V mobilu nainstaluj aplikaci **ntfy** a přihlas se k odběru stejného topicu, jaký máš v `NTFY_URL`.

Po startu kontejneru přijde testovací notifikace **„Ticket notifier spuštěn“** s aktuálním stavem vstupenek – podle ní poznáš, že je všechno správně propojené. Když nepřijde, podívej se do `docker compose logs`.

Aktualizace: `git pull && docker compose up -d --build`

## Konfigurace (`.env`)

| proměnná    | význam                                                   |
|-------------|----------------------------------------------------------|
| `NTFY_URL`  | ntfy topic, např. `https://ntfy.sh/muj-tajny-topic`      |
| `EVENT_URL` | stránka akce na tickethk.cz                               |
| `INTERVAL`  | interval kontroly v sekundách (výchozí 120)              |
| `ZONES`     | volitelně jen některé zóny podle názvu, např. `Student`  |

Bez Dockeru: `NTFY_URL=... python3 check_tickets.py` (jedna kontrola), s `INTERVAL=120` běží ve smyčce.
