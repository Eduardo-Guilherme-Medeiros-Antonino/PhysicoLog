from fastapi import FastAPI
from pydantic import BaseModel
from pysentimiento import create_analyzer
from fastapi.middleware.cors import CORSMiddleware
import json
import os

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

# Rota básica para verificar se o backend está rodando
@app.get("/")
def home():
    return {"mensagem": "Backend funcionando perfeitamente 🚀"}

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