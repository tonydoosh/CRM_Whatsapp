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

# ---------- FUNÇÕES ----------
def gerar_hash(senha: str) -> str:
    return hashlib.sha256(senha.encode()).hexdigest()

def verificar_senha(senha: str, senha_hash: str) -> bool:
    return gerar_hash(senha) == senha_hash

def registrar_log(acao: str):
    try:
        supabase.table("logs").insert({
            "usuario": st.session_state.get("usuario"),
            "acao": acao,
            "data_hora": datetime.now().isoformat()
        }).execute()
    except Exception:
        pass

def gerar_link_whatsapp(telefone: str, mensagem: str) -> str:
    telefone = "".join(filter(str.isdigit, telefone))
    texto = urllib.parse.quote(mensagem)
    return f"https://web.whatsapp.com/send?phone=55{telefone}&text={texto}"

def gerar_mensagem_ia(cliente: dict) -> str:
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

@st.cache_data(ttl=86400)  # 24 horas_data(ttl=60)
def carregar_clientes(nivel, usuario):
    if nivel == "admin":
        return supabase.table("clientes").select("*").execute().data
    return supabase.table("clientes").select("*").eq("usuario", usuario).execute().data

@st.cache_data(ttl=86400)  # 24 horas_data(ttl=60)
def carregar_usuarios():
    return supabase.table("usuarios").select("*").execute().data

@st.cache_data(ttl=86400)  # 24 horas_data(ttl=60)
def carregar_logs():
    return supabase.table("logs").select("*").order("id", desc=True).limit(100).execute().data

# ---------- LOGIN ----------
def login():
    st.title("🔐 Login CRM WhatsApp")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar", use_container_width=True):
        res = supabase.table("usuarios").select("*").eq("usuario", usuario).execute().data
        if not res or not verificar_senha(senha, res[0]["senha"]) or not res[0]["ativo"]:
            st.error("Usuário ou senha inválidos")
            return
        st.session_state.update({
            "logado": True,
            "usuario": usuario,
            "nivel": res[0]["nivel"]
        })
        registrar_log("Login")
        st.rerun()

# ---------- SESSÃO ----------
if "logado" not in st.session_state:
    st.session_state["logado"] = False
if not st.session_state["logado"]:
    login()
    st.stop()

# ---------- SIDEBAR ----------
st.sidebar.title("🔧 Menu")
if st.sidebar.button("🚪 Sair", use_container_width=True):
    registrar_log("Logout")
    st.session_state.clear()
    st.cache_data.clear()
    st.rerun()

menu = st.sidebar.radio(
    "Selecione:",
    ["CRM", "Usuários", "Logs"] if st.session_state["nivel"] == "admin" else ["CRM"]
)

# ---------- CRM ----------
if menu == "CRM":
    st.title("📲 CRM de Clientes – WhatsApp")

    clientes = carregar_clientes(st.session_state["nivel"], st.session_state["usuario"])
    df = pd.DataFrame(clientes) if clientes else pd.DataFrame()

    with st.form("form_add"):
        st.subheader("➕ Adicionar Cliente")
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome *")
            telefone = st.text_input("Telefone *")
            banco = st.text_input("Banco")
        with col2:
            tipo = st.selectbox("Tipo *", ["cartão", "consignado", "empréstimo", "saque", "benefício", "crédito"])
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

    if not df.empty:
        st.subheader("📋 Clientes")
        for _, row in df.iterrows():
            with st.expander(f"{row['nome']} - {row['telefone']}"):
                nome_e = st.text_input("Nome", row["nome"], key=f"n{row['id']}")
                tel_e = st.text_input("Telefone", row["telefone"], key=f"t{row['id']}")
                banco_e = st.text_input("Banco", row.get("banco",""), key=f"b{row['id']}")
                tipo_e = st.text_input("Tipo", row.get("tipo_contrato",""), key=f"tp{row['id']}")
                status_e = st.selectbox("Status", STATUS_OPCOES, STATUS_OPCOES.index(row["status"]), key=f"s{row['id']}")
                obs_e = st.text_area("Obs", row.get("observacoes",""), key=f"o{row['id']}")

                c1, c2, c3 = st.columns(3)

                if c1.button("💾 Atualizar", key=f"u{row['id']}"):
                    supabase.table("clientes").update({
                        "nome": nome_e,
                        "telefone": tel_e,
                        "banco": banco_e,
                        "tipo_contrato": tipo_e,
                        "status": status_e,
                        "observacoes": obs_e
                    }).eq("id", row["id"]).execute()
                    registrar_log(f"Atualizou cliente {nome_e}")
                    st.cache_data.clear()
                    st.rerun()

                if c2.button("🧠 Gerar IA", key=f"ia{row['id']}"):
                    st.session_state[f"ia_{row['id']}"] = gerar_mensagem_ia(row)

                if c3.button("📲 WhatsApp", key=f"w{row['id']}"):
                    msg = st.session_state.get(f"ia_{row['id']}") or gerar_mensagem_ia(row)
                    st.link_button("Abrir WhatsApp", gerar_link_whatsapp(row["telefone"], msg))

                if f"ia_{row['id']}" in st.session_state:
                    st.text_area("Mensagem IA", st.session_state[f"ia_{row['id']}"], height=120)


# ---------- USUÁRIOS ----------
if menu == "Usuários":
    st.title("👤 Gestão de Usuários (Operadores)")

if menu == "Usuários":
    st.dataframe(pd.DataFrame(carregar_usuarios()), use_container_width=True)
   
    st.subheader("➕ Adicionar Usuário")
    with st.form("form_add_user"):
        col1, col2, col3 = st.columns(3)
        with col1:
            novo_usuario = st.text_input("Usuário *")
            nova_senha = st.text_input("Senha *", type="password")
        with col2:
            nivel = st.selectbox("Nível *", ["operador", "admin"])
        with col3:
            ativo = st.selectbox("Ativo", [True, False])

        if st.form_submit_button("Salvar usuário", use_container_width=True):
            if not novo_usuario or not nova_senha:
                st.error("Preencha usuário e senha")
            else:
                supabase.table("usuarios").insert({
                    "usuario": novo_usuario,
                    "senha": gerar_hash(nova_senha),
                    "nivel": nivel,
                    "ativo": ativo
                }).execute()
                registrar_log(f"Criou usuário {novo_usuario}")
                st.cache_data.clear()
                st.rerun()

    st.divider()
    st.subheader("📋 Usuários cadastrados")

    usuarios = carregar_usuarios()
    df_users = pd.DataFrame(usuarios) if usuarios else pd.DataFrame()

    if df_users.empty:
        st.info("Nenhum usuário encontrado")
    else:
        for _, row in df_users.iterrows():
            with st.expander(f"{row['usuario']} | {row['nivel']} | {'Ativo' if row['ativo'] else 'Inativo'}"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    usuario_e = st.text_input(
                        "Usuário",
                        row["usuario"],
                        key=f"user_{row['id']}"
                    )
                    nivel_e = st.selectbox(
                        "Nível",
                        ["operador", "admin"],
                        index=0 if row["nivel"] == "operador" else 1,
                        key=f"nivel_{row['id']}"
                    )

                with col2:
                    ativo_e = st.selectbox(
                        "Ativo",
                        [True, False],
                        index=0 if row["ativo"] else 1,
                        key=f"ativo_{row['id']}"
                    )
                    nova_senha_e = st.text_input(
                        "Nova senha (opcional)",
                        type="password",
                        key=f"senha_{row['id']}"
                    )

                with col3:
                    if st.button("💾 Atualizar", key=f"up_{row['id']}"):
                        dados = {
                            "usuario": usuario_e,
                            "nivel": nivel_e,
                            "ativo": ativo_e
                        }
                        if nova_senha_e:
                            dados["senha"] = gerar_hash(nova_senha_e)

                        supabase.table("usuarios").update(dados).eq("id", row["id"]).execute()
                        registrar_log(f"Atualizou usuário {usuario_e}")
                        st.cache_data.clear()
                        st.rerun()

                    if st.button("🗑️ Excluir", key=f"del_{row['id']}"):
                        supabase.table("usuarios").delete().eq("id", row["id"]).execute()
                        registrar_log(f"Excluiu usuário {row['usuario']}")
                        st.cache_data.clear()
                        st.rerun()

# ---------- LOGS ----------
if menu == "Logs":
    st.dataframe(pd.DataFrame(carregar_logs()), use_container_width=True)


