import requests
import re
import json
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# ================= CONFIG =================
SPREADSHEET_ID = "1J-lnx-_1TLD_TDqfqRTidrdNolzvOGTO-nJYoRK20n0"
ABA = "RESULTADOS"

SITES = {
    "PT-RJ": "https://bichocerto.com/resultados/rj/para-todos/",
    "LOOK-GO": "https://bichocerto.com/resultados/lk/look/",
    "NACIONAL": "https://bichocerto.com/resultados/ln/loteria-nacional/",
    "FEDERAL": "https://bichocerto.com/resultados/fd/loteria-federal/",
}


# ================= GOOGLE =================
def conectar():
    import os
    import json

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    # 🔹 Se estiver rodando local (com arquivo)
    if os.path.exists("credenciais.json"):
        creds = Credentials.from_service_account_file(
            "credenciais.json",
            scopes=scopes
        )
    else:
        # 🔹 Se estiver rodando no GitHub (via Secret)
        creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])

        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=scopes
        )

    client = gspread.authorize(creds)

    return client.open_by_key(SPREADSHEET_ID).worksheet(ABA)

# ================= PEGAR DATA =================
def pegar_data(html):
    m = re.search(r'value="(\d{4}-\d{2}-\d{2})"', html)
    if m:
        return datetime.strptime(m.group(1), "%Y-%m-%d").strftime("%d/%m/%Y")
    return datetime.now().strftime("%d/%m/%Y")

# ================= EXTRAIR DADOS =================
def extrair(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    html = requests.get(url, headers=headers, timeout=30).text

    data = pegar_data(html)

    match_horas = re.search(r'var horasExtracoes = (\[.*?\]);', html, re.DOTALL)
    match_dados = re.search(r'var dados = (\[.*?\]);', html, re.DOTALL)

    if not match_dados:
        print("Não encontrou dados no site:", url)
        return []

    dados = json.loads(match_dados.group(1))

    if match_horas:
        horas = json.loads(match_horas.group(1))
        horas = []
        for h in json.loads(match_horas.group(1)):
            h = str(h)

            if ":" in h:
                h = h.split(":")[0]
            elif "h" in h:
                h = h.replace("h", "")

            horas.append(h.strip().zfill(2))
    else:
        horas = []

    lista = []

    for i, d in enumerate(dados):
        horario = horas[i] if i < len(horas) else f"SEM_HORA_{i+1}"

        lista.append({
            "data": data,
            "horario": horario,
            "m1": str(d.get("1p", "")).zfill(4),
            "m2": str(d.get("2p", "")).zfill(4),
            "m3": str(d.get("3p", "")).zfill(4),
            "m4": str(d.get("4p", "")).zfill(4),
            "m5": str(d.get("5p", "")).zfill(4),
            "m6": str(d.get("6p", ""))[-4:].zfill(4),
            "m7": str(d.get("7p", "")).zfill(3),
        })

    return lista

# ================= DUPLICIDADE =================
def existentes(aba):
    dados = aba.get_all_values()
    chaves = set()

    for linha in dados[1:]:
        if len(linha) >= 3:
            chave = f"{linha[0]}|{linha[1]}|{linha[2]}"
            chaves.add(chave)

    return chaves

# ================= EXECUTAR =================
def rodar():
    aba = conectar()
    chaves = existentes(aba)

    novas = []

    for loteria, url in SITES.items():
        print("Lendo:", loteria)

        try:
            dados = extrair(url)
        except Exception as e:
            print("Erro:", e)
            continue

        for r in dados:
            chave = f"{r['data']}|{loteria}|{r['horario']}"

            if chave in chaves:
                print("Já existe:", chave)
                continue

            novas.append([
                r["data"],
                loteria,
                r["horario"],
                r["m1"],
                r["m2"],
                r["m3"],
                r["m4"],
                r["m5"],
                r["m6"],
                r["m7"],
            ])

            chaves.add(chave)

    if novas:
        aba.append_rows(novas)
        print(f"{len(novas)} novos registros inseridos!")
    else:
        print("Nada novo.")

# ================= RUN =================
if __name__ == "__main__":
    rodar()
