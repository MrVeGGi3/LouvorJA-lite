const diasSemanaEl = document.getElementById("dias-semana");
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

// A liturgia é organizada por dia da semana; o índice segue Date.getDay() (0=domingo).
const DIAS = ["domingo", "segunda", "terca", "quarta", "quinta", "sexta", "sabado"];
const ROTULOS_DIAS = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

let liturgiaAtual = null;
let diaAtual = null;
let fixosAtuais = null;
let fixoDestinoId = null;
let itemDestinoId = null;
let abaAtiva = "semana";
let resultadosVisiveis = [];
let buscaTimeout = null;
// Janela de projeção aberta pelo play/"Abrir Projeção" — reutilizada e focada em vez de reaberta.
let projecaoWin = null;
let vigiaProjecao = null;

// Estado do player: as faixas da música atual, os slides e a linha do tempo em segundos.
let faixas = { cantado: null, playback: null };
let faixaAtual = "cantado";
let slidesAtuais = [];
let linhaDoTempo = [];
let slideProjetado = -1;

function diaHojeSlug() {
  return DIAS[new Date().getDay()];
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

  // O botão diz em qual momento o hino vai cair, porque o destino muda conforme o momento que
  // estiver marcado (e, nos fixos, conforme a lista se enche).
  const destino = abaAtiva === "fixos" ? destinoFixo() : destinoItem();
  const nomeDestino = destino && (abaAtiva === "fixos" ? destino.nome : destino.descricao);

  for (const item of lista) {
    const li = document.createElement("li");

    const texto = document.createElement("span");
    texto.textContent = item.titulo;
    texto.title = "Clique para projetar";
    texto.addEventListener("click", () => projetarItem(item));
    li.appendChild(texto);

    const btAdicionar = document.createElement("button");
    if (destino) {
      // O momento recém-criado ainda não tem nome; sem ele o rótulo vira "+ em (sem nome)".
      const alvo = nomeDestino || "(sem nome)";
      btAdicionar.textContent = `+ em ${alvo}`;
      btAdicionar.title = vazio(destino)
        ? `Colocar este hino em "${alvo}"`
        : `Trocar o que está em "${alvo}" por este hino`;
    } else if (abaAtiva === "fixos") {
      btAdicionar.textContent = "+ novo momento";
      btAdicionar.title = "Todos os momentos já estão preenchidos — este vira um momento novo";
    } else {
      btAdicionar.textContent = "+ adicionar";
      btAdicionar.title = "Adicionar ao fim da liturgia da semana";
    }
    btAdicionar.addEventListener("click", () =>
      abaAtiva === "fixos" ? encaixarEmFixo(item) : encaixarEmItem(item),
    );
    li.appendChild(btAdicionar);

    resultadosEl.appendChild(li);
  }
}

async function carregarLiturgia() {
  try {
    liturgiaAtual = await api(`/api/liturgias/${diaAtual}`);
  } catch {
    liturgiaAtual = null;
  }
  renderLiturgia();
}

function renderLiturgia() {
  itensLiturgiaEl.innerHTML = "";
  const itens = liturgiaAtual?.itens || [];
  liturgiaVaziaEl.style.display = itens.length ? "none" : "block";

  const destino = destinoItem();

  itens.forEach((item, index) => {
    const li = document.createElement("li");
    li.classList.toggle("alvo", destino?.id === item.id);
    li.addEventListener("click", (evento) => {
      if (!evento.target.closest("button, input")) mirarItem(item);
    });

    const descricao = document.createElement("input");
    descricao.className = "nome-momento";
    descricao.value = item.descricao || "";
    descricao.placeholder = "o que é este momento";
    descricao.title = "Momento do culto a que este item pertence";
    descricao.addEventListener("change", () =>
      salvarItem(item, { descricao: descricao.value.trim() }),
    );
    li.appendChild(descricao);

    const texto = document.createElement("span");
    texto.className = "conteudo-item";
    if (item.url_video) {
      texto.classList.add("video");
      texto.textContent = `🎬 ${rotuloVideo(item.url_video)}`;
      texto.title = `Abrir numa aba nova: ${item.url_video}`;
      texto.addEventListener("click", () => abrirVideo(item));
    } else if (item.ref_id) {
      texto.textContent = item.titulo_exibicao;
    } else {
      texto.classList.add("vazio");
      texto.textContent = "(só o momento)";
    }
    li.appendChild(texto);

    const botoes = document.createElement("div");
    botoes.className = "item-botoes";

    // O vídeo não tem slides no banco, então abre numa aba em vez de projetar; o momento sem
    // nada ainda não tem o que tocar, e mostra por onde escolher.
    if (item.url_video) {
      const btAbrir = document.createElement("button");
      btAbrir.textContent = "🎬";
      btAbrir.title = "Abrir o vídeo numa aba nova";
      btAbrir.addEventListener("click", () => abrirVideo(item));
      botoes.appendChild(btAbrir);
    } else if (item.ref_id) {
      const btProjetar = document.createElement("button");
      btProjetar.textContent = "▶";
      btProjetar.title = "Projetar";
      btProjetar.addEventListener("click", () => projetarItem(item, index));
      botoes.appendChild(btProjetar);
    } else {
      const btHino = document.createElement("button");
      btHino.textContent = "+ hino";
      btHino.title = "Escolher um hino para este momento";
      btHino.addEventListener("click", () => escolherHinoParaItem(item));
      botoes.appendChild(btHino);

      const btVideo = document.createElement("button");
      btVideo.textContent = "+ vídeo";
      btVideo.title = "Colar o link de um vídeo para este momento";
      btVideo.addEventListener("click", () => definirVideoItem(item));
      botoes.appendChild(btVideo);
    }

    // Esvaziar devolve o item ao momento só de nome, mantendo a descrição e o lugar na ordem.
    if (!vazio(item)) {
      const btLimpar = document.createElement("button");
      btLimpar.textContent = "⌫";
      btLimpar.title = item.url_video
        ? "Tirar o vídeo, mantendo o momento"
        : "Tirar o hino, mantendo o momento";
      btLimpar.addEventListener("click", () =>
        salvarItem(item, {
          tipo: "nota", origem: null, ref_id: null, titulo_exibicao: "", url_video: null,
        }),
      );
      botoes.appendChild(btLimpar);
    }

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

  // O rótulo do "+" na busca nomeia o momento de destino, que acabou de mudar.
  if (abaAtiva === "semana") renderResultados(resultadosVisiveis);
}

// Recebe tanto o resultado da busca (só hino, sem descrição) quanto o momento fixo copiado pelo
// "→" (que pode ser vídeo e traz o nome do momento). O `ordem: 0` é descartado: quem numera é o
// servidor, pelo tamanho da lista.
async function adicionarItemLiturgia(item) {
  liturgiaAtual = await api(`/api/liturgias/${diaAtual}/itens`, {
    method: "POST",
    body: JSON.stringify({
      ordem: 0,
      tipo: tipoDoItem(item),
      origem: item.origem || null,
      ref_id: item.ref_id || null,
      titulo_exibicao: item.titulo || "",
      descricao: item.descricao || "",
      url_video: item.url_video || null,
    }),
  });
  renderLiturgia();
}

// O momento que ainda não toca nada: só o nome, para o sonoplasta saber o que acontece ali.
// Nasce vazio e mirado, para o próximo hino da busca já cair nele.
async function adicionarMomento() {
  liturgiaAtual = await api(`/api/liturgias/${diaAtual}/itens`, {
    method: "POST",
    body: JSON.stringify({ ordem: 0, tipo: "nota", titulo_exibicao: "", descricao: "" }),
  });
  itemDestinoId = liturgiaAtual.itens[liturgiaAtual.itens.length - 1].id;
  renderLiturgia();
}

// O endpoint troca o item inteiro (só o `id` ele preserva), então toda edição de linha — a
// descrição, o vídeo, o esvaziar — passa por aqui com os campos que mudaram.
async function salvarItem(item, mudancas) {
  liturgiaAtual = await api(`/api/liturgias/${diaAtual}/itens/${item.id}`, {
    method: "PUT",
    body: JSON.stringify({ ...item, ...mudancas }),
  });
  renderLiturgia();
}

// Hino, vídeo e nota são o mesmo item preenchido de jeitos diferentes; o `tipo` é consequência do
// que está lá dentro, não uma escolha à parte.
function tipoDoItem({ ref_id, url_video }) {
  if (url_video) return "video";
  return ref_id ? "hino" : "nota";
}

// Quem recebe o próximo hino da busca na aba da semana. Diferente dos fixos, não há queda no
// primeiro momento vazio: na semana os momentos vazios costumam ser oração, avisos e pregação, e
// um hino caindo sozinho num deles seria surpresa. Sem mira, o "+" acrescenta no fim, como antes.
function destinoItem() {
  return (liturgiaAtual?.itens || []).find((i) => i.id === itemDestinoId) || null;
}

function mirarItem(item) {
  itemDestinoId = item.id;
  renderLiturgia();
}

function escolherHinoParaItem(item) {
  mirarItem(item);
  buscaInput.focus();
  buscaInput.select();
}

async function encaixarEmItem(resultado) {
  const destino = destinoItem();
  if (!destino) return adicionarItemLiturgia(resultado);

  itemDestinoId = null;
  // O hino toma o lugar do vídeo, se havia um: o momento toca um ou outro, nunca os dois.
  await salvarItem(destino, {
    tipo: "hino",
    origem: resultado.origem,
    ref_id: resultado.ref_id,
    titulo_exibicao: resultado.titulo,
    url_video: null,
  });
}

async function removerItem(itemId) {
  liturgiaAtual = await api(`/api/liturgias/${diaAtual}/itens/${itemId}`, { method: "DELETE" });
  renderLiturgia();
}

async function moverItem(de, para) {
  const ids = liturgiaAtual.itens.map((i) => i.id);
  const [movido] = ids.splice(de, 1);
  ids.splice(para, 0, movido);
  liturgiaAtual = await api(`/api/liturgias/${diaAtual}/reordenar`, {
    method: "PUT",
    body: JSON.stringify(ids),
  });
  renderLiturgia();
}

async function projetarItem(item, itemIndex = null) {
  // Antes de qualquer await: a projeção precisa abrir ainda dentro do gesto do clique, senão o
  // navegador bloqueia o pop-up e nem chega a pedir a permissão de gerenciamento de janelas.
  garantirProjecao();

  const [slides, audio] = await Promise.all([
    api(`/api/musicas/${item.ref_id}/slides`),
    api(`/api/musicas/${item.ref_id}/audio`).catch(() => ({ cantado: null, playback: null })),
  ]);

  const estado = await api("/api/projecao/estado", {
    method: "POST",
    body: JSON.stringify({
      liturgia_id: liturgiaAtual?.id || null,
      dia: diaAtual,
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

// Garante que a projeção esteja aberta e, quando há um monitor externo (Window Management API, só
// Chromium e com permissão), joga a janela pra ele. Precisa ser chamada dentro do gesto do clique:
// a janela é aberta de imediato (para escapar do bloqueador de pop-up) e só depois é movida.
async function garantirProjecao() {
  if (projecaoWin && !projecaoWin.closed) {
    projecaoWin.focus();
    return;
  }

  projecaoWin = window.open("/projecao", "louvorja-projecao", "popup,width=1280,height=720");
  if (projecaoWin) vigiarProjecao();

  // Sem multitela ou fora do Chromium, fica como janela normal (arraste pro telão e F11/duplo-clique).
  if (!(window.screen?.isExtended && "getScreenDetails" in window)) return;

  let detalhes;
  try {
    detalhes = await window.getScreenDetails();
  } catch {
    return; // permissão negada — segue como janela normal
  }

  const alvo =
    detalhes.screens.find((s) => s !== detalhes.currentScreen) ||
    detalhes.screens.find((s) => !s.isPrimary);
  if (alvo && projecaoWin && !projecaoWin.closed) {
    projecaoWin.moveTo(alvo.availLeft, alvo.availTop);
    projecaoWin.resizeTo(alvo.availWidth, alvo.availHeight);
  }
}

async function definirVideoItem(item) {
  const url = pedirUrlVideo(item.url_video);
  if (!url) return;
  // O vídeo toma o lugar do hino, se havia um.
  await salvarItem(item, {
    tipo: "video", origem: null, ref_id: null, titulo_exibicao: "", url_video: url,
  });
}

// Fechar a projeção para a música: não há evento confiável entre janelas, então vigiamos o
// `closed` da janela e, quando ela some, pausamos o áudio e voltamos ao início da faixa.
function vigiarProjecao() {
  clearInterval(vigiaProjecao);
  vigiaProjecao = setInterval(() => {
    if (projecaoWin && !projecaoWin.closed) return;
    clearInterval(vigiaProjecao);
    vigiaProjecao = null;
    audioEl.pause();
    audioEl.currentTime = 0;
  }, 500);
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

// Vale para o momento fixo e para o item da liturgia: os dois guardam hino e vídeo nos mesmos
// campos, e estar vazio é não ter nenhum dos dois — só o nome do momento.
function vazio(item) {
  return !item.ref_id && !item.url_video;
}

// Quem recebe o próximo hino da busca: o momento que o usuário marcou ou, enquanto ele não
// marcar nenhum, o primeiro ainda sem nada. Marcar é uma mira de um tiro só (`encaixarEmFixo`
// desmarca depois de encaixar), então preencher a lista de cima para baixo continua sendo só
// clicar em "+" várias vezes.
function destinoFixo() {
  const itens = fixosAtuais?.itens || [];
  return itens.find((i) => i.id === fixoDestinoId) || itens.find(vazio) || null;
}

function mirarFixo(item) {
  fixoDestinoId = item.id;
  renderFixos();
}

// O momento sem hino não tinha por onde começar: só clicando na linha, o que ninguém adivinha.
// O botão faz os dois passos de uma vez — mira o momento e põe o cursor na busca, de onde o
// hino sai pelo "+ em <momento>".
function escolherHinoPara(item) {
  mirarFixo(item);
  buscaInput.focus();
  buscaInput.select();
}

// O "→" vale tanto para o momento com hino quanto para o com vídeo — só o momento vazio não
// tem o que copiar.
function botaoLiturgia(item, titulo) {
  const bt = document.createElement("button");
  bt.textContent = "→";
  bt.title = titulo;
  bt.addEventListener("click", () => enviarParaLiturgia(item, bt));
  return bt;
}

// Hino e vídeo dividem o mesmo espaço no momento, então esvaziar é sempre esvaziar os dois.
function botaoLimpar(item, titulo) {
  const bt = document.createElement("button");
  bt.textContent = "⌫";
  bt.title = titulo;
  bt.addEventListener("click", () => {
    item.origem = null;
    item.ref_id = null;
    item.titulo_exibicao = null;
    item.url_video = null;
    salvarFixos();
  });
  return bt;
}

// O louvor que não está no banco — vem do YouTube. Fica guardado como link e abre numa aba;
// a projeção continua sendo só dos hinos do banco. Devolve `null` se o usuário desistir ou colar
// algo que o servidor recusaria de qualquer jeito.
function pedirUrlVideo(atual) {
  const resposta = prompt("Cole o link do vídeo (YouTube):", atual || "");
  if (resposta === null) return null;

  const url = resposta.trim();
  if (!url) return null;
  if (!/^https?:\/\//i.test(url)) {
    alert("O link precisa começar com http:// ou https://");
    return null;
  }
  return url;
}

async function definirVideo(item) {
  const url = pedirUrlVideo(item.url_video);
  if (!url) return;

  // Pôr um vídeo tira o hino: o momento toca um ou outro, nunca os dois.
  item.origem = null;
  item.ref_id = null;
  item.titulo_exibicao = null;
  item.url_video = url;
  await salvarFixos();
}

function abrirVideo(item) {
  window.open(item.url_video, "_blank", "noopener");
}

// O espaço da linha é curto: o "https://www." não identifica vídeo nenhum, então some (a URL
// inteira fica no tooltip) e o que sobra da largura vai para a parte que distingue um link do
// outro.
function rotuloVideo(url) {
  return url.replace(/^https?:\/\/(www\.)?/i, "");
}

function renderFixos() {
  const destino = destinoFixo();
  itensFixosEl.innerHTML = "";

  for (const item of fixosAtuais?.itens || []) {
    const li = document.createElement("li");
    li.classList.toggle("alvo", destino?.id === item.id);
    li.title = "Clique para o próximo hino da busca cair aqui";
    li.addEventListener("click", (evento) => {
      if (!evento.target.closest("button, input")) mirarFixo(item);
    });

    const nome = document.createElement("input");
    nome.className = "nome-momento";
    nome.value = item.nome;
    nome.title = "Nome do momento do culto";
    nome.addEventListener("change", () => {
      item.nome = nome.value.trim() || "Sem nome";
      salvarFixos();
    });
    li.appendChild(nome);

    const hino = document.createElement("span");
    hino.className = "conteudo-item";
    if (item.ref_id) {
      hino.textContent = item.titulo_exibicao;
    } else if (item.url_video) {
      hino.classList.add("video");
      hino.textContent = `🎬 ${rotuloVideo(item.url_video)}`;
      hino.title = `Abrir numa aba nova: ${item.url_video}`;
      hino.addEventListener("click", () => abrirVideo(item));
    } else {
      hino.classList.add("vazio");
      hino.textContent = "(sem hino)";
    }
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

      botoes.appendChild(botaoLiturgia(item, "Copiar este hino para a liturgia da semana"));

      botoes.appendChild(botaoLimpar(item, "Tirar o hino, mantendo o momento"));
    } else if (item.url_video) {
      const btAbrir = document.createElement("button");
      btAbrir.textContent = "🎬";
      btAbrir.title = "Abrir o vídeo numa aba nova";
      btAbrir.addEventListener("click", () => abrirVideo(item));
      botoes.appendChild(btAbrir);

      const btTrocar = document.createElement("button");
      btTrocar.textContent = "✎";
      btTrocar.title = "Trocar o link do vídeo";
      btTrocar.addEventListener("click", () => definirVideo(item));
      botoes.appendChild(btTrocar);

      botoes.appendChild(botaoLiturgia(item, "Copiar este vídeo para a liturgia da semana"));

      botoes.appendChild(botaoLimpar(item, "Tirar o vídeo, mantendo o momento"));
    } else {
      const btEscolher = document.createElement("button");
      btEscolher.textContent = "+ hino";
      btEscolher.title = "Escolher um hino para este momento";
      btEscolher.addEventListener("click", () => escolherHinoPara(item));
      botoes.appendChild(btEscolher);

      const btVideo = document.createElement("button");
      btVideo.textContent = "+ vídeo";
      btVideo.title = "Colar o link de um vídeo (YouTube) para este momento";
      btVideo.addEventListener("click", () => definirVideo(item));
      botoes.appendChild(btVideo);
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

  // O rótulo do "+" na busca nomeia o momento de destino, que acabou de mudar.
  if (abaAtiva === "fixos") renderResultados(resultadosVisiveis);
}

async function encaixarEmFixo(item) {
  const destino = destinoFixo();
  if (!destino) {
    // Todos os momentos já estão preenchidos e nenhum está marcado: o hino vira um momento novo.
    fixosAtuais = await api("/api/fixos/itens", {
      method: "POST",
      body: JSON.stringify({
        nome: "Novo momento",
        origem: item.origem,
        ref_id: item.ref_id,
        titulo_exibicao: item.titulo,
      }),
    });
    renderFixos();
    return;
  }
  destino.origem = item.origem;
  destino.ref_id = item.ref_id;
  destino.titulo_exibicao = item.titulo;
  destino.url_video = null; // o hino toma o lugar do vídeo, se havia um
  fixoDestinoId = null;
  await salvarFixos();
}

// O momento fixo é copiado, não movido: ele continua na aba de fixos para o culto que vem, e
// na semana vira um item comum, que dá para reordenar e remover como qualquer outro. O `nome` do
// momento vai junto como descrição — é o que diz, na liturgia, o que aquele hino ou vídeo é.
async function enviarParaLiturgia(item, botao) {
  await adicionarItemLiturgia({
    origem: item.origem,
    ref_id: item.ref_id,
    titulo: item.titulo_exibicao,
    url_video: item.url_video,
    descricao: item.nome,
  });
  botao.textContent = "✓";
  setTimeout(() => (botao.textContent = "→"), 1500);
}

abaSemanaBt.addEventListener("click", () => trocarAba("semana"));
abaFixosBt.addEventListener("click", () => trocarAba("fixos"));

document.getElementById("novo-momento").addEventListener("click", adicionarMomento);

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
  // O clique no ▶ é o gesto que autoriza o autoplay: a faixa Cantado já começa a tocar.
  trocarFaixa(faixaAtual, { autoplay: true });

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

document.getElementById("abrir-projecao").addEventListener("click", garantirProjecao);

buscaInput.addEventListener("input", () => {
  clearTimeout(buscaTimeout);
  buscaTimeout = setTimeout(buscar, 300);
});
buscaEdicao.addEventListener("change", buscar);

function renderDiasSemana() {
  diasSemanaEl.innerHTML = "";
  DIAS.forEach((dia, i) => {
    const bt = document.createElement("button");
    bt.type = "button";
    bt.className = "dia" + (dia === diaAtual ? " ativo" : "");
    bt.textContent = ROTULOS_DIAS[i];
    bt.dataset.dia = dia;
    bt.addEventListener("click", () => selecionarDia(dia));
    diasSemanaEl.appendChild(bt);
  });
}

function selecionarDia(dia) {
  diaAtual = dia;
  itemDestinoId = null; // a mira era de um item do dia que está saindo da tela
  diasSemanaEl.querySelectorAll(".dia").forEach((bt) => {
    bt.classList.toggle("ativo", bt.dataset.dia === dia);
  });
  carregarLiturgia();
}

diaAtual = diaHojeSlug();
renderDiasSemana();
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
