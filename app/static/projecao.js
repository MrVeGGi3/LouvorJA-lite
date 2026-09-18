const telaEl = document.getElementById("tela");
const blocoEl = document.getElementById("bloco");
const letraEl = document.getElementById("letra");
const letraAuxEl = document.getElementById("letra-aux");

let ultimaAtualizacao = null;

function aplicarSlide(estado) {
  const slide = estado.slide || {};

  // Tela preta sem descarregar o hino: com a tela espelhada, minimizar a projeção jogaria a área
  // de trabalho no telão, então escurecer é o jeito de sair da letra entre um momento e outro.
  if (estado.blackout) {
    telaEl.style.backgroundColor = "#000000";
    telaEl.style.backgroundImage = "none";
    blocoEl.style.display = "none";
    return;
  }

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

  // Sem texto nenhum a caixa não tem o que proteger, e sobraria uma tarja escura vazia no meio
  // da tela — é o estado inicial e o que fica depois do "parar".
  blocoEl.style.display = slide.letra || slide.letra_aux ? "flex" : "none";
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

// Virar o slide daqui é o que faz o modo manual funcionar com a tela espelhada: a projeção cobre
// a tela de controle e fica com o foco do teclado, e trazer o controle de volta jogaria a mesa do
// operador no telão. As teclas são as mesmas do controle, mais as que os controles remotos de
// apresentação mandam (PageUp/PageDown, B para escurecer).
const PROXIMO = ["ArrowRight", "ArrowDown", "PageDown", " ", "Enter"];
const ANTERIOR = ["ArrowLeft", "ArrowUp", "PageUp", "Backspace"];

async function postar(caminho, corpo = "{}") {
  try {
    await fetch(caminho, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: corpo,
    });
  } catch {
    // Passar do último slide responde 400 — é o fim da música, não um erro do operador.
  }
}

function navegar(direcao) {
  postar("/api/projecao/navegar", JSON.stringify({ direcao }));
}

document.addEventListener("keydown", (evento) => {
  if (PROXIMO.includes(evento.key)) {
    evento.preventDefault();
    navegar("prox");
  } else if (ANTERIOR.includes(evento.key)) {
    evento.preventDefault();
    navegar("ant");
  } else if (evento.key === "b" || evento.key === "B" || evento.key === ".") {
    evento.preventDefault();
    postar("/api/projecao/blackout");
  } else if (evento.key === "f" || evento.key === "F") {
    // Espelhado não há para onde mover a janela: ela nasce 1280x720 e precisa virar tela cheia.
    evento.preventDefault();
    if (document.fullscreenElement) document.exitFullscreen();
    else document.documentElement.requestFullscreen?.().catch(() => {});
  } else if (evento.key === "Escape" && document.fullscreenElement) {
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
