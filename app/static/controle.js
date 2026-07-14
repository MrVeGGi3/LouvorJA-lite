const semanaInput = document.getElementById("semana");
const buscaInput = document.getElementById("busca-input");
const buscaEdicao = document.getElementById("busca-edicao");
const resultadosEl = document.getElementById("resultados");
const itensLiturgiaEl = document.getElementById("itens-liturgia");
const liturgiaVaziaEl = document.getElementById("liturgia-vazia");
const itemAtualEl = document.getElementById("item-atual");
const slideContadorEl = document.getElementById("slide-contador");

const abaSemanaBt = document.getElementById("aba-semana");
const abaFixosBt = document.getElementById("aba-fixos");
const painelSemanaEl = document.getElementById("painel-semana");
const painelFixosEl = document.getElementById("painel-fixos");
const itensFixosEl = document.getElementById("itens-fixos");

const playerEl = document.getElementById("player");
const audioEl = document.getElementById("audio");
const playBt = document.getElementById("player-play");
const faixaCantadoBt = document.getElementById("faixa-cantado");
const faixaPlaybackBt = document.getElementById("faixa-playback");
const progressoEl = document.getElementById("player-progresso");
const tempoEl = document.getElementById("player-tempo");
const volumeEl = document.getElementById("player-volume");
const seguirEl = document.getElementById("player-seguir");
const avisoEl = document.getElementById("player-aviso");

let liturgiaAtual = null;
let fixosAtuais = null;
let abaAtiva = "semana";
let resultadosVisiveis = [];
let buscaTimeout = null;

// Estado do player: as faixas da música atual, os slides e a linha do tempo em segundos.
let faixas = { cantado: null, playback: null };
let faixaAtual = "cantado";
let slidesAtuais = [];
let linhaDoTempo = [];
let slideProjetado = -1;

function hojeISO() {
  return new Date().toISOString().slice(0, 10);
}

async function api(path, options = {}) {
  const resp = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!resp.ok) {
    const detalhe = await resp.json().catch(() => ({}));
    throw new Error(detalhe.detail || `Erro ${resp.status} em ${path}`);
  }
  return resp.status === 204 ? null : resp.json();
}

async function buscar() {
  const q = buscaInput.value.trim();
  resultadosEl.innerHTML = "";
  if (!q) return;

  const edicao = buscaEdicao.value;
  let resultados;
  if (edicao === "tudo") {
    const musicas = await api(`/api/musicas/busca?q=${encodeURIComponent(q)}`);
    resultados = musicas.map((m) => ({
      origem: "musicas",
      ref_id: m.id_music,
      titulo: m.album ? `${m.titulo} — ${m.album}` : m.titulo,
    }));
  } else {
    const hinos = await api(`/api/hinario?q=${encodeURIComponent(q)}&edicao=${edicao}`);
    resultados = hinos.map((h) => ({
      origem: edicao === "1996" ? "hinario_1996" : "hinario",
      ref_id: h.id_music,
      titulo: `${h.numero} - ${h.titulo}`,
    }));
  }
  renderResultados(resultados);
}

function renderResultados(lista) {
  resultadosVisiveis = lista;
  resultadosEl.innerHTML = "";
  for (const item of lista) {
    const li = document.createElement("li");

    const texto = document.createElement("span");
    texto.textContent = item.titulo;
    texto.title = "Clique para projetar";
    texto.addEventListener("click", () => projetarItem(item));
    li.appendChild(texto);

    const btAdicionar = document.createElement("button");
    btAdicionar.textContent = "+ adicionar";
    btAdicionar.title = abaAtiva === "fixos"
      ? "Encaixar no primeiro momento sem hino"
      : "Adicionar à liturgia da semana";
    btAdicionar.addEventListener("click", () =>
      abaAtiva === "fixos" ? encaixarEmFixo(item) : adicionarItemLiturgia(item),
    );
    li.appendChild(btAdicionar);

    resultadosEl.appendChild(li);
  }
}

async function carregarLiturgia() {
  const week = semanaInput.value;
  try {
    liturgiaAtual = await api(`/api/liturgias/${week}`);
  } catch {
    liturgiaAtual = null;
  }
  renderLiturgia();
}

function renderLiturgia() {
  itensLiturgiaEl.innerHTML = "";
  const itens = liturgiaAtual?.itens || [];
  liturgiaVaziaEl.style.display = itens.length ? "none" : "block";

  itens.forEach((item, index) => {
    const li = document.createElement("li");

    const texto = document.createElement("span");
    texto.textContent = item.titulo_exibicao;
    li.appendChild(texto);

    const botoes = document.createElement("div");
    botoes.className = "item-botoes";

    const btProjetar = document.createElement("button");
    btProjetar.textContent = "▶";
    btProjetar.title = "Projetar";
    btProjetar.addEventListener("click", () => projetarItem(item, index));
    botoes.appendChild(btProjetar);

    if (index > 0) {
      const btCima = document.createElement("button");
      btCima.textContent = "↑";
      btCima.addEventListener("click", () => moverItem(index, index - 1));
      botoes.appendChild(btCima);
    }
    if (index < itens.length - 1) {
      const btBaixo = document.createElement("button");
      btBaixo.textContent = "↓";
      btBaixo.addEventListener("click", () => moverItem(index, index + 1));
      botoes.appendChild(btBaixo);
    }

    const btRemover = document.createElement("button");
    btRemover.textContent = "✕";
    btRemover.addEventListener("click", () => removerItem(item.id));
    botoes.appendChild(btRemover);

    li.appendChild(botoes);
    itensLiturgiaEl.appendChild(li);
  });
}

async function adicionarItemLiturgia(item) {
  const week = semanaInput.value;
  liturgiaAtual = await api(`/api/liturgias/${week}/itens`, {
    method: "POST",
    body: JSON.stringify({
      ordem: 0,
      tipo: "hino",
      origem: item.origem,
      ref_id: item.ref_id,
      titulo_exibicao: item.titulo,
    }),
  });
  renderLiturgia();
}

async function removerItem(itemId) {
  const week = semanaInput.value;
  liturgiaAtual = await api(`/api/liturgias/${week}/itens/${itemId}`, { method: "DELETE" });
  renderLiturgia();
}

async function moverItem(de, para) {
  const week = semanaInput.value;
  const ids = liturgiaAtual.itens.map((i) => i.id);
  const [movido] = ids.splice(de, 1);
  ids.splice(para, 0, movido);
  liturgiaAtual = await api(`/api/liturgias/${week}/reordenar`, {
    method: "PUT",
    body: JSON.stringify(ids),
  });
  renderLiturgia();
}

async function projetarItem(item, itemIndex = null) {
  const [slides, audio] = await Promise.all([
    api(`/api/musicas/${item.ref_id}/slides`),
    api(`/api/musicas/${item.ref_id}/audio`).catch(() => ({ cantado: null, playback: null })),
  ]);

  const estado = await api("/api/projecao/estado", {
    method: "POST",
    body: JSON.stringify({
      liturgia_id: liturgiaAtual?.id || null,
      week_of: semanaInput.value,
      item_index: itemIndex,
      titulo_item: item.titulo_exibicao || item.titulo,
      slides,
      slide_index: 0,
    }),
  });
  itemAtualEl.textContent = estado.titulo_item || "Sem título";
  atualizarContador(estado);

  slidesAtuais = slides;
  slideProjetado = 0;
  prepararPlayer(audio);
}

// ---------------------------------------------------------------- hinos fixos

function trocarAba(qual) {
  abaAtiva = qual;
  abaSemanaBt.classList.toggle("ativa", qual === "semana");
  abaFixosBt.classList.toggle("ativa", qual === "fixos");
  painelSemanaEl.hidden = qual !== "semana";
  painelFixosEl.hidden = qual !== "fixos";
  // Redesenha os resultados: o "+ adicionar" passa a apontar para a outra aba.
  renderResultados(resultadosVisiveis);
}

async function carregarFixos() {
  fixosAtuais = await api("/api/fixos");
  renderFixos();
}

async function salvarFixos() {
  fixosAtuais = await api("/api/fixos", {
    method: "PUT",
    body: JSON.stringify(fixosAtuais),
  });
  renderFixos();
}

function renderFixos() {
  itensFixosEl.innerHTML = "";
  for (const item of fixosAtuais?.itens || []) {
    const li = document.createElement("li");

    const nome = document.createElement("input");
    nome.className = "nome-fixo";
    nome.value = item.nome;
    nome.title = "Nome do momento do culto";
    nome.addEventListener("change", () => {
      item.nome = nome.value.trim() || "Sem nome";
      salvarFixos();
    });
    li.appendChild(nome);

    const hino = document.createElement("span");
    hino.className = item.ref_id ? "hino-fixo" : "hino-fixo vazio";
    hino.textContent = item.titulo_exibicao || "(sem hino)";
    li.appendChild(hino);

    const botoes = document.createElement("div");
    botoes.className = "item-botoes";

    if (item.ref_id) {
      const btProjetar = document.createElement("button");
      btProjetar.textContent = "▶";
      btProjetar.title = "Projetar";
      btProjetar.addEventListener("click", () =>
        projetarItem({ ref_id: item.ref_id, titulo: item.titulo_exibicao }),
      );
      botoes.appendChild(btProjetar);

      const btLimpar = document.createElement("button");
      btLimpar.textContent = "⌫";
      btLimpar.title = "Tirar o hino, mantendo o momento";
      btLimpar.addEventListener("click", () => {
        item.ref_id = null;
        item.titulo_exibicao = null;
        salvarFixos();
      });
      botoes.appendChild(btLimpar);
    }

    const btRemover = document.createElement("button");
    btRemover.textContent = "✕";
    btRemover.title = "Remover o momento";
    btRemover.addEventListener("click", async () => {
      fixosAtuais = await api(`/api/fixos/itens/${item.id}`, { method: "DELETE" });
      renderFixos();
    });
    botoes.appendChild(btRemover);

    li.appendChild(botoes);
    itensFixosEl.appendChild(li);
  }
}

// O hino vai para o primeiro momento ainda vazio — é o caso comum (a lista de momentos já
// existe e só falta preencher). Se todos estiverem preenchidos, cria um momento novo.
async function encaixarEmFixo(item) {
  const vazio = (fixosAtuais?.itens || []).find((i) => !i.ref_id);
  if (vazio) {
    vazio.ref_id = item.ref_id;
    vazio.titulo_exibicao = item.titulo;
    await salvarFixos();
    return;
  }
  fixosAtuais = await api("/api/fixos/itens", {
    method: "POST",
    body: JSON.stringify({ nome: "Novo momento", ref_id: item.ref_id, titulo_exibicao: item.titulo }),
  });
  renderFixos();
}

abaSemanaBt.addEventListener("click", () => trocarAba("semana"));
abaFixosBt.addEventListener("click", () => trocarAba("fixos"));

document.getElementById("novo-fixo").addEventListener("click", async () => {
  fixosAtuais = await api("/api/fixos/itens", {
    method: "POST",
    body: JSON.stringify({ nome: "Novo momento" }),
  });
  renderFixos();
});

// ---------------------------------------------------------------- player de áudio

function tempoParaSegundos(hhmmss) {
  if (!hhmmss) return 0;
  const [h, m, s] = hhmmss.split(":").map(Number);
  return (h || 0) * 3600 + (m || 0) * 60 + (s || 0);
}

function formatarSegundos(total) {
  if (!Number.isFinite(total)) return "0:00";
  const m = Math.floor(total / 60);
  const s = Math.floor(total % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

// A escolha da linha do tempo é por música, não por slide: misturar `tempo_instrumental` zerado
// com valores reais produziria uma linha do tempo que anda para trás.
function montarLinhaDoTempo(faixa) {
  const usaInstrumental =
    faixa === "playback" &&
    slidesAtuais.some((s) => tempoParaSegundos(s.tempo_instrumental) > 0);

  return slidesAtuais.map((s) =>
    tempoParaSegundos(usaInstrumental ? s.tempo_instrumental : s.tempo),
  );
}

function prepararPlayer(audio) {
  faixas = audio || { cantado: null, playback: null };

  const disponivel = (f) => Boolean(f && f.disponivel);
  faixaPlaybackBt.disabled = !disponivel(faixas.playback);
  faixaCantadoBt.disabled = !disponivel(faixas.cantado);

  if (!disponivel(faixas.cantado) && !disponivel(faixas.playback)) {
    playerEl.hidden = true;
    audioEl.pause();
    audioEl.removeAttribute("src");
    return;
  }

  playerEl.hidden = false;
  faixaAtual = disponivel(faixas.cantado) ? "cantado" : "playback";
  trocarFaixa(faixaAtual, { autoplay: false });

  const semPlayback = faixas.playback && !faixas.playback.disponivel;
  avisoEl.hidden = !semPlayback;
  if (semPlayback) avisoEl.textContent = "playback não baixado";
}

function trocarFaixa(qual, { autoplay = true } = {}) {
  const faixa = faixas[qual];
  if (!faixa || !faixa.disponivel) return;

  faixaAtual = qual;
  faixaCantadoBt.classList.toggle("ativa", qual === "cantado");
  faixaPlaybackBt.classList.toggle("ativa", qual === "playback");

  // Cantado e playback têm tempos diferentes — a linha do tempo é remontada junto com a faixa.
  linhaDoTempo = montarLinhaDoTempo(qual);

  audioEl.src = faixa.url;
  audioEl.load();
  if (autoplay) audioEl.play().catch(() => {});
}

function indiceDoSlideEm(segundos) {
  let indice = 0;
  for (let i = 0; i < linhaDoTempo.length; i++) {
    if (linhaDoTempo[i] <= segundos) indice = i;
    else break;
  }
  return indice;
}

async function irParaSlide(indice) {
  if (indice === slideProjetado) return;
  slideProjetado = indice;
  try {
    const estado = await api("/api/projecao/slide", {
      method: "POST",
      body: JSON.stringify({ slide_index: indice }),
    });
    atualizarContador(estado);
  } catch (erro) {
    console.warn(erro.message);
  }
}

audioEl.addEventListener("loadedmetadata", () => {
  progressoEl.max = audioEl.duration || 0;
  tempoEl.textContent = `0:00 / ${formatarSegundos(audioEl.duration)}`;
});

audioEl.addEventListener("timeupdate", () => {
  progressoEl.value = audioEl.currentTime;
  tempoEl.textContent =
    `${formatarSegundos(audioEl.currentTime)} / ${formatarSegundos(audioEl.duration)}`;

  if (seguirEl.checked && linhaDoTempo.length) {
    irParaSlide(indiceDoSlideEm(audioEl.currentTime));
  }
});

audioEl.addEventListener("play", () => (playBt.textContent = "⏸"));
audioEl.addEventListener("pause", () => (playBt.textContent = "▶"));

playBt.addEventListener("click", () => {
  if (audioEl.paused) audioEl.play().catch(() => {});
  else audioEl.pause();
});

// Arrastar a barra reposiciona o slide pelo mesmo caminho do auto-advance.
progressoEl.addEventListener("input", () => {
  audioEl.currentTime = Number(progressoEl.value);
});

volumeEl.addEventListener("input", () => (audioEl.volume = Number(volumeEl.value)));

faixaCantadoBt.addEventListener("click", () => trocarFaixa("cantado"));
faixaPlaybackBt.addEventListener("click", () => trocarFaixa("playback"));

function atualizarContador(estado) {
  slideContadorEl.textContent = `${estado.total_slides ? estado.slide_index + 1 : 0}/${estado.total_slides}`;
}

async function navegarSlide(direcao) {
  try {
    const estado = await api("/api/projecao/navegar", {
      method: "POST",
      body: JSON.stringify({ direcao }),
    });
    // Sem isto, o próximo timeupdate acharia que o slide "mudou" e puxaria a projeção de volta.
    slideProjetado = estado.slide_index;
    atualizarContador(estado);
  } catch (erro) {
    console.warn(erro.message);
  }
}

document.getElementById("slide-anterior").addEventListener("click", () => navegarSlide("ant"));
document.getElementById("slide-proximo").addEventListener("click", () => navegarSlide("prox"));

document.getElementById("abrir-projecao").addEventListener("click", () => {
  window.open("/projecao", "louvorja-projecao", "fullscreen=yes");
});

buscaInput.addEventListener("input", () => {
  clearTimeout(buscaTimeout);
  buscaTimeout = setTimeout(buscar, 300);
});
buscaEdicao.addEventListener("change", buscar);

semanaInput.value = hojeISO();
semanaInput.addEventListener("change", carregarLiturgia);
carregarLiturgia();
carregarFixos();

document.addEventListener("keydown", (evento) => {
  if (evento.target.tagName === "INPUT" || evento.target.tagName === "SELECT") return;
  if (evento.key === "ArrowRight" || evento.key === " ") {
    evento.preventDefault();
    navegarSlide("prox");
  } else if (evento.key === "ArrowLeft") {
    navegarSlide("ant");
  } else if (evento.key === "p" || evento.key === "P") {
    evento.preventDefault();
    playBt.click();
  }
});
