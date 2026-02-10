# app_clientes.py
# Streamlit + Supabase: Tabela/Operação de Clientes com visual "smooth" (clean/dark premium)
# Requisitos:
#   pip install streamlit supabase pandas
# Secrets (.streamlit/secrets.toml):
#   SUPABASE_URL="https://xxxx.supabase.co"
#   SUPABASE_KEY="sua_service_role_ou_anon"

import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client

# ===================== CONFIG =====================
st.set_page_config(page_title="Operação • Clientes", layout="wide")

SUPABASE_URL = st.secrets["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV1bnZyeGlmanh3bWh4b2t6bmJtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTA2OTQwMSwiZXhwIjoyMDg0NjQ1NDAxfQ.unLG1tk2WExgA3pqzXkOJpzAEtwLjdlwSLiJnShKJU0"]
SUPABASE_KEY = st.secrets["https://uunvrxifjxwmhxokznbm.supabase.co"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

STATUS_OPCOES = [
    "em análise",
    "solicitar fatura",
    "boleto de quitação",
    "aguardando averbação",
    "aguardando liquidação",
    "fechado",
    "cancelado",
]


# ===================== UI (SMOOTH) =====================
def inject_smooth_ui():
    st.markdown(
        """
    <style>
      /* Base */
      .stApp { background: #0b0f14; color: #e7eef7; }
      [data-testid="stHeader"] { background: transparent; }
      [data-testid="stSidebar"] { background: #070a0f; border-right: 1px solid rgba(255,255,255,.06); }
      .block-container { padding-top: 1.2rem; padding-bottom: 2.5rem; max-width: 1200px; }

      /* Typography */
      h1, h2, h3 { letter-spacing: -0.02em; }
      p, label, div { font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial; }

      /* Inputs */
      .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
        background: rgba(255,255,255,.04) !important;
        border: 1px solid rgba(255,255,255,.07) !important;
        border-radius: 14px !important;
      }
      .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: rgba(120,180,255,.35) !important;
        box-shadow: 0 0 0 3px rgba(120,180,255,.12) !important;
      }

      /* Buttons */
      .stButton button {
        border-radius: 14px !important;
        border: 1px solid rgba(255,255,255,.10) !important;
        background: rgba(255,255,255,.06) !important;
        transition: transform .06s ease, background .15s ease, border .15s ease;
      }
      .stButton button:hover { background: rgba(255,255,255,.10) !important; border-color: rgba(255,255,255,.18) !important; }
      .stButton button:active { transform: scale(0.98); }

      /* Cards */
      .smooth-card {
        background: linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.03));
        border: 1px solid rgba(255,255,255,.08);
        border-radius: 18px;
        padding: 16px 16px 14px 16px;
        box-shadow: 0 10px 30px rgba(0,0,0,.35);
      }
      .smooth-muted { color: rgba(231,238,247,.72); font-size: 13px; }
      .smooth-title { font-size: 18px; font-weight: 650; margin: 0; }
      .smooth-badge {
        display:inline-block; padding: 4px 10px; border-radius: 999px;
        background: rgba(120,180,255,.14);
        border: 1px solid rgba(120,180,255,.22);
        font-size: 12px; color: rgba(231,238,247,.9);
      }
      .smooth-row { display:flex; gap:10px; flex-wrap:wrap; align-items:center; }

      /* Dataframe */
      [data-testid="stDataFrame"] { border-radius: 16px; overflow: hidden; border: 1px solid rgba(255,255,255,.06); }
    </style>
    """,
        unsafe_allow_html=True,
    )


inject_smooth_ui()


# ===================== SUPABASE CRUD =====================
def listar_clientes(status=None, operador=None, busca=None, limit=48):
    q = (
        supabase.table("clientes")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
    )

    if status:
        q = q.eq("status", status)

    if operador:
        q = q.eq("operador", operador)

    if busca:
        # OR: nome / telefone / cpf
        b = busca.replace('"', "").strip()
        q = q.or_(f"nome.ilike.%{b}%,telefone.ilike.%{b}%,cpf.ilike.%{b}%")

    res = q.execute()
    return res.data or []


def criar_cliente(payload: dict):
    return supabase.table("clientes").insert(payload).execute()


def atualizar_cliente(cliente_id: str, payload: dict):
    return supabase.table("clientes").update(payload).eq("id", cliente_id).execute()


def deletar_cliente(cliente_id: str):
    return supabase.table("clientes").delete().eq("id", cliente_id).execute()


# ===================== COMPONENTES =====================
def status_badge_html(status: str):
    safe = status if status else "—"
    return f'<span class="smooth-badge">{safe}</span>'


def cliente_card(cliente: dict, on_update_status, on_mark_contact, on_delete):
    nome = cliente.get("nome", "Sem nome")
    status = cliente.get("status", "em análise")
    tel = cliente.get("telefone") or "-"
    cpf = cliente.get("cpf") or "-"
    operador = cliente.get("operador") or "—"
    prioridade = int(cliente.get("prioridade") or 3)

    st.markdown(
        f"""
      <div class="smooth-card">
        <div class="smooth-row" style="justify-content:space-between;">
          <div>
            <p class="smooth-title">{nome}</p>
            <p class="smooth-muted">CPF: {cpf} • Tel: {tel}</p>
          </div>
          <div>{status_badge_html(status)}</div>
        </div>
        <div class="smooth-row" style="margin-top:10px;">
          <span class="smooth-muted">Operador:</span><span>{operador}</span>
          <span class="smooth-muted" style="margin-left:10px;">Prioridade:</span><span>{prioridade}</span>
        </div>
      </div>
    """,
        unsafe_allow_html=True,
    )

    a1, a2, a3 = st.columns([2, 1, 1])
    with a1:
        novo_status = st.selectbox(
            "Status",
            STATUS_OPCOES,
            index=STATUS_OPCOES.index(status) if status in STATUS_OPCOES else 0,
            key=f"status_{cliente['id']}",
        )
    with a2:
        st.write("")
        if st.button("Salvar", key=f"save_{cliente['id']}"):
            on_update_status(cliente["id"], novo_status)

    with a3:
        st.write("")
        if st.button("Contato", key=f"contact_{cliente['id']}"):
            on_mark_contact(cliente["id"])

    b1, b2 = st.columns([2, 1])
    with b1:
        obs_nova = st.text_area(
            "Observações",
            value=cliente.get("observacoes") or "",
            key=f"obs_{cliente['id']}",
            height=80,
        )
        if st.button("Atualizar observações", key=f"obsbtn_{cliente['id']}"):
            on_update_status(cliente["id"], novo_status, obs_override=obs_nova)

    with b2:
        st.write("")
        st.write("")
        if st.button("Excluir", key=f"del_{cliente['id']}"):
            on_delete(cliente["id"])


def tela_clientes_smooth():
    st.markdown("## 📋 Clientes")
    st.markdown(
        "<p class='smooth-muted'>Operação em modo clean: filtros rápidos + cards com ações.</p>",
        unsafe_allow_html=True,
    )

    f1, f2, f3, f4 = st.columns([1.2, 1.2, 1.6, 1])
    with f1:
        filtro_status = st.selectbox("Status", ["Todos"] + STATUS_OPCOES, index=0)
    with f2:
        filtro_operador = st.text_input("Operador (exato)")
    with f3:
        busca = st.text_input("Buscar (nome/cpf/tel)")
    with f4:
        qtd = st.selectbox("Qtd", [24, 48, 96, 200], index=1)

    status_param = None if filtro_status == "Todos" else filtro_status
    operador_param = filtro_operador.strip() if filtro_operador.strip() else None
    busca_param = busca.strip() if busca.strip() else None

    clientes = listar_clientes(
        status=status_param,
        operador=operador_param,
        busca=busca_param,
        limit=int(qtd),
    )

    if not clientes:
        st.info("Nenhum cliente encontrado.")
        return

    def on_update_status(cliente_id, status_novo, obs_override=None):
        payload = {"status": status_novo}
        if obs_override is not None:
            payload["observacoes"] = obs_override.strip() if obs_override.strip() else None
        atualizar_cliente(cliente_id, payload)
        st.success("Atualizado.")
        st.rerun()

    def on_mark_contact(cliente_id):
        atualizar_cliente(cliente_id, {"last_contact_at": datetime.utcnow().isoformat()})
        st.success("Contato registrado.")
        st.rerun()

    def on_delete(cliente_id):
        deletar_cliente(cliente_id)
        st.warning("Cliente excluído.")
        st.rerun()

    # Grid
    cols = 3
    for i in range(0, len(clientes), cols):
        row = st.columns(cols, gap="large")
        for j in range(cols):
            idx = i + j
            if idx >= len(clientes):
                break
            with row[j]:
                cliente_card(clientes[idx], on_update_status, on_mark_contact, on_delete)


# ===================== CADASTRO (SMOOTH) =====================
def bloco_cadastro():
    st.markdown("## ➕ Cadastrar cliente")
    st.markdown(
        "<p class='smooth-muted'>Cadastro rápido pra alimentar o funil.</p>",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        nome = st.text_input("Nome *")
        cpf = st.text_input("CPF (opcional)")
    with c2:
        telefone = st.text_input("Telefone")
        email = st.text_input("Email")
    with c3:
        status = st.selectbox("Status inicial", STATUS_OPCOES, index=0)
        prioridade = st.selectbox("Prioridade", [1, 2, 3], index=2)

    d1, d2, d3 = st.columns([1.2, 1.2, 1.6])
    with d1:
        produto = st.text_input("Produto (ex: consignado)")
    with d2:
        origem = st.text_input("Origem (ex: anúncio/indicação)")
    with d3:
        operador = st.text_input("Operador responsável")

    obs = st.text_area("Observações", height=110)

    if st.button("Salvar cliente", type="primary"):
        if not nome.strip():
            st.error("Nome é obrigatório.")
            return

        payload = {
            "nome": nome.strip(),
            "cpf": cpf.strip() if cpf and cpf.strip() else None,
            "telefone": telefone.strip() if telefone and telefone.strip() else None,
            "email": email.strip() if email and email.strip() else None,
            "status": status,
            "produto": produto.strip() if produto and produto.strip() else None,
            "origem": origem.strip() if origem and origem.strip() else None,
            "operador": operador.strip() if operador and operador.strip() else None,
            "prioridade": int(prioridade),
            "observacoes": obs.strip() if obs and obs.strip() else None,
            "last_contact_at": None,
        }

        try:
            criar_cliente(payload)
            st.success("Cliente cadastrado!")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao cadastrar: {e}")


# ===================== HOME =====================
with st.sidebar:
    st.markdown("### ⚙️ Operação")
    pagina = st.radio("Navegação", ["Clientes", "Cadastrar", "Tabela (debug)"], index=0)
    st.markdown("<div class='smooth-muted'>Dica: use filtros por status e busca pra rodar a fila.</div>", unsafe_allow_html=True)

if pagina == "Cadastrar":
    bloco_cadastro()
elif pagina == "Tabela (debug)":
    st.markdown("## 🧾 Tabela (debug)")
    dados = listar_clientes(limit=200)
    df = pd.DataFrame(dados)
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    tela_clientes_smooth()
