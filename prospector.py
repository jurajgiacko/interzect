#!/usr/bin/env python3
"""
Vitar Prospector - AI-Powered B2B Pharmacy Discovery
Processes SÚKL pharmacy register into scored prospect database.
"""

import csv
import json
import os
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
DASHBOARD_DIR = os.path.join(BASE_DIR, 'dashboard')
SUKL_CSV = os.path.join(DATA_DIR, 'lekarny_seznam.csv')
DB_PATH = os.path.join(DATA_DIR, 'prospector.db')

TIER_1_CITIES = {'Praha', 'Brno', 'Ostrava', 'Plzeň'}
TIER_2_CITIES = {
    'Olomouc', 'Liberec', 'České Budějovice', 'Hradec Králové',
    'Ústí nad Labem', 'Pardubice', 'Zlín', 'Karlovy Vary', 'Jihlava',
    'Opava', 'Frýdek-Místek', 'Karviná', 'Most', 'Teplice',
    'Havířov', 'Kladno', 'Děčín', 'Chomutov', 'Přerov', 'Prostějov',
    'Mladá Boleslav', 'Třebíč', 'Znojmo', 'Příbram', 'Tábor',
}

PHARMACY_TYPE_LABELS = {
    'Z': 'Lékárna',
    'Z/OOVL': 'Lékárna s OOVL',
    'O': 'Lékárna s odb. prac.',
    'OOVL': 'OOVL',
    'NO': 'Nemocniční lékárna',
    'NO/OOVL': 'Nemocniční s OOVL',
    'L': 'Lékárna (L)',
    'L/OOVL': 'Lékárna (L) s OOVL',
    'LO': 'Lékárna s odb. prac. (LO)',
    'LO/OOVL': 'LO s OOVL',
    'V': 'Výdejna',
    'NZ': 'Nemocniční základní',
    'A': 'Apatykářský',
    '': 'Nespecifikováno',
}


def get_region(psc):
    if not psc or len(psc.replace(' ', '')) < 3:
        return 'Neznámý'
    try:
        p = int(psc.replace(' ', '')[:3])
    except ValueError:
        return 'Neznámý'

    if 100 <= p <= 199: return 'Praha'
    if 200 <= p <= 299: return 'Středočeský kraj'
    if 300 <= p <= 349: return 'Plzeňský kraj'
    if 350 <= p <= 364: return 'Karlovarský kraj'
    if 365 <= p <= 369: return 'Plzeňský kraj'
    if 370 <= p <= 399: return 'Jihočeský kraj'
    if 400 <= p <= 459: return 'Ústecký kraj'
    if 460 <= p <= 499: return 'Liberecký kraj'
    if 500 <= p <= 529: return 'Královéhradecký kraj'
    if 530 <= p <= 569: return 'Pardubický kraj'
    if 570 <= p <= 599: return 'Kraj Vysočina'
    if 600 <= p <= 699: return 'Jihomoravský kraj'
    if 700 <= p <= 749: return 'Moravskoslezský kraj'
    if 750 <= p <= 779: return 'Olomoucký kraj'
    if 780 <= p <= 799: return 'Zlínský kraj'
    return 'Neznámý'


def score_pharmacy(row):
    score = 0
    reasons = []

    email = row.get('EMAIL', '').strip()
    if email:
        score += 25
        reasons.append('Email dostupný (+25)')

    phone = row.get('TELEFON', '').strip()
    if phone:
        score += 10
        reasons.append('Telefon (+10)')

    www = row.get('WWW', '').strip()
    if www:
        score += 10
        reasons.append('Web (+10)')

    city = row.get('MESTO', '').strip()
    if city in TIER_1_CITIES:
        score += 15
        reasons.append(f'Tier 1 město (+15)')
    elif city in TIER_2_CITIES:
        score += 10
        reasons.append(f'Tier 2 město (+10)')

    typ = row.get('TYP_LEKARNY', '').strip()
    if typ == 'Z':
        score += 15
        reasons.append('Základní lékárna (+15)')
    elif typ in ('Z/OOVL', 'L', 'O', 'LO'):
        score += 10
        reasons.append('Lékárna s rozšířením (+10)')

    if row.get('ZASILKOVY_PRODEJ', '').strip() == 'ANO':
        score += 10
        reasons.append('Zásilkový prodej (+10)')

    if row.get('ERP', '') == '1':
        score += 5
        reasons.append('E-recept (+5)')

    lekarnik = row.get('LEKARNIK_PRIJMENI', '').strip()
    if lekarnik:
        score += 10
        reasons.append('Kontaktní osoba (+10)')

    return min(score, 100), reasons


def get_city_tier(city):
    if city in TIER_1_CITIES:
        return 'Tier 1'
    if city in TIER_2_CITIES:
        return 'Tier 2'
    return 'Tier 3'


def generate_outreach_email(pharmacy):
    name = pharmacy['name']
    city = pharmacy['city']
    contact_name = ''
    if pharmacy.get('lekarnik_titul') and pharmacy.get('lekarnik_prijmeni'):
        contact_name = f"{pharmacy['lekarnik_titul']} {pharmacy['lekarnik_prijmeni']}"

    greeting = f"Vážený/á {contact_name}" if contact_name else "Dobrý den"

    return (
        f"{greeting},\n\n"
        f"obracím se na Vás jako zástupce společnosti Vitar – jedničky na českém trhu "
        f"s vitamíny a doplňky stravy.\n\n"
        f"Rádi bychom Vám představili naše portfolio pro lékárny, které zahrnuje:\n\n"
        f"• MaxiVita – nejprodávanější řada vitamínů v ČR\n"
        f"• Vitar – prémiová řada s klinicky ověřenými dávkami\n"
        f"• MaxiVita Essentials – nová řada pro moderní zákazníky\n"
        f"• Vitar Eco-Friendly – přírodní řada (probiotika, kolagen, detox)\n\n"
        f"Nabízíme konkurenceschopné velkoobchodní podmínky, marketingovou podporu "
        f"a POS materiály přímo do Vaší lékárny v {city}.\n\n"
        f"Mohu Vám zaslat aktuální katalog a ceník?\n\n"
        f"S pozdravem,\n"
        f"Obchodní tým Vitar"
    )


def parse_sukl_data():
    pharmacies = []

    with open(SUKL_CSV, 'r', encoding='windows-1250') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            score, reasons = score_pharmacy(row)
            city = row.get('MESTO', '').strip()
            psc = row.get('PSC', '').strip()

            pharmacy = {
                'id': row.get('KOD_LEKARNY', '').strip(),
                'name': row.get('NAZEV', '').strip(),
                'kod_pracoviste': row.get('KOD_PRACOVISTE', '').strip(),
                'icz': row.get('ICZ', '').strip(),
                'ico': row.get('ICO', '').strip(),
                'city': city,
                'street': row.get('ULICE', '').strip(),
                'psc': psc,
                'region': get_region(psc),
                'lekarnik_prijmeni': row.get('LEKARNIK_PRIJMENI', '').strip(),
                'lekarnik_jmeno': row.get('LEKARNIK_JMENO', '').strip(),
                'lekarnik_titul': row.get('LEKARNIK_TITUL', '').strip(),
                'www': row.get('WWW', '').strip(),
                'email': row.get('EMAIL', '').strip(),
                'phone': row.get('TELEFON', '').strip(),
                'fax': row.get('FAX', '').strip(),
                'erp': row.get('ERP', '') == '1',
                'type_code': row.get('TYP_LEKARNY', '').strip(),
                'type_label': PHARMACY_TYPE_LABELS.get(
                    row.get('TYP_LEKARNY', '').strip(), 'Neznámý'
                ),
                'mail_order': row.get('ZASILKOVY_PRODEJ', '').strip() == 'ANO',
                'emergency': row.get('POHOTOVOST', '').strip() == 'ANO',
                'score': score,
                'score_reasons': reasons,
                'city_tier': get_city_tier(city),
                'eway_status': 'unknown',
            }
            pharmacy['outreach_email'] = generate_outreach_email(pharmacy)
            pharmacies.append(pharmacy)

    pharmacies.sort(key=lambda x: x['score'], reverse=True)
    return pharmacies


def compute_stats(pharmacies):
    total = len(pharmacies)
    with_email = sum(1 for p in pharmacies if p['email'])
    with_phone = sum(1 for p in pharmacies if p['phone'])
    with_web = sum(1 for p in pharmacies if p['www'])
    with_mail_order = sum(1 for p in pharmacies if p['mail_order'])
    with_erp = sum(1 for p in pharmacies if p['erp'])
    avg_score = round(sum(p['score'] for p in pharmacies) / total, 1) if total else 0
    top_prospects = sum(1 for p in pharmacies if p['score'] >= 75)

    regions = Counter(p['region'] for p in pharmacies)
    cities_top = Counter(p['city'] for p in pharmacies).most_common(20)
    types = Counter(p['type_code'] for p in pharmacies)
    tiers = Counter(p['city_tier'] for p in pharmacies)

    score_distribution = {
        '90-100': sum(1 for p in pharmacies if p['score'] >= 90),
        '75-89': sum(1 for p in pharmacies if 75 <= p['score'] < 90),
        '60-74': sum(1 for p in pharmacies if 60 <= p['score'] < 74),
        '45-59': sum(1 for p in pharmacies if 45 <= p['score'] < 60),
        '30-44': sum(1 for p in pharmacies if 30 <= p['score'] < 44),
        '0-29': sum(1 for p in pharmacies if p['score'] < 30),
    }

    return {
        'total': total,
        'with_email': with_email,
        'with_phone': with_phone,
        'with_web': with_web,
        'with_mail_order': with_mail_order,
        'with_erp': with_erp,
        'avg_score': avg_score,
        'top_prospects': top_prospects,
        'email_pct': round(with_email * 100 / total, 1),
        'regions': dict(sorted(regions.items(), key=lambda x: -x[1])),
        'cities_top': cities_top,
        'types': {k: v for k, v in sorted(types.items(), key=lambda x: -x[1])},
        'type_labels': PHARMACY_TYPE_LABELS,
        'tiers': dict(tiers),
        'score_distribution': score_distribution,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'data_source': 'SÚKL Open Data (opendata.sukl.cz)',
        'data_date': '2026-02-27',
    }


def save_to_sqlite(pharmacies):
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE pharmacies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kod_lekarny TEXT,
        name TEXT,
        ico TEXT,
        city TEXT,
        street TEXT,
        psc TEXT,
        region TEXT,
        email TEXT,
        phone TEXT,
        www TEXT,
        type_code TEXT,
        type_label TEXT,
        score INTEGER,
        city_tier TEXT,
        mail_order BOOLEAN,
        erp BOOLEAN,
        lekarnik TEXT,
        eway_status TEXT DEFAULT 'unknown'
    )''')

    for p in pharmacies:
        lekarnik = ' '.join(filter(None, [
            p['lekarnik_titul'], p['lekarnik_jmeno'], p['lekarnik_prijmeni']
        ]))
        c.execute(
            '''INSERT INTO pharmacies (kod_lekarny, name, ico, city, street, psc,
               region, email, phone, www, type_code, type_label, score,
               city_tier, mail_order, erp, lekarnik, eway_status)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (p['id'], p['name'], p['ico'], p['city'], p['street'], p['psc'],
             p['region'], p['email'], p['phone'], p['www'], p['type_code'],
             p['type_label'], p['score'], p['city_tier'], p['mail_order'],
             p['erp'], lekarnik, p['eway_status'])
        )

    conn.commit()
    conn.close()
    print(f"  SQLite: {DB_PATH}")


def export_csvs(pharmacies):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    scored_path = os.path.join(OUTPUT_DIR, 'prospects_scored.csv')
    with open(scored_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow([
            'Score', 'Název', 'IČO', 'Město', 'Ulice', 'PSČ', 'Kraj',
            'Email', 'Telefon', 'Web', 'Typ', 'Zásilkový', 'E-recept',
            'Lékárník', 'Tier', 'eWay Status'
        ])
        for p in pharmacies:
            lekarnik = ' '.join(filter(None, [
                p['lekarnik_titul'], p['lekarnik_jmeno'], p['lekarnik_prijmeni']
            ]))
            w.writerow([
                p['score'], p['name'], p['ico'], p['city'], p['street'],
                p['psc'], p['region'], p['email'], p['phone'], p['www'],
                p['type_label'], 'Ano' if p['mail_order'] else 'Ne',
                'Ano' if p['erp'] else 'Ne', lekarnik, p['city_tier'],
                p['eway_status']
            ])
    print(f"  CSV (all): {scored_path} ({len(pharmacies)} rows)")

    email_path = os.path.join(OUTPUT_DIR, 'prospects_with_email.csv')
    email_prospects = [p for p in pharmacies if p['email']]
    with open(email_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow([
            'Score', 'Název', 'IČO', 'Město', 'Kraj', 'Email',
            'Telefon', 'Typ', 'Tier'
        ])
        for p in email_prospects:
            w.writerow([
                p['score'], p['name'], p['ico'], p['city'], p['region'],
                p['email'], p['phone'], p['type_label'], p['city_tier']
            ])
    print(f"  CSV (email): {email_path} ({len(email_prospects)} rows)")


def generate_dashboard_data(pharmacies, stats):
    os.makedirs(DASHBOARD_DIR, exist_ok=True)

    dashboard_pharmacies = []
    for p in pharmacies:
        lekarnik = ' '.join(filter(None, [
            p['lekarnik_titul'], p['lekarnik_jmeno'], p['lekarnik_prijmeni']
        ]))
        dashboard_pharmacies.append({
            'id': p['id'],
            'n': p['name'],
            'ico': p['ico'],
            'c': p['city'],
            'st': p['street'],
            'psc': p['psc'],
            'r': p['region'],
            'e': p['email'],
            'ph': p['phone'],
            'w': p['www'],
            'tc': p['type_code'],
            'tl': p['type_label'],
            's': p['score'],
            'sr': p['score_reasons'],
            'ct': p['city_tier'],
            'mo': p['mail_order'],
            'erp': p['erp'],
            'lk': lekarnik,
            'oe': p['outreach_email'],
        })

    data = {
        'stats': stats,
        'pharmacies': dashboard_pharmacies,
    }

    data_js_path = os.path.join(DASHBOARD_DIR, 'data.js')
    with open(data_js_path, 'w', encoding='utf-8') as f:
        f.write('const PROSPECTOR_DATA = ')
        json.dump(data, f, ensure_ascii=False, indent=None)
        f.write(';\n')
    print(f"  Dashboard data: {data_js_path}")

    json_path = os.path.join(OUTPUT_DIR, 'dashboard_data.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  JSON: {json_path}")


def main():
    print("=" * 60)
    print("  VITAR PROSPECTOR - SÚKL Pharmacy Analysis")
    print("=" * 60)

    print("\n[1/5] Parsing SÚKL data...")
    pharmacies = parse_sukl_data()
    print(f"  Loaded {len(pharmacies)} pharmacies")

    print("\n[2/5] Computing statistics...")
    stats = compute_stats(pharmacies)
    print(f"  Avg score: {stats['avg_score']}")
    print(f"  Top prospects (75+): {stats['top_prospects']}")
    print(f"  With email: {stats['with_email']} ({stats['email_pct']}%)")
    print(f"  Regions: {len(stats['regions'])}")

    print("\n[3/5] Saving to SQLite...")
    save_to_sqlite(pharmacies)

    print("\n[4/5] Exporting CSVs...")
    export_csvs(pharmacies)

    print("\n[5/5] Generating dashboard data...")
    generate_dashboard_data(pharmacies, stats)

    print("\n" + "=" * 60)
    print("  DONE!")
    print(f"  Dashboard: open dashboard/index.html in browser")
    print("=" * 60)


if __name__ == '__main__':
    main()
