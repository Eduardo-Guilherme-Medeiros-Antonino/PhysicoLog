import json
import time
import os
import jwt
from typing import Optional
from passlib.context import CryptContext

# =============================
# Configurações gerais
# =============================
SECRET_KEY = "CHANGE_THIS_SECRET"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 60 * 60 * 24

# 🔐 Bcrypt — configuração única e confiável
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__ident="2b"  # força o identificador correto
)

# Caminho fixo do arquivo de usuários
USERS_FILE = r"C:\Users\PC\Desktop\DiarioEmocional\backend\data\usuarios.json"
print(f"📂 Caminho fixo de USERS_FILE: {USERS_FILE}")

# =============================
# Funções auxiliares
# =============================

def verify_password(plain, hashed):
    """Verifica a senha com segurança"""
    try:
        return pwd_context.verify(plain, hashed)
    except Exception as e:
        print(f"⚠️ Erro na verificação de senha: {e}")
        print(f"🧩 Hash recebido: {hashed}")
        return False


def get_password_hash(password: str):
    """Cria um hash bcrypt seguro"""
    return pwd_context.hash(password[:72])


def load_users():
    """Carrega usuários do arquivo JSON"""
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"👥 {len(data)} usuários carregados com sucesso.")
        return data
    except Exception as e:
        print(f"❌ Erro ao ler usuários: {e}")
        return []


# =============================
# Autenticação principal
# =============================

def authenticate_user(email: str, senha: str):
    print(f"\n🔍 Tentando autenticar {email} ...")
    print(f"📁 USERS_FILE: {USERS_FILE}")

    usuarios = load_users()
    print(f"👥 Usuários carregados: {[u.get('email') for u in usuarios]}")

    for usuario in usuarios:
        if usuario["email"] != email:
            continue

        if "senha_hash" in usuario:
            if verify_password(senha, usuario["senha_hash"]):
                print("✅ Login bem-sucedido (senha hash)")
                return usuario
            else:
                print("❌ Hash não confere para este usuário.")
        elif "senha" in usuario:
            if usuario["senha"] == senha:
                print("✅ Login bem-sucedido (senha simples)")
                return usuario

    print("❌ Nenhum usuário autenticado — email ou senha incorretos.")
    return None


# =============================
# JWT
# =============================

def create_access_token(data: dict, expires_delta: int = ACCESS_TOKEN_EXPIRE_SECONDS):
    to_encode = data.copy()
    to_encode.update({"exp": int(time.time()) + expires_delta})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        return None
