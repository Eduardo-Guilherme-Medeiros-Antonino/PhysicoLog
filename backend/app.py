from fastapi import FastAPI
from pydantic import BaseModel
from pysentimiento import create_analyzer  # Importado aqui
from fastapi.middleware.cors import CORSMiddleware
import json
import os
from services.auth_service import (
    load_users, get_password_hash, authenticate_user, create_access_token, USERS_FILE
)
from services.auth_service import authenticate_user
from fastapi.responses import JSONResponse

# Mapa de tradução das emoções
emotions_map = {
    "nervousness": "nervoso",
    "happiness": "feliz",
    "sadness": "triste",
    "anger": "irritado",
    "fear": "com medo",
    "surprise": "surpreso",
    "neutral": "neutra"
}

# Inicializa a aplicação FastAPI
app = FastAPI()

# -----------------------------------------------------------------
# ✨ SOLUÇÃO: Carregue o modelo de IA apenas UMA VEZ
# -----------------------------------------------------------------
print("Carregando modelo de emoções (pysentimiento)... Aguarde.")
# Esta linha agora executa apenas na inicialização do servidor
analizador_emocao = create_analyzer(task="emotion", lang="pt")
print("✅ Modelo de emoções carregado. Servidor pronto.")
# -----------------------------------------------------------------


# Habilita CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelo de dados de entrada
class Diario(BaseModel):
    texto: str
    respostas: dict

class UserRegister(BaseModel):
    nome: str
    email: str
    senha: str
    tipo: str

class UserLogin(BaseModel):
    email: str
    senha: str

# Rota básica
@app.get("/")
def home():
    return {"mensagem": "Backend funcionando perfeitamente 🚀"}

# Rota de Registro
@app.post("/register")
def register(user: UserRegister):
    users = load_users()

    if any(u["email"] == user.email for u in users):
        return {"detail": "Email já cadastrado."}, 400

    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(data_dir, exist_ok=True)

    new_user = {
        "nome": user.nome,
        "email": user.email,
        "senha_hash": get_password_hash(user.senha),
        "tipo": user.tipo
    }
    users.append(new_user)

    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

    return {"mensagem": "Usuário registrado com sucesso!"}

# Rota de Login
@app.post("/login")
def login(user: UserLogin):
    usuario = authenticate_user(user.email, user.senha)
    if not usuario:
        return JSONResponse(content={"detail": "Email ou senha incorretos."}, status_code=401)

    token = create_access_token({"sub": user.email})
    tipo = usuario.get("tipo", "aluno")
    nome = usuario.get("nome", "Usuário")

    resposta = {
        "access_token": token,
        "token_type": "bearer",
        "tipo": tipo,
        "nome": nome
    }
    print("✅ LOGIN BEM-SUCEDIDO:", resposta)
    return JSONResponse(content=resposta, status_code=200)


# Rota principal de análise (Agora otimizada)
@app.post("/analisar")
def analisar(entry: Diario):
    
    # ❌ O modelo NÃO é mais carregado aqui
    # analizador_emocao = create_analyzer(task="emotion", lang="pt")

    # ✅ Apenas usamos o modelo que já está na memória
    resultado = analizador_emocao.predict(entry.texto)

    # Garante que a emoção retornada seja sempre string
    emocao = resultado.output
    if isinstance(emocao, list):
        emocao = emocao[0] if len(emocao) > 0 else "neutral"

    # Traduz para português
    emocao = emotions_map.get(emocao.lower(), emocao)
    probas = resultado.probas

    # Estrutura de pontuação
    score = {"tdah": 0, "ansiedade": 0, "depressao": 0}
    mapping = {
        "nunca": 0,
        "raramente": 1,
        "às vezes": 2,
        "as vezes": 2,
        "frequentemente": 3,
        "sempre": 4
    }

    for chave, valor in entry.respostas.items():
        valor_formatado = valor.lower().strip()
        if chave in score:
            score[chave] = mapping.get(valor_formatado, 0)

    # Interpretação
    tendencia = "Sem tendências significativas"
    explicacao = "Nenhum comportamento preocupante detectado."

    if score["tdah"] >= 3:
        tendencia = "Tendência a TDAH"
        explicacao = "O usuário demonstra sinais de desatenção e impulsividade frequente."
    elif score["ansiedade"] >= 3 or emocao.lower() in ["medo", "ansiedade", "nervosismo", "nervoso"]:
        tendencia = "Tendência a Ansiedade"
        explicacao = "Há indicativos de tensão e preocupação elevada."
    elif score["depressao"] >= 3 or emocao.lower() in ["tristeza", "desânimo", "triste"]:
        tendencia = "Tendência à Depressão leve"
        explicacao = "O texto e respostas indicam sintomas de humor deprimido ou desmotivação."

    # Salvar histórico
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    historico_path = os.path.join(data_dir, "historico.json")

    if os.path.exists(historico_path):
        with open(historico_path, "r", encoding="utf-8") as f:
            try:
                historico = json.load(f)
            except json.JSONDecodeError:
                historico = []
    else:
        historico = []

    historico.append({
        "texto": entry.texto,
        "respostas": entry.respostas,
        "emocao": emocao,
        "tendencia": tendencia,
        "pontuacao": score
    })

    with open(historico_path, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)

    # Retorno JSON (agora será instantâneo)
    return {
        "emocao": {"principal": emocao, "probabilidades": probas},
        "tendencia": tendencia,
        "explicacao": explicacao,
        "pontuacao": score
    }

# Rota de registros
@app.get("/registros")
def listar_registros():
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    historico_path = os.path.join(data_dir, "historico.json")

    if not os.path.exists(historico_path):
        return {"mensagem": "Nenhum registro encontrado."}

    with open(historico_path, "r", encoding="utf-8") as f:
        try:
            historico = json.load(f)
        except json.JSONDecodeError:
            historico = []

    return historico

# Rota de correção de senhas
@app.get("/corrigir_senhas")
def corrigir_senhas():
    from services.auth_service import get_password_hash, USERS_FILE, load_users
    import json

    users = load_users()
    alterado = False

    for u in users:
        if "senha" in u and not u.get("senha", "").startswith("$2b$"):
            u["senha_hash"] = get_password_hash(u["senha"])
            u.pop("senha")
            alterado = True

    if alterado:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        return {"status": "✅ Senhas criptografadas com sucesso!"}
    else:
        return {"status": "ℹ️ Nenhuma senha precisou ser alterada."}