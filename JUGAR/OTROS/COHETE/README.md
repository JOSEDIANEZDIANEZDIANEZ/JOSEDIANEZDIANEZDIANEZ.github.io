# Cohetes: construye, prueba y reza

Requisitos: Python 3 y pygame (`pip install pygame`; con Python 3.14 usa `pip install pygame-ce`).
Ejecutar: `python main.py`

## Fase 1 · Construcción
↑↓ elegir, ←→ cambiar (o clic), Enter en "Nombre" para escribir. Motores, combustible, tanques,
etapas, tamaño, colores, aletas, pararrayos, tripulado y torre de escape.

## Fase 2 · Ascenso (≈3 min)
Los motores empiezan APAGADOS: enciéndelos tú (E o botón). Al separar una etapa, enciende la siguiente.
W/S acelerador · A/D cabeceo · ESPACIO separar · G piloto automático · C refrigerar · V ventear
R reiniciar sistemas · T acelerar tiempo · M sonido · X / botón ABORTAR.
- Un fallo accidental que explota el cohete puede arrasar las ciudades de debajo; abortar tú no.
- Un rayo sobre un cohete SIN pararrayos lo destruye casi siempre.
- Objetivo: perigeo ≥ 120 km y apogeo ≥ 500 km, y APAGAR los motores (E).

## Fase 3 · Acoplamiento
A/D girar, W empujar, S frenar. Alinea la nariz con el satélite, mantén la línea naranja sobre la
verde y llega a < 0,8 m/s, dentro del cono del puerto. Si vas rápido o desalineado, chocas.

## Fase 4 · Reentrada y paracaídas
W/S cambian el ángulo de ataque: mantenlo en la banda verde (cambia con la altitud y oscila), o
te quemas. ESPACIO abre el paracaídas: entre 7 y 2 km. Muy pronto se rasga; muy tarde te estrellas.

## Pantalla completa
F11 (o Alt+Enter) activa y desactiva la pantalla completa. La ventana también se puede redimensionar.

## Novedades
- **Aviso de separación:** cuando queda poco combustible aparece un aviso amarillo; al vaciarse la etapa sale un panel rojo "¡SEPARA LA ETAPA! (ESPACIO)" con una cuenta atrás de 15 s. Si no separas a tiempo, el cohete explota.
- **Distancia al satélite:** en la fase de acoplamiento se muestra en grande los km (o m) que faltan y el tiempo estimado de llegada.

## Crear un .exe (solo en Windows)
1. Haz doble clic en `crear_exe.bat` (instala PyInstaller y pygame-ce y compila).
2. El juego queda en `dist\Cohetes.exe`; puedes copiarlo donde quieras.
Si el antivirus lo marca, es un falso positivo típico de PyInstaller.
- **Satélite más cercano:** empiezas a ~300 m (antes ~1,3 km), ya yendo hacia él a ~3 m/s. Para acoplar: a menos de 6 m, velocidad < 1,2 m/s, rumbo < 20° y dentro del cono (30°).
