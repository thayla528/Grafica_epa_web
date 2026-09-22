import email
import os


import requests
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_required, login_user, logout_user, current_user, UserMixin


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
            flash('Erro de conexão com o servidor login (API fora do ar).', 'danger')

    return render_template('login.html')


@app.route('/usuarios', methods=['GET', 'POST']) # Adicionado 'GET' para renderizar a página inicialmente
def cadastro():
    if current_user.is_authenticated:
        return redirect(url_for('cadastro'))

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
            flash('Erro de conexão com o servidor cadastro (API fora do ar).', 'danger')

    return render_template('cadastro.html')


@app.route('/material', methods=['GET', 'POST'])
@login_required
def api_material():
    if request.method == 'POST':
        dados_formulario = {
            "produtos_vincular": request.form.get('produtos_vincular'),
            "id_material": request.form.get('id_equipe'),
            "produtos_vinculados": request.form.get('produtos_vincular'),
            "codigo_material": request.form.get('codigo_material'),
            "descriçao_material": request.form.get('descriçao_material'),
            "unidade_medida": request.form.get('unidade_medida'),

        }
        try:
            resposta = requests.post(f"{API_URL}/material", json=dados_formulario, timeout=5, proxies=DESVIAR_PROXY)
            if resposta.status_code == 201:
                flash('material de distribuição cadastrado com sucesso!', 'success')
                return redirect(url_for('visualizar_material'))
            elif resposta.status_code in [400, 409]:
                flash(resposta.json().get('erro'), 'warning')
        except requests.exceptions.RequestException:
            flash('Servidor material offline.', 'danger')

    # CORREÇÃO: Aponta para o nome real do arquivo físico na sua pasta
    return render_template('api_material.html')

@app.route('/equipe')
@login_required
def montar_equipe():
    # CAPTURA: Pega a página atual da URL (padrão é 1)
    page = request.args.get('page', 1, type=int)

    try:
        # ENVIO: Passa o parâmetro page na requisição para a API
        resposta = requests.get(f"{API_URL}/equipe", params={"page": page}, timeout=5, proxies=DESVIAR_PROXY)
        if resposta.status_code == 200:
            dados = resposta.json()
            return render_template(
                'montar_equipe.html',
                equipe=dados.get('montar_equipe', []),
                current_page=dados.get('current_page', 1),
                total_pages=dados.get('total_pages', 1),
                total_items=dados.get('total_items', 0)
            )
        else:
            flash('Erro ao carregar equipe de distribuição.', 'warning')
    except requests.exceptions.RequestException as e:
        print(f"Erro: {e}")
        flash('Servidor equipe offline.', 'danger')

    return render_template('equipe.html', equipe=[], current_page=1, total_pages=1, total_items=0)


@app.route('/material')
@login_required
def api_material():
    # CAPTURA: Pega a página atual da URL (padrão é 1)
    page = request.args.get('page', 1, type=int)

    try:
        # ENVIO: Passa o parâmetro page na requisição para a API
        resposta = requests.get(f"{API_URL}/material", params={"page": page}, timeout=5, proxies=DESVIAR_PROXY)
        if resposta.status_code == 200:
            dados = resposta.json()
            return render_template(
                'material.html',
                material=dados.get('material', []),
                current_page=dados.get('current_page', 1),
                total_pages=dados.get('total_pages', 1),
                total_items=dados.get('total_items', 0)
            )
        else:
            flash('Erro ao carregar material de distribuição.', 'warning')
    except requests.exceptions.RequestException as e:
        print(f"Erro: {e}")
        flash('Servidor material offline.', 'danger')

    return render_template('material.html', material=[], current_page=1, total_pages=1, total_items=0)



@app.route('/produçao')
@login_required
def a_produçao():
    # CAPTURA: Pega a página atual da URL (padrão é 1)
    page = request.args.get('page', 1, type=int)

    try:
        # ENVIO: Passa o parâmetro page na requisição para a API
        resposta = requests.get(f"{API_URL}/produçao", params={"page": page}, timeout=5, proxies=DESVIAR_PROXY)
        if resposta.status_code == 200:
            dados = resposta.json()
            return render_template(
                'produçao.html',
                produçao=dados.get('produçao', []),
                current_page=dados.get('current_page', 1),
                total_pages=dados.get('total_pages', 1),
                total_items=dados.get('total_items', 0)
            )
        else:
            flash('Erro ao carregar produçao de distribuição.', 'warning')
    except requests.exceptions.RequestException as e:
        print(f"Erro: {e}")
        flash('Servidor produçao offline.', 'danger')

    return render_template('produçao.html', produçao=[], current_page=1, total_pages=1, total_items=0)


@app.route('/equipe', methods=['GET', 'POST'])
@login_required
def api_equipe():
    if request.method == 'POST':
        dados_formulario = {
            "cpf_informados": request.form.get('cpf_informados'),
            "nome_da_equipe": request.form.get('nome_da_equipe'),
        }
        try:
            resposta = requests.post(f"{API_URL}/equipe", json=dados_formulario, timeout=5, proxies=DESVIAR_PROXY)
            if resposta.status_code == 201:
                flash('equipe de distribuição cadastrado com sucesso!', 'success')
                return redirect(url_for('visualizar_material'))
            elif resposta.status_code in [400, 409]:
                flash(resposta.json().get('erro'), 'warning')
        except requests.exceptions.RequestException:
            flash('Servidor equipe offline.', 'danger')

    # CORREÇÃO: Aponta para o nome real do arquivo físico na sua pasta
    return render_template('api_equipe.html')

@app.route('/produçao', methods=['GET', 'POST'])
@login_required
def a_produçao():
    if request.method == 'POST':
        dados_formulario = {
            "hora_inico_env": request.form.get('hora_inico_env'),
            "hora_fim_env": request.form.get('hora_fim_env'),
        }
        try:
            resposta = requests.post(f"{API_URL}/produçao", json=dados_formulario, timeout=5, proxies=DESVIAR_PROXY)
            if resposta.status_code == 201:
                flash('produçao de distribuição cadastrado com sucesso!', 'success')
                return redirect(url_for('visualizar_produçao'))
            elif resposta.status_code in [400, 409]:
                flash(resposta.json().get('erro'), 'warning')
        except requests.exceptions.RequestException:
            flash('Servidor produçao offline.', 'danger')

    # CORREÇÃO: Aponta para o nome real do arquivo físico na sua pasta
    return render_template('produçao.html')




if __name__ == '__main__':
    # Roda na porta 5002 sem dar conflito com a API
    app.run(debug=True, port=5002, host="0.0.0.0")
