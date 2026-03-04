# Vitar Prospector

AI-Powered B2B Pharmacy Discovery pro Vitar Group.

## Co to dělá

Zpracovává veřejný registr lékáren (SÚKL Open Data) a vytváří prioritizovanou databázi prospektů pro B2B obchodní tým.

### Klíčové funkce

- **2 671 lékáren** z oficiálního registru SÚKL
- **AI scoring** (0-100) — prioritizace podle kontaktních údajů, lokace, typu a digitální vyspělosti
- **eWay CRM matching** — upload CSV s IČO zákazníků → okamžitá identifikace "už zákazník" vs "prospect"
- **Outreach šablony** — personalizované emaily podle segmentu a regionu
- **Interaktivní dashboard** s filtry, grafy a exportem CSV

## Rychlý start

```bash
# 1. Stáhni SÚKL data a zpracuj
python3 prospector.py

# 2. Spusť dashboard
cd dashboard && python3 -m http.server 8090
# Otevři http://localhost:8090
```

## Struktura

```
├── prospector.py          # Hlavní procesor (parse → score → export)
├── dashboard/
│   ├── index.html         # Interaktivní dashboard (Tailwind + Chart.js)
│   └── data.js            # Generovaná data pro dashboard
├── data/
│   ├── lekarny_seznam.csv # SÚKL registr lékáren
│   ├── lekarny_typ.csv    # Typy lékáren
│   └── prospector.db      # SQLite databáze
└── output/
    ├── prospects_scored.csv       # Všechny lékárny (seřazené)
    ├── prospects_with_email.csv   # Pouze s emailem (outreach-ready)
    └── dashboard_data.json        # JSON export
```

## Scoring model

| Kritérium | Body | Max |
|-----------|------|-----|
| Email dostupný | +25 | 25 |
| Kontaktní osoba | +10 | 10 |
| Telefon | +10 | 10 |
| Web | +10 | 10 |
| Tier 1 město (Praha/Brno/Ostrava/Plzeň) | +15 | 15 |
| Tier 2 město (krajská města) | +10 | |
| Základní lékárna (typ Z) | +15 | 15 |
| Lékárna s rozšířením | +10 | |
| Zásilkový prodej | +10 | 10 |
| E-recept připojený | +5 | 5 |
| **Maximum** | | **100** |

## eWay CRM matching

Dashboard umožňuje nahrát CSV export z eWay CRM. Vyžaduje sloupec `IČO`. Výsledek:
- **Zákazník** — IČO nalezeno v eWay → už je partner Vitar
- **Prospect** — IČO nenalezeno → příležitost pro obchodní tým

## Datový zdroj

[SÚKL Open Data](https://opendata.sukl.cz/?q=katalog%2Fseznam-lekaren) — veřejný registr lékáren ČR, aktualizovaný měsíčně.

## Tech stack

- Python 3 (zpracování dat, SQLite)
- Tailwind CSS (UI)
- Chart.js (grafy)
- Vanilla JavaScript (interaktivita)

---

Built for Vitar Group | 2026
