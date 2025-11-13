"""
Serviço simples de "análise" de sentimento.
Substitua por pysentimiento ou outro modelo quando quiser.
"""
from typing import Dict


POS_WORDS = {"feliz","otimo","bom","alegre","animado","tranquilo","bem","content"}
NEG_WORDS = {"triste","mal","deprimido","ansioso","ansiosa","chateado","sofrendo","sofrer","cansado","cansada","nervoso","stress"}


def analyze_text_simple(text: str) -> Dict:
    t = text.lower()
    # ⬇️ Indentação CORRIGIDA aqui
    pos = sum(1 for w in POS_WORDS if w in t)
    neg = sum(1 for w in NEG_WORDS if w in t)
    score = pos - neg
    label = "neutro"
    
    if score > 0:
        label = "positivo"
    elif score < 0:
        label = "negativo"
        
    return {"score": score, "label": label, "pos_matches": pos, "neg_matches": neg}


# função para detectar se devemos criar alerta
def should_alert(analysis: Dict) -> bool:
    # Exemplo simples: alerta se label negativo e magnitude >=1
    return analysis.get("label") == "negativo" and abs(analysis.get("score", 0)) >= 1