# RutaSur · Ecosistema Logístico y de Inteligencia de Ventas

> **Recreación.** Este proyecto es una versión nueva y simplificada de una herramienta que construí durante mi pasantía en Servimax. No contiene código ni datos de la empresa: todos los registros de ejemplo son ficticios.

Aplicación web para planificar rutas de asesores comerciales y ver el impacto de las devoluciones por sector geográfico. Reemplaza el trazado manual de rutas con un mapa interactivo que se arma solo a partir de los clientes registrados.

## Qué hace

- Mapa interactivo (Folium/Leaflet) con una escala de color por intensidad de ventas o de devoluciones.
- Ruta sugerida por asesor (vecino más cercano) con los kilómetros estimados.
- Control de rutas en el mapa: cada asesor tiene una casilla que muestra u oculta su ruta junto con los puntos de sus clientes.
- Descarga del mapa como archivo HTML independiente, con los filtros y la capa de intensidad activos.
- Filtros por sector y por asesor, tanto en la interfaz como en la API.
- Resumen de logística inversa: devoluciones por sector y su tasa sobre las ventas.
- Alta y baja de clientes, y registro de devoluciones.
- Exportación a CSV respetando los filtros activos.

## Stack

Python · Flask · Flask-SQLAlchemy · Folium · Bootstrap 5 · Boxicons

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate      # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # opcional, ver "Variables de entorno"
python app.py
```

Abre http://127.0.0.1:5000. En el primer arranque se crea la base de datos y se cargan clientes de ejemplo en Soacha.

## Base de datos

Por defecto los registros se guardan en un archivo SQLite: `instance/logistica.db`.

Para usar otra base de datos, define `DATABASE_URL` en tu archivo `.env` (ver [Variables de entorno](#variables-de-entorno)) o en la terminal antes de arrancar. Necesitas instalar el driver correspondiente:

```bash
export DATABASE_URL="mysql+pymysql://usuario:clave@localhost/logistica"
```

Si la variable no existe, o la conexión falla, la app usa SQLite automáticamente y lo avisa en consola.

## Variables de entorno

La configuración vive en variables de entorno, no en el código. El archivo `.env.example` trae todas las variables con valores de ejemplo. Para usarlas:

```bash
cp .env.example .env           # en Windows: copy .env.example .env
```

Edita `.env` con tus valores y arranca la app con normalidad: el archivo se lee solo al iniciar (con `python-dotenv`). Algunas cosas a tener en cuenta:

- `.env` está en `.gitignore`. Al repositorio sube solo `.env.example`, sin credenciales reales.
- Si una variable también está definida en la terminal, esa tiene prioridad sobre el archivo.
- Si no existe `.env`, la app arranca con los valores por defecto de la tabla.

| Variable | Valor por defecto | Descripción |
|----------|-------------------|-------------|
| `DATABASE_URL` | vacía (SQLite en `instance/logistica.db`) | URL de SQLAlchemy de la base de datos. Si falta o la conexión falla, se usa SQLite |
| `HOST` | `127.0.0.1` | Dirección en la que escucha el servidor. Con `0.0.0.0` queda abierto a la red |
| `PORT` | `5000` | Puerto del servidor. Cámbialo si corres varias apps a la vez |
| `FLASK_DEBUG` | `0` | Con `1` se activa la depuración y la recarga automática. No lo uses en producción |
| `CARGAR_EJEMPLOS` | `1` | Con `1` se cargan datos ficticios si la base está vacía. Con `0` queda vacía, que es lo recomendable en una base real |

## API

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/clientes` | Lista de clientes. Acepta `?sector=` y `?asesor=` |
| POST | `/api/clientes` | Crea un cliente (`nombre`, `sector`, `lat`, `lng`, `ventas`, `asesor_id`) |
| DELETE | `/api/clientes/<id>` | Elimina un cliente y sus devoluciones |
| POST | `/api/devoluciones` | Registra una devolución (`cliente_id`, `valor`, `motivo`) |
| GET | `/api/devoluciones/resumen` | Devoluciones y tasa por sector |
| GET | `/api/rutas` | Orden de visita y km por asesor. Acepta los mismos filtros |
| GET | `/api/exportar.csv` | Descarga de clientes en CSV. Acepta los mismos filtros |
| GET | `/mapa` | Mapa en HTML. Acepta `?capa=ventas\|devoluciones` y los filtros. Con `&descargar=1` se entrega como archivo adjunto (`mapa_clientes.html`) |

Ejemplo:

```bash
curl -X POST http://127.0.0.1:5000/api/clientes \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Tienda El Parque", "sector": "Compartir", "lat": 4.58, "lng": -74.21, "ventas": 2500000}'
```

## Control de rutas y descarga del mapa

**Control por asesor.** En la esquina inferior izquierda del mapa aparece un panel con una casilla por asesor. Cada entrada muestra el color de la ruta, el nombre y los kilómetros, por ejemplo "Carlos Rojas · 13.4 km". Al desmarcar una casilla se ocultan la ruta y los puntos de los clientes de ese asesor; al volver a marcarla reaparecen. Algunos detalles:

- Los asesores salen en orden alfabético y los clientes sin asesor, en gris como "Sin asignar", al final.
- Un asesor con un solo cliente también tiene casilla (con 0.0 km), para poder ocultar su punto.
- La leyenda de colores se calcula con todos los clientes del filtro, así que no cambia al ocultar un asesor.
- Al aplicar un filtro el mapa se recarga y todas las casillas vuelven a quedar marcadas.

**Descarga en HTML.** El botón "Descargar HTML" del encabezado del mapa baja el mismo mapa que se ve en pantalla, con los filtros de sector y asesor y la capa de intensidad activos. También se puede pedir directamente:

```
http://127.0.0.1:5000/mapa?sector=Compartir&capa=devoluciones&descargar=1
```

El archivo funciona por sí solo, sin el servidor Flask, y conserva el control por asesor. Siempre se abre con todas las rutas visibles, porque la selección de casillas no se guarda. Necesita conexión a internet, ya que Leaflet y los mosaicos del fondo se cargan desde la red.

**Mosaicos del fondo.** Dentro de la aplicación el mapa usa OpenStreetMap. El archivo descargado usa los mosaicos de calles de Esri, porque OpenStreetMap bloquea (error 403, "Access blocked") las páginas abiertas con doble clic desde el disco: el navegador no envía la cabecera `Referer` que su política de uso exige. Para usar otro proveedor en la descarga, cambia el diccionario `MOSAICOS_DESCARGA` de `geo.py` (`tiles` con la URL y `attr` con la atribución). Esri pide mostrar su atribución, que el mapa ya incluye; en un uso comercial o de mucho tráfico conviene revisar sus condiciones.

## Identidad visual

RutaSur toma su identidad del ícono: azul `#0d6efd` como color de marca, azul marino `#0a2a5e` para la barra y los encabezados, y ámbar `#ffd43b` como acento. El motivo propio es la ruta punteada del ícono, que aparece como línea bajo la barra y como divisor en tarjetas y ventanas. Los títulos usan Sora (Google Fonts) y, si no carga, la fuente del sistema. El mapa usa una escala azul para ventas y una amarillo-rojo para devoluciones.

Los colores y la fuente se cambian desde las variables al inicio de `static/tema.css` (`--azul`, `--azul-rgb`, `--marino`, `--ambar`, `--fuente`). `--azul-rgb` lleva el mismo color en formato R, G, B. Si cambias la fuente, actualiza también el enlace de Google Fonts en `templates/base.html`.

## Estructura

```
app.py          fábrica de la aplicación
.env.example    variables de entorno de ejemplo
models.py       modelos, selección de base de datos y datos de ejemplo
routes.py       blueprint con las vistas y la API
geo.py          capas del mapa, cálculo de rutas, control por asesor y construcción del mapa
static/         tema.css (identidad visual) e ícono
templates/      interfaz con Bootstrap
```

## Cómo agregar una capa al mapa

Las capas (lo que define el color de cada cliente) se declaran en el diccionario `CAPAS` de `geo.py`. Cada entrada tiene el texto que se ve en la interfaz y una función que recibe el cliente y lo devuelto por él, y entrega el número que se pinta. Opcionalmente, `escala` define la paleta: puede ser una de `branca.colormap.linear` (por ejemplo `linear.YlOrRd_09`) o una propia, como `LinearColormap(["#bcd4ff", "#0d6efd", "#0a2a5e"])`, que es la que usa la capa de ventas. Si no se indica, se usa amarillo-rojo. El selector "Intensidad del mapa", la leyenda y la validación de `/mapa?capa=` se actualizan solos.

Ejemplo: pintar la tasa de devolución (devuelto sobre ventas).

```python
"tasa": {
    "nombre": "Tasa de devolución (%)",
    "valor": lambda cliente, devuelto: devuelto.get(cliente.id, 0) / cliente.ventas * 100 if cliente.ventas else 0,
},
```

Pégala dentro de `CAPAS`, reinicia la app y aparecerá en el selector.

## Cómo cambiar el algoritmo de rutas

`ordenar_ruta(clientes)` en `geo.py` recibe una lista de clientes y devuelve la lista ordenada y los kilómetros totales. Mientras mantenga esa firma, puedes reemplazarla por otro método (OR-Tools, OSRM, rutas por calles) y el mapa, la API y los totales seguirán funcionando.

## Cómo agregar un filtro

1. Agrega el parámetro en `clientes_filtrados()` (`routes.py`), por ejemplo `consulta.filter_by(canal=request.args["canal"])`.
2. Agrega el `<select>` con ese `name` en el formulario de `templates/index.html`.

El mapa, las rutas, la tabla, la exportación a CSV y la API usan esa misma función, así que el filtro se aplica en todos lados.

## Cómo agregar un dato al cliente

1. Agrega la columna al modelo `Cliente` en `models.py`.
2. Inclúyela en `to_dict()` y en la exportación (`exportar()` en `routes.py`) si debe salir en la API y en el CSV.

`db.create_all()` solo crea las tablas que no existen; no modifica las que ya están. En desarrollo borra `instance/logistica.db` y vuelve a arrancar. En producción usa una migración (Flask-Migrate) o un `ALTER TABLE`.

## Cómo escalarlo

- Cambiar `DATABASE_URL` a MySQL o PostgreSQL no requiere tocar el código.
- Si crece, se puede separar `routes.py` en un blueprint por módulo (clientes, devoluciones, rutas).

## Limitaciones

- La ruta usa distancia en línea recta, no calles reales.
- El HTML descargado necesita conexión a internet para cargar Leaflet y el fondo del mapa.
- No incluye autenticación; para uso real hay que ponerla delante.
