from fastapi import FastAPI
from pydantic import BaseModel
from pysentimiento import create_analyzer
from fastapi.middleware.cors import CORSMiddleware
import json
import os
from services.auth_service import (
    load_users, get_password_hash, authenticate_user, create_access_token, USERS_FILE
)
from services.auth_service import authenticate_user

# Mapa de tradução das emoções do inglês para português
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

# Habilita CORS (permite o acesso do front-end)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # altere se quiser restringir (ex: ["http://127.0.0.1:5500"])
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelo de dados de entrada (texto + respostas)
class Diario(BaseModel):
    texto: str
    respostas: dict  # Exemplo: {"tdah": "frequentemente", "ansiedade": "as vezes"}

class UserRegister(BaseModel):
    nome: str
    email: str
    senha: str
    tipo: str

class UserLogin(BaseModel):
    email: str
    senha: str

# Rota básica para verificar se o backend está rodando
@app.get("/")
def home():
    return {"mensagem": "Backend funcionando perfeitamente 🚀"}

@app.post("/register")
def register(user: UserRegister):
    users = load_users()

    # Verifica se já existe usuário com o mesmo e-mail
    if any(u["email"] == user.email for u in users):
        return {"detail": "Email já cadastrado."}, 400

    # Garante que o diretório 'data' existe
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


from fastapi.responses import JSONResponse

@app.post("/login")
def login(user: UserLogin):
    usuario = authenticate_user(user.email, user.senha)
    if not usuario:
        return JSONResponse(content={"detail": "Email ou senha incorretos."}, status_code=401)

    token = create_access_token({"sub": user.email})

    # ✅ Garante que o tipo e nome existam
    tipo = usuario.get("tipo", "aluno")
    nome = usuario.get("nome", "Usuário")

    resposta = {
        "access_token": token,
        "token_type": "bearer",
        "tipo": tipo,
        "nome": nome
    }

    print("✅ LOGIN BEM-SUCEDIDO:", resposta)  # debug visível no terminal

    return JSONResponse(content=resposta, status_code=200)


# Rota principal de análise
@app.post("/analisar")
def analisar(entry: Diario):
    # Cria o analisador de emoções (modelo em português)
    analizador_emocao = create_analyzer(task="emotion", lang="pt")

    # Processa o texto
    resultado = analizador_emocao.predict(entry.texto)

    # Garante que a emoção retornada seja sempre string
    emocao = resultado.output
    if isinstance(emocao, list):
        emocao = emocao[0] if len(emocao) > 0 else "neutral"  # usar key do mapa

    # Traduz para português usando o mapa
    emocao = emotions_map.get(emocao.lower(), emocao)

    probas = resultado.probas

    # Estrutura de pontuação do questionário
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

    # Interpretação dos resultados
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

    # Salvar histórico localmente
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    historico_path = os.path.join(data_dir, "historico.json")

    # Lê histórico anterior, se existir
    if os.path.exists(historico_path):
        with open(historico_path, "r", encoding="utf-8") as f:
            try:
                historico = json.load(f)
            except json.JSONDecodeError:
                historico = []
    else:
        historico = []

    # Adiciona nova entrada
    historico.append({
        "texto": entry.texto,
        "respostas": entry.respostas,
        "emocao": emocao,
        "tendencia": tendencia,
        "pontuacao": score
    })

    # Salva novamente o histórico
    with open(historico_path, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)

    # Retorno JSON para o front-end
    return {
        "emocao": {"principal": emocao, "probabilidades": probas},
        "tendencia": tendencia,
        "explicacao": explicacao,
        "pontuacao": score
    }

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




@app.get("/corrigir_senhas")
def corrigir_senhas():
    from services.auth_service import get_password_hash, USERS_FILE, load_users
    import json

    users = load_users()
    alterado = False

    for u in users:
        # Se a senha ainda estiver em texto comum, gera o hash e remove a original
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
