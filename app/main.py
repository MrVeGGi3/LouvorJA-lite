from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api import albuns, hinario, liturgia, media, musicas, projecao
from app.config import DATA_DIR, resource_path

# Congelado, o static/ vive dentro do bundle (sys._MEIPASS), não ao lado do .py.
STATIC_DIR = resource_path("app", "static")

app = FastAPI(title="LouvorJA Lite")

app.include_router(hinario.router)
app.include_router(musicas.router)
app.include_router(albuns.router)
app.include_router(liturgia.router)
app.include_router(projecao.router)
app.include_router(media.router)

DATA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/data", StaticFiles(directory=DATA_DIR, check_dir=False), name="data")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def root():
    return RedirectResponse(url="/static/controle.html")


@app.get("/controle")
def controle_page():
    return RedirectResponse(url="/static/controle.html")


@app.get("/projecao")
def projecao_page():
    return RedirectResponse(url="/static/projecao.html")
