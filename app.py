import os
import sqlite3
import mercadopago
from flask import Flask, render_template, request, redirect, session
from werkzeug.utils import secure_filename

# 1. DEFINIÇÃO DE CAMINHOS ABSOLUTOS (ESSENCIAL PARA CPANEL)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_PUBLICA = '/home/dominionulocom/projetointegrador'
DB_NAME = os.path.join(BASE_DIR, 'sistema.db')

app = Flask(__name__, 
            static_folder=os.path.join(PASTA_PUBLICA, 'static'),
            template_folder=os.path.join(BASE_DIR, 'templates'))

app.secret_key = 'chave_secreta_caroli_excursoes'

# --- CREDENCIAL DO MERCADO PAGO ---
sdk = mercadopago.SDK("APP_USR-4508380654619786-050619-e6b70695379fd4e5cdd4ded2c2614463-3384502064")

# --- CONFIGURAÇÃO DE UPLOADS ---
UPLOAD_FOLDER = os.path.join(PASTA_PUBLICA, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ... (Mantenha as funções auxiliares e a rota index iguais) ...

# --- ROTA DE EDITAR COM RASTREADOR DE ERRO ---
@app.route('/editar/<int:id>')
def editar_viagem(id):
    try:
        conn = sqlite3.connect(DB_NAME)
        viagem = conn.cursor().execute("SELECT * FROM viagens WHERE id=?", (id,)).fetchone()
        conn.close()
        
        if not viagem:
            return "<h1>Aviso: Nenhuma viagem encontrada com este ID.</h1>", 200
            
        return render_template('editar.html', v=viagem)
    except Exception as e:
        # O ", 200" engana o LiteSpeed para ele exibir o nosso texto em vez da tela preta
        return f"<h1 style='color:#367C2B'>O VERDADEIRO ERRO É:</h1><p>{str(e)}</p>", 200
# ... (Mantenha o restante do código igual) ...

def salvar_imagem(file_obj):
    if file_obj and file_obj.filename != '':
        nome = secure_filename(file_obj.filename)
        file_obj.save(os.path.join(app.config['UPLOAD_FOLDER'], nome))
        return nome
    return None

def inicializar_banco():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Tabelas do Sistema
    cursor.execute('''CREATE TABLE IF NOT EXISTS viagens (id INTEGER PRIMARY KEY AUTOINCREMENT, destino TEXT NOT NULL, data TEXT NOT NULL, vagas_totais INTEGER, preco REAL, imagem TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, email TEXT NOT NULL UNIQUE, senha TEXT NOT NULL, cpf TEXT NOT NULL, telefone TEXT NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS reservas (id INTEGER PRIMARY KEY AUTOINCREMENT, id_usuario INTEGER, id_viagem INTEGER, data_reserva TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (id_usuario) REFERENCES usuarios(id), FOREIGN KEY (id_viagem) REFERENCES viagens(id))''')

    # Novas Tabelas do CMS
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS configuracoes (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        nome_agencia TEXT, logo TEXT,
        banner1_img TEXT, banner1_link TEXT,
        banner2_img TEXT, banner2_link TEXT,
        passo1_tit TEXT, passo1_desc TEXT
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS depoimentos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, nota INTEGER, texto TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS faqs (id INTEGER PRIMARY KEY AUTOINCREMENT, pergunta TEXT, resposta TEXT)''')

    cursor.execute("SELECT id FROM configuracoes WHERE id=1")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO configuracoes (id, nome_agencia, banner1_link, banner2_link, passo1_tit, passo1_desc) VALUES (1, 'PI Excursões', '#', '#', 'Escolha e Compre', 'Selecione o evento desejado e pague com segurança.')")
        cursor.execute("INSERT INTO depoimentos (nome, nota, texto) VALUES ('Mariana Silva', 5, 'Ônibus super confortável, recomendo muito!')")
        cursor.execute("INSERT INTO faqs (pergunta, resposta) VALUES ('O ônibus tem ar-condicionado?', 'Sim! Todos os nossos veículos possuem ar e banheiro.')")

    conn.commit()
    conn.close()

inicializar_banco()

def obter_dados_cms():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    config = cursor.execute("SELECT * FROM configuracoes WHERE id=1").fetchone()
    deps = cursor.execute("SELECT * FROM depoimentos ORDER BY id DESC").fetchall()
    faqs = cursor.execute("SELECT * FROM faqs ORDER BY id DESC").fetchall()
    conn.close()
    return config, deps, faqs

# --- ROTAS ADMINISTRATIVAS ---
@app.route('/')
def index():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Busca as viagens normais
    viagens = cursor.execute("SELECT * FROM viagens").fetchall()
    
    # 2. Busca os usuários
    usuarios = cursor.execute("SELECT * FROM usuarios").fetchall()
    
    # 3. Mágica: Para cada usuário, busca as viagens que ele comprou
    clientes_lista = []
    for u in usuarios:
        id_usuario = u[0]
        compras = cursor.execute('''
            SELECT v.destino, v.data 
            FROM reservas r 
            JOIN viagens v ON r.id_viagem = v.id 
            WHERE r.id_usuario = ?
        ''', (id_usuario,)).fetchall()
        
        clientes_lista.append({
            'nome': u[1],
            'email': u[2],
            'cpf': u[4],
            'telefone': u[5],
            'compras': compras
        })

    # --- MATEMÁTICA DO DASHBOARD ---
    total_viagens = len(viagens)
    total_clientes = len(usuarios)
    total_reservas = cursor.execute("SELECT COUNT(*) FROM reservas").fetchone()[0]
    
    faturamento_db = cursor.execute('''
        SELECT SUM(v.preco) 
        FROM reservas r 
        JOIN viagens v ON r.id_viagem = v.id
    ''').fetchone()[0]
    
    faturamento = faturamento_db if faturamento_db else 0.0
    faturamento_formatado = f"{faturamento:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    stats = {
        'viagens': total_viagens,
        'clientes': total_clientes,
        'reservas': total_reservas,
        'faturamento': faturamento_formatado
    }
        
    conn.close()
    config, deps, faqs = obter_dados_cms()
    
    return render_template('index.html', lista=viagens, clientes=clientes_lista, conf=config, deps=deps, faqs=faqs, stats=stats)

@app.route('/cadastrar', methods=['POST'])
def cadastrar():
    destino, data, vagas, preco = request.form.get('destino'), request.form.get('data'), request.form.get('vagas'), request.form.get('preco')
    imagem_nome = salvar_imagem(request.files.get('imagem'))
    conn = sqlite3.connect(DB_NAME)
    conn.cursor().execute("INSERT INTO viagens (destino, data, vagas_totais, preco, imagem) VALUES (?, ?, ?, ?, ?)", (destino, data, vagas, preco, imagem_nome))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/editar/<int:id>')
def editar_viagem(id):
    conn = sqlite3.connect(DB_NAME)
    viagem = conn.cursor().execute("SELECT * FROM viagens WHERE id=?", (id,)).fetchone()
    conn.close()
    return render_template('editar.html', v=viagem)

@app.route('/atualizar/<int:id>', methods=['POST'])
def atualizar_viagem(id):
    destino, data, vagas, preco = request.form.get('destino'), request.form.get('data'), request.form.get('vagas'), request.form.get('preco')
    imagem_nome = salvar_imagem(request.files.get('imagem'))
    conn = sqlite3.connect(DB_NAME)
    if imagem_nome:
        conn.cursor().execute("UPDATE viagens SET destino=?, data=?, vagas_totais=?, preco=?, imagem=? WHERE id=?", (destino, data, vagas, preco, imagem_nome, id))
    else:
        conn.cursor().execute("UPDATE viagens SET destino=?, data=?, vagas_totais=?, preco=? WHERE id=?", (destino, data, vagas, preco, id))
    conn.commit()
    conn.close()
    return redirect('/')

# --- ROTAS DO CMS ---
@app.route('/salvar_identidade', methods=['POST'])
def salvar_identidade():
    nome_agencia = request.form.get('nome_agencia')
    b1_link, b2_link = request.form.get('banner1_link'), request.form.get('banner2_link')
    
    logo = salvar_imagem(request.files.get('logo'))
    b1_img = salvar_imagem(request.files.get('banner1_img'))
    b2_img = salvar_imagem(request.files.get('banner2_img'))

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE configuracoes SET nome_agencia=?, banner1_link=?, banner2_link=? WHERE id=1', (nome_agencia, b1_link, b2_link))
    if logo: cursor.execute("UPDATE configuracoes SET logo=? WHERE id=1", (logo,))
    if b1_img: cursor.execute("UPDATE configuracoes SET banner1_img=? WHERE id=1", (b1_img,))
    if b2_img: cursor.execute("UPDATE configuracoes SET banner2_img=? WHERE id=1", (b2_img,))
    conn.commit()
    conn.close()
    return redirect('/#pane-config-site')

@app.route('/salvar_passo', methods=['POST'])
def salvar_passo():
    p1_tit, p1_desc = request.form.get('passo1_tit'), request.form.get('passo1_desc')
    conn = sqlite3.connect(DB_NAME)
    conn.cursor().execute('UPDATE configuracoes SET passo1_tit=?, passo1_desc=? WHERE id=1', (p1_tit, p1_desc))
    conn.commit()
    conn.close()
    return redirect('/#pane-config-site')

@app.route('/add_depoimento', methods=['POST'])
def add_depoimento():
    nome, nota, texto = request.form.get('nome'), request.form.get('nota'), request.form.get('texto')
    conn = sqlite3.connect(DB_NAME)
    conn.cursor().execute("INSERT INTO depoimentos (nome, nota, texto) VALUES (?, ?, ?)", (nome, nota, texto))
    conn.commit()
    conn.close()
    return redirect('/#pane-config-site')

@app.route('/del_depoimento/<int:id>')
def del_depoimento(id):
    conn = sqlite3.connect(DB_NAME)
    conn.cursor().execute("DELETE FROM depoimentos WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect('/#pane-config-site')

@app.route('/add_faq', methods=['POST'])
def add_faq():
    pergunta, resposta = request.form.get('pergunta'), request.form.get('resposta')
    conn = sqlite3.connect(DB_NAME)
    conn.cursor().execute("INSERT INTO faqs (pergunta, resposta) VALUES (?, ?)", (pergunta, resposta))
    conn.commit()
    conn.close()
    return redirect('/#pane-config-site')

@app.route('/del_faq/<int:id>')
def del_faq(id):
    conn = sqlite3.connect(DB_NAME)
    conn.cursor().execute("DELETE FROM faqs WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect('/#pane-config-site')

# --- ROTAS DO SITE E CLIENTE ---
@app.route('/site')
def site_oficial():
    conn = sqlite3.connect(DB_NAME)
    viagens = conn.cursor().execute("SELECT * FROM viagens").fetchall()
    conn.close()
    config, deps, faqs = obter_dados_cms()
    return render_template('site.html', lista=viagens, conf=config, deps=deps, faqs=faqs)

@app.route('/cadastro')
def tela_cadastro(): 
    return render_template('cadastro.html')

@app.route('/cadastrar_usuario', methods=['POST'])
def cadastrar_usuario():
    nome, email, senha, cpf, telefone = request.form.get('nome'), request.form.get('email'), request.form.get('senha'), request.form.get('cpf'), request.form.get('telefone')
    conn = sqlite3.connect(DB_NAME)
    try:
        conn.cursor().execute("INSERT INTO usuarios (nome, email, senha, cpf, telefone) VALUES (?, ?, ?, ?, ?)", (nome, email, senha, cpf, telefone))
        conn.commit()
    except:
        return "<h1>Erro: Este e-mail já está em uso!</h1><a href='/cadastro'>Voltar</a>"
    finally: 
        conn.close()
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET': 
        return render_template('login.html')
    
    email, senha = request.form.get('email'), request.form.get('senha')
    conn = sqlite3.connect(DB_NAME)
    usuario = conn.cursor().execute("SELECT * FROM usuarios WHERE email = ? AND senha = ?", (email, senha)).fetchone()
    conn.close()
    
    if usuario:
        session['usuario_id'] = usuario[0]
        session['usuario_nome'] = usuario[1]
        return redirect('/dashboard')
    else:
        return "<h1>Erro: Login ou senha incorretos!</h1><a href='/login'>Tentar novamente</a>"

@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session: return redirect('/login')
    conn = sqlite3.connect(DB_NAME)
    viagens = conn.cursor().execute("SELECT * FROM viagens").fetchall()
    conn.close()
    return render_template('dashboard.html', lista=viagens)

# --- INTEGRAÇÃO MERCADO PAGO ---
@app.route('/comprar/<int:id_viagem>')
def comprar(id_viagem):
    if 'usuario_id' not in session: return redirect('/login')
    
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Busca a excursão
        viagem = cursor.execute("SELECT * FROM viagens WHERE id = ?", (id_viagem,)).fetchone()
        
        # Registra a reserva
        cursor.execute("INSERT INTO reservas (id_usuario, id_viagem) VALUES (?, ?)", (session['usuario_id'], id_viagem))
        conn.commit()
        conn.close()

        # Cria a cobrança no Mercado Pago
        preference_data = {
            "items": [
                {
                    "title": f"Excursão: {viagem[1]}",
                    "quantity": 1,
                    "currency_id": "BRL",
                    "unit_price": float(viagem[4])
                }
            ],
            "back_urls": {
                "success": "https://projetointegrador.dominionulo.com.br/sucesso",
                "failure": "https://projetointegrador.dominionulo.com.br/falha",
                "pending": "https://projetointegrador.dominionulo.com.br/pendente"
            },
            "auto_return": "approved"
        }

        preference_response = sdk.preference().create(preference_data)
        
        # VERIFICAÇÃO DE ERRO
        if "response" not in preference_response or "init_point" not in preference_response["response"]:
            return f"<h1>O Mercado Pago recusou a ligação. Erro:</h1><p>{preference_response}</p>"
        
        # Redireciona o cliente para a tela de pagamento
        return redirect(preference_response["response"]["init_point"])

    except Exception as e:
        return f"<h1>Erro interno no servidor:</h1><p>{str(e)}</p>"

# --- ROTAS DE RETORNO DO PAGAMENTO ---
@app.route('/sucesso')
def sucesso():
    return "<div style='text-align:center; margin-top:100px; font-family:sans-serif;'><h1>Pagamento Aprovado! 🎉</h1><p>A tua vaga está garantida na excursão.</p><br><a href='/dashboard' style='background:#2980b9; color:white; padding:10px 20px; text-decoration:none; border-radius:5px;'>Voltar às minhas viagens</a></div>"

@app.route('/falha')
def falha():
    return "<div style='text-align:center; margin-top:100px; font-family:sans-serif;'><h1>Pagamento Recusado ❌</h1><p>Houve um problema com a tua transação. Tente novamente.</p><br><a href='/dashboard' style='background:#e74c3c; color:white; padding:10px 20px; text-decoration:none; border-radius:5px;'>Tentar Novamente</a></div>"

@app.route('/pendente')
def pendente():
    return "<div style='text-align:center; margin-top:100px; font-family:sans-serif;'><h1>Pagamento Pendente ⏳</h1><p>Estamos a aguardar a compensação do teu Pix ou Boleto.</p><br><a href='/dashboard' style='background:#f39c12; color:white; padding:10px 20px; text-decoration:none; border-radius:5px;'>Acompanhar Pedido</a></div>"

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)
