import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client

# ======== CONFIG ========
SUPABASE_URL = st.secrets["https://uunvrxifjxwmhxokznbm.supabase.co"]
SUPABASE_KEY = st.secrets["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV1bnZyeGlmanh3bWh4b2t6bmJtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTA2OTQwMSwiZXhwIjoyMDg0NjQ1NDAxfQ.unLG1tk2WExgA3pqzXkOJpzAEtwLjdlwSLiJnShKJU0"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

STATUS_OPCOES = [
    "em análise",
    "solicitar fatura",
    "boleto de quitação",
    "aguardando averbação",
    "aguardando liquidação",
    "fechado",
    "cancelado",
]

# ======== HELPERS ========
def listar_clientes(status=None, operador=None, busca=None, limit=500):
    q = supabase.table("clientes").select("*").order("created_at", desc=True).limit(limit)

    if status and status != "Todos":
        q = q.eq("status", status)
    if operador and operador != "Todos":
        q = q.eq("operador", operador)
    if busca:
        # busca simples: nome/telefone/cpf
        # supabase python suporta ilike em colunas individuais
        # aqui fazemos OR via "or" (string)
        busca_esc = busca.replace('"', "")
        q = q.or_(f'nome.ilike.%{busca_esc}%,telefone.ilike.%{busca_esc}%,cpf.ilike.%{busca_esc}%')

    res = q.execute()
    return res.data or []

def criar_cliente(payload: dict):
    return supabase.table("clientes").insert(payload).execute()

def atualizar_cliente(cliente_id: str, payload: dict):
    return supabase.table("clientes").update(payload).eq("id", cliente_id).execute()

def deletar_cliente(cliente_id: str):
    return supabase.table("clientes").delete().eq("id", cliente_id).execute()

# ======== UI ========
st.subheader("📋 Clientes (Operação)")

# filtros
colf1, colf2, colf3 = st.columns([1, 1, 2])
with colf1:
    filtro_status = st.selectbox("Status", ["Todos"] + STATUS_OPCOES, index=0)
with colf2:
    filtro_operador = st.text_input("Operador (ou deixe em branco)")
with colf3:
    busca = st.text_input("Buscar (nome, cpf, telefone)")

operador_param = filtro_operador.strip() if filtro_operador.strip() else None

dados = listar_clientes(
    status=filtro_status,
    operador=operador_param,
    busca=busca.strip() if busca else None
)

df = pd.DataFrame(dados)
if df.empty:
    st.info("Nenhum cliente encontrado com esses filtros.")
else:
    # melhora visual: colunas principais
    cols = ["nome", "cpf", "telefone", "status", "produto", "operador", "prioridade", "created_at", "last_contact_at", "id"]
    cols = [c for c in cols if c in df.columns]
    st.dataframe(df[cols], use_container_width=True, hide_index=True)

st.divider()

# ======== CRIAR CLIENTE ========
with st.expander("➕ Cadastrar novo cliente", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        nome = st.text_input("Nome *")
        cpf = st.text_input("CPF")
    with c2:
        telefone = st.text_input("Telefone")
        email = st.text_input("Email")
    with c3:
        status = st.selectbox("Status inicial", STATUS_OPCOES, index=0)
        produto = st.text_input("Produto")
        origem = st.text_input("Origem")

    c4, c5 = st.columns([2, 1])
    with c4:
        obs = st.text_area("Observações")
    with c5:
        operador = st.text_input("Operador responsável")
        prioridade = st.selectbox("Prioridade", [1, 2, 3], index=2)

    if st.button("Salvar cliente", type="primary"):
        if not nome.strip():
            st.error("Nome é obrigatório.")
        else:
            payload = {
                "nome": nome.strip(),
                "cpf": cpf.strip() if cpf else None,
                "telefone": telefone.strip() if telefone else None,
                "email": email.strip() if email else None,
                "status": status,
                "produto": produto.strip() if produto else None,
                "origem": origem.strip() if origem else None,
                "observacoes": obs.strip() if obs else None,
                "operador": operador.strip() if operador else None,
                "prioridade": int(prioridade),
                "last_contact_at": None
            }
            try:
                criar_cliente(payload)
                st.success("Cliente cadastrado!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao cadastrar: {e}")

st.divider()

# ======== EDITAR STATUS / ATUALIZAR CONTATO ========
st.subheader("✍️ Atualizar cliente rápido (status / último contato)")

if df.empty:
    st.stop()

# seletor por id (mostra nome na label)
opcoes = {f"{row['nome']} • {row.get('cpf','')} • {row['id'][:8]}": row["id"] for _, row in df.iterrows()}
label = st.selectbox("Selecione o cliente", list(opcoes.keys()))
cliente_id = opcoes[label]

cliente_row = df[df["id"] == cliente_id].iloc[0].to_dict()

c1, c2, c3 = st.columns(3)
with c1:
    novo_status = st.selectbox("Novo status", STATUS_OPCOES, index=STATUS_OPCOES.index(cliente_row["status"]) if cliente_row.get("status") in STATUS_OPCOES else 0)
with c2:
    novo_operador = st.text_input("Operador", value=cliente_row.get("operador") or "")
with c3:
    nova_prioridade = st.selectbox("Prioridade", [1, 2, 3], index=[1,2,3].index(int(cliente_row.get("prioridade") or 3)))

obs_nova = st.text_area("Observações", value=cliente_row.get("observacoes") or "")

colb1, colb2, colb3 = st.columns([1,1,1])
with colb1:
    if st.button("Salvar alterações", type="primary"):
        payload = {
            "status": novo_status,
            "operador": novo_operador.strip() if novo_operador.strip() else None,
            "prioridade": int(nova_prioridade),
            "observacoes": obs_nova.strip() if obs_nova.strip() else None,
        }
        try:
            atualizar_cliente(cliente_id, payload)
            st.success("Atualizado!")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao atualizar: {e}")

with colb2:
    if st.button("Marcar contato agora"):
        try:
            atualizar_cliente(cliente_id, {"last_contact_at": datetime.utcnow().isoformat()})
            st.success("Último contato registrado!")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao registrar contato: {e}")

with colb3:
    if st.button("Excluir cliente", type="secondary"):
        try:
            deletar_cliente(cliente_id)
            st.warning("Cliente excluído.")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao excluir: {e}")
