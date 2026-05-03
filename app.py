import os
import sqlite3
from flask import Flask, render_template, request, redirect, session
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'chave_secreta_caroli_excursoes'

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def salvar_imagem(file_obj):
    if file_obj and file_obj.filename != '':
        nome = secure_filename(file_obj.filename)
        file_obj.save(os.path.join(app.config['UPLOAD_FOLDER'], nome))
        return nome
    return None

def inicializar_banco():
    conn = sqlite3.connect('excursoes.db')
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS viagens (id INTEGER PRIMARY KEY AUTOINCREMENT, destino TEXT NOT NULL, data TEXT NOT NULL, vagas_totais INTEGER, preco REAL, imagem TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, email TEXT NOT NULL UNIQUE, senha TEXT NOT NULL, cpf TEXT NOT NULL, telefone TEXT NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS reservas (id INTEGER PRIMARY KEY AUTOINCREMENT, id_usuario INTEGER, id_viagem INTEGER, data_reserva TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (id_usuario) REFERENCES usuarios(id), FOREIGN KEY (id_viagem) REFERENCES viagens(id))''')

    # Tabela CMS Atualizada (Sem titulos de banner, com links, e com 3 depoimentos/FAQs)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS configuracoes (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        nome_agencia TEXT, logo TEXT,
        banner1_img TEXT, banner1_link TEXT,
        banner2_img TEXT, banner2_link TEXT,
        passo1_tit TEXT, passo1_desc TEXT,
        dep1_nome TEXT, dep1_nota INTEGER, dep1_texto TEXT,
        dep2_nome TEXT, dep2_nota INTEGER, dep2_texto TEXT,
        dep3_nome TEXT, dep3_nota INTEGER, dep3_texto TEXT,
        faq1_perg TEXT, faq1_resp TEXT,
        faq2_perg TEXT, faq2_resp TEXT,
        faq3_perg TEXT, faq3_resp TEXT
    )
    ''')

    cursor.execute("SELECT id FROM configuracoes WHERE id=1")
    if not cursor.fetchone():
        cursor.execute('''
        INSERT INTO configuracoes (
            id, nome_agencia, banner1_link, banner2_link, 
            passo1_tit, passo1_desc, 
            dep1_nome, dep1_nota, dep1_texto, 
            dep2_nome, dep2_nota, dep2_texto, 
            dep3_nome, dep3_nota, dep3_texto,
            faq1_perg, faq1_resp, faq2_perg, faq2_resp, faq3_perg, faq3_resp
        ) VALUES (
            1, 'PI Excursões', '#', '#', 
            'Escolha e Compre', 'Selecione o evento desejado e pague com segurança.', 
            'Mariana Silva', 5, 'Fui no evento do ano passado e foi incrível.', 
            'Carlos Eduardo', 5, 'A praticidade não tem preço. Recomendo!', 
            'Ana Paula', 5, 'Ônibus confortável e motoristas muito seguros.',
            'O ônibus tem ar-condicionado?', 'Sim! Todos os nossos veículos possuem climatização.', 
            'Inclui ingresso?', 'Apenas o transporte, a menos que especificado explicitamente.',
            'Quais são as formas de pagamento?', 'Aceitamos Pix e Cartão de Crédito.'
        )
        ''')

    conn.commit()
    conn.close()

inicializar_banco()


# --- ROTAS ADMINISTRATIVAS ---
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

# --- ROTA PARA EDITAR VIAGEM ---
@app.route('/editar/<int:id>')
def editar_viagem(id):
    conn = sqlite3.connect('excursoes.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM viagens WHERE id=?", (id,))
    viagem = cursor.fetchone()
    conn.close()
    return render_template('editar.html', v=viagem)

@app.route('/atualizar/<int:id>', methods=['POST'])
def atualizar_viagem(id):
    destino, data, vagas, preco = request.form.get('destino'), request.form.get('data'), request.form.get('vagas'), request.form.get('preco')
    imagem_nome = salvar_imagem(request.files.get('imagem'))
    conn = sqlite3.connect('excursoes.db')
    cursor = conn.cursor()
    if imagem_nome:
        cursor.execute("UPDATE viagens SET destino=?, data=?, vagas_totais=?, preco=?, imagem=? WHERE id=?", (destino, data, vagas, preco, imagem_nome, id))
    else:
        cursor.execute("UPDATE viagens SET destino=?, data=?, vagas_totais=?, preco=? WHERE id=?", (destino, data, vagas, preco, id))
    conn.commit()
    conn.close()
    return redirect('/')


# --- ROTAS DO CMS ---
@app.route('/salvar_identidade', methods=['POST'])
def salvar_identidade():
    nome_agencia = request.form.get('nome_agencia')
    b1_link, b2_link = request.form.get('banner1_link'), request.form.get('banner2_link')
    logo, b1_img, b2_img = salvar_imagem(request.files.get('logo')), salvar_imagem(request.files.get('banner1_img')), salvar_imagem(request.files.get('banner2_img'))

    conn = sqlite3.connect('excursoes.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE configuracoes SET nome_agencia=?, banner1_link=?, banner2_link=? WHERE id=1', (nome_agencia, b1_link, b2_link))
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
    d3_n, d3_no, d3_t = request.form.get('dep3_nome'), request.form.get('dep3_nota'), request.form.get('dep3_texto')
    f1_p, f1_r = request.form.get('faq1_perg'), request.form.get('faq1_resp')
    f2_p, f2_r = request.form.get('faq2_perg'), request.form.get('faq2_resp')
    f3_p, f3_r = request.form.get('faq3_perg'), request.form.get('faq3_resp')

    conn = sqlite3.connect('excursoes.db')
    cursor = conn.cursor()
    cursor.execute('''UPDATE configuracoes SET 
                      passo1_tit=?, passo1_desc=?, 
                      dep1_nome=?, dep1_nota=?, dep1_texto=?, 
                      dep2_nome=?, dep2_nota=?, dep2_texto=?, 
                      dep3_nome=?, dep3_nota=?, dep3_texto=?, 
                      faq1_perg=?, faq1_resp=?, 
                      faq2_perg=?, faq2_resp=?, 
                      faq3_perg=?, faq3_resp=? 
                      WHERE id=1''', 
                   (p1_tit, p1_desc, d1_n, d1_no, d1_t, d2_n, d2_no, d2_t, d3_n, d3_no, d3_t, f1_p, f1_r, f2_p, f2_r, f3_p, f3_r))
    conn.commit()
    conn.close()
    return redirect('/#pane-config-site')

# --- ROTAS DO SITE E CLIENTE ---
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
