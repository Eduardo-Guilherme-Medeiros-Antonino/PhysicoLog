document.getElementById("btn-analisar").addEventListener("click", async (event) => {
    // 🛑 ESSENCIAL: Previne o comportamento padrão do botão, que pode recarregar a página
    // (comum se o botão estiver em um <form> ou por padrão do navegador),
    // o que faria o resultado do 'fetch' piscar e sumir.
    event.preventDefault(); 
    
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

    const resultadoCard = document.getElementById("resultado-card");
    const resultadoDiv = document.getElementById("resultado");

    // Exibe o card de resultado e aplica a animação
    resultadoCard.style.display = "block";
    resultadoCard.classList.add("fade-in");
    resultadoDiv.innerHTML = "Analisando emoções... 🧭";

    try {
        const res = await fetch("http://127.0.0.1:8000/analisar", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ texto, respostas })
        });

        if (!res.ok) throw new Error(`Erro ${res.status}`);

        const data = await res.json();

        // Monta o HTML do resultado com os dados do back-end
        resultadoDiv.innerHTML = `
            <p><strong>Emoção principal:</strong> ${data.emocao.principal}</p>
            <p><strong>Tendência detectada:</strong> ${data.tendencia}</p>
            <p><strong>Explicação:</strong> ${data.explicacao}</p>
            <p><strong>TDAH:</strong> ${data.pontuacao?.tdah ?? 0} | 
               <strong>Ansiedade:</strong> ${data.pontuacao?.ansiedade ?? 0} | 
               <strong>Depressão:</strong> ${data.pontuacao?.depressao ?? 0}</p>
        `;
    } catch (err) {
        resultadoDiv.innerHTML = `<p style="color:red;">❌ Erro: ${err.message}</p>`;
    }
});