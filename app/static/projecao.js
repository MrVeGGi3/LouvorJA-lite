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
  letraEl.style.fontSize = `${slide.tamanho_letra || 40}pt`;

  if (slide.letra_aux) {
    letraAuxEl.textContent = slide.letra_aux;
    letraAuxEl.style.color = slide.cor_letra_aux || slide.cor_letra || "#ffffff";
    letraAuxEl.style.display = "block";
  } else {
    letraAuxEl.style.display = "none";
  }
}

async function atualizar() {
  try {
    const resp = await fetch("/api/projecao/estado");
    if (!resp.ok) return;
    const estado = await resp.json();
    if (estado.atualizado_em === ultimaAtualizacao) return;
    ultimaAtualizacao = estado.atualizado_em;
    aplicarSlide(estado);
  } catch {
    // Mantém o último slide renderizado em caso de falha momentânea do servidor.
  }
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

atualizar();
setInterval(atualizar, 500);
