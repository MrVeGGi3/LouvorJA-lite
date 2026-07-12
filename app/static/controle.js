const semanaInput = document.getElementById("semana");
const buscaInput = document.getElementById("busca-input");
const buscaEdicao = document.getElementById("busca-edicao");
const resultadosEl = document.getElementById("resultados");
const itensLiturgiaEl = document.getElementById("itens-liturgia");
const liturgiaVaziaEl = document.getElementById("liturgia-vazia");
const itemAtualEl = document.getElementById("item-atual");
const slideContadorEl = document.getElementById("slide-contador");

let liturgiaAtual = null;
let buscaTimeout = null;

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
    resultados = await api(`/api/musicas/busca?q=${encodeURIComponent(q)}`);
    resultados = resultados.map((m) => ({
      origem: "MUSICAS",
      ref_id: m.ID,
      titulo: m.NOME,
    }));
  } else {
    resultados = await api(`/api/hinario?q=${encodeURIComponent(q)}&edicao=${edicao}`);
    resultados = resultados.map((h) => ({
      origem: edicao === "1996" ? "HINARIO_ADVENTISTA_1996" : "HINARIO_ADVENTISTA",
      ref_id: h.ID,
      titulo: `${h.FAIXA} - ${h.NOME_COM || h.NOME}`,
    }));
  }
  renderResultados(resultados);
}

function renderResultados(lista) {
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
    btAdicionar.addEventListener("click", () => adicionarItemLiturgia(item));
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
  const slides = await api(`/api/musicas/${item.origem}/${item.ref_id}/slides`);
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
}

function atualizarContador(estado) {
  slideContadorEl.textContent = `${estado.total_slides ? estado.slide_index + 1 : 0}/${estado.total_slides}`;
}

async function navegarSlide(direcao) {
  try {
    const estado = await api("/api/projecao/navegar", {
      method: "POST",
      body: JSON.stringify({ direcao }),
    });
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

document.addEventListener("keydown", (evento) => {
  if (evento.target.tagName === "INPUT" || evento.target.tagName === "SELECT") return;
  if (evento.key === "ArrowRight" || evento.key === " ") {
    evento.preventDefault();
    navegarSlide("prox");
  } else if (evento.key === "ArrowLeft") {
    navegarSlide("ant");
  }
});
