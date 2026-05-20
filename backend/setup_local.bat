@echo off
:: PDFShield — Setup Local para Windows
:: Uso: Duplo clique em setup_local.bat

title PDFShield — Setup Local

echo.
echo   ==========================================
echo     PDFShield -- Setup Local Windows
echo   ==========================================
echo.

:: 1. Python
where python >nul 2>&1
if errorlevel 1 (
    echo   [ERRO] Python nao encontrado.
    echo   Instale em: https://python.org/downloads
    echo   Marque "Add Python to PATH" durante a instalacao.
    pause
    exit /b 1
)
echo   [OK] Python encontrado

:: 2. Instalar dependencias
echo   Instalando dependencias...
pip install reportlab pypdf --quiet
if errorlevel 1 (
    echo   [ERRO] Falha ao instalar dependencias.
    pause
    exit /b 1
)
echo   [OK] reportlab + pypdf instalados

:: 3. Instalar FastAPI (opcional)
pip install fastapi uvicorn python-multipart stripe httpx resend pydantic --quiet 2>nul
echo   [OK] Dependencias opcionais instaladas (ou ja instaladas)

:: 4. Verificar arquivos
if not exist "server_local.py" (
    echo   [ERRO] server_local.py nao encontrado.
    echo   Execute este script a partir da pasta backend/
    pause
    exit /b 1
)
echo   [OK] server_local.py encontrado

:: 5. Testar motor
python -c "import sys; sys.path.insert(0,'.'); from app.pdf_engine import BuyerInfo; print('[OK] Motor de PDF funcionando')"
if errorlevel 1 (
    echo   [ERRO] Motor de PDF nao carregou.
    pause
    exit /b 1
)

:: 6. Iniciar
echo.
echo   ==========================================
echo   Servidor iniciando...
echo   Abra no browser: http://localhost:8000
echo   CTRL+C para parar
echo   ==========================================
echo.

python server_local.py
pause
