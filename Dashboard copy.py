# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client
import hashlib
import requests
import urllib.parse

# ---------- CONFIG ----------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
GROQ_API_KEY = st.secrets["api_key"]

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
    "cancelado"
]

# ---------- CSS GLOBAL ----------
st.markdown("""
<style>

body, .stApp {
    background-color: #263d33;
}

/* LOGIN */

/* CARDS */
.card {
    background:#1f332b;
    padding:20px;
    border-radius:16px;
    border:1px solid #3e665a;
    margin-bottom:20px;
}

/* NÃO esconder botões */
.stButton > button,
.stForm button {
    background:#c9a24d !important;
    color:#263d33 !important;
    border-radius:10px;
    font-weight:700;
}

/* Botão IA animado */
button[key^="ia_"] {
    background: linear-gradient(135deg,#c9a24d,#b68c2e)!important;
    animation:pulse 2s infinite;
}

@keyframes pulse {
    0% { box-shadow:0 0 0 0 rgba(201,162,77,.6); }
    70% { box-shadow:0 0 0 12px rgba(201,162,77,0); }
    100% { box-shadow:0 0 0 0 rgba(201,162,77,0); }
}

</style>
""", unsafe_allow_html=True)

# ---------- FUNÇÕES ----------
def gerar_hash(s):
    return hashlib.sha256(s.encode()).hexdigest()

def verificar_senha(s, h):
    return gerar_hash(s) == h

def registrar_log(acao):
    try:
        supabase.table("logs").insert({
            "usuario": st.session_state.get("usuario"),
            "acao": acao,
            "data_hora": datetime.now().isoformat()
        }).execute()
    except:
        pass

def gerar_link_whatsapp(tel, msg):
    tel = "".join(filter(str.isdigit, tel))
    return f"https://web.whatsapp.com/send?phone=55{tel}&text={urllib.parse.quote(msg)}"

def gerar_mensagem_ia(cliente):
    payload = {
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "messages": [
            {"role": "system", "content": "Consultor financeiro especialista em WhatsApp"},
            {"role": "user", "content": f"""
Cliente: {cliente['nome']}
Produto: {cliente.get('tipo_contrato')}
Banco: {cliente.get('banco')}
Status: {cliente.get('status')}
Observações: {cliente.get('observacoes')}
Gere uma mensagem curta e profissional.
"""}
        ],
        "temperature": 0.4,
        "max_tokens": 150
    }
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        json=payload,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"}
    )
    return r.json()["choices"][0]["message"]["content"]

@st.cache_data(ttl=86400)
def carregar_clientes(nivel, usuario):
    if nivel == "admin":
        return supabase.table("clientes").select("*").execute().data
    return supabase.table("clientes").select("*").eq("usuario", usuario).execute().data

@st.cache_data(ttl=86400)
def carregar_usuarios():
    return supabase.table("usuarios").select("*").execute().data

@st.cache_data(ttl=86400)
def carregar_logs():
    return supabase.table("logs").select("*").order("id", desc=True).limit(100).execute().data

# ---------- LOGIN ----------
def login():
    st.markdown('<div class="login-box">', unsafe_allow_html=True)

    st.markdown(f"""
    <div style="display:flex;justify-content:center;margin-bottom:25px;">
        <img src="{LOGO_URL}" width="220">
    </div>
    """, unsafe_allow_html=True)

    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("🔐 Entrar", use_container_width=True):
        res = supabase.table("usuarios").select("*").eq("usuario", usuario).execute().data
        if not res or not verificar_senha(senha, res[0]["senha"]) or not res[0]["ativo"]:
            st.error("Usuário ou senha inválidos")
        else:
            st.session_state.update({
                "logado": True,
                "usuario": usuario,
                "nivel": res[0]["nivel"]
            })
            registrar_log("Login")
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ---------- SESSÃO ----------
if "logado" not in st.session_state:
    st.session_state["logado"] = False

if not st.session_state["logado"]:
    login()
    st.stop()

# ---------- SIDEBAR ----------
st.sidebar.image(LOGO_URL, use_container_width=True)
st.sidebar.markdown("---")

if st.sidebar.button("🚪 Sair", use_container_width=True):
    registrar_log("Logout")
    st.session_state.clear()
    st.cache_data.clear()
    st.rerun()

menu = st.sidebar.radio(
    "Menu",
    ["CRM", "Usuários", "Logs"] if st.session_state["nivel"] == "admin" else ["CRM"]
)

# ---------- CRM ----------
if menu == "CRM":
    st.title("📲 CRM de Clientes – WhatsApp")

    with st.form("add_cliente"):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome *")
        telefone = col1.text_input("Telefone *")
        banco = col1.text_input("Banco")
        tipo = col2.selectbox("Tipo", ["cartão","consignado","empréstimo","saque","benefício","crédito"])
        status = col2.selectbox("Status", STATUS_OPCOES)
        obs = st.text_area("Observações")

        if st.form_submit_button("➕ Adicionar Cliente", use_container_width=True):
            supabase.table("clientes").insert({
                "nome": nome,
                "telefone": telefone,
                "banco": banco,
                "tipo_contrato": tipo,
                "status": status,
                "observacoes": obs,
                "usuario": st.session_state["usuario"]
            }).execute()
            registrar_log(f"Adicionou cliente {nome}")
            st.cache_data.clear()
            st.rerun()

    for c in carregar_clientes(st.session_state["nivel"], st.session_state["usuario"]):
        st.markdown(f"""
        <div class="card">
        <b>{c['nome']}</b><br>
        📞 {c['telefone']}<br>
        🏦 {c.get('banco','')}<br>
        📄 {c.get('tipo_contrato','')}<br>
        📌 {c.get('status','')}
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)

        if col1.button("💾 Atualizar", key=f"up_{c['id']}"):
            registrar_log(f"Atualizou cliente {c['nome']}")
            st.success("Atualizado")

        if col2.button("🤖 Gerar IA", key=f"ia_{c['id']}"):
            st.session_state[f"msg_{c['id']}"] = gerar_mensagem_ia(c)

        if col3.button("📲 WhatsApp", key=f"w_{c['id']}"):
            msg = st.session_state.get(f"msg_{c['id']}") or gerar_mensagem_ia(c)
            st.link_button("Abrir WhatsApp", gerar_link_whatsapp(c["telefone"], msg))

        if f"msg_{c['id']}" in st.session_state:
            st.text_area("Mensagem IA", st.session_state[f"msg_{c['id']}"], height=100)

# ---------- USUÁRIOS ----------
if menu == "Usuários":
    st.title("👤 Usuários")
    for u in carregar_usuarios():
        st.write(f"{u['usuario']} | {u['nivel']} | {'Ativo' if u['ativo'] else 'Inativo'}")

# ---------- LOGS ----------
if menu == "Logs":
    st.title("📜 Logs")
    st.dataframe(pd.DataFrame(carregar_logs()), use_container_width=True)

