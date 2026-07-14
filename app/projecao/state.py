from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, computed_field

from app.config import PROJECAO_STATE_PATH


class SlideAtual(BaseModel):
    tipo: str = "letra"
    ordem: int = 0
    letra: str = ""
    letra_aux: Optional[str] = None
    imagem_fundo: Optional[str] = None
    cor_fundo: str = "#000000"
    cor_letra: str = "#ffffff"
    cor_letra_aux: Optional[str] = None
    # Em % da altura da tela, como no LouvorJA — o título é maior que a letra.
    tamanho_letra: int = 14
    tamanho_letra_aux: int = 10


class EstadoProjecao(BaseModel):
    liturgia_id: Optional[str] = None
    week_of: Optional[str] = None
    item_index: Optional[int] = None
    titulo_item: Optional[str] = None
    slides: list[SlideAtual] = Field(default_factory=list)
    slide_index: int = 0
    atualizado_em: datetime = Field(default_factory=datetime.now)

    @computed_field
    @property
    def slide(self) -> SlideAtual:
        if 0 <= self.slide_index < len(self.slides):
            return self.slides[self.slide_index]
        return SlideAtual()

    @computed_field
    @property
    def total_slides(self) -> int:
        return len(self.slides)


def _write_atomic(path: Path, conteudo: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(conteudo, encoding="utf-8")
    tmp.replace(path)


def salvar_estado(estado: EstadoProjecao) -> None:
    estado.atualizado_em = datetime.now()
    _write_atomic(PROJECAO_STATE_PATH, estado.model_dump_json(indent=2))


def carregar_estado() -> EstadoProjecao:
    if not PROJECAO_STATE_PATH.exists():
        return EstadoProjecao()
    return EstadoProjecao.model_validate_json(PROJECAO_STATE_PATH.read_text(encoding="utf-8"))
