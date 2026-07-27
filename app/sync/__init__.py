"""Busca do catálogo e da mídia no servidor oficial do LouvorJA.

Este pacote vive dentro de `app/` de propósito: assim ele entra no bundle do PyInstaller pelo
grafo de imports, e o AppImage distribuído consegue baixar os próprios dados. Antes tudo isso
morava em `scripts/`, que fica de fora do bundle — o app pedia ao usuário para rodar um script
que não existia na máquina dele.
"""
