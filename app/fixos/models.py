import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.liturgia.models import OrigemHino, validar_url_video


class HinoFixo(BaseModel):
    """Um momento do culto que sempre acontece, com o hino que a igreja canta nele.

    O `nome` é livre e editável ("Doxologia", "Oração Intercessória", "Ofertas") — é ele que
    identifica o momento, não o hino, que pode até ainda não estar escolhido.

    A `origem` acompanha o hino porque o momento fixo pode ser copiado para a liturgia da
    semana, e o `ItemLiturgia` de lá carrega essa dica de onde o hino foi escolhido. Fica
    `None` nos momentos sem hino — e nos que foram gravados antes deste campo existir.

    O momento pode, em vez do hino, apontar para um vídeo (`url_video`) — o louvor que vem do
    YouTube e não existe no banco. Um ou outro, nunca os dois: são dois jeitos de preencher o
    mesmo espaço, e ter os dois deixaria ambíguo o que o momento toca.
    """

    id: str = Field(default_factory=lambda: f"fixo-{uuid.uuid4().hex[:8]}")
    ordem: int = 0
    nome: str
    origem: Optional[OrigemHino] = None
    ref_id: Optional[int] = None
    titulo_exibicao: Optional[str] = None
    url_video: Optional[str] = None

    @field_validator("url_video")
    @classmethod
    def _url_plausivel(cls, url: Optional[str]) -> Optional[str]:
        return validar_url_video(url)

    @model_validator(mode="after")
    def _hino_ou_video(self) -> "HinoFixo":
        if self.ref_id is not None and self.url_video is not None:
            raise ValueError("O momento tem hino ou vídeo, não os dois")
        return self


class ListaFixos(BaseModel):
    itens: list[HinoFixo] = Field(default_factory=list)
    atualizado_em: datetime = Field(default_factory=datetime.now)
