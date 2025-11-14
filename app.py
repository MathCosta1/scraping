# app.py
import sys
import asyncio
from pathlib import Path

import streamlit as st
import pandas as pd

# Corrige o event loop no Windows (necessário pro Playwright funcionar dentro do Streamlit)
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# importa do seu arquivo petronect_scraper.py
from petronect_scraper import scrape_once, OUTPUT_DIR

st.set_page_config(
    page_title="Petronect Scraper - API 610",
    page_icon="🔍",
    layout="wide",
)

st.title("🔍 Petronect Scraper - API 610 / OH / BB")
st.markdown(
    "Este app roda o **scraper da Petronect** e salva os resultados em CSV/XLSX, "
    "filtrando apenas licitações relacionadas a **bombas centrífugas / API 610 / OH / BB**."
)
st.divider()

if st.button("🚀 Iniciar Coleta"):
    with st.spinner("Executando o Playwright e coletando os dados... ⏳"):
        try:
            # roda a função assíncrona do seu petronect_scraper.py
            asyncio.run(scrape_once())

            # após rodar, procuramos o CSV mais recente na pasta de saída
            OUTPUT_DIR.mkdir(exist_ok=True)
            csv_files = sorted(OUTPUT_DIR.glob("petronect_api610_*.csv"))
            if not csv_files:
                st.warning("Nenhum arquivo CSV encontrado na pasta de saída.")
            else:
                latest_csv: Path = csv_files[-1]
                df = pd.read_csv(latest_csv)

                st.success(f"Coleta concluída! Arquivo carregado: `{latest_csv.name}`")
                if df.empty:
                    st.info("O arquivo foi gerado, mas não há linhas (nenhuma licitação bateu com os filtros).")
                else:
                    st.dataframe(df, width="stretch")

                    # botão para baixar o CSV exibido
                    csv_bytes = df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "⬇️ Baixar CSV",
                        data=csv_bytes,
                        file_name=latest_csv.name,
                        mime="text/csv",
                    )

        except Exception as e:
            st.error(f"Ocorreu um erro ao executar o scraper: {e}")
else:
    st.info("Clique em **Iniciar Coleta** para rodar o scraper da Petronect.")
