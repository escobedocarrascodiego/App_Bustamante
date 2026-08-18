@echo off
REM ============================================================
REM  Kiosko de Turnos - Municipalidad Distrital JLBR
REM  PRODUCCION: el servidor esta en 10.0.0.4:8052
REM  Copiar este archivo al ESCRITORIO del equipo kiosko (y a
REM  shell:startup para que arranque solo al encender).
REM
REM  Doble clic -> abre el kiosko a pantalla completa con
REM  impresion automatica del ticket (sin dialogo).
REM  Para SALIR del modo kiosko: Alt + F4
REM ============================================================

start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" ^
  --user-data-dir="C:\kiosko-chrome" ^
  --kiosk ^
  --kiosk-printing ^
  --no-first-run ^
  --disable-pinch ^
  http://10.0.0.4:8052/colas/kiosko/
