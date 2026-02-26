@echo off
echo === Koto Ollama Model Setup ===
echo.
echo Installing required models for Koto...
echo 1. DeepSeek-R1:14b (Main Brain)
echo 2. Nomic-Embed-Text (Memory/Embeddings)
echo 3. Llava (Vision)
echo.

echo Pulling deepseek-r1:14b...
ollama pull deepseek-r1:14b

echo.
echo Pulling nomic-embed-text...
ollama pull nomic-embed-text

echo.
echo Pulling llava...
ollama pull llava

echo.
echo === Setup Complete! ===
echo.
pause
