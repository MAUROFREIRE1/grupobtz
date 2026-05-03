import re
import json
import html
import base64
import mimetypes
import unicodedata
from pathlib import Path
from collections import defaultdict
from typing import Optional

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


# =========================
# Configuração da página
# =========================
st.set_page_config(
    page_title="Cronograma de Lubrificação - BTZ Matriz",
    layout="wide", # Mantemos wide para desktop, mas o CSS vai adaptar para mobile
    initial_sidebar_state="collapsed",
)

# =========================
# CSS global + responsividade
# =========================
st.markdown(
    """
    <style>
        h1,h2,h3,h4 { color: inherit !important; }

        /* Remove topo nativo do Streamlit */
        header[data-testid="stHeader"] { display: none !important; height: 0 !important; }
        div[data-testid="stToolbar"] { display: none !important; }
        div[data-testid="stDecoration"] { display: none !important; }
        div[data-testid="stStatusWidget"] { display: none !important; }
        #MainMenu { visibility: hidden !important; }
        footer { visibility: hidden !important; }

        /* Sidebar e botão */
        section[data-testid="stSidebar"] { display: none !important; }
        button[kind="header"] { display: none !important; }

        /* Sobe conteúdo ao máximo */
        [data-testid="stAppViewContainer"] .main {
            padding-top: 0 !important;
            margin-top: 0 !important;
        }

        [data-testid="stAppViewContainer"] .main .block-container{
            padding-top: 0 !important;
            margin-top: -8px !important;
            padding-bottom: 0.8rem !important;
        }

        [data-testid="stAppViewContainer"] .main .block-container > div:first-child{
            margin-top: 0 !important;
            padding-top: 0 !important;
        }

        /* Logo dentro de container nativo (mesmo contorno do bloco de filtros) */
        /* Removendo altura fixa aqui, pois o container externo vai gerenciar */
        .logo-inner {
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            margin: 0;
            padding: 4px 2px;
            box-sizing: border-box;
            height: 100%; /* Garante que a logo ocupe toda a altura disponível na sua coluna */
        }

        .logo-inner img {
            max-height: 140px;
            max-width: 100%;
            width: auto;
            height: auto;
            object-fit: contain;
            display: block;
            margin: 0 auto;
        }

        /* Evita sobras verticais nos widgets do card de filtros */
        [data-testid="stDateInput"],
        [data-testid="stMultiSelect"] {
            margin-bottom: 0 !important;
            width: 100% !important;
        }

        /* Responsividade global de colunas */
        @media (max-width: 1200px) {
            /* O container externo com borda já vai se comportar bem */
            .main-header-container > div[data-testid="stHorizontalBlock"] {
                flex-wrap: wrap !important;
                gap: 0.5rem !important;
            }
            .main-header-container > div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                min-width: calc(50% - 0.5rem) !important;
                flex: 1 1 calc(50% - 0.5rem) !important;
            }
        }

        /* Ajustes ESPECÍFICOS para telas de celular (max-width: 768px) */
        @media (max-width: 768px) {
            /* Colunas sempre empilhadas em telas pequenas */
            .main-header-container > div[data-testid="stHorizontalBlock"] {
                flex-direction: column !important;
                gap: 1rem !important; /* Aumenta o espaçamento entre os blocos empilhados */
            }
            .main-header-container > div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                min-width: 100% !important;
                flex: 1 1 100% !important;
            }

            /* Logo menor em mobile */
            .logo-inner {
                height: 80px; /* Altura reduzida para a logo em mobile */
                padding: 2px;
            }
            .logo-inner img {
                max-height: 70px; /* Ajusta o tamanho da imagem da logo */
            }

            /* Ajusta padding e margens para mobile */
            [data-testid="stAppViewContainer"] .main .block-container{
                padding-left: 0.5rem !important;
                padding-right: 0.5rem !important;
                padding-bottom: 0.5rem !important;
            }

            /* Títulos menores para mobile */
            h1 { font-size: 2em !important; }
            h2 { font-size: 1.5em !important; }
            h3 { font-size: 1.2em !important; }
            h4 { font-size: 1em !important; }

            /* Botões e inputs maiores para toque */
            .stButton > button, .stTextInput > div > div > input, .stMultiSelect > div > div {
                padding: 10px !important;
                font-size: 16px !important;
            }

            /* Esconde a coluna de métricas em mobile para economizar espaço */
            .metrics-container {
                display: none;
            }

            /* Ajustes para a tabela em mobile */
            .tbl {
                min-width: unset; /* Remove o min-width fixo para permitir rolagem horizontal */
                width: 100%; /* Ocupa 100% da largura disponível */
                display: block; /* Permite rolagem horizontal */
                overflow-x: auto; /* Adiciona barra de rolagem horizontal se necessário */
                white-space: nowrap; /* Impede que o conteúdo da tabela quebre linha */
            }
            .tbl thead, .tbl tbody, .tbl th, .tbl td, .tbl tr {
                display: block; /* Para permitir rolagem horizontal */
            }
            .tbl thead th.cat-h, .tbl tbody td.cat {
                position: static; /* Remove sticky para a coluna de categoria em mobile */
                min-width: unset;
                width: 100%; /* Ocupa toda a largura disponível */
                text-align: left;
                box-shadow: none; /* Remove sombra da coluna congelada */
            }
            .tbl thead th:not(.cat-h), .tbl tbody td:not(.cat) {
                display: inline-block; /* Permite que as células de semana fiquem lado a lado */
                width: 48px; /* Largura fixa para as células de semana */
                box-sizing: border-box;
            }
            .tbl thead th:not(.cat-h) {
                border-bottom: none !important; /* Remove borda inferior para as semanas no cabeçalho */
            }
            .tbl tbody td {
                border-bottom: none !important; /* Remove borda inferior para as semanas no corpo */
            }
            .tbl tbody tr {
                border-bottom: 1px solid var(--border-color); /* Adiciona uma borda para separar as linhas */
            }
            .tbl tbody tr.lvl-6 td.cat {
                border-left: none !important; /* Remove a borda esquerda para serviços em mobile */
            }
        }

        /* Estilos para a página de login */
        .login-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            background-color: var(--background-color);
            padding-top: 10vh;
            padding-bottom: 5vh;
        }
        .login-logo-wrapper {
            padding: 15px;
            border-radius: 10px;
            background-color: var(--secondary-background-color);
            margin-bottom: 20px;
            width: 100%;
            max-width: 200px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-card {
            padding: 30px;
            border-radius: 10px;
            background-color: var(--secondary-background-color);
            width: 100%;
            max-width: 200px;
            text-align: center;
        }
        .login-card h2 {
            margin-bottom: 20px;
            color: var(--text-color);
        }
        .login-card .stTextInput > div > div > input {
            border-radius: 5px;
            padding: 10px;
            border: 1px solid var(--border-color);
        }
        .login-card .stButton > button {
            width: 100%;
            padding: 10px;
            border-radius: 5px;
            background-color: #4CAF50;
            color: white;
            border: none;
            font-size: 16px;
            cursor: pointer;
        }
        .login-card .stButton > button:hover {
            background-color: #45a049;
        }
        .login-card .stAlert {
            margin-top: 15px;
        }
        .login-logo-inner {
            display: flex;
            height: auto;
            padding: 0;
        }
        .login-logo-inner img {
            max-height: 80px;
            width: auto;
            height: auto;
            object-fit: contain;
        }

        /* Removendo os estilos de altura igual anteriores, pois a nova abordagem é diferente */
        /* O container principal com border=True vai garantir o alinhamento */
        .main-header-container > div[data-testid="stHorizontalBlock"] {
            display: flex;
            align-items: stretch; /* Garante que as colunas se estiquem para a altura do conteúdo mais alto */
        }

        .main-header-container .logo-inner {
            height: 100%; /* Garante que a logo ocupe toda a altura da sua coluna */
            display: flex;
            flex-direction: column;
            justify-content: center; /* Centraliza a logo verticalmente */
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================
# Utilitários
# =========================
MESES_ABR = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def fmt_dd_mmm(d: pd.Timestamp) -> str:
    return f"{d.day:02d}/{MESES_ABR[d.month - 1]}"


def norm(s: str) -> str:
    s = str(s).strip().upper()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^A-Z0-9]+", "_", s).strip("_")
    return s


def tema_atual_streamlit() -> str:
    base = st.get_option("theme.base")
    if isinstance(base, str) and base.lower() in {"light", "dark"}:
        return base.lower()
    return "light"


def mapear_colunas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [norm(c) for c in df.columns]

    aliases = {
        "AREA": ["AREA", "AREA_"],
        "EQUIPAMENTO": ["EQUIPAMENTO"],
        "CONJUNTO": ["CONJUNTO"],
        "SUBCONJUNTO": ["SUBCONJUNTO"],
        "PONTO": ["PONTO"],
        "SERVICO": ["SERVICO", "SERVIÇO"],
        "QTD": ["QTD", "QUANTIDADE"],
        "MATERIAL": ["MATERIAL"],
        "FREQUENCIA": ["FREQUENCIA", "FREQUENCIA_DIAS", "PERIODICIDADE"],
        "CONDICAO_SERVICO": ["CONDICAO_SERVICO", "CONDICAO_DO_SERVICO", "CONDICAO_DE_SERVICO"],
        "TIPO": ["TIPO"],
    }

    rename_map = {}
    for canon, possiveis in aliases.items():
        for p in possiveis:
            if p in df.columns:
                rename_map[p] = canon
                break

    df = df.rename(columns=rename_map)

    # fallback por posição
    if "PONTO" not in df.columns:
        df["PONTO"] = df.iloc[:, 4] if df.shape[1] > 4 else "N/A"
    if "SERVICO" not in df.columns:
        df["SERVICO"] = df.iloc[:, 7] if df.shape[1] > 7 else "N/A"
    if "QTD" not in df.columns:
        df["QTD"] = df.iloc[:, 9] if df.shape[1] > 9 else "N/A"
    if "MATERIAL" not in df.columns:
        df["MATERIAL"] = df.iloc[:, 11] if df.shape[1] > 11 else "N/A"

    obrigatorias = [
        "AREA", "EQUIPAMENTO", "CONJUNTO", "SUBCONJUNTO",
        "PONTO", "SERVICO", "QTD", "MATERIAL",
        "FREQUENCIA", "CONDICAO_SERVICO", "TIPO",
    ]
    for c in obrigatorias:
        if c not in df.columns:
            df[c] = "N/A"

    for c in df.columns:
        df[c] = (
            df[c]
            .astype(str)
            .replace({"nan": "N/A", "None": "N/A", "": "N/A"})
            .fillna("N/A")
            .str.strip()
        )

    return df


def descricao_servico(r: pd.Series) -> str:
    serv = str(r.get("SERVICO", "N/A")).strip()
    if norm(serv) == "LUBRIFICAR":
        qtd = str(r.get("QTD", "N/A")).strip()
        material = str(r.get("MATERIAL", "N/A")).strip()
        return f"{serv} com {qtd} Gr de {material}"
    return serv


def freq_para_dias(freq: str) -> int:
    txt = str(freq).strip().lower()

    if txt.isdigit():
        return max(1, int(txt))

    m = re.search(r"(\d+)\s*(dia|dias|semana|semanas|mes|meses|m[eê]s|m[eê]ses|ano|anos)", txt)
    if m:
        n = int(m.group(1))
        u = m.group(2)
        if "dia" in u:
            return max(1, n)
        if "semana" in u:
            return max(1, n * 7)
        if "mes" in u or "mês" in u:
            return max(1, n * 30)
        if "ano" in u:
            return max(1, n * 365)

    mapa = {
        "diaria": 1, "diário": 1, "diario": 1,
        "semanal": 7, "quinzenal": 15, "mensal": 30,
        "bimestral": 60, "trimestral": 90, "semestral": 180, "anual": 365,
    }
    for k, v in mapa.items():
        if k in txt:
            return v

    return 30


def mask_por_filtros(df_in: pd.DataFrame, filtros: dict, excluir_coluna=None) -> pd.Series:
    m = pd.Series(True, index=df_in.index)
    for col, valores in filtros.items():
        if col == excluir_coluna:
            continue
        if valores:
            m &= df_in[col].isin(valores)
    return m


def semanas_programadas(freq: str, inicio: pd.Timestamp, qtd_semanas: int = 52) -> set[int]:
    fim = inicio + pd.Timedelta(days=7 * qtd_semanas - 1)
    passo = freq_para_dias(freq)

    d = inicio
    semanas = set()
    while d <= fim:
        idx = (d - inicio).days // 7
        if 0 <= idx < qtd_semanas:
            semanas.add(int(idx))
        d += pd.Timedelta(days=passo)
    return semanas


def node_id(path: tuple) -> str:
    return "n|" + "|".join([norm(x) for x in path])


def encontrar_logo() -> Optional[Path]:
    base_dir = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()

    candidatos = [
        base_dir / "grupobtzlog.png",
        base_dir / "grupo-btz-log.png",
        base_dir / "grupo_btz_log.png",
        base_dir / "grupobtzlog.jpg",
        base_dir / "grupo-btz-log.jpg",
        base_dir / "grupobtzlog.jpeg",
        base_dir / "grupo-btz-log.jpeg",
        base_dir / "grupobtzlog.webp",
        base_dir / "grupo-btz-log.webp",
    ]

    for p in candidatos:
        if p.exists() and p.is_file():
            return p

    for p in base_dir.iterdir():
        if p.is_file():
            stem = p.stem.lower()
            if "grupo" in stem and "btz" in stem and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                return p

    return None


def logo_data_uri(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    if not mime:
        mime = "image/png"
    b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


# =========================
# Matriz hierárquica
# =========================
def montar_matriz_hierarquica(df_base: pd.DataFrame, inicio: pd.Timestamp, qtd_semanas: int = 52):
    leaf_weeks = defaultdict(set)

    for _, r in df_base.iterrows():
        serv_txt = descricao_servico(r)
        path6 = (
            r["AREA"], r["EQUIPAMENTO"], r["CONJUNTO"], r["SUBCONJUNTO"], r["PONTO"], serv_txt
        )
        leaf_weeks[path6] |= semanas_programadas(r["FREQUENCIA"], inicio, qtd_semanas=qtd_semanas)

    nodes = {}
    children = defaultdict(list)

    def ensure_node(path: tuple):
        if path in nodes:
            return
        level = len(path)
        parent = path[:-1] if level > 1 else tuple()
        name = path[-1] if level > 0 else ""
        nodes[path] = {"path": path, "level": level, "name": name, "parent": parent, "children": []}
        if level > 0:
            children[parent].append(path)

    for p6 in leaf_weeks.keys():
        ensure_node((p6[0],))
        ensure_node((p6[0], p6[1]))
        ensure_node((p6[0], p6[1], p6[2]))
        ensure_node((p6[0], p6[1], p6[2], p6[3]))
        ensure_node((p6[0], p6[1], p6[2], p6[3], p6[4]))
        ensure_node(p6)

    for p in list(nodes.keys()):
        nodes[p]["children"] = sorted(children[p], key=lambda x: tuple(norm(y) for y in x))

    memo = {}

    def calc_weeks(path: tuple):
        if path in memo:
            return memo[path]
        lvl = len(path)
        if lvl == 6:
            w = [1 if i in leaf_weeks[path] else 0 for i in range(qtd_semanas)]
            memo[path] = w
            return w

        agg = [0] * qtd_semanas
        for ch in nodes[path]["children"]:
            cw = calc_weeks(ch)
            agg = [1 if (agg[i] or cw[i]) else 0 for i in range(qtd_semanas)]
        memo[path] = agg
        return agg

    top = sorted(children[tuple()], key=lambda x: tuple(norm(y) for y in x))
    for p in top:
        calc_weeks(p)

    rows = []

    def walk(path: tuple):
        lvl = len(path)
        name = nodes[path]["name"]

        if lvl == 1:
            label = f"Área: {name}"
        elif lvl == 2:
            label = f"Equipamento: {name}"
        elif lvl == 3:
            label = f"Conjunto: {name}"
        elif lvl == 4:
            label = f"Subconjunto: {name}"
        elif lvl == 5:
            label = f"Ponto: {name}"
        else:
            label = f"Serviço: {name}"

        rows.append({
            "id": node_id(path),
            "parent": node_id(path[:-1]) if lvl > 1 else "",
            "level": lvl,
            "label": label,
            "has_children": len(nodes[path]["children"]) > 0,
            "weeks": memo[path],
        })

        for ch in nodes[path]["children"]:
            walk(ch)

    for p in top:
        walk(p)

    return rows


def render_matriz_html(
    rows: list,
    inicio: pd.Timestamp,
    qtd_semanas: int = 52,
    theme_base: str = "light",
    status_filter: Optional[list] = None,
    tree_cmd: Optional[dict] = None,
):
    if not status_filter:
        status_filter = ["planned", "done", "not_done"]

    status_filter_json = json.dumps(status_filter, ensure_ascii=False)
    tree_cmd_json = json.dumps(tree_cmd or {"action": "none", "seq": 0}, ensure_ascii=False)

    theme_class = "theme-light" if theme_base == "light" else "theme-dark"
    datas = [inicio + pd.Timedelta(days=7 * i) for i in range(qtd_semanas)]
    headers = "".join([f"<th>{fmt_dd_mmm(d)}</th>" for d in datas])

    indent_map = {1: 2, 2: 24, 3: 46, 4: 68, 5: 90, 6: 120}

    body_rows = []
    for r in rows:
        lvl = r["level"]
        indent = indent_map.get(lvl, (lvl - 1) * 22)

        if r["has_children"]:
            toggle = f'<button class="tg" data-id="{html.escape(r["id"])}" aria-label="expandir">[+]</button>'
        else:
            toggle = '<span class="tg-placeholder"></span>'

        week_cells_list = []
        for wi, v in enumerate(r["weeks"]):
            if v == 1:
                if lvl == 6:
                    # Nível 6 (serviço) sempre mostra o botão de status
                    week_cells_list.append(
                        f'<td class="c" data-week-idx="{wi}"><button class="pg-btn" data-row="{html.escape(r["id"])}" data-week="{wi}" title="Marcar execução"><span class="pg pg--planned"></span></button></td>'
                    )
                else:
                    # Níveis pais (1-5) mostram uma elipse "parent-planned" que será controlada pelo JS
                    week_cells_list.append(
                        f'<td class="c" data-week-idx="{wi}"><span class="pg pg--planned pg--parent-planned"></span></td>'
                    )
            else:
                week_cells_list.append(f'<td class="c" data-week-idx="{wi}"></td>')

        week_cells = "".join(week_cells_list)
        display_style = "" if lvl == 1 else 'style="display:none;"'

        tr = f"""
        <tr class="r lvl-{lvl}" data-id="{html.escape(r['id'])}" data-parent="{html.escape(r['parent'])}" data-level="{lvl}" data-has-children="{int(r['has_children'])}" {display_style}>
            <td class="cat" style="padding-left:{indent}px;">{toggle}<span class="txt">{html.escape(r['label'])}</span></td>
            {week_cells}
        </tr>
        """
        body_rows.append(tr)

    body = "\n".join(body_rows)

    template = """
<!doctype html>
<html>
<head><meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body>
<div class="wrap __THEME_CLASS__" id="wrap-matriz">
  <table class="tbl">
    <thead>
      <tr>
        <th class="cat-h">Categoria</th>
        __HEADERS__
      </tr>
    </thead>
    <tbody>__BODY__</tbody>
  </table>
</div>

<div id="exec-menu" class="exec-menu" style="display:none;">
  <button type="button" data-value="done">Realizado</button>
  <button type="button" data-value="not_done">Não Realizado</button>
  <button type="button" data-value="clear">Sem seleção</button>
</div>

<script>
const STATUS_FILTER = __STATUS_FILTER__;
const TREE_CMD = __TREE_CMD__;

const rows = Array.from(document.querySelectorAll("tr.r"));
const rowById = new Map();
rows.forEach(r => rowById.set(r.dataset.id, r));

const childrenMap = new Map();
rows.forEach(row => {
  const p = row.dataset.parent || "";
  if (!childrenMap.has(p)) childrenMap.set(p, []);
  childrenMap.get(p).push(row);
});

const expanded = new Set();

function hideDescendants(id) {
  const kids = childrenMap.get(id) || [];
  kids.forEach(k => {
    k.style.display = "none";
    const kidId = k.dataset.id;
    expanded.delete(kidId);
    const btn = k.querySelector("button.tg");
    if (btn) btn.textContent = "[+]";
    hideDescendants(kidId);
  });
}

function isParentChainExpanded(row) {
  let parentId = row.dataset.parent;
  while (parentId) {
    if (!expanded.has(parentId)) return false;
    const parentRow = rowById.get(parentId);
    if (!parentRow) break;
    parentId = parentRow.dataset.parent;
  }
  return true;
}

document.querySelectorAll("button.tg").forEach(btn => {
  btn.addEventListener("click", (e) => {
    const row = btn.closest("tr.r");
    const id = row.dataset.id;
    if (expanded.has(id)) {
      expanded.delete(id);
      btn.textContent = "[+]";
      hideDescendants(id);
    } else {
      expanded.add(id);
      btn.textContent = "[-]";
      childrenMap.get(id).forEach(k => {
        if (k.dataset.filterHidden === "0") k.style.display = "";
      });
    }
    updateParentPlannedDots(); // Chama a função após expandir/recolher
  });
});

const execState = JSON.parse(localStorage.getItem("execState") || "{}");
function saveExecState() { localStorage.setItem("execState", JSON.stringify(execState)); }

function keyOf(btn) { return `${btn.dataset.row}-${btn.dataset.week}`; }
function getBtnStatus(btn) { return execState[keyOf(btn)] || "planned"; }

function applyState(btn) {
  const st = getBtnStatus(btn);
  const dot = btn.querySelector(".pg");
  dot.classList.remove("pg--planned", "pg--done", "pg--not");
  if (st === "done") dot.classList.add("pg--done");
  else if (st === "not_done") dot.classList.add("pg--not");
  else dot.classList.add("pg--planned");
}

const execButtons = Array.from(document.querySelectorAll(".pg-btn"));
execButtons.forEach(applyState);

function leafMatchesFilter(row) {
  const btns = Array.from(row.querySelectorAll(".pg-btn"));
  if (!btns.length) return false;
  return btns.some(btn => STATUS_FILTER.includes(getBtnStatus(btn)));
}

const matchCache = new Map();
function rowMatchesFilterRecursive(row) {
  const id = row.dataset.id;
  if (matchCache.has(id)) return matchCache.get(id);

  const lvl = Number(row.dataset.level || "0");
  let ok = false;

  if (lvl === 6) {
    ok = leafMatchesFilter(row);
  } else {
    const kids = childrenMap.get(id) || [];
    ok = kids.some(ch => rowMatchesFilterRecursive(ch));
  }
  matchCache.set(id, ok);
  return ok;
}

function applyStatusFilterToRows() {
  matchCache.clear();
  rows.forEach(row => {
    const lvl = Number(row.dataset.level || "0");
    const ok = rowMatchesFilterRecursive(row);
    row.dataset.filterHidden = ok ? "0" : "1";

    if (!ok) { row.style.display = "none"; return; }
    if (lvl === 1) row.style.display = "";
    else row.style.display = isParentChainExpanded(row) ? "" : "none";
  });
  updateParentPlannedDots(); // Chama a função após aplicar filtros
}

function expandAllRows() {
  rows.forEach(row => {
    const btn = row.querySelector("button.tg");
    if (btn) { expanded.add(row.dataset.id); btn.textContent = "[-]"; }
  });
  applyStatusFilterToRows();
}

function collapseAllRows() {
  expanded.clear();
  document.querySelectorAll("button.tg").forEach(btn => { btn.textContent = "[+]"; });
  applyStatusFilterToRows();
}

const menu = document.getElementById("exec-menu");
let activeBtn = null;

function openMenu(targetBtn) {
  activeBtn = targetBtn;
  const rect = targetBtn.getBoundingClientRect();
  menu.style.display = "flex";
  menu.style.left = `${window.scrollX + rect.left + rect.width + 6}px`;
  menu.style.top = `${window.scrollY + rect.top - 2}px`;
}
function closeMenu() { menu.style.display = "none"; activeBtn = null; }

execButtons.forEach(btn => {
  btn.addEventListener("click", (e) => { e.stopPropagation(); openMenu(btn); });
});

menu.querySelectorAll("button").forEach(opt => {
  opt.addEventListener("click", (e) => {
    e.stopPropagation();
    if (!activeBtn) return;

    const value = opt.dataset.value;
    const k = keyOf(activeBtn);

    if (value === "clear") delete execState[k];
    else execState[k] = value;

    saveExecState();
    applyState(activeBtn);
    applyStatusFilterToRows();
    closeMenu();
  });
});

// NOVA FUNÇÃO PARA CONTROLAR A VISIBILIDADE DAS ELIPSES AZUIS DOS PAIS
function updateParentPlannedDots() {
    rows.forEach(parentRow => {
        const parentId = parentRow.dataset.id;
        const parentLevel = Number(parentRow.dataset.level);
        const hasChildren = parentRow.dataset.hasChildren === "1";

        if (parentLevel < 6 && hasChildren) { // Apenas para nós pais com filhos
            const parentPlannedDots = parentRow.querySelectorAll('.pg--parent-planned');
            const kids = childrenMap.get(parentId) || [];

            // Verifica se algum filho direto está visível E não está filtrado
            const anyChildVisibleAndNotFiltered = kids.some(childRow => {
                return childRow.style.display !== 'none' && childRow.dataset.filterHidden === '0';
            });

            if (anyChildVisibleAndNotFiltered) {
                // Se há filhos visíveis e não filtrados, esconde as elipses do pai
                parentPlannedDots.forEach(dot => dot.style.visibility = 'hidden');
            } else {
                // Se não há filhos visíveis ou todos estão filtrados, mostra as elipses do pai (se houver planejamento)
                parentPlannedDots.forEach(dot => {
                    // A elipse só deve aparecer se a célula td não estiver vazia (ou seja, se v == 1 no Python)
                    // E se o próprio pai não estiver filtrado
                    if (dot.closest('td').dataset.weekIdx !== undefined && parentRow.dataset.filterHidden === '0') {
                        dot.style.visibility = 'visible';
                    } else {
                        dot.style.visibility = 'hidden'; // Garante que esteja oculto se não houver planejamento ou se o pai estiver filtrado
                    }
                });
            }
        }
    });
}


applyStatusFilterToRows(); // Chama no carregamento inicial para configurar a visibilidade

if (TREE_CMD && TREE_CMD.action === "expand_all") expandAllRows();
else if (TREE_CMD && TREE_CMD.action === "collapse_all") collapseAllRows();

document.addEventListener("click", () => closeMenu());
window.addEventListener("scroll", () => closeMenu(), true);
window.addEventListener("resize", () => closeMenu());
</script>

<style>
html, body { margin: 0; padding: 0; }

.wrap { width: 100%; overflow: auto; border-radius: 12px; }

.tbl {
  border-collapse: collapse;
  min-width: 1850px; /* Mantido para desktop, será sobrescrito em mobile */
  width: max-content;
  font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
}
.tbl thead th {
  position: sticky;
  top: 0;
  z-index: 2;
  font-weight: 700;
  padding: 8px 10px;
  text-align: center;
  white-space: nowrap;
}

/* Categoria congelada */
.tbl thead th.cat-h {
  text-align: left;
  min-width: 460px; /* Mantido para desktop, será sobrescrito em mobile */
  position: sticky;
  left: 0;
  z-index: 7;
}
.tbl tbody td { height: 34px; }

.cat {
  min-width: 460px; /* Mantido para desktop, será sobrescrito em mobile */
  white-space: nowrap;
  position: sticky;
  left: 0;
  z-index: 4;
}
.txt { vertical-align: middle; font-size: 15px; }
.c { width: 48px; text-align: center; }

.pg-btn { border: none; background: transparent; padding: 0; cursor: pointer; }
.pg {
  display: inline-block; width: 16px; height: 10px; border-radius: 999px; vertical-align: middle;
}
.pg--planned { background: #3b82f6; }
.pg--done    { background: #22c55e; }
.pg--not     { background: #ef4444; }

.exec-menu {
  position: absolute; z-index: 9999; display: flex; flex-direction: column; gap: 4px;
  padding: 6px; border-radius: 8px; background: #ffffff; border: 1px solid #d1d5db;
  box-shadow: 0 8px 20px rgba(0,0,0,0.12);
}
.exec-menu button {
  border: 1px solid #d1d5db; background: #f8fafc; border-radius: 6px; padding: 5px 8px;
  font-size: 12px; cursor: pointer; text-align: left;
}
.exec-menu button:hover { background: #eef2f7; }

.tg {
  margin-right: 8px; border-radius: 6px; font-size: 12px; padding: 2px 6px; cursor: pointer;
}
.tg-placeholder { display: inline-block; width: 34px; }

.wrap.theme-dark {
  border: 1px solid rgba(148,163,184,.20);
  background: linear-gradient(180deg, rgba(17,24,39,.90), rgba(15,17,23,.90));
}
.wrap.theme-dark .tbl { color: #e6edf3; }
.wrap.theme-dark .tbl thead th {
  background: #141a24; color: #cbd5e1;
  border-bottom: 1px solid rgba(148,163,184,.20);
  border-right: 1px solid rgba(148,163,184,.20);
}
.wrap.theme-dark .tbl tbody td {
  border-right: 1px solid rgba(148,163,184,.20);
  border-bottom: 1px solid rgba(148,163,184,.20);
  background: #0b1220;
}
.wrap.theme-dark .tg {
  border: 1px solid rgba(148,163,184,.25);
  background: #0b1220;
  color: #d1d5db;
}
.wrap.theme-dark .exec-menu { background: #111827; border-color: #374151; }
.wrap.theme-dark .exec-menu button {
  background: #1f2937; color: #e5e7eb; border-color: #374151;
}

.wrap.theme-light { border: 1px solid #d1d5db; background: #ffffff; }
.wrap.theme-light .tbl { color: #111827; }

.wrap.theme-light .tbl thead th.cat-h {
  background: #c0c8d3; color: #0f172a;
  border-bottom: 1px solid #aeb8c5; border-right: 1px solid #b8c1cc;
}
.wrap.theme-light .tbl thead th:not(.cat-h) {
  color: #0f172a; border-bottom: 1px solid #b8c1cc; border-right: 1px solid #c2cad4;
}
.wrap.theme-light .tbl thead th:not(.cat-h):nth-child(even) { background: #d7dde6; }
.wrap.theme-light .tbl thead th:not(.cat-h):nth-child(odd) { background: #e3e8ef; }

.wrap.theme-light .tbl tbody td {
  border-right: 1px solid #e5e7eb; border-bottom: 1px solid #e5e7eb;
}
.wrap.theme-light .tbl tbody td:not(.cat) { background: #ffffff; }
.wrap.theme-light .tbl tbody td:nth-child(even):not(.cat) { background: #eceff3; }
.wrap.theme-light .tbl tbody td:nth-child(odd):not(.cat) { background: #f7f8fa; }

.wrap.theme-light .tbl tbody tr.lvl-1 td.cat { background: #e6edf7 !important; border-left: 4px solid #8aa4c7; font-weight: 700; }
.wrap.theme-light .tbl tbody tr.lvl-2 td.cat { background: #edf3fa !important; border-left: 4px solid #a8bdd8; font-weight: 600; }
.wrap.theme-light .tbl tbody tr.lvl-3 td.cat { background: #f3f7fc !important; border-left: 4px solid #c1d0e4; }
.wrap.theme-light .tbl tbody tr.lvl-4 td.cat { background: #f8fbff !important; border-left: 4px solid #d5dfec; }
.wrap.theme-light .tbl tbody tr.lvl-5 td.cat { background: #fbfdff !important; border-left: 4px solid #dfe7f2; }
.wrap.theme-light .tbl tbody tr.lvl-6 td.cat { background: #ffffff !important; border-left: 4px solid #e8edf5; }

.wrap.theme-light .tg {
  border: 1px solid #c7cdd6; background: #eef2f7; color: #111827;
}
.wrap.theme-light .tg:hover { background: #e5e7eb; }

/* Separador visual da coluna congelada */
.wrap.theme-light .tbl thead th.cat-h,
.wrap.theme-light .tbl tbody td.cat { box-shadow: 2px 0 0 #cfd6df; }

.wrap.theme-dark .tbl thead th.cat-h,
.wrap.theme-dark .tbl tbody td.cat { box-shadow: 2px 0 0 rgba(148,163,184,.35); }
</style>
</body>
</html>
    """

    return (
        template
        .replace("__THEME_CLASS__", theme_class)
        .replace("__HEADERS__", headers)
        .replace("__BODY__", body)
        .replace("__STATUS_FILTER__", status_filter_json)
        .replace("__TREE_CMD__", tree_cmd_json)
    )

# =========================
# Dados de Login
# =========================
CREDENTIALS = {
    "mauro freire": "126429",
    "pcm-matriz": "btz2026",
    "lubrificador 1": "btz2026",
    "lubrificador 2": "btz2026",
    "lubrificador 3": "btz2026",
    "lubrificador 4": "btz2026",
}

def check_credentials(username, password):
    """Verifica se o nome de usuário e a senha correspondem aos dados."""
    return CREDENTIALS.get(username.lower()) == password

def show_login_page():
    """Exibe a página de login."""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)

    # --- Adicionar a logo acima do card de login ---
    with st.container(): # Um container para a logo
        st.markdown('<div class="login-logo-wrapper">', unsafe_allow_html=True) # Novo wrapper para a logo
        logo_path = encontrar_logo()
        if logo_path:
            uri = logo_data_uri(logo_path)
            st.markdown(
                f"""
                <div class="logo-inner login-logo-inner">
                    <img src="{uri}" alt="BTZ Logo" />
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.warning("Logo não encontrada na mesma pasta do app.py.")
        st.markdown('</div>', unsafe_allow_html=True) # Fechar o wrapper da logo
    # --- Fim da adição da logo ---

    with st.container():
        st.markdown('<div class="login-card">', unsafe_allow_html=True)

        st.markdown("## Login")

        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")

        if st.button("Entrar"):
            if check_credentials(username, password):
                st.session_state["logged_in"] = True
                st.session_state["username"] = username # Armazena o nome de usuário original para exibição
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def show_main_app():
    """Exibe o aplicativo principal após o login."""
    # Adiciona a mensagem de boas-vindas no topo com contorno e botão de sair na frente
    if "username" in st.session_state:
        with st.container(border=True): # Contorno para a mensagem e o botão
            welcome_col, logout_col = st.columns([0.8, 0.2])
            with welcome_col:
                st.markdown(f"### Bem-vindo, {st.session_state['username']}!")
            with logout_col:
                # O botão de sair agora está na frente (direita) da mensagem
                if st.button("Sair", key="logout_button", use_container_width=True):
                    st.session_state["logged_in"] = False
                    del st.session_state["username"]
                    st.rerun()
        # REMOVIDO: st.markdown("---") # Linha separadora para organizar

    # =========================
    # Carregar arquivo local
    # =========================
    candidatos_excel = [
        "PLANO_DE_LUBRIFICAO_V2.xlsx",
        "PLANO DE LUBRIFICAÇÃO V2.xlsx",
        "PLANO_DE_LUBRIFICACAO_V2.xlsx",
        "PLANO DE LUBRIFICACAO V2.xlsx",
        "plano_lubrificacao.xlsx",
    ]

    arquivo_local = next((f for f in candidatos_excel if Path(f).exists()), None)

    if not arquivo_local:
        st.error("Arquivo Excel não encontrado na pasta do projeto. Coloque o arquivo .xlsx na mesma pasta do app.py.")
        st.stop()

    df_raw = pd.read_excel(arquivo_local)
    df = mapear_colunas(df_raw)


    # =========================
    # Topo (logo + filtros)
    # =========================
    # Usamos um ÚNICO container com borda para envolver as duas colunas
    with st.container(border=True): # A borda será aplicada aqui, envolvendo tudo
        # Adicionando um div com a classe 'main-header-container' para aplicar o CSS flexbox
        st.markdown('<div class="main-header-container">', unsafe_allow_html=True)
        col_logo, col_filtros = st.columns([1.15, 5.35], vertical_alignment="top")

        with col_logo:
            # Removido o st.container(border=True) individual aqui
            logo_path = encontrar_logo()
            if logo_path:
                uri = logo_data_uri(logo_path)
                st.markdown(
                    f"""
                    <div class="logo-inner">
                        <img src="{uri}" alt="BTZ Logo" />
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.warning("Logo não encontrada na mesma pasta do app.py.")

        with col_filtros:
            # Removido o st.container(border=True) individual aqui
            if "tree_cmd_seq" not in st.session_state:
                st.session_state["tree_cmd_seq"] = 0
            if "tree_cmd_action" not in st.session_state:
                st.session_state["tree_cmd_action"] = "none"

            # Título + botões na mesma linha
            # Em mobile, estas colunas se empilharão devido ao CSS @media
            t1, t2 = st.columns([1.2, 2.8], vertical_alignment="center")
            with t1:
                st.markdown("**Filtros**")
            with t2:
                # Em mobile, estes botões se empilharão devido ao CSS @media
                b1, b2, _ = st.columns([1.2, 1.2, 2.0], vertical_alignment="center")
                with b1:
                    if st.button("Expandir tudo", use_container_width=True, key="btn_expand_all"):
                        st.session_state["tree_cmd_seq"] += 1
                        st.session_state["tree_cmd_action"] = "expand_all"
                with b2:
                    if st.button("Recolher tudo", use_container_width=True, key="btn_collapse_all"):
                        st.session_state["tree_cmd_seq"] += 1
                        st.session_state["tree_cmd_action"] = "collapse_all"

            hoje = pd.Timestamp.today().normalize()
            inicio_padrao = hoje - pd.Timedelta(days=hoje.weekday())  # segunda-feira

            # Em mobile, estas colunas se empilharão devido ao CSS @media
            c0, c1, c2, c3 = st.columns([1.2, 1.5, 1.5, 2.2])

            with c0:
                inicio = pd.Timestamp(st.date_input("Início do calendário", value=inicio_padrao, key="inicio_cal"))

            filtro_cols = {"AREA": "Área", "FREQUENCIA": "Frequência"}

            for col in filtro_cols:
                key = f"f_{col}"
                if key not in st.session_state:
                    st.session_state[key] = []

            selecoes = {col: st.session_state[f"f_{col}"] for col in filtro_cols}

            with c1:
                col = "AREA"
                mask_outros = mask_por_filtros(df, selecoes, excluir_coluna=col)
                opcoes = sorted(df.loc[mask_outros, col].dropna().astype(str).unique().tolist())
                st.session_state[f"f_{col}"] = [v for v in st.session_state[f"f_{col}"] if v in opcoes]
                st.multiselect("Área", options=opcoes, key=f"f_{col}", placeholder="Selecione")
                selecoes[col] = st.session_state[f"f_{col}"]

            with c2:
                col = "FREQUENCIA"
                mask_outros = mask_por_filtros(df, selecoes, excluir_coluna=col)
                opcoes = sorted(df.loc[mask_outros, col].dropna().astype(str).unique().tolist())
                st.session_state[f"f_{col}"] = [v for v in st.session_state[f"f_{col}"] if v in opcoes]
                st.multiselect("Frequência", options=opcoes, key=f"f_{col}", placeholder="Selecione")
                selecoes[col] = st.session_state[f"f_{col}"]

            with c3:
                status_options = ["planned", "done", "not_done"]
                status_labels = {
                    "planned": "🔵 Programados",
                    "done": "🟢 Realizados",
                    "not_done": "🔴 Não Realizados",
                }

                if "status_segmentacao" not in st.session_state:
                    st.session_state["status_segmentacao"] = []

                status_selecionados = st.multiselect(
                    "Segmentação de Dados (Serviços)",
                    options=status_options,
                    key="status_segmentacao",
                    format_func=lambda x: status_labels.get(x, x),
                    placeholder="Selecione",
                )
        # Fechando o div 'main-header-container'
        st.markdown('</div>', unsafe_allow_html=True)


    mask_final = mask_por_filtros(df, selecoes)
    df_f = df[mask_final].copy()

    if df_f.empty:
        st.warning("Sem dados para os filtros selecionados.")
        st.stop()


    # =========================
    # Matriz
    # =========================
    rows = montar_matriz_hierarquica(df_f, inicio, qtd_semanas=52)

    if not rows:
        st.warning("Não foi possível montar a matriz hierárquica.")
        st.stop()

    tree_cmd = {
        "action": st.session_state.get("tree_cmd_action", "none"),
        "seq": st.session_state.get("tree_cmd_seq", 0),
    }

    tema = tema_atual_streamlit()
    html_matrix = render_matriz_html(
        rows,
        inicio=inicio,
        qtd_semanas=52,
        theme_base=tema,
        status_filter=status_selecionados,
        tree_cmd=tree_cmd,
    )
    # Ajustei a altura para ser um pouco menor em mobile, mas mantendo a rolagem
    components.html(html_matrix, height=600, scrolling=True)

    # limpa ação para não repetir automaticamente
    st.session_state["tree_cmd_action"] = "none"


    # =========================
    # Métricas
    # =========================
    # Adicionando um container para as métricas para poder escondê-las em mobile
    st.markdown('<div class="metrics-container">', unsafe_allow_html=True)
    n_areas = df_f["AREA"].nunique()
    n_eq = df_f["EQUIPAMENTO"].nunique()
    n_conj = df_f["CONJUNTO"].nunique()
    n_sub = df_f["SUBCONJUNTO"].nunique()
    n_ponto = df_f["PONTO"].nunique()
    n_serv = df_f["SERVICO"].nunique()

    # Em mobile, estas colunas se empilharão ou serão escondidas pelo CSS
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Áreas", n_areas)
    m2.metric("Equipamentos", n_eq)
    m3.metric("Conjuntos", n_conj)
    m4.metric("Subconjuntos", n_sub)
    m5.metric("Pontos", n_ponto)
    m6.metric("Serviços", n_serv)
    st.markdown('</div>', unsafe_allow_html=True) # Fechando o container das métricas

# =========================
# Lógica principal do aplicativo
# =========================
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if st.session_state["logged_in"]:
    show_main_app()
else:
    show_login_page()