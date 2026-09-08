from flask import Flask, render_template

from routes.auth import auth

app = Flask(__name__)
# mover para .env
app.config['SECRET_KEY'] = 'Casa aberta'



@app.route('/')
def public_page():
    return render_template('public_page.html')

@app.route('/historico')
def historico():
    return render_template('historico.html')

@app.route('/cadastro')
def cadastro():
    return render_template('cadastro.html')

@app.route('/inscricao')
def inscricao():
    return render_template('inscricao.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/convite')
def convite():
    return render_template('convite.html')

if __name__ == '__main__':
    app.run(debug=True, port=5002)