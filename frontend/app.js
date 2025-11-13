document.addEventListener("DOMContentLoaded", () => {
  const botao = document.getElementById("btn-analisar");
  const resultadoCard = document.getElementById("resultado-card");
  const resultadoDiv = document.getElementById("resultado");

  if (!botao) return;

  // 🔒 Garante que o botão não envie nenhum formulário
  botao.setAttribute("type", "button");

  // 🔒 Bloqueia qualquer submit global
  document.querySelectorAll("form").forEach(form => {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      e.stopImmediatePropagation();
      console.log("🛑 Bloqueado submit padrão do form.");
    });
  });

  botao.addEventListener("click", async (event) => {
    event.preventDefault();
    event.stopPropagation();

    console.log("✅ Clique detectado, iniciando análise...");

    const texto = document.getElementById("diario").value.trim();
    if (!texto) {
      alert("Por favor, escreva algo antes de analisar!");
      return;
    }

    const respostas = {
      tdah: document.getElementById("p1").value,
      ansiedade: document.getElementById("p2").value,
      depressao: document.getElementById("p3").value
    };

    resultadoCard.style.display = "block";
    resultadoCard.classList.add("fade-in");
    resultadoDiv.innerHTML = "Analisando emoções... 🧭";

    try {
      const res = await fetch("http://127.0.0.1:8000/analisar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texto, respostas }),
      });

      console.log("🛰️ Resposta do backend (status):", res.status);

      if (!res.ok) throw new Error(`Erro ${res.status}`);

      const data = await res.json();
      console.log("📦 Dados recebidos do backend:", data);

      // TRY/CATCH ANINHADO PARA ISOLAR FALHAS DE RENDERIZAÇÃO
      try {
        resultadoDiv.innerHTML = `
          <p><strong>Emoção principal:</strong> ${data.emocao?.principal ?? "—"}</p>
          <p><strong>Tendência detectada:</strong> ${data.tendencia ?? "—"}</p>
          <p><strong>Explicação:</strong> ${data.explicacao ?? "—"}</p>
          <p><strong>TDAH:</strong> ${data.pontuacao?.tdah ?? 0} |
            <strong>Ansiedade:</strong> ${data.pontuacao?.ansiedade ?? 0} |
            <strong>Depressão:</strong> ${data.pontuacao?.depressao ?? 0}</p>
        `;
        console.log("✅ Renderização do resultado concluída com sucesso.");
      } catch (renderErr) {
          console.error("❌ ERRO FATAL na renderização:", renderErr); 
          resultadoDiv.innerHTML = `<p style="color: red;">❌ Erro de renderização: ${renderErr.message}</p>`;
      }
      
    } catch (err) {
      console.error("❌ Erro durante a análise (Fetch/Rede):", err);
      resultadoDiv.innerHTML = `<p style="color:red;">❌ Erro: ${err.message}</p>`;
    }
    
    // O GUARDA-RAIL FINAL ESTÁ AQUI
    return false; 
    
  });
});