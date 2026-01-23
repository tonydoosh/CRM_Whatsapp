# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client
import hashlib
import requests
import urllib.parse
import webbrowser


supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="CRM WhatsApp", layout="wide")

# ---------- FUNÇÕES AUXILIARES ----------
def gerar_hash(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def verificar_senha(senha_digitada, senha_hash):
    return gerar_hash(senha_digitada) == senha_hash

def registrar_log(acao):
    try:
        supabase.table("logs").insert({
            "usuario": st.session_state.get("usuario", "desconhecido"),
            "acao": acao,
            "data_hora": datetime.now().isoformat()
        }).execute()
    except Exception as e:
        st.warning(f"Erro ao registrar log: {e}")

def gerar_mensagem_whatsapp(cliente):
    try:
        # Criar prompt mais detalhado e profissional
        status_map = {
            "em análise": "está sendo analisado",
            "aguardando averbação": "está aguardando averbação",
            "aguardando liquidação": "está aguardando liquidação",
            "fechado": "foi finalizado",
            "cancelado": "foi cancelado"
        }
        
        status_desc = status_map.get(cliente['status'], cliente['status'])
        horario = (datetime.now() - timedelta(hours=3)).strftime("%d/%m/%Y %H:%M")
        
        prompt = f"""Você é um especialista em crédito e consultoria financeira. Gere uma mensagem WhatsApp profissional, mas amigável e persuasiva para o seguinte contexto:

Cliente: {cliente['nome']}
Tipo de Produto: {cliente['tipo_contrato']}
Banco/Instituição: {cliente['banco']}
Status Atual: {status_desc}
Observações: {cliente.get('observacoes', 'Nenhuma')}

Requisitos:
- Máximo 2 linhas e meia
- Tom profissional mas acessível
- Use emoji se apropriado
- Inclua call-to-action claro
- Não inclua links ou números de telefone
- Foque em próximo passo no processo
- Horario em tempo real {horario} para personalização

Gere apenas a mensagem, sem explicações."""
        
        payload = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [
                {
                    "role": "system", 
                    "content": "Você é um consultor financeiro especialista em comunicação via WhatsApp. Suas mensagens são claras, profissionais e conseguem engajar clientes de forma natural e efetiva."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
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
            mensagem = r.json()["choices"][0]["message"]["content"].strip()
            return mensagem
        else:
            return f"⚠️ Erro API: {r.status_code}"
    except Exception as e:
        return f"⚠️ Erro ao gerar: {str(e)}"

def abrir_whatsapp(telefone, mensagem):
    try:
        telefone = ''.join(filter(str.isdigit, telefone))
        texto = urllib.parse.quote(mensagem)
        url = f"https://web.whatsapp.com/send?phone=55{telefone}&text={texto}"
        webbrowser.open_new_tab(url)
    except Exception as e:
        st.error(f"Erro ao abrir WhatsApp: {e}")

# ---------- LOGIN ----------
def login():
    st.title("🔐 Login CRM WhatsApp")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        usuario = st.text_input("Usuário").strip()
        senha = st.text_input("Senha", type="password").strip()
        
        if st.button("Entrar", use_container_width=True):
            if not usuario or not senha:
                st.error("Preencha usuário e senha")
            else:
                try:
                    res = supabase.table("usuarios").select("*").eq("usuario", usuario).execute().data
                    if not res:
                        st.error("Usuário ou senha inválidos")
                    else:
                        usuario_db = res[0]
                        if not usuario_db["ativo"]:
                            st.error("Usuário BLOQUEADO. Contate o administrador.")
                        elif verificar_senha(senha, usuario_db["senha"]):
                            st.session_state["logado"] = True
                            st.session_state["usuario"] = usuario
                            st.session_state["nivel"] = usuario_db["nivel"]
                            registrar_log("Login")
                            st.rerun()
                        else:
                            st.error("Usuário ou senha inválidos")
                except Exception as e:
                    st.error(f"Erro ao fazer login: {e}")

# ---------- INICIALIZAR SESSÃO ----------
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
    st.rerun()

menu = st.sidebar.radio(
    "Selecione:",
    ["CRM", "Usuários", "Logs"] if st.session_state["nivel"] == "admin" else ["CRM"]
)

# ---------- CRM ----------
if menu == "CRM":
    st.title("📲 CRM de Clientes – WhatsApp")
    
    try:
        # Carregar clientes (admin vê todos, operador vê apenas seus)
        try:
            if st.session_state["nivel"] == "admin":
                clientes = supabase.table("clientes").select("*").execute().data
            else:
                # Tentar carregar com filtro de usuario
                clientes = supabase.table("clientes").select("*").eq("usuario", st.session_state["usuario"]).execute().data
        except Exception as e:
            # Se a coluna usuario não existe, carregar todos os clientes
            if "usuario" in str(e).lower() or "does not exist" in str(e):
                st.warning("⚠️ Coluna 'usuario' ainda não foi criada. Por enquanto, mostrando todos os clientes.")
                clientes = supabase.table("clientes").select("*").execute().data
            else:
                raise e
        
        df_clientes = pd.DataFrame(clientes) if clientes else pd.DataFrame()
        
        # Métricas
        st.subheader("📊 Visão Geral")
        if not df_clientes.empty:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("👥 Total", len(df_clientes))
            col2.metric("⏳ Em análise", len(df_clientes[df_clientes["status"] == "em análise"]))
            col3.metric("📎 Aguardando", len(df_clientes[df_clientes["status"].isin(["aguardando averbação", "aguardando liquidação"])]))
            col4.metric("✅ Fechados", len(df_clientes[df_clientes["status"] == "fechado"]))
        
        st.divider()
        
        # Formulário para adicionar cliente
        with st.form("form_adicionar_cliente"):
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
            
            enviado = st.form_submit_button("💾 Salvar Cliente", use_container_width=True)
            
            if enviado:
                if not nome or not telefone or not tipo or tipo == "":
                    st.error("Preencha todos os campos obrigatórios (*)")
                else:
                    try:
                        supabase.table("clientes").insert({
                            "nome": nome,
                            "telefone": telefone,
                            "banco": banco,
                            "tipo_contrato": tipo,
                            "status": status,
                            "observacoes": obs,
                            "usuario": st.session_state["usuario"]
                        }).execute()
                        registrar_log(f"Cadastro cliente: {nome}")
                        st.success("✅ Cliente salvo com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar cliente: {e}")
        
        st.divider()
        
        # Lista de clientes
        if not df_clientes.empty:
            st.subheader("📋 Lista de Clientes")
            
            for _, row in df_clientes.iterrows():
                try:
                    titulo = f"📌 {row['nome']} - {row['telefone']}"
                    
                    with st.expander(titulo, expanded=False):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.write(f"**Banco:** {row['banco']}")
                            st.write(f"**Tipo:** {row['tipo_contrato']}")
                            st.write(f"**Status:** {row['status']}")
                            if row['observacoes']:
                                st.write(f"**Observações:** {row['observacoes']}")
                        
                        with col2:
                            st.write("**Ações:**")
                            if st.button("🤖 Gerar IA", key=f"ia_{row['id']}", use_container_width=True):
                                with st.spinner("Gerando mensagem..."):
                                    msg = gerar_mensagem_whatsapp(row)
                                    st.session_state[f"msg_{row['id']}"] = msg
                                    st.rerun()
                            
                            if st.button("✏️ Editar", key=f"edit_{row['id']}", use_container_width=True):
                                st.session_state["editar_id"] = row["id"]
                                st.rerun()
                            
                            # Permitir deletar apenas se for o dono ou admin
                            can_delete = st.session_state["nivel"] == "admin" or row.get("usuario") == st.session_state["usuario"]
                            if can_delete:
                                if st.button("🗑️ Deletar", key=f"del_{row['id']}", use_container_width=True):
                                    supabase.table("clientes").delete().eq("id", row["id"]).execute()
                                    registrar_log(f"Deletou cliente: {row['nome']}")
                                    st.success("✅ Cliente deletado!")
                                    st.rerun()
                        
                        # Mostrar mensagem gerada
                        msg_key = f"msg_{row['id']}"
                        if msg_key in st.session_state:
                            st.divider()
                            st.write("**💬 Mensagem WhatsApp:**")
                            with st.form(f"form_whatsapp_{row['id']}"):
                                texto = st.text_area(
                                    "Mensagem para editar",
                                    st.session_state[msg_key],
                                    height=100,
                                    key=f"txt_{row['id']}",
                                    label_visibility="collapsed"
                                )
                                
                                if st.form_submit_button("📲 Abrir WhatsApp", use_container_width=True):
                                    abrir_whatsapp(row["telefone"], texto)
                                    registrar_log(f"Enviou WhatsApp para: {row['nome']}")
                                    st.success("✅ WhatsApp aberto!")
                
                except Exception as e:
                    st.error(f"Erro ao exibir cliente: {e}")
        else:
            st.info("📭 Nenhum cliente cadastrado ainda.")
        
        # Formulário de edição (se selecionado)
        if "editar_id" in st.session_state:
            st.divider()
            cliente_id = st.session_state["editar_id"]
            try:
                cliente = supabase.table("clientes").select("*").eq("id", cliente_id).execute().data[0]
                
                st.subheader(f"✏️ Editando: {cliente['nome']}")
                
                with st.form("form_editar_cliente"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        nome_edit = st.text_input("Nome", value=cliente["nome"])
                        telefone_edit = st.text_input("Telefone", value=cliente["telefone"])
                        banco_edit = st.text_input("Banco", value=cliente.get("banco", ""))
                    
                    with col2:
                        tipo_edit = st.selectbox(
                            "Tipo",
                            ["cartão", "saque", "benefício", "crédito"],
                            index=["cartão", "saque", "benefício", "crédito"].index(cliente["tipo_contrato"])
                        )
                        status_edit = st.selectbox(
                            "Status",
                            ["em análise", "aguardando averbação", "aguardando liquidação", "fechado", "cancelado"],
                            index=["em análise", "aguardando averbação", "aguardando liquidação", "fechado", "cancelado"].index(cliente["status"])
                        )
                        obs_edit = st.text_area("Observações", value=cliente.get("observacoes", ""))
                    
                    if st.form_submit_button("💾 Salvar Alterações", use_container_width=True):
                        update_data = {
                            "nome": nome_edit,
                            "telefone": telefone_edit,
                            "banco": banco_edit,
                            "tipo_contrato": tipo_edit,
                            "status": status_edit,
                            "observacoes": obs_edit
                        }
                        
                        # Adicionar usuario se existir na linha
                        if "usuario" in cliente:
                            update_data["usuario"] = cliente.get("usuario", st.session_state["usuario"])
                        
                        supabase.table("clientes").update(update_data).eq("id", cliente_id).execute()
                        registrar_log(f"Editou cliente: {nome_edit}")
                        st.success("✅ Cliente atualizado!")
                        del st.session_state["editar_id"]
                        st.rerun()
            except Exception as e:
                st.error(f"Erro ao editar cliente: {e}")
    
    except Exception as e:
        st.error(f"Erro ao carregar clientes: {e}")

# ---------- USUÁRIOS ----------
if menu == "Usuários":
    st.title("👤 Gerenciar Usuários")
    
    try:
        usuarios = supabase.table("usuarios").select("*").execute().data
        df_usuarios = pd.DataFrame(usuarios) if usuarios else pd.DataFrame()
        
        # Criar novo usuário
        with st.form("form_novo_usuario"):
            st.subheader("➕ Criar Novo Usuário")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                novo_usuario = st.text_input("Usuário")
            with col2:
                nova_senha = st.text_input("Senha", type="password")
            with col3:
                nivel = st.selectbox("Nível", ["operador", "admin"])
            
            if st.form_submit_button("Criar Usuário", use_container_width=True):
                if not novo_usuario or not nova_senha:
                    st.error("Preencha todos os campos")
                else:
                    try:
                        supabase.table("usuarios").insert({
                            "usuario": novo_usuario,
                            "senha": gerar_hash(nova_senha),
                            "nivel": nivel,
                            "ativo": True
                        }).execute()
                        registrar_log(f"Criou usuário: {novo_usuario}")
                        st.success(f"✅ Usuário {novo_usuario} criado!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {str(e)}")
        
        st.divider()
        
        # Lista de usuários
        if not df_usuarios.empty:
            st.subheader("📋 Usuários Existentes")
            
            for _, u in df_usuarios.iterrows():
                col1, col2, col3, col4, col5 = st.columns([2, 1.5, 1.5, 1.5, 2])
                
                col1.write(f"**{u['usuario']}**")
                col2.write(u['nivel'].upper())
                col3.write("✅ Ativo" if u['ativo'] else "🔒 Bloqueado")
                
                if u['usuario'] != st.session_state.get('usuario'):
                    if col4.button("🔄", key=f"toggle_{u['id']}", help="Bloquear/Desbloquear"):
                        novo_status = not u['ativo']
                        supabase.table("usuarios").update({"ativo": novo_status}).eq("id", u["id"]).execute()
                        registrar_log(f"{'Bloqueou' if not novo_status else 'Desbloqueou'}: {u['usuario']}")
                        st.rerun()
                    
                    if col5.button("🗑️ Deletar", key=f"del_user_{u['id']}", use_container_width=True):
                        supabase.table("usuarios").delete().eq("id", u["id"]).execute()
                        registrar_log(f"Deletou usuário: {u['usuario']}")
                        st.success("✅ Usuário deletado!")
                        st.rerun()
                else:
                    col4.info("👤 Você")
        else:
            st.info("Nenhum usuário cadastrado")
    
    except Exception as e:
        st.error(f"Erro ao carregar usuários: {e}")

# ---------- LOGS ----------
if menu == "Logs":
    st.title("🕒 Logs do Sistema")
    
    try:
        logs = supabase.table("logs").select("*").order("id", desc=True).limit(100).execute().data
        if logs:
            df_logs = pd.DataFrame(logs)
            st.dataframe(df_logs, use_container_width=True)
        else:
            st.info("Nenhum log registrado")
    except Exception as e:
        st.error(f"Erro ao carregar logs: {e}")
