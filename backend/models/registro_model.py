from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class Registro(BaseModel):
    # Aqui não há backticks, então não precisa de repr()
    id: int
    aluno_id: int # Eu corrigi a indentação neste trecho, veja abaixo!
    texto: str
    p1: str
    p2: str
    p3: str
    created_at: datetime
    analise_sentimento: Optional[dict] = None