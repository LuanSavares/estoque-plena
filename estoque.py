import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib

# --- FUNÇÕES DE SEGURANÇA ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return True
    return False

# --- BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('techstock.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  name TEXT, 
                  category TEXT, 
                  quantity INTEGER, 
                  min_stock INTEGER,
                  barcode TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, user TEXT, product_name TEXT, 
                  type TEXT, qty_change INTEGER, origin TEXT, destination TEXT)''')
    
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES ('admin', ?, 'admin')", (make_hashes('admin123'),))
    conn.commit()
    conn.close()

def run_query(query, params=(), fetch=False):
    conn = sqlite3.connect('techstock.db')
    c = conn.cursor()
    c.execute(query, params)
    if fetch:
        data = c.fetchall()
        conn.close()
        return data
    conn.commit()
    conn.close()

def main():
    st.set_page_config(page_title="LS Tecnologias - Estoque", layout="wide", page_icon="🔧")
    init_db()

    # --- SESSÃO DE LOGIN ---
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        st.markdown("<h1 style='text-align: center;'>🔧 LS Tecnologias</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center;'>Controle de Estoque</h3>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            user = st.text_input("Usuário")
            pw = st.text_input("Senha", type="password")
            if st.button("Entrar", use_container_width=True):
                res = run_query("SELECT password, role FROM users WHERE username = ?", (user,), fetch=True)
                if res and check_hashes(pw, res[0][0]):
                    st.session_state['logged_in'] = True
                    st.session_state['user'] = user
                    st.session_state['role'] = res[0][1]
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
        return

    # --- MENU LATERAL ---
    st.sidebar.title("🔧 LS Tecnologias")
    st.sidebar.write(f"Usuário: **{st.session_state['user']}**")
    
    menu_options = ["Visão Geral", "Entrada/Saída", "Maleta Técnica", "Histórico", "Minha Conta"]
    if st.session_state['role'] == 'admin':
        menu_options.insert(1, "Cadastrar Produto")
        menu_options.append("Gerenciar Usuários")

    menu = st.sidebar.radio("Navegação", menu_options)
    
    st.sidebar.markdown("---")
    st.sidebar.link_button("📷 Instagram", "https://www.instagram.com/ls_tecnologiass?igsh=MXR6eG5kd3Z1b2c2NA==")
    st.sidebar.link_button("💬 WhatsApp", "https://wa.me/5511954053352")
    
    if st.sidebar.button("Sair"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- TELAS ---

    if menu == "Visão Geral":
        st.title("📦 Inventário Atual")
        df = pd.read_sql_query("SELECT name as 'Nome', category as 'Categoria', quantity as 'Qtd', min_stock as 'Mínimo', barcode as 'Código' FROM products", sqlite3.connect('techstock.db'))
        st.dataframe(df, use_container_width=True, hide_index=True)

    elif menu == "Cadastrar Produto":
        st.title("📝 Novo Item")
        with st.form("new_p"):
            n = st.text_input("Nome do Produto")
            c = st.selectbox("Categoria", ["Hardware", "Redes", "Ferramentas", "Consumíveis", "Outros"])
            b = st.text_input("Código de Barras (Opcional)", help="Bipe o código aqui")
            q = st.number_input("Estoque Inicial", min_value=0)
            m = st.number_input("Estoque Mínimo (Alerta)", min_value=1)
            if st.form_submit_button("Salvar no Sistema"):
                run_query("INSERT INTO products (name, category, quantity, min_stock, barcode) VALUES (?,?,?,?,?)", (n,c,q,m,b))
                st.success(f"Item {n} cadastrado!")

    elif menu == "Entrada/Saída":
        st.title("🔄 Movimentações de Estoque")
        barcode_in = st.text_input("🔍 Busca Rápida (Bipar Código)")
        
        selected_p = None
        if barcode_in:
            res = run_query("SELECT name FROM products WHERE barcode = ?", (barcode_in,), fetch=True)
            if res: selected_p = res[0][0]
            else: st.warning("Código não encontrado.")

        prods = [p[0] for p in run_query("SELECT name FROM products", fetch=True)]
        tipo = st.radio("Operação", ["Entrada (Compra)", "Saída (Venda/Uso)"])
        
        with st.form("mov"):
            p = st.selectbox("Produto", prods, index=prods.index(selected_p) if selected_p in prods else 0)
            q = st.number_input("Quantidade", min_value=1)
            loc = st.text_input("Origem/Destino")
            if st.form_submit_button("Confirmar Movimentação"):
                res_qty = run_query("SELECT quantity FROM products WHERE name=?", (p,), fetch=True)
                if res_qty:
                    atual = res_qty[0][0]
                    if "Saída" in tipo and atual - q < 0:
                        st.error("ERRO: O estoque não pode ficar negativo!")
                    else:
                        nova_qtd = atual + q if "Entrada" in tipo else atual - q
                        run_query("UPDATE products SET quantity=? WHERE name=?", (nova_qtd, p))
                        run_query("INSERT INTO transactions (timestamp, user, product_name, type, qty_change, origin, destination) VALUES (?,?,?,?,?,?,?)",
                                  (datetime.now().strftime("%d/%m/%Y %H:%M"), st.session_state['user'], p, tipo.split()[0].upper(), q if "Entrada" in tipo else -q, "Estoque" if "Saída" in tipo else loc, loc if "Saída" in tipo else "Estoque"))
                        st.success("Estoque atualizado!")

    elif menu == "Maleta Técnica":
        st.title("🧰 Controle de Materiais para Obra")
        prods = [p[0] for p in run_query("SELECT name FROM products", fetch=True)]
        t1, t2 = st.tabs(["📤 Retirada de Material", "📥 Retorno de Sobra"])
        
        with t1:
            with st.form("m_out"):
                p = st.selectbox("Item", prods)
                q = st.number_input("Quantidade para levar", min_value=1)
                tec = st.text_input("Técnico Responsável / Destino")
                if st.form_submit_button("Confirmar Retirada"):
                    atual = run_query("SELECT quantity FROM products WHERE name=?", (p,), fetch=True)[0][0]
                    if atual - q < 0: st.error("Saldo insuficiente no estoque.")
                    else:
                        run_query("UPDATE products SET quantity=? WHERE name=?", (atual-q, p))
                        run_query("INSERT INTO transactions (timestamp, user, product_name, type, qty_change, origin, destination) VALUES (?,?,?,?,?,?,?)",
                                  (datetime.now().strftime("%d/%m/%Y %H:%M"), st.session_state['user'], p, 'MALETA_SAIDA', -q, 'Estoque', tec))
                        st.success("Retirada registrada!")
        with t2:
            with st.form("m_in"):
                p = st.selectbox("Item", prods, key="m_in_p")
                q = st.number_input("Quantidade que sobrou", min_value=1, key="m_in_q")
                if st.form_submit_button("Confirmar Devolução ao Estoque"):
                    atual = run_query("SELECT quantity FROM products WHERE name=?", (p,), fetch=True)[0][0]
                    run_query("UPDATE products SET quantity=? WHERE name=?", (atual+q, p))
                    run_query("INSERT INTO transactions (timestamp, user, product_name, type, qty_change, origin, destination) VALUES (?,?,?,?,?,?,?)",
                              (datetime.now().strftime("%d/%m/%Y %H:%M"), st.session_state['user'], p, 'MALETA_RETORNO', q, 'Técnico/Sobra', 'Estoque'))
                    st.success("Item devolvido ao saldo principal!")

    elif menu == "Histórico":
        st.title("📜 Logs do Sistema")
        df = pd.read_sql_query("SELECT timestamp as Data, user as Usuário, product_name as Produto, type as Tipo, qty_change as Qtd, origin as Origem, destination as Destino FROM transactions ORDER BY id DESC", sqlite3.connect('techstock.db'))
        st.dataframe(df, use_container_width=True, hide_index=True)

    elif menu == "Minha Conta":
        st.title("👤 Alterar Senha")
        with st.form("ch_pw"):
            o = st.text_input("Senha Atual", type="password")
            n = st.text_input("Nova Senha", type="password")
            c = st.text_input("Confirmar Nova Senha", type="password")
            if st.form_submit_button("Mudar Senha"):
                res = run_query("SELECT password FROM users WHERE username=?", (st.session_state['user'],), fetch=True)
                if check_hashes(o, res[0][0]) and n == c and n != "":
                    run_query("UPDATE users SET password=? WHERE username=?", (make_hashes(n), st.session_state['user']))
                    st.success("Senha atualizada!")
                else:
                    st.error("Verifique os dados digitados.")

    elif menu == "Gerenciar Usuários":
        st.title("👥 Gestão de Equipe")
        with st.form("new_u"):
            u = st.text_input("Novo Usuário (Login)")
            p = st.text_input("Senha Inicial", type="password")
            r = st.selectbox("Nível de Acesso", ["user", "admin"])
            if st.form_submit_button("Cadastrar Funcionário"):
                run_query("INSERT INTO users VALUES (?,?,?)", (u, make_hashes(p), r))
                st.success("Usuário criado com sucesso!")

    # --- RODAPÉ FIXO ---
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    st.markdown("""
        <style>
        .footer {position: fixed; bottom: 0; left: 0; width: 100%; background-color: #f8f9fa; color: #31333F; 
                 text-align: center; padding: 10px 0; border-top: 1px solid #e6e9ef; z-index: 999; font-size: 14px;}
        .main .block-container {padding-bottom: 80px;}
        </style>
        <div class="footer">© 2026 <b>LS Tecnologias</b> - Todos os direitos reservados.</div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()