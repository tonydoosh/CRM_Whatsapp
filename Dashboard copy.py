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
    "cancelado"
]

# ================= CSS (LEVE) =================
st.markdown("""
<style>
body { background:#263d33; }

.card {
    background:#1f332c;
    border:1px solid #3d5e52;
    border-radius:16px;
    padding:16px;
    margin-bottom:14px;
}
.card h4 { color:#d4b15c; margin-bottom:4px; }

.badge {
    display:inline-block;
    padding:4px 10px;
    border-radius:999px;
    font-size:12px;
    font-weight:700;
    background:#3d5e52;
    color:#eaf2ef;
}

button[key^="ia_"] {
    background:linear-gradient(135deg,#d4b15c,#b18b3b);
    color:#263d33;
    font-weight:700;
    animation:pulse 2s infinite;
}

@keyframes pulse {
0%{box-shadow:0 0 0 0 rgba(212,177,92,.6);}
70%{box-shadow:0 0 0 10px rgba(212,177,92,0);}
100%{box-shadow:0 0 0 0 rgba(212,177,92,0);}
}
</style>
""", unsafe_allow_html=True)

# ================= FUNÇÕES =================
def gerar_hash(s): return hashlib.sha256(s.encode()).hexdigest()
def verificar_senha(s,h): return gerar_hash(s)==h

def registrar_log(a):
    try:
        supabase.table("logs").insert({
            "usuario": st.session_state.get("usuario"),
            "acao": a,
            "data_hora": datetime.now().isoformat()
        }).execute()
    except: pass

def gerar_link_whatsapp(t,m):
    t="".join(filter(str.isdigit,t))
    return f"https://web.whatsapp.com/send?phone=55{t}&text={urllib.parse.quote(m)}"

def gerar_mensagem_ia(c):
    payload={
        "model":"meta-llama/llama-4-scout-17b-16e-instruct",
        "messages":[
            {"role":"system","content":"Consultor financeiro especialista"},
            {"role":"user","content":f"""
Cliente:{c['nome']}
Produto:{c.get('tipo_contrato')}
Banco:{c.get('banco')}
Status:{c.get('status')}
Obs:{c.get('observacoes')}
Gere mensagem curta para WhatsApp."""}
        ],
        "temperature":0.4,"max_tokens":120
    }
    r=requests.post(GROQ_URL,json=payload,headers={
        "Authorization":f"Bearer {GROQ_API_KEY}",
        "Content-Type":"application/json"},timeout=30)
    return r.json()["choices"][0]["message"]["content"]

@st.cache_data(ttl=86400)
def carregar_clientes(n,u):
    return supabase.table("clientes").select("*").execute().data if n=="admin" else \
           supabase.table("clientes").select("*").eq("usuario",u).execute().data

@st.cache_data(ttl=86400)
def carregar_usuarios(): return supabase.table("usuarios").select("*").execute().data
@st.cache_data(ttl=86400)
def carregar_logs(): return supabase.table("logs").select("*").order("id",desc=True).limit(200).execute().data

# ================= LOGIN =================
def login():
    st.image(LOGO_URL, width=180)
    u=st.text_input("Usuário")
    s=st.text_input("Senha", type="password")
    if st.button("🔐 Entrar", use_container_width=True):
        r=supabase.table("usuarios").select("*").eq("usuario",u).execute().data
        if not r or not verificar_senha(s,r[0]["senha"]) or not r[0]["ativo"]:
            st.error("Credenciais inválidas")
        else:
            st.session_state.update({"logado":True,"usuario":u,"nivel":r[0]["nivel"]})
            registrar_log("Login")
            st.rerun()

if not st.session_state.get_
