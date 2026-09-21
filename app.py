import os
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


if __name__ == '__main__':
    app.run(debug=True, port=5002, host="0.0.0.0")
