/* painel_professor.js
   Requisitos:
   - Usa token JWT salvo em localStorage ('token')
   - Busca /registros e /alertas
   - Se /alertas não existir ou retornar vazio, gera alertas localmente
   - Constrói 3 gráficos: emoções (pizza), tendências (barras) e pontuações (linha média diária)
*/

const token = localStorage.getItem('token');
const headers = { 'Content-Type': 'application/json' };
if (token) headers['Authorization'] = `Bearer ${token}`;

// Mapa simples para normalizar emoções (se vier em inglês)
const emotionsMap = {
  nervousness: 'nervoso',
  happiness: 'feliz',
  sadness: 'triste',
  anger: 'irritado',
  fear: 'com medo',
  surprise: 'surpreso',
  neutral: 'neutra',
  excitement: 'animado'
};

function normalizeEmotion(e) {
  if (!e) return 'neutra';
  const low = String(e).toLowerCase();
  return emotionsMap[low] || low;
}

function formatAlunoLabel(r) {
  if (r.aluno_nome) return `${r.aluno_nome} (id:${r.aluno_id ?? '—'})`;
  if (r.aluno_id) return `Aluno — id:${r.aluno_id}`;
  return 'Aluno — Desconhecido';
}

// DOM refs
const elAlertas = document.getElementById('alertas');
const elLista = document.getElementById('lista-registros');
const selAluno = document.getElementById('select-aluno');
const btnLogout = document.getElementById('btn-logout');
const btnRefresh = document.getElementById('btn-refresh');

let registrosCache = [];
let chartEmocoes = null;
let chartTendencias = null;
let chartPontuacoes = null;

async function fetchRegistros() {
  try {
    const res = await fetch('/registros', { headers });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    // normalize timestamps if missing, and ensure structure
    return data.map((r, idx) => ({
      id: r.id ?? idx + 1,
      aluno_id: r.aluno_id ?? r.alunoId ?? null,
      aluno_nome: r.aluno_nome ?? r.nome_aluno ?? null,
      texto: r.texto ?? '',
      respostas: r.respostas ?? {},
      emocao: normalizeEmotion(r.emocao ?? r.emotion),
      tendencia: r.tendencia ?? 'Sem tendências significativas',
      pontuacao: r.pontuacao ?? r.score ?? { tdah: 0, ansiedade: 0, depressao: 0 },
      created_at: r.created_at ?? r.data ?? new Date().toISOString()
    }));
  } catch (err) {
    // Se endpoint não existir, informar usuário
    console.error('Erro ao buscar /registros:', err);
    throw new Error('Não foi possível obter registros do backend. Verifique se a rota /registros está implementada.');
  }
}

async function fetchAlertas() {
  try {
    const res = await fetch('/alertas', { headers });
    if (!res.ok) {
      // 404 ou outro: fallback para geração local
      return null;
    }
    const data = await res.json();
    return Array.isArray(data) ? data : null;
  } catch (err) {
    console.warn('Erro ao buscar /alertas:', err);
    return null;
  }
}

// Gera alertas locais a partir dos registros (fallback)
function gerarAlertasLocais(registros) {
  // Estratégia simples:
  // - se um aluno tiver 2 ou mais registros com tendência contendo "Depress" ou "Ansiedade" ou "TDAH", cria alerta
  const grouped = {};
  registros.forEach(r => {
    const id = r.aluno_id ?? 'desconhecido';
    grouped[id] = grouped[id] || [];
    grouped[id].push(r);
  });

  const alertas = [];
  Object.entries(grouped).forEach(([alunoId, regs]) => {
    const countByTend = {};
    regs.forEach(r => {
      const t = (r.tendencia || 'Sem tendências significativas').toLowerCase();
      countByTend[t] = (countByTend[t] || 0) + 1;
    });
    // detecta padrões alarmantes
    Object.entries(countByTend).forEach(([tend, count]) => {
      if (tend.includes('depress') || tend.includes('depre') ) {
        if (count >= 1) {
          alertas.push({
            aluno_id: alunoId,
            message: 'Padrão de humor compatível com depressão detectado no histórico.',
            tendencia: tend,
            ocorrencias: count
          });
        }
      } else if (tend.includes('ansiedade') || tend.includes('ansioso') || tend.includes('nerv')) {
        if (count >= 2) {
          alertas.push({
            aluno_id: alunoId,
            message: 'Padrão recorrente de ansiedade detectado.',
            tendencia: tend,
            ocorrencias: count
          });
        }
      } else if (tend.includes('tdah')) {
        if (count >= 3) {
          alertas.push({
            aluno_id: alunoId,
            message: 'Possível padrão consistente de sintomas relacionados a TDAH.',
            tendencia: tend,
            ocorrencias: count
          });
        }
      }
    });
  });

  // também procura registros individuais com emoção claramente negativa e pontuação alta em depressao
  registros.forEach(r => {
    if ((r.emocao || '').includes('triste') || (r.pontuacao && r.pontuacao.depressao >= 3)) {
      alertas.push({
        aluno_id: r.aluno_id ?? 'desconhecido',
        message: 'Registro com sinal de sofrimento (emoção/pontuação).',
        tendencia: r.tendencia,
        registro_id: r.id
      });
    }
  });

  // dedup
  const seen = new Set();
  return alertas.filter(a => {
    const key = `${a.aluno_id}|${a.message}|${a.tendencia}|${a.registro_id ?? a.ocorrencias ?? ''}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

// Popula select de alunos
function popularSelectAlunos(registros) {
  const map = new Map();
  registros.forEach(r => {
    const id = r.aluno_id ?? 'desconhecido';
    const label = r.aluno_nome ? `${r.aluno_nome} (id:${id})` : `Aluno — id:${id}`;
    if (!map.has(id)) map.set(id, label);
  });

  // limpa e preenche
  selAluno.innerHTML = '<option value="__all__">Todos os alunos</option>';
  for (const [id, label] of map.entries()) {
    const opt = document.createElement('option');
    opt.value = id;
    opt.innerText = label;
    selAluno.appendChild(opt);
  }
}

// Render lista de registros
function renderLista(registros) {
  if (!registros || registros.length === 0) {
    elLista.innerHTML = '<p>Nenhum registro encontrado.</p>';
    return;
  }
  // ordena por data descendente
  const sorted = registros.slice().sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  elLista.innerHTML = sorted.map(r => {
    const alunoLabel = r.aluno_nome ? r.aluno_nome : (r.aluno_id ? `Aluno — id:${r.aluno_id}` : 'Aluno — Desconhecido');
    return `
      <div class="registro">
        <p><strong>${alunoLabel}</strong> <small>${new Date(r.created_at).toLocaleString()}</small></p>
        <p style="margin:6px 0;">${r.texto ? sanitize(r.texto) : '<em>(texto vazio)</em>'}</p>
        <p><strong>Análise:</strong> ${sanitize(r.emocao)} — <em>${sanitize(r.tendencia)}</em></p>
        <p><strong>Pontuações:</strong> TDAH: ${r.pontuacao?.tdah ?? 0} • Ansiedade: ${r.pontuacao?.ansiedade ?? 0} • Depressão: ${r.pontuacao?.depressao ?? 0}</p>
      </div>
    `;
  }).join('');
}

// Monta gráfico de emoções (pizza)
function buildEmotionChart(registros, ctx) {
  const counts = {};
  registros.forEach(r => {
    const e = normalizeEmotion(r.emocao);
    counts[e] = (counts[e] || 0) + 1;
  });
  const labels = Object.keys(counts);
  const values = labels.map(l => counts[l]);
  if (chartEmocoes) chartEmocoes.destroy();
  chartEmocoes = new Chart(ctx, {
    type: 'pie',
    data: {
      labels,
      datasets: [{ data: values }]
    },
    options: { responsive: true }
  });
}

// Monta gráfico de tendências (barras)
function buildTendencyChart(registros, ctx) {
  const counts = {};
  registros.forEach(r => {
    const t = r.tendencia || 'Sem tendências significativas';
    counts[t] = (counts[t] || 0) + 1;
  });
  const labels = Object.keys(counts);
  const values = labels.map(l => counts[l]);
  if (chartTendencias) chartTendencias.destroy();
  chartTendencias = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{ data: values }]
    },
    options: { indexAxis: 'y', responsive: true }
  });
}

// Monta gráfico de pontuações (média por dia)
function buildScoresChart(registros, ctx) {
  // agrupamos por data (YYYY-MM-DD)
  const byDate = {};
  registros.forEach(r => {
    const d = new Date(r.created_at);
    const key = d.toISOString().slice(0, 10);
    byDate[key] = byDate[key] || { tdah: 0, ansiedade: 0, depressao: 0, count: 0 };
    byDate[key].tdah += (r.pontuacao?.tdah ?? 0);
    byDate[key].ansiedade += (r.pontuacao?.ansiedade ?? 0);
    byDate[key].depressao += (r.pontuacao?.depressao ?? 0);
    byDate[key].count += 1;
  });

  const dates = Object.keys(byDate).sort();
  const tdahAvg = dates.map(d => (byDate[d].tdah / byDate[d].count).toFixed(2));
  const ansAvg = dates.map(d => (byDate[d].ansiedade / byDate[d].count).toFixed(2));
  const depAvg = dates.map(d => (byDate[d].depressao / byDate[d].count).toFixed(2));

  if (chartPontuacoes) chartPontuacoes.destroy();
  chartPontuacoes = new Chart(ctx, {
    type: 'line',
    data: {
      labels: dates,
      datasets: [
        { label: 'TDAH (média)', data: tdahAvg, fill: false, tension: 0.2 },
        { label: 'Ansiedade (média)', data: ansAvg, fill: false, tension: 0.2 },
        { label: 'Depressão (média)', data: depAvg, fill: false, tension: 0.2 }
      ]
    },
    options: { responsive: true, interaction: { mode: 'index', intersect: false } }
  });
}

function sanitize(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function renderAlertas(alertas) {
  if (!alertas || alertas.length === 0) {
    elAlertas.innerHTML = '<p>Sem alertas no momento.</p>';
    return;
  }
  elAlertas.innerHTML = alertas.map(a => {
    const alunoLabel = a.aluno_nome ? a.aluno_nome : (a.aluno_id ? `Aluno — id:${a.aluno_id}` : 'Aluno — Desconhecido');
    const when = a.created_at ? ` • ${new Date(a.created_at).toLocaleString()}` : '';
    return `
      <div class="alert-card">
        <p><strong>${alunoLabel}</strong>${when}</p>
        <p>${sanitize(a.message || a.mensagem || a.message_pt || 'Alerta gerado')}</p>
        <p style="font-size:0.85em;color:#555;"><em>Tendência:</em> ${sanitize(a.tendencia || '')} ${a.ocorrencias ? `• ocorrências: ${a.ocorrencias}` : ''}</p>
      </div>
    `;
  }).join('');
}

// Filtra registros por aluno selecionado
function filtrarPorAluno(registros, alunoId) {
  if (!alunoId || alunoId === '__all__') return registros;
  return registros.filter(r => String(r.aluno_id ?? 'desconhecido') === String(alunoId));
}

// Inicialização principal
async function init() {
  try {
    registrosCache = await fetchRegistros();
  } catch (err) {
    // mostra erro amigável
    elAlertas.innerHTML = `<p style="color:crimson">Erro: ${err.message}</p>`;
    elLista.innerHTML = '<p>Não foi possível carregar registros.</p>';
    return;
  }

  // popular select de alunos
  popularSelectAlunos(registrosCache);

  // tenta buscar alertas do backend
  let alertas = await fetchAlertas();
  if (!alertas || alertas.length === 0) {
    // fallback: gerar localmente
    alertas = gerarAlertasLocais(registrosCache);
  }

  renderAlertas(alertas);

  // render general charts with all registros
  const emCtx = document.getElementById('chartEmocoes').getContext('2d');
  const tdCtx = document.getElementById('chartTendencias').getContext('2d');
  const ptCtx = document.getElementById('chartPontuacoes').getContext('2d');

  buildEmotionChart(registrosCache, emCtx);
  buildTendencyChart(registrosCache, tdCtx);
  buildScoresChart(registrosCache, ptCtx);

  // render lista inicial
  renderLista(registrosCache);

  // handlers
  selAluno.addEventListener('change', () => {
    const filtro = filtrarPorAluno(registrosCache, selAluno.value);
    // rebuild charts with filtro
    buildEmotionChart(filtro, document.getElementById('chartEmocoes').getContext('2d'));
    buildTendencyChart(filtro, document.getElementById('chartTendencias').getContext('2d'));
    buildScoresChart(filtro, document.getElementById('chartPontuacoes').getContext('2d'));
    renderLista(filtro);
  });

  btnRefresh.addEventListener('click', async () => {
    btnRefresh.disabled = true;
    btnRefresh.innerText = 'Atualizando...';
    try {
      registrosCache = await fetchRegistros();
      popularSelectAlunos(registrosCache);
      const backendAlertas = await fetchAlertas();
      const finalAlertas = backendAlertas && backendAlertas.length ? backendAlertas : gerarAlertasLocais(registrosCache);
      renderAlertas(finalAlertas);

      // atualiza visual
      selAluno.value = '__all__';
      buildEmotionChart(registrosCache, document.getElementById('chartEmocoes').getContext('2d'));
      buildTendencyChart(registrosCache, document.getElementById('chartTendencias').getContext('2d'));
      buildScoresChart(registrosCache, document.getElementById('chartPontuacoes').getContext('2d'));
      renderLista(registrosCache);
    } catch (e) {
      alert('Erro ao atualizar: ' + e.message);
    } finally {
      btnRefresh.disabled = false;
      btnRefresh.innerText = 'Atualizar';
    }
  });

  btnLogout.addEventListener('click', () => {
    localStorage.removeItem('token');
    localStorage.removeItem('tipo');
    window.location.href = '/';
  });
}

init();
