import sqlite3

from app.db.text_utils import normaliza_semac

_TABELAS = {
    "atual": "HINARIO_ADVENTISTA",
    "1996": "HINARIO_ADVENTISTA_1996",
}


def buscar_hinario(conn: sqlite3.Connection, valor: str, edicao: str = "atual") -> list[sqlite3.Row]:
    tabela = _TABELAS.get(edicao, _TABELAS["atual"])
    valor = (valor or "").strip()
    if valor.isdigit():
        sql = f"SELECT * FROM {tabela} WHERE FAIXA = ? ORDER BY FAIXA"
        params = (int(valor),)
    else:
        sql = f"SELECT * FROM {tabela} WHERE NOME_SEMAC LIKE ? ORDER BY FAIXA"
        params = (f"%{normaliza_semac(valor)}%",)
    return conn.execute(sql, params).fetchall()


def listar_hinario(conn: sqlite3.Connection, edicao: str = "atual") -> list[sqlite3.Row]:
    tabela = _TABELAS.get(edicao, _TABELAS["atual"])
    return conn.execute(f"SELECT * FROM {tabela} ORDER BY FAIXA").fetchall()
