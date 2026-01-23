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

# ================= CSS =================
st.markdown("""
<style>
body { background:#263d33; }
.card {
    background:#1f332c;padding:20px;border-radius:16px;
    border:1px solid #3d5e52;margin-bottom:16px;
}
h4 {color:#d4b15c;}
button[key^="ia_"] {
    background:linear-gradient(135deg,#d4b15c,#b18b3b);
    animation:pulse 2s infinite;font-weight:700;color:#263d33;
}
@keyframes pulse {
0%{box-shadow:0 0 0 0 rgba(212,177,92,.6);}
70%{box-shadow:0 0 0 12px rgba(212,177,92,0);}
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
            "usuario":st.session_state.get("usuario"),
            "acao":a,"data_hora":datetime.now().isoformat()
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
    st.image("https://github.com/tonydoosh/CRM_Whatsapp/blob/main/logo.jpeg?raw=true",width=180)
    u=st.text_input("Usuário")
    s=st.text_input("Senha",type="password")
    if st.button("🔐 Entrar",use_container_width=True):
        r=supabase.table("usuarios").select("*").eq("usuario",u).execute().data
        if not r or not verificar_senha(s,r[0]["senha"]) or not r[0]["ativo"]:
            st.error("Credenciais inválidas")
        else:
            st.session_state.update({"logado":True,"usuario":u,"nivel":r[0]["nivel"]})
            registrar_log("Login")
            st.rerun()

if not st.session_state.get("logado"):
    login(); st.stop()

# ================= SIDEBAR =================
st.sidebar.image("https://github.com/tonydoosh/CRM_Whatsapp/blob/main/logo.jpeg?raw=true")
menu=st.sidebar.radio("Menu",["CRM","Usuários","Logs"] if st.session_state["nivel"]=="admin" else ["CRM"])
if st.sidebar.button("🚪 Sair",use_container_width=True):
    registrar_log("Logout"); st.session_state.clear(); st.cache_data.clear(); st.rerun()

# ================= CRM =================
if menu=="CRM":
    st.title("📲 CRM de Clientes")

    # ---- TABELA / FORM CLÁSSICO ----
    with st.form("add_cliente"):
        c1,c2=st.columns(2)
        nome=c1.text_input("Nome*")
        tel=c1.text_input("Telefone*")
        banco=c1.text_input("Banco")
        tipo=c2.selectbox("Tipo*",["cartão","consignado","empréstimo","saque","benefício","crédito"])
        status=c2.selectbox("Status*",STATUS_OPCOES)
        obs=st.text_area("Observações")
        if st.form_submit_button("💾 Adicionar cliente",use_container_width=True):
            supabase.table("clientes").insert({
                "nome":nome,"telefone":tel,"banco":banco,
                "tipo_contrato":tipo,"status":status,
                "observacoes":obs,"usuario":st.session_state["usuario"]
            }).execute()
            registrar_log(f"Novo cliente {nome}")
            st.cache_data.clear(); st.rerun()

    st.divider()

    for c in carregar_clientes(st.session_state["nivel"],st.session_state["usuario"]):
        st.markdown(f"""
        <div class="card">
        <h4>{c['nome']}</h4>
        📞 {c['telefone']}<br>
        🏦 {c.get('banco','')}<br>
        📄 {c.get('tipo_contrato','')}<br>
        📌 {c.get('status','')}
        </div>
        """,unsafe_allow_html=True)

        col1,col2,col3=st.columns(3)
        if col1.button("🤖 Gerar IA",key=f"ia_{c['id']}"):
            st.session_state[f"msg_{c['id']}"]=gerar_mensagem_ia(c)
        if col2.button("📲 WhatsApp",key=f"w_{c['id']}"):
            st.link_button("Abrir WhatsApp",gerar_link_whatsapp(
                c["telefone"], st.session_state.get(f"msg_{c['id']}") or gerar_mensagem_ia(c)))
        if col3.button("✏️ Editar",key=f"edit_{c['id']}"):
            st.session_state["edit_id"]=c["id"]

        if st.session_state.get("edit_id")==c["id"]:
            with st.form(f"edit_form_{c['id']}"):
                status_e=st.selectbox("Status",STATUS_OPCOES,STATUS_OPCOES.index(c["status"]))
                obs_e=st.text_area("Obs",c.get("observacoes",""))
                if st.form_submit_button("💾 Atualizar"):
                    supabase.table("clientes").update({
                        "status":status_e,"observacoes":obs_e
                    }).eq("id",c["id"]).execute()
                    registrar_log(f"Atualizou cliente {c['nome']}")
                    st.session_state.pop("edit_id")
                    st.cache_data.clear(); st.rerun()

        if f"msg_{c['id']}" in st.session_state:
            st.text_area("Mensagem IA",st.session_state[f"msg_{c['id']}"],height=90)

# ================= USUÁRIOS =================
if menu=="Usuários":
    st.title("👤 Operadores")

    with st.form("add_user"):
        u=st.text_input("Usuário")
        s=st.text_input("Senha",type="password")
        n=st.selectbox("Nível",["operador","admin"])
        if st.form_submit_button("Adicionar"):
            supabase.table("usuarios").insert({
                "usuario":u,"senha":gerar_hash(s),"nivel":n,"ativo":True
            }).execute()
            registrar_log(f"Criou usuário {u}")
            st.cache_data.clear(); st.rerun()

    st.divider()

    for u in carregar_usuarios():
        with st.expander(u["usuario"]):
            ativo=st.checkbox("Ativo",value=u["ativo"],key=f"a{u['id']}")
            nivel=st.selectbox("Nível",["operador","admin"],
                               index=0 if u["nivel"]=="operador" else 1,key=f"n{u['id']}")
            nova=st.text_input("Nova senha",type="password",key=f"s{u['id']}")
            if st.button("Salvar",key=f"save{u['id']}"):
                d={"ativo":ativo,"nivel":nivel}
                if nova: d["senha"]=gerar_hash(nova)
                supabase.table("usuarios").update(d).eq("id",u["id"]).execute()
                registrar_log(f"Editou usuário {u['usuario']}")
                st.cache_data.clear(); st.rerun()

# ================= LOGS =================
if menu=="Logs":
    st.title("📜 Logs")
    st.dataframe(pd.DataFrame(carregar_logs()),use_container_width=True)
