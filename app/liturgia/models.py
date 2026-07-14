import uuid
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

# `ref_id` é sempre um `id_music`; a origem sobrou apenas como dica de exibição (de onde o
# item foi escolhido), não como espaço de identificadores separado.
OrigemHino = Literal["hinario", "hinario_1996", "musicas"]


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
    week_of: date
    titulo: str
    criado_em: datetime = Field(default_factory=datetime.now)
    atualizado_em: datetime = Field(default_factory=datetime.now)
    itens: list[ItemLiturgia] = Field(default_factory=list)
