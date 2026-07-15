import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

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


class ItemLiturgia(BaseModel):
    id: str = Field(default_factory=lambda: f"item-{uuid.uuid4().hex[:8]}")
    ordem: int
    tipo: Literal["hino", "nota"]
    origem: Optional[OrigemHino] = None
    ref_id: Optional[int] = None
    titulo_exibicao: str
    observacao: str = ""
    texto: Optional[str] = None


class Liturgia(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    dia: DiaSemana
    titulo: str
    criado_em: datetime = Field(default_factory=datetime.now)
    atualizado_em: datetime = Field(default_factory=datetime.now)
    itens: list[ItemLiturgia] = Field(default_factory=list)
