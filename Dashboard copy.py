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
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(
    page_title="CRM WhatsApp",
    layout="wide",
    initial_sidebar_state="expanded"
)

STATUS_OPCOES = [
    "em análise",
    "solicitar fatura",
    "boleto de quitação",
    "aguardando averbação",
    "aguardando liquidação",
    "fechado",
    "cancelado"
]

# ---------- CSS ----------
st.markdown("""
<style>
body, .stApp { background-color:#263d33; color:#FFF; }

.card {
    background:#1f322b;
    padding:20px;
    border-radius:16px;
    border:1px solid #3e665a;
    margin-bottom:16px;
}

.card h4 { color:#c9a24d; }

button[kind="primary"] {
    background:linear-gradient(135deg,#c9a24d,#b68c2e)!important;
    color:#1f322b!important;
    font-weight:700;
}

button[key^="ia_"] {
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
            {"role":"system","content":"Consultor financeiro especialista em WhatsApp"},
            {"role":"user","content":f"""
Cliente: {cliente['nome']}
Produto: {cliente.get('tipo_contrato')}
Banco: {cliente.get('banco')}
Status: {cliente.get('status')}
Observações: {cliente.get('observacoes')}
"""}
        ],
        "temperature":0.4,
        "max_tokens":150
    }
    r = requests.post(GROQ_URL, json=payload, headers={
        "Authorization":f"Bearer {GROQ_API_KEY}",
        "Content-Type":"application/json"
    }, timeout=30)
    return r.json()["choices"][0]["message"]["content"]

@st.cache_data(ttl=86400)
def carregar_clientes(nivel, usuario):
    if nivel=="admin":
        return supabase.table("clientes").select("*").execute().data
    return supabase.table("clientes").select("*").eq("usuario",usuario).execute().data

@st.cache_data(ttl=86400)
def carregar_usuarios():
    return supabase.table("usuarios").select("*").execute().data

@st.cache_data(ttl=86400)
def carregar_logs():
    return supabase.table("logs").select("*").order("id",desc=True).limit(200).execute().data

# ---------- LOGIN ----------
def login():
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.image(
        "https://github.com/tonydoosh/CRM_Whatsapp/blob/main/logo.jpeg?raw=true",
        width=220
    )
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("🔐 Entrar", use_container_width=True):
        res = supabase.table("usuarios").select("*").eq("usuario",usuario).execute().data
        if not res or not verificar_senha(senha,res[0]["senha"]) or not res[0]["ativo"]:
            st.error("Usuário ou senha inválidos")
        else:
            st.session_state.update({
                "logado":True,
                "usuario":usuario,
                "nivel":res[0]["nivel"]
            })
            registrar_log("Login")
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ---------- SESSÃO ----------
if "logado" not in st.session_state:
    st.session_state["logado"]=False
if not st.session_state["logado"]:
    login()
    st.stop()

# ---------- SIDEBAR ----------
st.sidebar.image(
    "https://github.com/tonydoosh/CRM_Whatsapp/blob/main/logo.jpeg?raw=true",
    use_container_width=True
)
st.sidebar.markdown("---")

if st.sidebar.button("🚪 Sair", use_container_width=True):
    registrar_log("Logout")
    st.session_state.clear()
    st.cache_data.clear()
    st.rerun()

menu = st.sidebar.radio(
    "Menu",
    ["CRM","Usuários","Logs"] if st.session_state["nivel"]=="admin" else ["CRM"]
)

# ---------- CRM ----------
if menu=="CRM":
    st.title("📲 CRM de Clientes")

    clientes = carregar_clientes(
        st.session_state["nivel"],
        st.session_state["usuario"]
    )
    for c in clientes:
        st.markdown(f"""
        <div class="card">
        <h4>{c['nome']}</h4>
        📞 {c['telefone']}<br>
        🏦 {c.get('banco','')}<br>
        📄 {c.get('tipo_contrato','')}<br>
        📌 {c.get('status','')}
        </div>
        """, unsafe_allow_html=True)

        col1,col2,col3 = st.columns(3)
        if col1.button("💾 Atualizar", key=f"up_{c['id']}"):
            registrar_log(f"Atualizou cliente {c['nome']}")
        if col2.button("🧠 Gerar IA", key=f"ia_{c['id']}"):
            st.session_state[f"msg_{c['id']}"]=gerar_mensagem_ia(c)
        if col3.button("📲 WhatsApp", key=f"w_{c['id']}"):
            msg = st.session_state.get(f"msg_{c['id']}") or gerar_mensagem_ia(c)
            st.link_button("Abrir WhatsApp", gerar_link_whatsapp(c["telefone"],msg))

        if f"msg_{c['id']}" in st.session_state:
            st.text_area("Mensagem IA", st.session_state[f"msg_{c['id']}"], height=100)

# ---------- USUÁRIOS ----------
if menu=="Usuários":
    st.title("👤 Usuários")

    usuarios = carregar_usuarios()
    st.dataframe(
        pd.DataFrame(usuarios)[["usuario","nivel","ativo"]],
        use_container_width=True
    )

    st.divider()
    st.subheader("Gerenciar Operadores")

    for u in usuarios:
        with st.expander(f"{u['usuario']} | {u['nivel']}"):
            novo_nome = st.text_input("Usuário", u["usuario"], key=f"u{u['id']}")
            nivel = st.selectbox(
                "Permissão",
                ["operador","admin"],
                index=0 if u["nivel"]=="operador" else 1,
                key=f"n{u['id']}"
            )
            ativo = st.checkbox("Ativo", value=u["ativo"], key=f"a{u['id']}")
            nova_senha = st.text_input(
                "Nova senha (opcional)",
                type="password",
                key=f"s{u['id']}"
            )

            col1,col2 = st.columns(2)
            if col1.button("💾 Salvar", key=f"save{u['id']}"):
                data={"usuario":novo_nome,"nivel":nivel,"ativo":ativo}
                if nova_senha:
                    data["senha"]=gerar_hash(nova_senha)
                supabase.table("usuarios").update(data).eq("id",u["id"]).execute()
                registrar_log(f"Editou usuário {novo_nome}")
                st.cache_data.clear()
                st.rerun()

            if col2.button("🗑️ Excluir", key=f"del{u['id']}"):
                supabase.table("usuarios").delete().eq("id",u["id"]).execute()
                registrar_log(f"Excluiu usuário {u['usuario']}")
                st.cache_data.clear()
                st.rerun()

# ---------- LOGS ----------
if menu=="Logs":
    st.title("📜 Logs")
    st.dataframe(pd.DataFrame(carregar_logs()), use_container_width=True)
