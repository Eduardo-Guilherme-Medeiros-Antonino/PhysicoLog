from pydantic import BaseModel, EmailStr
from typing import Literal, Optional


class Usuario(BaseModel):
    id: int
nome: str
email: EmailStr
senha_hash: Optional[str] = None # quando migrar para DB use hash
tipo: Literal['aluno', 'professor']
