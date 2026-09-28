from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api import albuns, atualizacao, fixos, hinario, liturgia, media, musicas, projecao
from app.config import DATA_DIR, resource_path

# Congelado, o static/ vive dentro do bundle (sys._MEIPASS), não ao lado do .py.
STATIC_DIR = resource_path("app", "static")

class StaticSemCacheVelho(StaticFiles):
    """Static que obriga o navegador a revalidar antes de reaproveitar o que guardou.

    Sem Cache-Control, o navegador usa frescor heurístico e reaproveita por dias o HTML/JS/CSS de
    uma versão anterior sem perguntar — trocar o AppImage deixava a tela nova com o controle.js
    velho. Com `no-cache` ele pergunta sempre, e o ETag faz a resposta ser um 304 sem corpo.
    """

    async def get_response(self, path, scope):
        resposta = await super().get_response(path, scope)
        resposta.headers["Cache-Control"] = "no-cache"
        return resposta


app = FastAPI(title="LouvorJA Lite")

app.include_router(hinario.router)
app.include_router(musicas.router)
app.include_router(albuns.router)
app.include_router(liturgia.router)
app.include_router(fixos.router)
app.include_router(projecao.router)
app.include_router(media.router)
app.include_router(atualizacao.router)

DATA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/data", StaticFiles(directory=DATA_DIR, check_dir=False), name="data")
app.mount("/static", StaticSemCacheVelho(directory=STATIC_DIR), name="static")


@app.get("/api/ping")
def ping():
    # Assinatura para o launcher reconhecer uma instância já aberta na porta, em vez de subir outra.
    return {"app": "louvorja-lite"}


# As páginas são servidas no próprio /controle e /projecao, e não por redirect para /static/*.html:
# quem já rodou uma versão antiga tem esses .html no cache sem data de validade, e o redirect
# cairia neles. Endereço novo, sem nada guardado — e o HTML traz os ?v= que escapam do JS/CSS velho.
def _pagina(nome: str) -> FileResponse:
    return FileResponse(STATIC_DIR / nome, headers={"Cache-Control": "no-cache"})


@app.get("/")
def root():
    return RedirectResponse(url="/controle")


@app.get("/controle")
def controle_page():
    return _pagina("controle.html")


@app.get("/projecao")
def projecao_page():
    return _pagina("projecao.html")
