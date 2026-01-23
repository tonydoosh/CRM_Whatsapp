# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client
import hashlib
import requests
import urllib.parse

# ---------- CONFIGURAÇÃO ----------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
GROQ_API_KEY = st.secrets["api_key"]
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="CRM WhatsApp", layout="wide")

# ---------- FUNÇÕES AUXILIARES ----------
def gerar_hash(senha: str) -> str:
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()

def verificar_senha(senha_digitada: str, senha_hash: str) -> bool:
    return gerar_hash(senha_digitada) == senha_hash

def registrar_log(acao: str):
    try:
        supabase.table("logs").insert({
            "usuario": st.session_state.get("usuario", "desconhecido"),
            "acao": acao,
            "data_hora": datetime.now().isoformat()
        }).execute()
    except Exception:
        pass

def gerar_mensagem_whatsapp(cliente: dict) -> str:
    try:
        status_map = {
            "em análise": "está sendo analisado",
            "aguardando averbação": "está aguardando averbação",
            "aguardando liquidação": "está aguardando liquidação",
            "fechado": "foi finalizado",
            "cancelado": "foi cancelado"
        }

        status_desc = status_map.get(cliente.get("status"), cliente.get("status"))
        horario = (datetime.now() - timedelta(hours=3)).strftime("%d/%m/%Y %H:%M")

        prompt = f"""Você é um especialista em crédito e consultoria financeira.

Cliente: {cliente.get('nome')}
Tipo de Produto: {cliente.get('tipo_contrato')}
Banco/Instituição: {cliente.get('banco')}
Status Atual: {status_desc}
Observações: {cliente.get('observacoes', 'Nenhuma')}

Gere uma mensagem WhatsApp profissional, curta e objetiva.
Horário atual {horario}.
"""

        payload = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [
                {"role": "system", "content": "Consultor financeiro especialista em WhatsApp."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5,
            "max_tokens": 150
        }

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        r = requests.post(GROQ_URL, json=payload, headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
        return "⚠️ Erro ao gerar mensagem"
    except Exception as e:
        return f"⚠️ {e}"

def gerar_link_whatsapp(telefone: str, mensagem: str) -> str:
    telefone = "".join(filter(str.isdigit, telefone))
    texto = urllib.parse.quote(mensagem)
    return f"https://web.whatsapp.com/send?phone=55{telefone}&text={texto}"

@st.cache_data(ttl=60)
def carregar_clientes(nivel: str, usuario: str):
    if nivel == "admin":
        return supabase.table("clientes").select("*").execute().data
    return supabase.table("clientes").select("*").eq("usuario", usuario).execute().data

# ---------- LOGIN ----------
def login():
    st.title("🔐 Login CRM WhatsApp")
    usuario = st.text_input("Usuário").strip()
    senha = st.text_input("Senha", type="password").strip()

    if st.button("Entrar", use_container_width=True):
        if not usuario or not senha:
            st.error("Preencha usuário e senha")
            return
        try:
            res = supabase.table("usuarios").select("*").eq("usuario", usuario).execute().data
            if not res:
                st.error("Usuário ou senha inválidos")
                return
            u = res[0]
            if not u.get("ativo", False):
                st.error("Usuário bloqueado")
                return
            if verificar_senha(senha, u.get("senha")):
                st.session_state["logado"] = True
                st.session_state["usuario"] = usuario
                st.session_state["nivel"] = u.get("nivel")
                registrar_log("Login")
                st.experimental_rerun()
            else:
                st.error("Usuário ou senha inválidos")
        except Exception as e:
            st.error(str(e))

# ---------- INICIALIZAÇÃO ----------
if "logado" not in st.session_state:
    st.session_state["logado"] = False
if "nivel" not in st.session_state:
    st.session_state["nivel"] = None
if "usuario" not in st.session_state:
    st.session_state["usuario"] = None

if not st.session_state["logado"]:
    login()
    st.stop()

# ---------- SIDEBAR ----------
st.sidebar.title("🔧 Menu")
if st.sidebar.button("🚪 Sair", use_container_width=True):
    registrar_log("Logout")
    st.session_state.clear()
    st.experimental_rerun()

menu = st.sidebar.radio(
    "Selecione:",
    ["CRM", "Usuários", "Logs"] if st.session_state["nivel"] == "admin" else ["CRM"]
)

# ---------- CRM ----------
if menu == "CRM":
    st.title("📲 CRM de Clientes – WhatsApp")

    clientes = carregar_clientes(st.session_state["nivel"], st.session_state["usuario"])
    df_clientes = pd.DataFrame(clientes) if clientes else pd.DataFrame()

    st.subheader("📊 Visão Geral")
    if not df_clientes.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("👥 Total", len(df_clientes))
        c2.metric("⏳ Em análise", len(df_clientes[df_clientes["status"] == "em análise"]))
        c3.metric("📎 Aguardando", len(df_clientes[df_clientes["status"].isin(["aguardando averbação", "aguardando liquidação"])]))
        c4.metric("✅ Fechados", len(df_clientes[df_clientes["status"] == "fechado"]))

    st.divider()

    with st.form("form_add"):
        st.subheader("➕ Adicionar Cliente")
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome *")
            telefone = st.text_input("Telefone *")
            banco = st.text_input("Banco")
        with col2:
            tipo = st.selectbox("Tipo *", ["cartão", "consignado", "empréstimo", "saque", "benefício", "crédito"])
            status = st.selectbox("Status *", ["em análise", "aguardando averbação", "aguardando liquidação", "fechado", "cancelado"])
            obs = st.text_area("Observações")
        if st.form_submit_button("Salvar", use_container_width=True):
            if nome and telefone:
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
                st.experimental_rerun()

    st.divider()

    if not df_clientes.empty:
        st.subheader("📋 Clientes")
        for _, row in df_clientes.iterrows():
            with st.expander(f"{row['nome']} - {row['telefone']}"):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.write(f"Banco: {row.get('banco','')}")
                    st.write(f"Tipo: {row.get('tipo_contrato','')}")
                    st.write(f"Status: {row.get('status','')}")
                    st.write(f"Obs: {row.get('observacoes','')}")

