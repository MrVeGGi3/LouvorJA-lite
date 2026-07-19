import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# `ref_id` é sempre um `id_music`; a origem sobrou apenas como dica de exibição (de onde o
# item foi escolhido), não como espaço de identificadores separado.
OrigemHino = Literal["hinario", "hinario_1996", "musicas"]

# A liturgia é organizada por dia da semana (reaproveitado em todas as semanas), não por data.
# Os slugs, sem acento, servem de chave de arquivo e de valor na URL; a ordem segue Date.getDay()
# (0=domingo … 6=sábado).
DiaSemana = Literal["domingo", "segunda", "terca", "quarta", "quinta", "sexta", "sabado"]
DIAS: tuple[str, ...] = ("domingo", "segunda", "terca", "quarta", "quinta", "sexta", "sabado")
ROTULOS_DIAS: dict[str, str] = {
    "domingo": "Domingo",
    "segunda": "Segunda",
    "terca": "Terça",
    "quarta": "Quarta",
    "quinta": "Quinta",
    "sexta": "Sexta",
    "sabado": "Sábado",
}


def rotulo_dia(dia: str) -> str:
    return ROTULOS_DIAS.get(dia, dia)


def validar_url_video(url: Optional[str]) -> Optional[str]:
    """Regra de link de vídeo, compartilhada pela liturgia da semana e pelos momentos fixos."""
    if url is None:
        return None
    url = url.strip()
    if not url:
        return None
    # O link só é aberto numa aba do navegador, então basta ser navegável. Não exigimos
    # que seja do YouTube: um vídeo no Drive ou no Vimeo abre do mesmo jeito.
    if not url.startswith(("http://", "https://")):
        raise ValueError("O link precisa começar com http:// ou https://")
    return url


class ItemLiturgia(BaseModel):
    """Uma linha da liturgia do dia: um hino do banco, um vídeo de fora dele ou uma nota.

    A `descricao` diz o que aquele momento é ("Doxologia", "Ofertas") — chega preenchida com o
    nome do momento quando o item vem da aba de fixos e fica em branco quando vem da busca, que
    não tem como saber em que ponto do culto o hino entra. É livre e editável na linha.

    O `tipo="nota"` é o momento que ainda não toca nada: só a descrição, para o sonoplasta saber
    o que acontece ali (oração, avisos, pregação). Pode receber um hino ou um vídeo depois, e
    voltar a ser nota se o hino for tirado — daí `titulo_exibicao` ter default vazio.

    O vídeo (`url_video`) mora no lugar do hino, nunca junto: são dois jeitos de preencher o
    mesmo espaço. Ele só abre numa aba — a projeção continua sendo só dos hinos do banco, que
    são os únicos com slides.
    """

    id: str = Field(default_factory=lambda: f"item-{uuid.uuid4().hex[:8]}")
    ordem: int
    tipo: Literal["hino", "nota", "video"]
    origem: Optional[OrigemHino] = None
    ref_id: Optional[int] = None
    titulo_exibicao: str = ""
    descricao: str = ""
    url_video: Optional[str] = None
    observacao: str = ""
    texto: Optional[str] = None

    @field_validator("url_video")
    @classmethod
    def _url_plausivel(cls, url: Optional[str]) -> Optional[str]:
        return validar_url_video(url)

    @model_validator(mode="after")
    def _hino_ou_video(self) -> "ItemLiturgia":
        if self.ref_id is not None and self.url_video is not None:
            raise ValueError("O item tem hino ou vídeo, não os dois")
        return self


class Liturgia(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    dia: DiaSemana
    titulo: str
    criado_em: datetime = Field(default_factory=datetime.now)
    atualizado_em: datetime = Field(default_factory=datetime.now)
    itens: list[ItemLiturgia] = Field(default_factory=list)
