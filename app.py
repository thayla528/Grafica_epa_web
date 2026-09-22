import os

import page
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, current_user, UserMixin

app = Flask(__name__)

# Chave de segurança para criptografia dos cookies da sessão
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'Grafica_EPA')

# URL oficial da sua API de 1022 linhas que roda na porta 5003
API_URL = 'http://127.0.0.1:5003'

# Configuração explícita para contornar o proxy da rede do SENAI
DESVIAR_PROXY = {"http": None, "https": None}

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class UserSession(UserMixin):
    def __init__(self, id, nome=None):
        self.id = id
        self.nome = nome

# ==============================================================================
# ADICIONADO: Obrigatório para o Flask-Login saber quem está conectado entre os cliques
# ==============================================================================
@login_manager.user_loader
def load_user(user_id):
    user_name = session.get('user_name')
    return UserSession(id=user_id, nome=user_name)


@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST']) # Adicionado 'GET' para renderizar a página inicialmente
def login():
    if current_user.is_authenticated:
        return redirect(url_for('login')) # Ajustado para redirecionar para uma rota válida existente

    if request.method == 'POST':
        credenciais = {
            "email": request.form.get('email'),
            "senha": request.form.get('senha'),
        }
        try:
            resposta = requests.post(f"{API_URL}/login", json=credenciais, timeout=5, proxies=DESVIAR_PROXY)
            if resposta.status_code == 200:
                dados_resposta = resposta.json()
                user_id = dados_resposta.get('user_id')
                user_name = dados_resposta.get('nome')

                # Salva o nome na sessão do Flask para o load_user ler depois
                session['user_name'] = user_name
                session.modified = True

                # Passa o ID e o Nome para a instância da sessão
                user = UserSession(id=user_id, nome=user_name)
                login_user(user)

                flash('Login realizado com sucesso!', 'success')
                return redirect(url_for('login'))
            else:
                dados_erro = resposta.json()
                erro = dados_erro.get('error') or dados_erro.get('erro') or 'Credenciais inválidas.'
                flash(erro, 'danger')
        except requests.exceptions.RequestException as e:
            print(f"\n[ERRO DE CONEXÃO NO LOGIN]: {e}\n")
            flash('Erro de conexão com o servidor central (API fora do ar).', 'danger')

    return render_template('login.html')


@app.route('/usuarios', methods=['GET', 'POST']) # Adicionado 'GET' para renderizar a página inicialmente
def cadastro():
    if current_user.is_authenticated:
        return redirect(url_for('centro_logistico'))

    if request.method == 'POST':
        dados_usuario = {
            "nome": request.form.get('nome'),
            "email": request.form.get('email'),
            "senha": request.form.get('senha'),
            "cpf": request.form.get('cpf'),
        }
        try:
            resposta = requests.post(f"{API_URL}/usuarios", json=dados_usuario, timeout=5, proxies=DESVIAR_PROXY)
            if resposta.status_code == 201:
                flash('Cadastro realizado com sucesso! Faça login.', 'success')
                return redirect(url_for('login'))
            else:
                dados_erro = resposta.json()
                erro = dados_erro.get('error') or dados_erro.get('erro') or 'Erro ao cadastrar.'
                flash(erro, 'danger')
        except requests.exceptions.RequestException as e:
            print(f"\n[ERRO DE CONEXÃO NO CADASTRO]: {e}\n")
            flash('Erro de conexão com o servidor central (API fora do ar).', 'danger')

    return render_template('cadastro.html')

@app.route('/equipe')

def montar_equipe():
    page = request.args.get('page', 1, type=int)

    try:
        resposta = requests.get(f"{API_URL}/equipe", params={"page": page}, timeout=5, proxies=DESVIAR_PROXY)
        if resposta.status_code == 200:
            dados = resposta.json()
            return render_template(
                'montar_equipe.html',
                equipe=dados.get('lista_equipe', []),       # AJUSTADO: era 'montar_equipe'
                current_page=dados.get('current_page', 1),
                total_pages=dados.get('total_pages', 1),
                total_items=dados.get('total_equipe', 0)    # AJUSTADO: era 'total_items'
            )
        else:
            flash('Erro ao carregar equipe de distribuição.', 'warning')
    except requests.exceptions.RequestException as e:
        print(f"Erro: {e}")
        flash('Servidor equipe offline.', 'danger')

    return render_template('equipe.html', equipe=[], current_page=1, total_pages=1, total_items=0)

@app.route('/cadastrar_equipe', methods=['GET', 'POST']) # SUGESTÃO: Mudei a rota web para não conflitar localmente com a de cima se estiverem no mesmo arquivo web

def cadastrar_equipe():
    if request.method == 'POST':
        # AJUSTADO: As chaves do dicionário agora batem exatamente com o que a API espera no request.get_json()
        dados_formulario = {
            "cpf": request.form.get('cpf_informados'),
            "nome_equipe": request.form.get('nome_da_equipe'),
        }
        try:
            resposta = requests.post(f"{API_URL}/equipe", json=dados_formulario, timeout=5, proxies=DESVIAR_PROXY)
            if resposta.status_code == 201:
                flash('Equipe de distribuição cadastrada com sucesso!', 'success')
                return redirect(url_for('visualizar_material'))
            elif resposta.status_code: # Adicionado 404 que sua API retorna se não achar o CPF
                flash(resposta.json().get('erro'), 'warning')
        except requests.exceptions.RequestException:
            flash('Servidor equipe offline.', 'danger')

    return render_template('api_equipe.html')


# 1. ROTA PARA EXIBIR A TELA E LISTAR AS PRODUÇÕES (GET)
@app.route('/producao', methods=['GET'])

def listar_producao():
    page = request.args.get('page', 1, type=int)

    # Simulação de filtros vindos do formulário de busca da tela (opcional)
    data_filtro = request.args.get('data_producao', '')
    func_filtro = request.args.get('fk_id_funcinario', '')

    params = {"page": page}
    if data_filtro: params["data_producao"] = data_filtro
    if func_filtro: params["fk_id_funcinario"] = func_filtro

    # ATENÇÃO: API exige JWT. Buscando o token que você salvou no login da Web
    token_jwt = session.get('token_jwt')
    headers = {"Authorization": f"Bearer {token_jwt}"}

    try:
        resposta = requests.get(
            f"{API_URL}/producao",
            params=params,
            headers=headers,
            timeout=5,
            proxies=DESVIAR_PROXY
        )

        if resposta.status_code == 200:
            dados = resposta.json()
            return render_template(
                'produçao.html',
                produçao=dados.get('producao', []),  # Bate com a chave da API
                current_page=dados.get('current_page', 1),
                total_pages=dados.get('total_pages', 1),
                total_items=dados.get('total_items', 0)  # Bate com a chave da API
            )
        elif resposta.status_code == 401:
            flash('Sua sessão expirou. Faça login novamente.', 'danger')
            return redirect(url_for('login'))
        else:
            flash('Erro ao carregar dados de produção.', 'warning')

    except requests.exceptions.RequestException as e:
        print(f"Erro de conexão: {e}")
        flash('Servidor de produção offline.', 'danger')

    return render_template('produçao.html', produçao=[], current_page=1, total_pages=1, total_items=0)


# 2. ROTA EXCLUSIVA PARA ENVIAR O CADASTRO (POST)
@app.route('/producao/cadastrar', methods=['POST'])

def cadastrar_producao():
    # Coleta os dados que o usuário digitou no <form> do HTML
    # Certifique-se de que os valores nos métodos .get() batem com os 'name' dos seus inputs HTML
    dados_formulario = {
        "fk_id_funcinario": request.form.get('fk_id_funcinario', type=int),
        "fk_id_equipe": request.form.get('fk_id_equipe', type=int),
        "hora_inicio_rodagem": request.form.get('hora_inicio_rodagem'),  # Deve vir no formato "HH:MM"
        "hora_fim_rodagem": request.form.get('hora_fim_rodagem'),  # Deve vir no formato "HH:MM"
        "material_perda": request.form.get('material_perda'),
        "quantidade_produto": request.form.get('quantidade_produto')
    }

    token_jwt = session.get('token_jwt')
    headers = {"Authorization": f"Bearer {token_jwt}"}

    try:
        resposta = requests.post(
            f"{API_URL}/producao",
            json=dados_formulario,
            headers=headers,
            timeout=5,
            proxies=DESVIAR_PROXY
        )

        if resposta.status_code == 201:
            flash('Produção cadastrada com sucesso!', 'success')
        elif resposta.status_code == 400:
            # Captura a mensagem de validação exata enviada pela API (ex: "Formato de hora inválido")
            flash(resposta.json().get('erro', 'Dados inválidos.'), 'warning')
        elif resposta.status_code == 401:
            flash('Sessão expirou. Faça login novamente.', 'danger')
            return redirect(url_for('login'))
        else:
            flash('Erro interno ao cadastrar produção.', 'danger')

    except requests.exceptions.RequestException:
        flash('Servidor de produção offline.', 'danger')

    return redirect(url_for('listar_producao'))

@app.route('/material', methods=['GET'])
def montar_material():
    page = request.args.get('page', 1, type=int)

    # Simulação de filtros vindos do formulário de busca da tela (opcional)
    material = request.args.get('codigo_material', '')
    data_filtro = request.args.get('descricao_material', '')
    func_filtro = request.args.get('unidade_medida', '')

    params = {"page": page}
    if material: params["codigo_material"] = data_filtro
    if data_filtro: params["descricao_material"] = data_filtro
    if func_filtro: params["unidade_medida"] = func_filtro

    # ATENÇÃO: API exige JWT. Buscando o token que você salvou no login da Web
    token_jwt = session.get('token_jwt')
    headers = {"Authorization": f"Bearer {token_jwt}"}

    try:
        resposta = requests.get(
            f"{API_URL}/material",
            params=params,
            headers=headers,
            timeout=5,
            proxies=DESVIAR_PROXY
        )

        if resposta.status_code == 200:
            dados = resposta.json()
            return render_template(
                'material.html',
                novo_material=dados.get('material', []),  # Bate com a chave da API
                current_page=dados.get('current_page', 1),
                total_pages=dados.get('total_pages', 1),
                total_items=dados.get('total_items', 0)  # Bate com a chave da API
            )
        elif resposta.status_code == 401:
            flash('Sua sessão expirou. Faça login novamente.', 'danger')
            return redirect(url_for('login'))
        else:
            flash('Erro ao carregar dados de produção.', 'warning')

    except requests.exceptions.RequestException as e:
        print(f"Erro de conexão: {e}")
        flash('Servidor de produção offline.', 'danger')

    return render_template('produçao.html',material =[], current_page=1, total_pages=1, total_items=0)

# 2. ROTA EXCLUSIVA PARA ENVIAR O CADASTRO (POST)
@app.route('/material/cadastrar', methods=['POST'])
def cadastrar_material():
    # Coleta os dados que o usuário digitou no <form> do HTML
    # Certifique-se de que os valores nos métodos .get() batem com os 'name' dos seus inputs HTML
    lista_materias = {
        "id_material": request.form.get('id_material'),
        "produtos_vinculados": request.form.get('produtos_vinculados'),
        "codigo_material": request.form.get('codigo_material'),  # Deve vir no formato "HH:MM"
        "descriçao_material": request.form.get('descriçao_material'),  # Deve vir no formato "HH:MM"
        "unidade_medida": request.form.get('unidade_medida'),
    }

    token_jwt = session.get('token_jwt')
    headers = {"Authorization": f"Bearer {token_jwt}"}

    try:
        resposta = requests.post(
            f"{API_URL}/material",
            json=lista_materias,
            headers=headers,
            timeout=5,
            proxies=DESVIAR_PROXY
        )

        if resposta.status_code == 201:
            flash('material cadastrada com sucesso!', 'success')
        elif resposta.status_code == 400:
            # Captura a mensagem de validação exata enviada pela API (ex: "Formato de hora inválido")
            flash(resposta.json().get('erro', 'Dados inválidos.'), 'warning')
        elif resposta.status_code == 401:
            flash('Sessão expirou. Faça login novamente.', 'danger')
            return redirect(url_for('login'))
        else:
            flash('Erro interno ao cadastrar material.', 'danger')

    except requests.exceptions.RequestException:
        flash('Servidor de material offline.', 'danger')

    return redirect(url_for('listar_material'))


@app.route('/turno', methods=['GET'])
def turno():
    page = request.args.get('page', 1, type=int)

    # Simulação de filtros vindos do formulário de busca da tela (opcional)
    id_equipe = request.args.get('id_equipe'),
    nome_equipe = request.args.get('nome_equipe'),
    hora_inicial = request.args.get('hora_inicial'),
    hora_fim = request.args.get('hora_fim'),

    params = {"page": page}
    if id_equipe: params["id_equipe"] = id_equipe
    if nome_equipe: params["nome_equipe"] = nome_equipe
    if hora_inicial: params["hora_inicial"] = hora_inicial
    if hora_fim: params["hora_fim"] = hora_fim

    # ATENÇÃO: API exige JWT. Buscando o token que você salvou no login da Web
    token_jwt = session.get('token_jwt')
    headers = {"Authorization": f"Bearer {token_jwt}"}

    try:
        resposta = requests.get(
            f"{API_URL}/turno",
            params=params,
            headers=headers,
            timeout=5,
            proxies=DESVIAR_PROXY
        )

        if resposta.status_code == 200:
            dados = resposta.json()
            return render_template(
                'turno.html',
                novo_turno=dados.get('turno', []),  # Bate com a chave da API
                current_page=dados.get('current_page', 1),
                total_pages=dados.get('total_pages', 1),
                total_items=dados.get('total_items', 0)  # Bate com a chave da API
            )
        elif resposta.status_code == 401:
            flash('Sua sessão expirou. Faça login novamente.', 'danger')
            return redirect(url_for('login'))
        else:
            flash('Erro ao carregar dados de produção.', 'warning')

    except requests.exceptions.RequestException as e:
        print(f"Erro de conexão: {e}")
        flash('Servidor de produção offline.', 'danger')

    return render_template('turno.html',turno =[], current_page=1, total_pages=1, total_items=0)

# 2. ROTA EXCLUSIVA PARA ENVIAR O CADASTRO (POST)
@app.route('/turno/cadastrar', methods=['POST'])
def cadastrar_turno():
    # Coleta os dados que o usuário digitou no <form> do HTML
    # Certifique-se de que os valores nos métodos .get() batem com os 'name' dos seus inputs HTML
    lista_turnos = {
        "id_turno": request.form.get('id_turno'),
        "fk_id_equipe": request.form.get('fk_id_equipe'),
        "nome_equipe": request.form.get('nome_equipe'),  # Deve vir no formato "HH:MM"
        "hora_inicio": request.form.get('hora_inicio'),  # Deve vir no formato "HH:MM"
        "hora_fim": request.form.get('hora_fim'),
    }

    token_jwt = session.get('token_jwt')
    headers = {"Authorization": f"Bearer {token_jwt}"}

    try:
        resposta = requests.post(
            f"{API_URL}/material",
            json=lista_turnos,
            headers=headers,
            timeout=5,
            proxies=DESVIAR_PROXY
        )

        if resposta.status_code == 201:
            flash('turno cadastrada com sucesso!', 'success')
        elif resposta.status_code == 400:
            # Captura a mensagem de validação exata enviada pela API (ex: "Formato de hora inválido")
            flash(resposta.json().get('erro', 'Dados inválidos.'), 'warning')
        elif resposta.status_code == 401:
            flash('Sessão expirou. Faça login novamente.', 'danger')
            return redirect(url_for('login'))
        else:
            flash('Erro interno ao cadastrar turno.', 'danger')

    except requests.exceptions.RequestException:
        flash('Servidor de turno offline.', 'danger')

    return redirect(url_for('listar_turno'))

@app.route('/produto', methods=['GET'])
def montar_produto():
    page = request.args.get('page', 1, type=int)

    # Simulação de filtros vindos do formulário de busca da tela (opcional)
    descricao = request.args.get('descricao'),
    quatidade_planejada = request.args.get('quatidade_planejada'),
    formato = request.args.get('formato'),

    params = {"page": page}
    if descricao: params["id_equipe"] = descricao
    if quatidade_planejada: params["nome_equipe"] = quatidade_planejada
    if formato: params["hora_inicial"] = formato

    # ATENÇÃO: API exige JWT. Buscando o token que você salvou no login da Web
    token_jwt = session.get('token_jwt')
    headers = {"Authorization": f"Bearer {token_jwt}"}

    try:
        resposta = requests.get(
            f"{API_URL}/produto",
            params=params,
            headers=headers,
            timeout=5,
            proxies=DESVIAR_PROXY
        )

        if resposta.status_code == 200:
            dados = resposta.json()
            return render_template(
                'produto.html',
                novo_produto=dados.get('produto', []),  # Bate com a chave da API
                current_page=dados.get('current_page', 1),
                total_pages=dados.get('total_pages', 1),
                total_items=dados.get('total_items', 0)  # Bate com a chave da API
            )
        elif resposta.status_code == 401:
            flash('Sua sessão expirou. Faça login novamente.', 'danger')
            return redirect(url_for('login'))
        else:
            flash('Erro ao carregar dados de produto.', 'warning')

    except requests.exceptions.RequestException as e:
        print(f"Erro de conexão: {e}")
        flash('Servidor de produto offline.', 'danger')

    return render_template('produto.html',produto =[], current_page=1, total_pages=1, total_items=0)

# 2. ROTA EXCLUSIVA PARA ENVIAR O CADASTRO (POST)
@app.route('/produto/cadastrar', methods=['POST'])
def cadastrar_produto():
    # Coleta os dados que o usuário digitou no <form> do HTML
    # Certifique-se de que os valores nos métodos .get() batem com os 'name' dos seus inputs HTML
    novo_produto = {

        "id_produto": request.form.get('id_produto'),
        "descriçao": request.form.get('descricao'),
        "quantidade_planejada": request.form.get('quantidade_planejada'),
        "formato": request.form.get('formato'),
        "materiais": request.form.get('formato'),

    }

    token_jwt = session.get('token_jwt')
    headers = {"Authorization": f"Bearer {token_jwt}"}

    try:
        resposta = requests.post(
            f"{API_URL}/produto",
            json=novo_produto,
            headers=headers,
            timeout=5,
            proxies=DESVIAR_PROXY
        )

        if resposta.status_code == 201:
            flash('produto cadastrada com sucesso!', 'success')
        elif resposta.status_code == 400:
            # Captura a mensagem de validação exata enviada pela API (ex: "Formato de hora inválido")
            flash(resposta.json().get('erro', 'Dados inválidos.'), 'warning')
        elif resposta.status_code == 401:
            flash('Sessão expirou. Faça login novamente.', 'danger')
            return redirect(url_for('login'))
        else:
            flash('Erro interno ao cadastrar produto.', 'danger')

    except requests.exceptions.RequestException:
        flash('Servidor de produto offline.', 'danger')

    return redirect(url_for('novo_produto'))


@app.route('/atualizar', methods=['GET', 'POST'])
def atualizar_usuario(id):
    if request.method == 'POST':
        dados_atualizados = {
            "nome_novo": request.form.get('nome_novo'),
            "senha_nova": request.form.get('senha_nova'),
            "email_novo": request.form.get('email_novo'),
        }

        try:
            resposta = requests.put(f"{API_URL}/usuarios/{id}", json=dados_atualizados, timeout=5, proxies=DESVIAR_PROXY)
            if resposta.status_code == 200:
                flash('Usuario atualizado com sucesso!', 'success')
                return redirect(url_for('visualizar_centros'))  # CORRIGIDO: Nome exato da sua função de rota anterior
            else:
                flash('Erro ao salvar alterações na API.', 'danger')
        except requests.exceptions.RequestException as e:
            print(f"Erro ao conectar na API: {e}")
            flash('Servidor central offline para salvar dados.', 'danger')

    # Método GET: Busca os dados atuais do centro para preencher a tela de edição
    try:
        resposta = requests.get(f"{API_URL}/usuarios/{id}", timeout=5, proxies=DESVIAR_PROXY)
        if resposta.status_code == 200:
            usuarios_dados = resposta.json()
            return render_template('atualizar.html', atualizar=usuarios_dados)  # CORRIGIDO: Passando a variável com o JSON da API
        else:
            flash('Não foi possível localizar este centro de distribuição.', 'warning')
            return redirect(url_for('visualizar_centros'))
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar centro: {e}")
        flash('Servidor central offline.', 'danger')
        return redirect(url_for('visualizar_centros'))

# 2. ROTA EXCLUSIVA PARA ENVIAR O CADASTRO (POST)
@app.route('/produto/cadastrar', methods=['POST'])
def cadastrar_produto():
    # Coleta os dados que o usuário digitou no <form> do HTML
    # Certifique-se de que os valores nos métodos .get() batem com os 'name' dos seus inputs HTML
    novo_produto = {

        "id_produto": request.form.get('id_produto'),
        "descriçao": request.form.get('descricao'),
        "quantidade_planejada": request.form.get('quantidade_planejada'),
        "formato": request.form.get('formato'),
        "materiais": request.form.get('formato'),

    }

    token_jwt = session.get('token_jwt')
    headers = {"Authorization": f"Bearer {token_jwt}"}

    try:
        resposta = requests.post(
            f"{API_URL}/produto",
            json=novo_produto,
            headers=headers,
            timeout=5,
            proxies=DESVIAR_PROXY
        )

        if resposta.status_code == 201:
            flash('produto cadastrada com sucesso!', 'success')
        elif resposta.status_code == 400:
            # Captura a mensagem de validação exata enviada pela API (ex: "Formato de hora inválido")
            flash(resposta.json().get('erro', 'Dados inválidos.'), 'warning')
        elif resposta.status_code == 401:
            flash('Sessão expirou. Faça login novamente.', 'danger')
            return redirect(url_for('login'))
        else:
            flash('Erro interno ao cadastrar produto.', 'danger')

    except requests.exceptions.RequestException:
        flash('Servidor de produto offline.', 'danger')

    return redirect(url_for('novo_produto'))





if __name__ == '__main__':
    app.run(debug=True, port=5002, host="0.0.0.0")




