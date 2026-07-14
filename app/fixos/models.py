import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class HinoFixo(BaseModel):
    """Um momento do culto que sempre acontece, com o hino que a igreja canta nele.

    O `nome` é livre e editável ("Doxologia", "Oração Intercessória", "Ofertas") — é ele que
    identifica o momento, não o hino, que pode até ainda não estar escolhido.
    """

    id: str = Field(default_factory=lambda: f"fixo-{uuid.uuid4().hex[:8]}")
    ordem: int = 0
    nome: str
    ref_id: Optional[int] = None
    titulo_exibicao: Optional[str] = None


class ListaFixos(BaseModel):
    itens: list[HinoFixo] = Field(default_factory=list)
    atualizado_em: datetime = Field(default_factory=datetime.now)
