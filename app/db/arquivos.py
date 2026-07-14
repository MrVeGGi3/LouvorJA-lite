"""Mapeia uma linha da tabela `files` para o caminho do arquivo em disco.

O layout local espelha o do LouvorJA Desktop — `musicas/<Álbum>/<Nome>.mp3`, `capas/<Nome>`,
`imagens/<Nome>` — e é o mesmo caminho usado pelo servidor de download sob o prefixo `config/`.
Espelhar permite semear `data/` copiando de uma instalação existente em vez de baixar ~15 GB.
"""

from pathlib import Path, PurePosixPath

SUBPASTA_POR_TIPO = {
    "music": "musicas",
    "image_album": "capas",
    "image_music": "imagens",
}

TIPOS_AUDIO = ("music",)


def caminho_relativo(tipo: str, dir_: str, file_name: str) -> PurePosixPath:
    """Caminho do arquivo relativo a `data/` (local) e a `config/` (remoto).

    O `dir` das músicas inclui o idioma (`/musics/pt/Hinário Adventista`), que não existe no
    layout em disco — só o nome do álbum é aproveitado.
    """
    subpasta = SUBPASTA_POR_TIPO.get(tipo)
    if subpasta is None:
        raise ValueError(f"tipo de arquivo sem layout conhecido: {tipo!r}")
    if tipo == "music":
        album = PurePosixPath(dir_).name
        return PurePosixPath(subpasta) / album / file_name
    return PurePosixPath(subpasta) / file_name


def caminho_local(data_dir: Path, tipo: str, dir_: str, file_name: str) -> Path:
    return data_dir / caminho_relativo(tipo, dir_, file_name)


def arquivo_completo(caminho: Path, tamanho_esperado: int) -> bool:
    """Decide se o arquivo em disco está inteiro. `files.size` é um piso, não um valor exato.

    Um download interrompido sempre fica MENOR que o esperado, então o piso continua pegando
    truncamento. Já o contrário acontece de verdade: o servidor às vezes substitui um arquivo por
    uma versão melhor (um mp3 reencodado em 256 kbps, por exemplo) sem atualizar o `size` do
    catálogo. Exigir igualdade exata descartaria o arquivo bom por causa de um metadado velho.
    """
    if not caminho.exists():
        return False
    return caminho.stat().st_size >= tamanho_esperado > 0


def caminho_remoto(tipo: str, dir_: str, file_name: str) -> str:
    return f"config/{caminho_relativo(tipo, dir_, file_name)}"
