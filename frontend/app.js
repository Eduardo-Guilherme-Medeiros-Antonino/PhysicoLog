// Seleciona elementos principais
const botao = document.getElementById("btn-analisar");
const resultadoCard = document.getElementById("resultado-card");
const resultadoDiv = document.getElementById("resultado");

// 🧩 Garante que o botão não cause recarregamento da página
botao.setAttribute("type", "button");

// Adiciona o listener de clique
botao.addEventListener("click", async (event) => {
    // 🛑 Evita qualquer reload acidental da página
    event.preventDefault();
    console.log("✅ Clique detectado, iniciando análise...");

    // Captura o texto do diário
    const texto = document.getElementById("diario").value.trim();
    if (!texto) {
        alert("Por favor, escreva algo antes de analisar!");
        return;
    }

    // Coleta as respostas do questionário
    const respostas = {
        tdah: document.getElementById("p1").value,
        ansiedade: document.getElementById("p2").value,
        depressao: document.getElementById("p3").value
    };

    // Exibe o card de resultado e mensagem de processamento
    resultadoCard.style.display = "block";
    resultadoCard.classList.add("fade-in");
    resultadoDiv.innerHTML = "Analisando emoções... 🧭";

    try {
        // Faz a requisição para o backend
        const res = await fetch("http://127.0.0.1:8000/analisar", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ texto, respostas })
        });

        console.log("🛰️ Resposta do backend (status):", res.status);

        if (!res.ok) throw new Error(`Erro ${res.status}`);

        const data = await res.json();
        console.log("📦 Dados recebidos do backend:", data);

        // Exibe os resultados da análise
        resultadoDiv.innerHTML = `
            <p><strong>Emoção principal:</strong> ${data.emocao.principal}</p>
            <p><strong>Tendência detectada:</strong> ${data.tendencia}</p>
            <p><strong>Explicação:</strong> ${data.explicacao}</p>
            <p><strong>TDAH:</strong> ${data.pontuacao?.tdah ?? 0} | 
               <strong>Ansiedade:</strong> ${data.pontuacao?.ansiedade ?? 0} | 
               <strong>Depressão:</strong> ${data.pontuacao?.depressao ?? 0}</p>
        `;

    } catch (err) {
        console.error("❌ Erro durante a análise:", err);
        resultadoDiv.innerHTML = `<p style="color:red;">❌ Erro: ${err.message}</p>`;
    }
});
