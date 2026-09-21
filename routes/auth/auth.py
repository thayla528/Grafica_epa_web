from flask import (
    Blueprint,
    render_template,

)

import requests


auth_bp = Blueprint(
    "auth",
    __name__
)

@auth_bp.route('/login')
def login():
    return render_template('login.html')

@auth_bp.route('/convite')
def convite():
    return render_template('convite.html')

@auth_bp.route('/cadastro')
def cadastro():
    return render_template('cadastro.html')