# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client
import hashlib
import requests
import urllib.parse

# ---------- CONFIGURAÇÃO ----------
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
    "cancelado"
]

# ---------- CSS GLOBAL ----------
st.markdown("""
<style>

/* Remove header verde do Streamlit */
header[data-testid="stHeader"] {
    display: none;
}

/* Fundo geral */
.stApp {
    background-color:#263d33;
    color:#F5F5F5;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color:#243F37;
}

/* Layout */
.block-container {
    padding-top: 2rem;
}


/* Cards */
.card {
    background:#243F37;
    padding:20px;
    border-radius:16px;
    border:1px solid #3E665A;
    margin-bottom:16px;
}

/* Botões padrão */
.stButton > button {
    background-color:#C9A24D;
    color:#1F3B33;
    font-weight:600;
    border-radius:10px;
    border:none;
}

.stButton > button:hover {
    background-color:#B68C2E;
}

/* Botão IA animado */
button[key^="ia_"] {
    background:linear-gradient(135deg,#C9A24D,#B68C2E)!important;
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
def gerar_hash(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def verificar_senha(senha, senha_hash):
    return gerar_hash(senha) == senha_hash

def registrar_log(acao):
    try:
        supabase.table("logs").insert({
            "usuario": st.session_state.get("usuario"),
            "acao": acao,
            "data_hora": datetime.now().isoformat()
        }).execute()
    except:
        pass

def gerar_link_whatsapp(telefone, mensagem):
    telefone = "".join(filter(str.isdigit, telefone))
    texto = urllib.parse.quote(mensagem)
    return f"https://web.whatsapp.com/send?phone=55{telefone}&text={texto}"

def gerar_mensagem_ia(cliente):
    prompt = f"""
Cliente: {cliente['nome']}
Produto: {cliente.get('tipo_contrato')}
Banco: {cliente.get('banco')}
Status: {cliente.get('status')}
Observações: {cliente.get('observacoes')}

Gere uma mensagem profissional, curta e objetiva para WhatsApp.
"""
    payload = {
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "messages": [
            {"role": "system", "content": "Consultor financeiro especialista em WhatsApp"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.4,
        "max_tokens": 150
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    r = requests.post(GROQ_URL, json=payload, headers=headers, timeout=30)
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
    st.image(LOGO_URL, width=200)
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

    with st.form("form_add"):
        st.subheader("➕ Adicionar Cliente")
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome *")
            telefone = st.text_input("Telefone *")
            banco = st.text_input("Banco")
        with col2:
            tipo = st.selectbox("Tipo *", ["cartão","consignado","empréstimo","saque","benefício","crédito"])
            status = st.selectbox("Status *", STATUS_OPCOES)
            obs = st.text_area("Observações")
        if st.form_submit_button("Salvar", use_container_width=True):
            supabase.table("clientes").insert({
                "nome": nome,
                "telefone": telefone,
                "banco": banco,
                "tipo_contrato": tipo,
                "status": status,
                "observacoes": obs,
                "usuario": st.session_state["usuario"]
            }).execute()
            registrar_log(f"Cadastrou cliente {nome}")
            st.cache_data.clear()
            st.rerun()

    clientes = carregar_clientes(st.session_state["nivel"], st.session_state["usuario"])
    df = pd.DataFrame(clientes) if clientes else pd.DataFrame()

    for _, row in df.iterrows():
        st.markdown(f"""
        <div class="card">
            <b>👤 {row['nome']}</b><br>
            📞 {row['telefone']}<br>
            🏦 {row.get('banco','')}<br>
            📄 {row.get('tipo_contrato','')}<br>
            📌 {row.get('status','')}<br>
            📝 {row.get('observacoes','')}
        </div>
        """, unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        if c1.button("🤖 Gerar IA", key=f"ia_{row['id']}"):
            st.session_state[f"msg_{row['id']}"] = gerar_mensagem_ia(row)

        if c2.button("📲 WhatsApp", key=f"w_{row['id']}"):
            msg = st.session_state.get(f"msg_{row['id']}") or gerar_mensagem_ia(row)
            st.link_button("Abrir WhatsApp", gerar_link_whatsapp(row["telefone"], msg))

        if f"msg_{row['id']}" in st.session_state:
            st.text_area("Mensagem IA", st.session_state[f"msg_{row['id']}"], height=100)

# ---------- USUÁRIOS ----------
if menu == "Usuários":
    st.title("👤 Gestão de Usuários")
    st.dataframe(pd.DataFrame(carregar_usuarios()), use_container_width=True)

# ---------- LOGS ----------
if menu == "Logs":
    st.title("📜 Logs")
    st.dataframe(pd.DataFrame(carregar_logs()), use_container_width=True)


