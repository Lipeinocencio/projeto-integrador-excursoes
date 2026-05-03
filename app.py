import os
import sqlite3
from flask import Flask, render_template, request, redirect, session
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'chave_secreta_caroli_excursoes'

# --- CONFIGURAÇÃO PARA UPLOAD DE IMAGENS ---
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def salvar_imagem(file_obj):
    if file_obj and file_obj.filename != '':
        nome = secure_filename(file_obj.filename)
        file_obj.save(os.path.join(app.config['UPLOAD_FOLDER'], nome))
        return nome
    return None

# --- 1. CONFIGURAÇÃO DO BANCO DE DADOS ---
def inicializar_banco():
    conn = sqlite3.connect('excursoes.db')
    cursor = conn.cursor()

    # Tabelas de Sistema
    cursor.execute('''CREATE TABLE IF NOT EXISTS viagens (id INTEGER PRIMARY KEY AUTOINCREMENT, destino TEXT NOT NULL, data TEXT NOT NULL, vagas_totais INTEGER, preco REAL, imagem TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, email TEXT NOT NULL UNIQUE, senha TEXT NOT NULL, cpf TEXT NOT NULL, telefone TEXT NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS reservas (id INTEGER PRIMARY KEY AUTOINCREMENT, id_usuario INTEGER, id_viagem INTEGER, data_reserva TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (id_usuario) REFERENCES usuarios(id), FOREIGN KEY (id_viagem) REFERENCES viagens(id))''')

    # Tabela do CMS (Configurações do Site)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS configuracoes (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        nome_agencia TEXT, logo TEXT,
        banner1_img TEXT, banner1_tit TEXT, banner1_sub TEXT,
        banner2_img TEXT, banner2_tit TEXT, banner2_sub TEXT,
        passo1_tit TEXT, passo1_desc TEXT,
        dep1_nome TEXT, dep1_nota INTEGER, dep1_texto TEXT,
        dep2_nome TEXT, dep2_nota INTEGER, dep2_texto TEXT,
        faq1_perg TEXT, faq1_resp TEXT,
        faq2_perg TEXT, faq2_resp TEXT
    )
    ''')

    # Insere as configurações padrão
    cursor.execute("SELECT id FROM configuracoes WHERE id=1")
    if not cursor.fetchone():
        cursor.execute('''
        INSERT INTO configuracoes (
            id, nome_agencia, banner1_tit, banner1_sub, banner2_tit, banner2_sub, 
            passo1_tit, passo1_desc, dep1_nome, dep1_nota, dep1_texto, 
            dep2_nome, dep2_nota, dep2_texto, faq1_perg, faq1_resp, faq2_perg, faq2_resp
        ) VALUES (
            1, 'PI Excursões', 'Sua Próxima Viagem Começa Aqui', 'Conforto e segurança para os melhores eventos.', 
            'Pacotes Especiais', 'Transporte e praticidade em um só lugar.', 
            'Escolha e Compre', 'Selecione o evento desejado e pague com segurança.', 
            'Mariana Silva', 5, 'Fui no evento do ano passado e foi incrível. Ônibus confortável.', 
            'Carlos Eduardo', 5, 'A praticidade não tem preço. Recomendo!', 
            'O ônibus tem ar-condicionado?', 'Sim! Todos os nossos veículos possuem climatização.', 
            'Inclui ingresso?', 'Apenas o transporte, a menos que especificado explicitamente.'
        )
        ''')

    conn.commit()
    conn.close()

inicializar_banco()


# --- 2. ROTAS DO PAINEL ADMINISTRATIVO ---
@app.route('/')
def index():
    conn = sqlite3.connect('excursoes.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM viagens")
    viagens = cursor.fetchall()
    cursor.execute("SELECT * FROM configuracoes WHERE id=1")
    config = cursor.fetchone()
    conn.close()
    return render_template('index.html', lista=viagens, conf=config)

@app.route('/cadastrar', methods=['POST'])
def cadastrar():
    destino, data, vagas, preco = request.form.get('destino'), request.form.get('data'), request.form.get('vagas'), request.form.get('preco')
    imagem_nome = salvar_imagem(request.files.get('imagem'))
    
    conn = sqlite3.connect('excursoes.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO viagens (destino, data, vagas_totais, preco, imagem) VALUES (?, ?, ?, ?, ?)", (destino, data, vagas, preco, imagem_nome))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/salvar_identidade', methods=['POST'])
def salvar_identidade():
    nome_agencia = request.form.get('nome_agencia')
    b1_tit, b1_sub = request.form.get('banner1_tit'), request.form.get('banner1_sub')
    b2_tit, b2_sub = request.form.get('banner2_tit'), request.form.get('banner2_sub')
    logo, b1_img, b2_img = salvar_imagem(request.files.get('logo')), salvar_imagem(request.files.get('banner1_img')), salvar_imagem(request.files.get('banner2_img'))

    conn = sqlite3.connect('excursoes.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE configuracoes SET nome_agencia=?, banner1_tit=?, banner1_sub=?, banner2_tit=?, banner2_sub=? WHERE id=1', (nome_agencia, b1_tit, b1_sub, b2_tit, b2_sub))
    if logo: cursor.execute("UPDATE configuracoes SET logo=? WHERE id=1", (logo,))
    if b1_img: cursor.execute("UPDATE configuracoes SET banner1_img=? WHERE id=1", (b1_img,))
    if b2_img: cursor.execute("UPDATE configuracoes SET banner2_img=? WHERE id=1", (b2_img,))
    conn.commit()
    conn.close()
    return redirect('/#pane-config-site')

@app.route('/salvar_conteudo', methods=['POST'])
def salvar_conteudo():
    p1_tit, p1_desc = request.form.get('passo1_tit'), request.form.get('passo1_desc')
    d1_n, d1_no, d1_t = request.form.get('dep1_nome'), request.form.get('dep1_nota'), request.form.get('dep1_texto')
    d2_n, d2_no, d2_t = request.form.get('dep2_nome'), request.form.get('dep2_nota'), request.form.get('dep2_texto')
    f1_p, f1_r = request.form.get('faq1_perg'), request.form.get('faq1_resp')
    f2_p, f2_r = request.form.get('faq2_perg'), request.form.get('faq2_resp')

    conn = sqlite3.connect('excursoes.db')
    cursor = conn.cursor()
    cursor.execute('''UPDATE configuracoes SET passo1_tit=?, passo1_desc=?, dep1_nome=?, dep1_nota=?, dep1_texto=?, dep2_nome=?, dep2_nota=?, dep2_texto=?, faq1_perg=?, faq1_resp=?, faq2_perg=?, faq2_resp=? WHERE id=1''', (p1_tit, p1_desc, d1_n, d1_no, d1_t, d2_n, d2_no, d2_t, f1_p, f1_r, f2_p, f2_r))
    conn.commit()
    conn.close()
    return redirect('/#pane-config-site')

# --- 3. ROTA DO SITE OFICIAL DINÂMICO ---
@app.route('/site')
def site_oficial():
    conn = sqlite3.connect('excursoes.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM viagens")
    viagens = cursor.fetchall()
    cursor.execute("SELECT * FROM configuracoes WHERE id=1")
    config = cursor.fetchone()
    conn.close()
    return render_template('site.html', lista=viagens, conf=config)

# --- 4. ROTAS ÁREA DO CLIENTE ---
@app.route('/cadastro')
def tela_cadastro(): return render_template('cadastro.html')

@app.route('/cadastrar_usuario', methods=['POST'])
def cadastrar_usuario():
    nome, email, senha, cpf, telefone = request.form.get('nome'), request.form.get('email'), request.form.get('senha'), request.form.get('cpf'), request.form.get('telefone')
    conn = sqlite3.connect('excursoes.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO usuarios (nome, email, senha, cpf, telefone) VALUES (?, ?, ?, ?, ?)", (nome, email, senha, cpf, telefone))
        conn.commit()
    except:
        return "<h1>Erro: Este e-mail já está em uso!</h1><a href='/cadastro'>Voltar</a>"
    finally: conn.close()
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET': return render_template('login.html')
    email, senha = request.form.get('email'), request.form.get('senha')
    conn = sqlite3.connect('excursoes.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE email = ? AND senha = ?", (email, senha))
    usuario = cursor.fetchone()
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
    conn = sqlite3.connect('excursoes.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM viagens")
    viagens = cursor.fetchall()
    conn.close()
    return render_template('dashboard.html', lista=viagens)

@app.route('/comprar/<int:id_viagem>')
def comprar(id_viagem):
    if 'usuario_id' not in session: return redirect('/login')
    conn = sqlite3.connect('excursoes.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO reservas (id_usuario, id_viagem) VALUES (?, ?)", (session['usuario_id'], id_viagem))
    conn.commit()
    conn.close()
    return "<h1>Reserva Confirmada!</h1><a href='/dashboard'>Voltar ao Dashboard</a>"

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)
