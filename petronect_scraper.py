# petronect_scraper.py
import asyncio, re, time, subprocess, sys
from datetime import datetime, timezone
import pandas as pd
from pathlib import Path
from playwright.async_api import async_playwright

PETRONECT_PUBLIC_URL = "https://www.petronect.com.br/irj/go/km/docs/pccshrcontent/Site%20Content%20%28Legacy%29/Portal2018/pt/lista_licitacoes_publicadas_ft.html"

# Palavras-chave alvo (API 610 OH/BB)
KEYWORDS = [
    "API 610",
    "bomba centrífuga","bomba","bombas","Aquisição de bombas centrífugas","bomba centrífuga",
    "OH1","OH-1","OH2","OH-2","OH3","OH-3","OH4","OH-4","OH5","OH-5","OH6","OH-6","OHH",
    "BB1","BB-1","BB2","BB-2","BB3","BB-3","BB4","BB-4","BB5","BB-5",
    "overhung","between bearings","entre mancais","axial split","radial split"
]

OUTPUT_DIR = Path("saida_petronect")
OUTPUT_DIR.mkdir(exist_ok=True)


def matches_pump_scope(text: str) -> bool:
    txt = text.lower()
    return any(k.lower() in txt for k in KEYWORDS)


def ensure_browsers_installed():
    """
    Em ambiente como o Streamlit Cloud não dá para rodar 'playwright install' no terminal.
    Então chamamos aqui via subprocess. Se já estiver instalado, o comando sai rápido.
    """
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        # se der erro aqui, deixamos o Playwright se virar e mostrar mensagem normal
        pass


async def scrape_once():
    # garante que o Chromium do Playwright existe
    ensure_browsers_installed()

    async with async_playwright() as p:
        # em servidor, sempre headless
        browser = await p.chromium.launch(headless=True)
        # se quiser testar local vendo o navegador, mude para headless=False

        context = await browser.new_context(locale="pt-BR")
        page = await context.new_page()
        await page.goto(PETRONECT_PUBLIC_URL, wait_until="domcontentloaded")

        all_rows = []

        def normalize_spaces(s: str) -> str:
            return re.sub(r"\s+", " ", s or "").strip()

        # Tente múltiplas iterações de paginação (limite defensivo)
        for _ in range(40):
            # Coletar linhas visíveis (ajuste o seletor conforme necessário)
            rows = await page.locator("table >> tr").all()
            for r in rows:
                cells = await r.locator("td,th").all_inner_texts()
                if len(cells) < 3:
                    continue
                row_text = " | ".join(normalize_spaces(c) for c in cells)
                if not row_text or ("Número" in row_text and "Objeto" in row_text):
                    continue
                # Filtrar por escopo API 610 bombas
                if matches_pump_scope(row_text):
                    all_rows.append({
                        "linha": row_text,
                        "pagina": page.url,
                    })

            # Tenta clicar “Próximo”; se não existir ou estiver desabilitado, pare
            next_btn = page.get_by_text("Próximo", exact=True)
            if await next_btn.count() == 0:
                break
            disabled = await next_btn.evaluate_handle("el => el.getAttribute('disabled')")
            if disabled and (await disabled.json_value()) is not None:
                break
            await next_btn.scroll_into_view_if_needed()
            await next_btn.click()
            await page.wait_for_timeout(1200)  # pequeno atraso para carregar

        # Salvar resultados
        ts = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d_%Hh%M")
        df = pd.DataFrame(all_rows).drop_duplicates()
        csv_path = OUTPUT_DIR / f"petronect_api610_{ts}.csv"
        xlsx_path = OUTPUT_DIR / f"petronect_api610_{ts}.xlsx"
        df.to_csv(csv_path, index=False, encoding="utf-8")
        df.to_excel(xlsx_path, index=False)
        print(f"Salvo:\n- {csv_path}\n- {xlsx_path}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(scrape_once())
