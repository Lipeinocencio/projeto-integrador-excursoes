import os
import sqlite3
import mercadopago
from flask import Flask, render_template, request, redirect, session
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'chave_secreta_caroli_excursoes'

# --- CONFIGURAÇÃO DE CAMINHOS REAIS (HOSTINGER/CPANEL) ---
# Onde o seu código e o banco de dados moram
PASTA_CODIGO = '/home/dominionulocom/codigo_pi'
# Onde o seu site exibe as fotos para o público
PASTA_PUBLICA = '/home/dominionulocom/projetointegrador'

# Endereço FIXO do Banco de Dados
DB_NAME = os.path.join(PASTA_CODIGO, 'sistema.db')

# Endereço FIXO das Imagens
UPLOAD_FOLDER = os.path.join(PASTA_PUBLICA, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- CREDENCIAL DO MERCADO PAGO ---
sdk = mercadopago.SDK("APP_USR-4508380654619786-050619-e6b70695379fd4e5cdd4ded2c2614463-3384502064")

def salvar_imagem(file_obj):
    if file_obj and file_obj.filename != '':
        nome = secure_filename(file_obj.filename)
        file_obj.save(os.path.join(app.config['UPLOAD_FOLDER'], nome))
        return nome
    return None

def inicializar_banco():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS viagens (id INTEGER PRIMARY KEY AUTOINCREMENT, destino TEXT NOT NULL, data TEXT NOT NULL, vagas_totais INTEGER, preco REAL, imagem TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, email TEXT NOT NULL UNIQUE, senha TEXT NOT NULL, cpf TEXT NOT NULL, telefone TEXT NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS reservas (id INTEGER PRIMARY KEY AUTOINCREMENT, id_usuario INTEGER, id_viagem INTEGER, data_reserva TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (id_usuario) REFERENCES usuarios(id), FOREIGN KEY (id_viagem) REFERENCES viagens(id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS configuracoes (id INTEGER PRIMARY KEY CHECK (id = 1), nome_agencia TEXT, logo TEXT, banner1_img TEXT, banner1_link TEXT, banner2_img TEXT, banner2_link TEXT, passo1_tit TEXT, passo1_desc TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS depoimentos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, nota INTEGER, texto TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS faqs (id INTEGER PRIMARY KEY AUTOINCREMENT, pergunta TEXT, resposta TEXT)''')
    
    cursor.execute("SELECT id FROM configuracoes WHERE id=1")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO configuracoes (id, nome_agencia, banner1_link, banner2_link, passo1_tit, passo1_desc) VALUES (1, 'PI Excursões', '#', '#', 'Escolha e Compre', 'Selecione o evento desejado e pague com segurança.')")
    
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
    viagens = cursor.execute("SELECT * FROM viagens").fetchall()
    usuarios = cursor.execute("SELECT * FROM usuarios").fetchall()
    
    clientes_lista = []
    for u in usuarios:
        compras = cursor.execute('''SELECT v.destino, v.data FROM reservas r JOIN viagens v ON r.id_viagem = v.id WHERE r.id_usuario = ?''', (u[0],)).fetchall()
        clientes_lista.append({'nome': u[1], 'email': u[2], 'cpf': u[4], 'telefone': u[5], 'compras': compras})

    total_viagens = len(viagens)
    total_clientes = len(usuarios)
    total_reservas = cursor.execute("SELECT COUNT(*) FROM reservas").fetchone()[0]
    faturamento_db = cursor.execute('''SELECT SUM(v.preco) FROM reservas r JOIN viagens v ON r.id_viagem = v.id''').fetchone()[0]
    
    faturamento = faturamento_db if faturamento_db else 0.0
    faturamento_formatado = f"{faturamento:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    stats = {'viagens': total_viagens, 'clientes': total_clientes, 'reservas': total_reservas, 'faturamento': faturamento_formatado}
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
    try:
        conn = sqlite3.connect(DB_NAME)
        viagem = conn.cursor().execute("SELECT * FROM viagens WHERE id=?", (id,)).fetchone()
        conn.close()
        config, deps, faqs = obter_dados_cms()
        
        if not viagem:
            # Mostra o caminho que ele tentou ler para debug
            return f"<h1 style='color:#367C2B'>ID {id} não encontrado.</h1><p>Base de dados em uso: {DB_NAME}</p>", 200
            
        return render_template('editar.html', v=viagem, conf=config)
    except Exception as e:
        return f"<h1 style='color:#367C2B'>Erro na edição:</h1><p>{str(e)}</p>", 200

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

# --- ROTAS DO CMS E SITE ---
@app.route('/salvar_identidade', methods=['POST'])
def salvar_identidade():
    nome_agencia = request.form.get('nome_agencia')
    b1_link, b2_link = request.form.get('banner1_link'), request.form.get('banner2_link')
    logo, b1_img, b2_img = salvar_imagem(request.files.get('logo')), salvar_imagem(request.files.get('banner1_img')), salvar_imagem(request.files.get('banner2_img'))
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE configuracoes SET nome_agencia=?, banner1_link=?, banner2_link=? WHERE id=1', (nome_agencia, b1_link, b2_link))
    if logo: cursor.execute("UPDATE configuracoes SET logo=? WHERE id=1", (logo,))
    if b1_img: cursor.execute("UPDATE configuracoes SET banner1_img=? WHERE id=1", (b1_img,))
    if b2_img: cursor.execute("UPDATE configuracoes SET banner2_img=? WHERE id=1", (b2_img,))
    conn.commit()
    conn.close()
    return redirect('/#pane-config-site')

@app.route('/site')
def site_oficial():
    conn = sqlite3.connect(DB_NAME)
    viagens = conn.cursor().execute("SELECT * FROM viagens").fetchall()
    conn.close()
    config, deps, faqs = obter_dados_cms()
    return render_template('site.html', lista=viagens, conf=config, deps=deps, faqs=faqs)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET': return render_template('login.html')
    email, senha = request.form.get('email'), request.form.get('senha')
    conn = sqlite3.connect(DB_NAME)
    usuario = conn.cursor().execute("SELECT * FROM usuarios WHERE email = ? AND senha = ?", (email, senha)).fetchone()
    conn.close()
    if usuario:
        session['usuario_id'], session['usuario_nome'] = usuario[0], usuario[1]
        return redirect('/dashboard')
    return "<h1>Erro: Login incorreto!</h1><a href='/login'>Tentar novamente</a>"

@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session: return redirect('/login')
    conn = sqlite3.connect(DB_NAME)
    viagens = conn.cursor().execute("SELECT * FROM viagens").fetchall()
    conn.close()
    config, _, _ = obter_dados_cms()
    return render_template('dashboard.html', lista=viagens, conf=config)

@app.route('/comprar/<int:id_viagem>')
def comprar(id_viagem):
    if 'usuario_id' not in session: return redirect('/login')
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        viagem = cursor.execute("SELECT * FROM viagens WHERE id = ?", (id_viagem,)).fetchone()
        cursor.execute("INSERT INTO reservas (id_usuario, id_viagem) VALUES (?, ?)", (session['usuario_id'], id_viagem))
        conn.commit()
        conn.close()
        preference_data = {
            "items": [{"title": f"Excursão: {viagem[1]}", "quantity": 1, "currency_id": "BRL", "unit_price": float(viagem[4])}],
            "back_urls": {"success": "https://projetointegrador.dominionulo.com.br/sucesso", "failure": "https://projetointegrador.dominionulo.com.br/falha", "pending": "https://projetointegrador.dominionulo.com.br/pendente"},
            "auto_return": "approved"
        }
        preference_response = sdk.preference().create(preference_data)
        return redirect(preference_response["response"]["init_point"])
    except Exception as e:
        return f"<h1>Erro no pagamento:</h1><p>{str(e)}</p>"

@app.route('/sucesso')
def sucesso(): return f"<div style='text-align:center; margin-top:100px;'><h1>Pagamento Aprovado! 🎉</h1><a href='/dashboard' style='background:#367C2B; color:white; padding:10px; text-decoration:none;'>Voltar</a></div>"

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)
