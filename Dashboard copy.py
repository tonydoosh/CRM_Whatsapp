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

/* ===== Login (verde mais escuro + barra atrás da logo + float) ===== */
.login-wrap{
  max-width: 420px;
  margin: 7.5vh auto 0 auto;
}
.login-box{
  background:#182a24;              /* verde mais escuro (contraste) */
  border:1px solid #3d5e52;
  border-radius:22px;
  padding:22px 22px 20px 22px;
  box-shadow:0 18px 44px rgba(0,0,0,.35);
}
.login-hero{
  position:relative;
  display:flex;
  justify-content:center;
  align-items:center;
  padding-top: 14px;
  margin-bottom: 10px;
}
.login-bar{
  position:absolute;
  top: 6px;
  width: 92%;
  height: 34px;                    /* proporção “barra” */
  border-radius: 999px;
  background:#1f332c;              /* tom por trás */
  border:1px solid #3d5e52;
  z-index:0;
  animation: floaty 4.2s ease-in-out infinite;
}
.login-logo{
  position:relative;
  z-index:2;
  width: 210px;
  border-radius: 14px;
  border:1px solid #3d5e52;
  background:#1f332c;
  animation: floaty 4.2s ease-in-out infinite;
  animation-delay: .18s;
}
@keyframes floaty{
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-7px); }
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

/* Inputs */
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

/* Botões */
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

def gerar_mensagem_ia(c: dict) -> str:
    payload = {
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "messages": [
            {"role": "system", "content": "Consultor financeiro especialista"},
            {"role": "user", "content": f"""
Cliente:{c.get('nome')}
Produto:{c.get('tipo_contrato')}
Banco:{c.get('banco')}
Status:{c.get('status')}
Obs:{c.get('observacoes')}
Gere mensagem curta para WhatsApp."""}
        ],
        "temperature": 0.4,
        "max_tokens": 120
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

# ================= LOGIN (barra atrás da logo + float) =================
def login():
    st.markdown('<div class="login-wrap"><div class="login-box">', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="login-hero">
          <div class="login-bar"></div>
          <img class="login-logo" src="{LOGO_URL}">
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

    clientes = carregar_clientes(st.session_state.get("nivel"), st.session_state.get("usuario"))
    cols = st.columns(2)

    for i, c in enumerate(clientes):
        with cols[i % 2]:
            st.markdown(f"""
            <div class="card">
              <h4>{c.get('nome','')}</h4>
              <div class="badge">{c.get('status','')}</div>
              📞 {c.get('telefone','')}<br>
              🏦 {c.get('banco','')}<br>
              📄 {c.get('tipo_contrato','')}
            </div>
            """, unsafe_allow_html=True)

            b1, b2, b3 = st.columns(3)

            if b1.button("🤖 Gerar IA", key=f"ia_{c['id']}"):
                st.session_state[f"msg_{c['id']}"] = gerar_mensagem_ia(c)

            if b2.button("✏️ Editar", key=f"edit_{c['id']}"):
                st.session_state["edit_id"] = c["id"]

            if b3.button("📲 WhatsApp", key=f"w_{c['id']}"):
                msg = st.session_state.get(f"msg_{c['id']}") or gerar_mensagem_ia(c)
                st.link_button("Abrir WhatsApp", gerar_link_whatsapp(c.get("telefone", ""), msg), use_container_width=True)

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
                st.text_area("Mensagem IA", st.session_state[f"msg_{c['id']}"], height=90)

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


