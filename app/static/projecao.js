const telaEl = document.getElementById("tela");
const letraEl = document.getElementById("letra");
const letraAuxEl = document.getElementById("letra-aux");

let ultimaAtualizacao = null;

function aplicarSlide(estado) {
  const slide = estado.slide || {};

  telaEl.style.backgroundColor = slide.cor_fundo || "#000000";
  telaEl.style.backgroundImage = slide.imagem_fundo ? `url("${slide.imagem_fundo}")` : "none";

  letraEl.textContent = slide.letra || "";
  letraEl.style.color = slide.cor_letra || "#ffffff";
  // O tamanho vem em % da altura da tela (o título é maior que a letra), como no LouvorJA.
  letraEl.style.fontSize = `${slide.tamanho_letra || 14}vh`;

  if (slide.letra_aux) {
    letraAuxEl.textContent = slide.letra_aux;
    letraAuxEl.style.color = slide.cor_letra_aux || slide.cor_letra || "#ffffff";
    letraAuxEl.style.fontSize = `${slide.tamanho_letra_aux || 10}vh`;
    letraAuxEl.style.display = "block";
  } else {
    letraAuxEl.style.display = "none";
  }
}

function aplicarEstado(estado) {
  if (estado.atualizado_em === ultimaAtualizacao) return;
  ultimaAtualizacao = estado.atualizado_em;
  aplicarSlide(estado);
}

async function atualizar() {
  try {
    const resp = await fetch("/api/projecao/estado");
    if (!resp.ok) return;
    aplicarEstado(await resp.json());
  } catch {
    // Mantém o último slide renderizado em caso de falha momentânea do servidor.
  }
}

// O SSE entrega a virada de slide na hora; o polling fica como rede de segurança, porque meio
// segundo de atraso é invisível num clique mas atrapalha a sincronia com o áudio.
let polling = null;

function iniciarPolling() {
  if (polling === null) polling = setInterval(atualizar, 500);
}

function conectarStream() {
  const stream = new EventSource("/api/projecao/stream");

  stream.addEventListener("message", (evento) => {
    clearInterval(polling);
    polling = null;
    aplicarEstado(JSON.parse(evento.data));
  });

  stream.addEventListener("error", () => {
    iniciarPolling();
  });
}

document.addEventListener("keydown", (evento) => {
  if (evento.key === "Escape" && document.fullscreenElement) {
    document.exitFullscreen();
  }
});

telaEl.addEventListener("dblclick", () => {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen();
  }
});

// Best-effort: alguns navegadores só entram em fullscreen com gesto próprio — nesses casos a
// janela já nasce cobrindo o monitor externo e o duplo-clique completa o fullscreen.
document.documentElement.requestFullscreen?.().catch(() => {});

atualizar();
if (window.EventSource) {
  conectarStream();
} else {
  iniciarPolling();
}
