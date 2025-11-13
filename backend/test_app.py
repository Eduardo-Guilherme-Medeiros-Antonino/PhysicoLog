import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import status
from app import app

@pytest.mark.asyncio
async def test_home_route():
    """Teste simples para verificar se o backend está online"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert "Backend funcionando" in response.json()["mensagem"]

@pytest.mark.asyncio
async def test_analisar_route(tmp_path, monkeypatch):
    """Teste da rota /analisar com texto e respostas simuladas"""

    # Mock do modelo de IA
    class FakeResult:
        output = "happiness"
        probas = {"happiness": 0.9, "sadness": 0.05, "anger": 0.05}

    class FakeAnalyzer:
        def predict(self, text):
            return FakeResult()

    # Substitui create_analyzer temporariamente
    monkeypatch.setattr("app.create_analyzer", lambda **_: FakeAnalyzer())

    # Cria diretório temporário
    monkeypatch.setattr("app.os.path.dirname", lambda _: str(tmp_path))

    payload = {
        "texto": "Hoje foi um ótimo dia!",
        "respostas": {"tdah": "nunca", "ansiedade": "às vezes", "depressao": "nunca"}
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/analisar", json=payload)

    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert "emocao" in data
    assert "tendencia" in data
    assert "pontuacao" in data
    assert isinstance(data["pontuacao"], dict)
