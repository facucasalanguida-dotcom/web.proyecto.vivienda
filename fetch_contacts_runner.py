"""
Busca contactos de tiendas argentinas usando DuckDuckGo HTML scraping + regex.
"""

import re
import time
import random
import shutil
import requests
from bs4 import BeautifulSoup
import openpyxl

INPUT  = "/root/.claude/uploads/681fbc52-da76-5dea-a6c8-8158eda9bdbb/cfeb0b3b-PUNTOS_DE_VENTA_CABA_Y_GBA.xlsx"
OUTPUT = "/home/user/web.proyecto.vivienda/PUNTOS_DE_VENTA_completado.xlsx"
LOG    = "/home/user/web.proyecto.vivienda/fetch_contacts.log"

# Argentine phone number patterns
PHONE_RE = re.compile(
    r'(?:'
    # International: +54 11 1234-5678 / +54 9 11 1234-5678
    r'(?:\+54|0054)\s*9?\s*(?:11|[2-9][0-9]{3})\s*[\-\s]?\s*[0-9]{3,4}[\-\s]?[0-9]{4}'
    r'|'
    # Local with 0: 011-1234-5678 / 02320 43-3270 / (011) 4xxx-xxxx
    r'0(?:11|[2-9][0-9]{3})\s*[\-\s]?\s*[0-9]{2,4}[\-\s]?[0-9]{4}'
    r')',
    re.IGNORECASE
)

# Website patterns: prefer .com.ar / .org.ar / .net.ar but also .com
WEBSITE_RE = re.compile(
    r'https?://(?:www\.)?'
    r'(?!'
    # Exclude known directories and generic sites
    r'(?:duckduckgo|google|bing|facebook|instagram|twitter|youtube|wikipedia'
    r'|amazon|chewy|mercadolibre|paginasamarillas|miguiaargentina'
    r'|todosnegocios|amarillas|guialocal|infobel|cuitonline|cylex'
    r'|empresite|businesslist|airtable|near-place|cercanooeste'
    r'|veterinariasanroque|infoveterinaria|doctorvet|veter\.com'
    r')\.(?:com|org|net|com\.ar|ar)'
    r')'
    r'[a-z0-9\-]+\.[a-z]{2,}(?:\.[a-z]{2})?(?:/[^\s<>"\']*)?',
    re.IGNORECASE
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
}

session = requests.Session()
session.headers.update(HEADERS)


def ddg_search(query: str) -> str:
    """Return full text from DuckDuckGo HTML result page."""
    try:
        r = session.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query, "kl": "ar-es"},
            timeout=15,
        )
        if r.status_code != 200:
            return ""
        soup = BeautifulSoup(r.text, "lxml")
        texts = []
        for res in soup.select(".result"):
            texts.append(res.get_text(" ", strip=True))
        return " ".join(texts)
    except Exception:
        return ""


def extract_info(text: str) -> tuple:
    phone_matches = PHONE_RE.findall(text)
    phone = ""
    for p in phone_matches:
        p = p.strip()
        digits = re.sub(r"[^\d+]", "", p)
        if len(digits) >= 8:
            phone = p
            break

    web_matches = WEBSITE_RE.findall(text)
    website = web_matches[0].rstrip(".,)>;\"'") if web_matches else ""

    return phone, website


def main():
    shutil.copy2(INPUT, OUTPUT)
    wb = openpyxl.load_workbook(OUTPUT)
    ws = wb["Hoja1"]

    ws.cell(row=2, column=6, value="Contacto")
    ws.cell(row=2, column=7, value="Web")

    data_rows = [
        (i, row)
        for i, row in enumerate(ws.iter_rows(min_row=3), start=3)
        if row[0].value is not None
        and str(row[0].value).replace(".0", "").isdigit()
    ]
    total = len(data_rows)
    found = 0

    with open(LOG, "w", encoding="utf-8") as logf:
        logf.write(f"Total tiendas: {total}\n")
        logf.flush()

        for idx, (row_num, row) in enumerate(data_rows):
            razon     = str(row[1].value or "").strip()
            domicilio = str(row[2].value or "").strip()
            localidad = str(row[3].value or "").strip()
            cluster   = str(row[4].value or "").strip()

            # Primary search: name + city
            query1 = f'"{razon}" {localidad} Argentina telefono'
            text = ddg_search(query1)
            time.sleep(random.uniform(0.5, 1.0))

            phone, website = extract_info(text)

            # If nothing found, retry with address + cluster
            if not phone and not website:
                query2 = f'{cluster} {domicilio} {localidad} Argentina contacto telefono'
                text2 = ddg_search(query2)
                phone, website = extract_info(text2)
                time.sleep(random.uniform(0.5, 1.0))

            ws.cell(row=row_num, column=6, value=phone)
            ws.cell(row=row_num, column=7, value=website)

            if phone or website:
                found += 1

            status = "OK" if (phone or website) else "--"
            line = f"[{idx+1}/{total}] {status} | {razon} | {localidad} | tel={phone} | web={website}"
            print(line, flush=True)
            logf.write(line + "\n")
            logf.flush()

            if (idx + 1) % 100 == 0:
                wb.save(OUTPUT)
                logf.write(f"  >> Guardado parcial fila {idx+1}\n")
                logf.flush()

            time.sleep(random.uniform(1.0, 2.0))

        wb.save(OUTPUT)
        summary = f"\nFinalizado. Encontrados: {found}/{total}\n"
        print(summary, flush=True)
        logf.write(summary)


if __name__ == "__main__":
    main()
