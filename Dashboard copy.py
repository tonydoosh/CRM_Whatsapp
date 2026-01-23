# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client
import hashlib
import requests
import urllib.parse

# ================= CONFIG =================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
GROQ_API_KEY = st.secrets["api_key"]
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
LOGO_URL = "https://github.com/tonydoosh/CRM_Whatsapp/blob/main/logo.jpeg?raw=true"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
st.set_page_config(page_title="CRM WhatsApp", layout="wide")

STATUS_OPCOES = [
    "em análise",
    "solicitar fatura",
    "boleto de quitação",
    "aguardando averbação",
    "aguardando liquidação",
    "fechado",
    "cancelado",
]

# ================= CSS (LEVE) =================
st.markdown("""
<style>
/* ===== Base ===== */
.stApp { background:#263d33; color:#eaf2ef; }
section[data-testid="stSidebar"]{
  background:#1b2e28;
  border-right:1px solid #3d5e52;
}

/* ===== Cards ===== */
.card{
  background:#1f332c;
  border:1px solid #3d5e52;
  border-radius:16px;
  padding:16px;
  margin-bottom:14px;
  box-shadow:0 10px 24px rgba(0,0,0,.15);
}
.card h4{ color:#d4b15c; margin:0 0 6px 0; }

.badge{
  display:inline-block;
  padding:4px 10px;
  border-radius:999px;
  font-size:12px;
  font-weight:800;
  background:#3d5e52;
  color:#eaf2ef;
  margin:6px 0 10px 0;
}

/* ===== Resumo topo ===== */
.kpi{
  background:#1f332c;
  border:1px solid #3d5e52;
  border-radius:18px;
  padding:14px 14px;
  box-shadow:0 10px 24px rgba(0,0,0,.12);
}
.kpi .kpi-title{
  color:#bfd1ca;
  font-weight:800;
  font-size:.88rem;
  margin:0 0 4px 0;
}
.kpi .kpi-value{
  color:#eaf2ef;
  font-weight:900;
  font-size:1.55rem;
  margin:0;
}
.kpi .kpi-sub{
  color:#bfd1ca;
  font-size:.80rem;
  margin:6px 0 0 0;
  opacity:.9;
}

/* ===== Botão IA ===== */
button[key^="ia_"]{
  background:linear-gradient(135deg,#d4b15c,#b18b3b) !important;
  color:#263d33 !important;
  font-weight:800 !important;
  animation:pulse 2s infinite;
}
@keyframes pulse{
  0%{box-shadow:0 0 0 0 rgba(212,177,92,.55);}
  70%{box-shadow:0 0 0 10px rgba(212,177,92,0);}
  100%{box-shadow:0 0 0 0 rgba(212,177,92,0);}
}

/* ===== Login (barras centralizadas atrás da logo + float) ===== */
.login-wrap{
  max-width: 420px;
  margin: 7.2vh auto 0 auto;
}
.login-box{
  background:#182a24;
  border:1px solid #3d5e52;
  border-radius:22px;
  padding:24px 22px 20px 22px;
  box-shadow:0 18px 44px rgba(0,0,0,.35);
}

/* Container só do “hero” (SEM retângulo grande) */
.login-hero{
  position:relative;
  display:flex;
  justify-content:center;
  align-items:center;
  padding: 18px 0 10px 0;
  margin-bottom: 8px;
}

/* Wrapper para logo + barras (centralizado) */
.hero-center{
  position:relative;
  width: 260px;
  height: 140px;
  display:flex;
  align-items:center;
  justify-content:center;
}

/* barras individuais (pílulas) atrás da logo */
.hero-pill{
  position:absolute;
  left:50%;
  transform: translateX(-50%);
  height: 30px;
  border-radius:999px;
  background: rgba(31,51,44,.92);
  border: 1px solid rgba(61,94,82,.85);
  z-index:0;
  opacity: .95;
}

/* variações de largura/posição */
.hero-pill.p1{ top: 6px;   width: 240px; opacity:.55; }
.hero-pill.p2{ top: 30px;  width: 300px; opacity:.18; }
.hero-pill.p3{ top: 54px;  width: 260px; opacity:.30; }
.hero-pill.p4{ top: 78px;  width: 320px; opacity:.12; }
.hero-pill.p5{ top: 102px; width: 220px; opacity:.22; }

/* leve brilho dourado */
.hero-glow{
  position:absolute;
  inset:-30px -60px -30px -60px;
  border-radius:999px;
  background: radial-gradient(circle at 50% 45%, rgba(212,177,92,.14), rgba(212,177,92,0) 65%);
  z-index:0;
  opacity:.55;
}

/* animação float */
@keyframes floaty{
  0%,100% { transform: translateY(0px); }
  50%     { transform: translateY(-6px); }
}
.float-group{
  animation: floaty 4.8s ease-in-out infinite;
}

/* logo por cima das barras */
.login-logo{
  position:relative;
  z-index:2;
  width: 210px;
  border-radius: 16px;
  border:1px solid #3d5e52;
  background:#1f332c;
}

/* inputs */
[data-baseweb="input"] > div{
  background:#1f332c !important;
  border:1px solid #3d5e52 !important;
  border-radius:14px !important;
}
input{ color:#eaf2ef !important; }
label{
  color:#bfd1ca !important;
  font-weight:700 !important;
}

/* botões */
.stButton > button{
  background:linear-gradient(135deg,#d4b15c,#b18b3b) !important;
  color:#263d33 !important;
  font-weight:900 !important;
  border:0 !important;
  border-radius:14px !important;
  padding:.62rem 1rem !important;
  transition: transform .12s ease, filter .12s ease;
}
.stButton > button:hover{
  filter: brightness(1.06);
  transform: translateY(-1px);
}
.stButton > button:active{
  transform: translateY(0px);
  filter: brightness(1.02);
}

.login-title{
  text-align:center;
  color:#d4b15c;
  font-weight:900;
  font-size: 1.10rem;
  margin: 6px 0 6px 0;
}
.login-sub{
  text-align:center;
  color:#bfd1ca;
  font-weight:600;
  font-size:.92rem;
  margin: 0 0 14px 0;
}
.login-hint{
  text-align:center;
  color:#bfd1ca;
  font-size:.86rem;
  margin-top: 10px;
  opacity: .92;
}
</style>
""", unsafe_allow_html=True)

# ================= FUNÇÕES =================
def gerar_hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def verificar_senha(s: str, h: str) -> bool:
    return gerar_hash(s) == h

def registrar_log(a: str):
    try:
        supabase.table("logs").insert({
            "usuario": st.session_state.get("usuario"),
            "acao": a,
            "data_hora": datetime.now().isoformat()
        }).execute()
    except Exception:
        pass

def gerar_link_whatsapp(t: str, m: str) -> str:
    t = "".join(filter(str.isdigit, t))
    return f"https://web.whatsapp.com/send?phone=55{t}&text={urllib.parse.quote(m)}"

def prompt_contextual(c: dict) -> str:
    status = (c.get("status") or "").lower().strip()
    nome = c.get("nome", "")
    banco = c.get("banco", "")
    tipo = c.get("tipo_contrato", "")
    obs = c.get("observacoes", "")

    # Direcionamento por status (sem prometer nada irreal)
    mapa = {
        "em análise": "Objetivo: confirmar dados e interesse, manter a conversa leve e avançar para o próximo passo.",
        "solicitar fatura": "Objetivo: pedir a fatura/documentos necessários de forma simples e objetiva para agilizar a simulação.",
        "boleto de quitação": "Objetivo: reforçar urgência e próximos passos para emitir/validar boleto de quitação com clareza.",
        "aguardando averbação": "Objetivo: tranquilizar, explicar que está em andamento e alinhar prazos sem promessas.",
        "aguardando liquidação": "Objetivo: alinhar expectativa de liberação e confirmar dados finais, mantendo confiança.",
        "fechado": "Objetivo: parabenizar, confirmar que está encaminhado e deixar portas abertas para suporte.",
        "cancelado": "Objetivo: reabrir conversa de forma respeitosa e oferecer ajuda caso queira retomar no futuro."
    }

    direcao = mapa.get(status, "Objetivo: criar uma mensagem clara e persuasiva, adequada ao contexto do cliente.")

    return f"""
Você é um consultor financeiro especialista em atendimento via WhatsApp.
Gere UMA mensagem curta, humana, persuasiva e diplomática, sem ser grosseiro e sem prometer resultados.

{direcao}

Regras:
- Texto em PT-BR
- No máximo 6 linhas
- Pode usar 1 ou 2 emojis no máximo
- Termine com uma pergunta de avanço (CTA)
- Se faltar informação, peça de forma simples

Dados do cliente:
Nome: {nome}
Banco: {banco}
Produto: {tipo}
Status atual: {status}
Observações: {obs}
""".strip()

def gerar_mensagem_ia(c: dict) -> str:
    payload = {
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "messages": [
            {"role": "system", "content": "Consultor financeiro especialista"},
            {"role": "user", "content": prompt_contextual(c)}
        ],
        "temperature": 0.35,
        "max_tokens": 140
    }
    r = requests.post(
        GROQ_URL,
        json=payload,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        timeout=30
    )
    try:
        data = r.json()
        return data["choices"][0]["message"]["content"]
    except Exception:
        return "⚠️ Erro ao gerar mensagem IA."

def excluir_cliente(cliente_id):
    supabase.table("clientes").delete().eq("id", cliente_id).execute()

@st.cache_data(ttl=86400)
def carregar_clientes(n: str, u: str):
    if n == "admin":
        return supabase.table("clientes").select("*").execute().data
    return supabase.table("clientes").select("*").eq("usuario", u).execute().data

@st.cache_data(ttl=86400)
def carregar_usuarios():
    return supabase.table("usuarios").select("*").execute().data

@st.cache_data(ttl=86400)
def carregar_logs():
    return supabase.table("logs").select("*").order("id", desc=True).limit(200).execute().data

# ================= LOGIN =================
def login():
    st.markdown('<div class="login-wrap"><div class="login-box">', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="login-hero">
          <div class="hero-center float-group">
            <div class="hero-glow"></div>
            <div class="hero-pill p1"></div>
            <div class="hero-pill p2"></div>
            <div class="hero-pill p3"></div>
            <div class="hero-pill p4"></div>
            <div class="hero-pill p5"></div>
            <img class="login-logo" src="{LOGO_URL}">
          </div>
        </div>
        <div class="login-title">Acesso ao CRM</div>
        <div class="login-sub">Entre com seu usuário e senha para continuar</div>
        """,
        unsafe_allow_html=True
    )

    u = st.text_input("Usuário", placeholder="Ex: operador1")
    s = st.text_input("Senha", type="password", placeholder="Digite sua senha")

    if st.button("🔐 Entrar", use_container_width=True):
        r = supabase.table("usuarios").select("*").eq("usuario", u).execute().data
        if not r or not verificar_senha(s, r[0]["senha"]) or not r[0]["ativo"]:
            st.error("Credenciais inválidas")
        else:
            st.session_state.update({"logado": True, "usuario": u, "nivel": r[0]["nivel"]})
            registrar_log("Login")
            st.rerun()

    st.markdown('<div class="login-hint">🔒 Acesso restrito • Se estiver bloqueado, fale com o administrador</div>', unsafe_allow_html=True)
    st.markdown("</div></div>", unsafe_allow_html=True)

# ================= SESSÃO =================
if "logado" not in st.session_state:
    st.session_state["logado"] = False

if "confirm_delete_id" not in st.session_state:
    st.session_state.confirm_delete_id = None

# filtros/pesquisa/ordenação
if "f_status" not in st.session_state:
    st.session_state.f_status = "Todos"
if "f_banco" not in st.session_state:
    st.session_state.f_banco = "Todos"
if "f_tipo" not in st.session_state:
    st.session_state.f_tipo = "Todos"
if "f_order" not in st.session_state:
    st.session_state.f_order = "Mais recente"
if "search_raw" not in st.session_state:
    st.session_state.search_raw = ""

# modal excluir
if "delete_cliente" not in st.session_state:
    st.session_state.delete_cliente = None

if not st.session_state.get("logado"):
    login()
    st.stop()

# ================= SIDEBAR =================
st.sidebar.image(LOGO_URL, use_container_width=True)
st.sidebar.markdown("---")
menu = st.sidebar.radio(
    "Menu",
    ["CRM", "Usuários", "Logs"] if st.session_state.get("nivel") == "admin" else ["CRM"]
)
if st.sidebar.button("🚪 Sair", use_container_width=True):
    registrar_log("Logout")
    st.session_state.clear()
    st.cache_data.clear()
    st.rerun()

# ================= CRM =================
if menu == "CRM":
    st.title("📲 CRM de Clientes")

    with st.form("add_cliente"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome*")
        tel = c1.text_input("Telefone*")
        banco = c1.text_input("Banco")
        tipo = c2.selectbox("Tipo*", ["cartão", "consignado", "empréstimo", "saque", "benefício", "crédito"])
        status = c2.selectbox("Status*", STATUS_OPCOES)
        obs = st.text_area("Observações")
        if st.form_submit_button("💾 Adicionar cliente", use_container_width=True):
            supabase.table("clientes").insert({
                "nome": nome,
                "telefone": tel,
                "banco": banco,
                "tipo_contrato": tipo,
                "status": status,
                "observacoes": obs,
                "usuario": st.session_state.get("usuario")
            }).execute()
            registrar_log(f"Novo cliente {nome}")
            st.cache_data.clear()
            st.rerun()

    st.divider()

    clientes = carregar_clientes(st.session_state.get("nivel"), st.session_state.get("usuario")) or []

    # ====== RESUMOS NO TOPO (KPIs) ======
    total = len(clientes)
    cont_status = {s: 0 for s in STATUS_OPCOES}
    for c in clientes:
        stt = c.get("status")
        if stt in cont_status:
            cont_status[stt] += 1

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f"""
        <div class="kpi">
          <div class="kpi-title">Total</div>
          <div class="kpi-value">{total}</div>
          <div class="kpi-sub">clientes na base</div>
        </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
        <div class="kpi">
          <div class="kpi-title">Em análise</div>
          <div class="kpi-value">{cont_status.get("em análise",0)}</div>
          <div class="kpi-sub">primeiro contato</div>
        </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
        <div class="kpi">
          <div class="kpi-title">Aguardando</div>
          <div class="kpi-value">{cont_status.get("aguardando averbação",0) + cont_status.get("aguardando liquidação",0)}</div>
          <div class="kpi-sub">andamento</div>
        </div>
        """, unsafe_allow_html=True)
    with k4:
        st.markdown(f"""
        <div class="kpi">
          <div class="kpi-title">Fechados</div>
          <div class="kpi-value">{cont_status.get("fechado",0)}</div>
          <div class="kpi-sub">concluídos</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # ====== FILTROS + BUSCA + ORDENAÇÃO ======
    bancos_unicos = sorted({(c.get("banco") or "").strip() for c in clientes if (c.get("banco") or "").strip()})
    tipos_unicos = sorted({(c.get("tipo_contrato") or "").strip() for c in clientes if (c.get("tipo_contrato") or "").strip()})

    with st.container():
        f1, f2, f3, f4, f5 = st.columns([2.2, 1.2, 1.2, 1.2, 1.2])

        with f1:
            st.text_input("🔎 Buscar (nome/telefone)", key="search_raw", placeholder="Ex: Ana / 98412...")

        with f2:
            st.selectbox("Status", ["Todos"] + STATUS_OPCOES, key="f_status")

        with f3:
            st.selectbox("Banco", ["Todos"] + bancos_unicos, key="f_banco")

        with f4:
            st.selectbox("Tipo", ["Todos"] + tipos_unicos, key="f_tipo")

        with f5:
            st.selectbox("Ordenar", ["Mais recente", "Status", "Nome"], key="f_order")

        c_limpar1, c_limpar2 = st.columns([1, 6])
        with c_limpar1:
            if st.button("🧹 Limpar", use_container_width=True):
                st.session_state.f_status = "Todos"
                st.session_state.f_banco = "Todos"
                st.session_state.f_tipo = "Todos"
                st.session_state.f_order = "Mais recente"
                st.session_state.search_raw = ""
                st.rerun()

    # ====== APLICA FILTROS ======
    q = (st.session_state.search_raw or "").strip().lower()

    def _match_busca(c: dict) -> bool:
        if not q:
            return True
        nome_ = (c.get("nome") or "").lower()
        tel_ = "".join(filter(str.isdigit, (c.get("telefone") or "")))
        q_digits = "".join(filter(str.isdigit, q))
        ok_nome = q in nome_
        ok_tel = (q_digits in tel_) if q_digits else False
        return ok_nome or ok_tel

    filtrados = []
    for c in clientes:
        if st.session_state.f_status != "Todos" and (c.get("status") or "") != st.session_state.f_status:
            continue
        if st.session_state.f_banco != "Todos" and (c.get("banco") or "") != st.session_state.f_banco:
            continue
        if st.session_state.f_tipo != "Todos" and (c.get("tipo_contrato") or "") != st.session_state.f_tipo:
            continue
        if not _match_busca(c):
            continue
        filtrados.append(c)

    # ====== ORDENAÇÃO ======
    status_rank = {s: i for i, s in enumerate(STATUS_OPCOES)}

    def _key_recente(c: dict):
        for k in ("created_at", "data_cadastro", "created", "dt_cadastro"):
            v = c.get(k)
            if v:
                return str(v)
        return str(c.get("id", ""))

    if st.session_state.f_order == "Nome":
        filtrados.sort(key=lambda x: (x.get("nome") or "").lower())
    elif st.session_state.f_order == "Status":
        filtrados.sort(key=lambda x: (status_rank.get(x.get("status"), 999), (x.get("nome") or "").lower()))
    else:
        filtrados.sort(key=_key_recente, reverse=True)

    # ====== MODAL EXCLUIR ======
    def abrir_modal_excluir(c: dict):
        st.session_state.delete_cliente = {
            "id": c.get("id"),
            "nome": c.get("nome", ""),
            "telefone": c.get("telefone", "")
        }

    if hasattr(st, "dialog"):
        @st.dialog("🗑️ Excluir cliente")
        def modal_excluir():
            cdel = st.session_state.get("delete_cliente") or {}
            st.markdown("### Confirmar exclusão")
            st.write("Você está prestes a excluir este cliente. Essa ação não pode ser desfeita.")
            st.markdown(f"**Cliente:** {cdel.get('nome','')}")
            st.markdown(f"**Telefone:** {cdel.get('telefone','')}")

            a1, a2 = st.columns(2)
            with a1:
                if st.button("✅ Excluir agora", use_container_width=True):
                    excluir_cliente(cdel.get("id"))
                    registrar_log(f"Excluiu cliente {cdel.get('nome','')}")
                    st.session_state.delete_cliente = None
                    st.cache_data.clear()
                    st.rerun()
            with a2:
                if st.button("❌ Cancelar", use_container_width=True):
                    st.session_state.delete_cliente = None
                    st.rerun()
    else:
        modal_excluir = None

    st.caption(f"📌 Exibindo **{len(filtrados)}** cliente(s) (após filtros)")

    st.divider()

    # ✅ 1 COLUNA
    cols = st.columns(1)

    for i, c in enumerate(filtrados):
        with cols[0]:
            st.markdown(f"""
            <div class="card">
              <h4>{c.get('nome','')}</h4>
              <div class="badge">{c.get('status','')}</div>
              📞 {c.get('telefone','')}<br>
              🏦 {c.get('banco','')}<br>
              📄 {c.get('tipo_contrato','')}
            </div>
            """, unsafe_allow_html=True)

            b1, b2, b3, b4 = st.columns(4)

            if b1.button("🤖 Gerar IA", key=f"ia_{c['id']}"):
                st.session_state[f"msg_{c['id']}"] = gerar_mensagem_ia(c)

            if b2.button("✏️ Editar", key=f"edit_{c['id']}"):
                st.session_state["edit_id"] = c["id"]

            if b3.button("📲 WhatsApp", key=f"w_{c['id']}"):
                msg = st.session_state.get(f"msg_{c['id']}") or gerar_mensagem_ia(c)
                st.link_button("Abrir WhatsApp", gerar_link_whatsapp(c.get("telefone", ""), msg), use_container_width=True)

            if b4.button("🗑️ Excluir", key=f"del_cliente_{c['id']}"):
                abrir_modal_excluir(c)
                if modal_excluir:
                    modal_excluir()
                else:
                    st.session_state.confirm_delete_id = c["id"]

            if (not hasattr(st, "dialog")) and st.session_state.confirm_delete_id == c["id"]:
                st.warning("Tem certeza que deseja excluir este cliente? Essa ação não pode ser desfeita.")
                d1, d2 = st.columns(2)
                if d1.button("✅ Confirmar exclusão", key=f"conf_del_cliente_{c['id']}", use_container_width=True):
                    excluir_cliente(c["id"])
                    registrar_log(f"Excluiu cliente {c.get('nome','')}")
                    st.session_state.confirm_delete_id = None
                    st.cache_data.clear()
                    st.rerun()
                if d2.button("❌ Cancelar", key=f"cancel_del_cliente_{c['id']}", use_container_width=True):
                    st.session_state.confirm_delete_id = None
                    st.rerun()

            if st.session_state.get("edit_id") == c["id"]:
                with st.form(f"edit_form_{c['id']}"):
                    st.markdown("**Editar cliente**")
                    banco_e = st.text_input("Banco", c.get("banco", ""))
                    tipo_e = st.text_input("Tipo", c.get("tipo_contrato", ""))
                    status_e = st.selectbox(
                        "Status",
                        STATUS_OPCOES,
                        index=STATUS_OPCOES.index(c.get("status")) if c.get("status") in STATUS_OPCOES else 0
                    )
                    obs_e = st.text_area("Observações", c.get("observacoes", ""))
                    if st.form_submit_button("💾 Atualizar", use_container_width=True):
                        supabase.table("clientes").update({
                            "banco": banco_e,
                            "tipo_contrato": tipo_e,
                            "status": status_e,
                            "observacoes": obs_e
                        }).eq("id", c["id"]).execute()
                        registrar_log(f"Atualizou cliente {c.get('nome', '')}")
                        st.session_state.pop("edit_id", None)
                        st.cache_data.clear()
                        st.rerun()

            if f"msg_{c['id']}" in st.session_state:
                st.text_area("Mensagem IA (contextual)", st.session_state[f"msg_{c['id']}"], height=90)

# ================= USUÁRIOS =================
if menu == "Usuários":
    st.title("👤 Operadores")

    with st.form("add_user"):
        u = st.text_input("Usuário")
        s = st.text_input("Senha", type="password")
        n = st.selectbox("Nível", ["operador", "admin"])
        ativo = st.selectbox("Ativo", [True, False], index=0)
        if st.form_submit_button("Adicionar", use_container_width=True):
            supabase.table("usuarios").insert({
                "usuario": u,
                "senha": gerar_hash(s),
                "nivel": n,
                "ativo": ativo
            }).execute()
            registrar_log(f"Criou usuário {u}")
            st.cache_data.clear()
            st.rerun()

    st.divider()

    for u in carregar_usuarios():
        with st.expander(f"{u.get('usuario','')} | {u.get('nivel','')} | {'Ativo' if u.get('ativo') else 'Inativo'}"):
            col1, col2, col3 = st.columns(3)

            with col1:
                usuario_e = st.text_input("Usuário", u.get("usuario", ""), key=f"user_{u['id']}")
                nivel_e = st.selectbox(
                    "Nível",
                    ["operador", "admin"],
                    index=0 if u.get("nivel") == "operador" else 1,
                    key=f"nivel_{u['id']}"
                )

            with col2:
                ativo_e = st.selectbox(
                    "Ativo",
                    [True, False],
                    index=0 if u.get("ativo") else 1,
                    key=f"ativo_{u['id']}"
                )
                nova_senha = st.text_input("Nova senha (opcional)", type="password", key=f"senha_{u['id']}")

            with col3:
                if st.button("💾 Salvar", key=f"save_{u['id']}", use_container_width=True):
                    d = {"usuario": usuario_e, "nivel": nivel_e, "ativo": ativo_e}
                    if nova_senha:
                        d["senha"] = gerar_hash(nova_senha)
                    supabase.table("usuarios").update(d).eq("id", u["id"]).execute()
                    registrar_log(f"Editou usuário {usuario_e}")
                    st.cache_data.clear()
                    st.rerun()

                if st.button("🗑️ Excluir", key=f"del_{u['id']}", use_container_width=True):
                    supabase.table("usuarios").delete().eq("id", u["id"]).execute()
                    registrar_log(f"Excluiu usuário {u.get('usuario','')}")
                    st.cache_data.clear()
                    st.rerun()

# ================= LOGS =================
if menu == "Logs":
    st.title("📜 Logs")
    logs = carregar_logs()
    if logs:
        st.dataframe(pd.DataFrame(logs), use_container_width=True)
    else:
        st.info("Nenhum log registrado")
