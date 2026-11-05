import csv
import io

from flask import Blueprint, Response, jsonify, render_template, request
from sqlalchemy import func

from geo import CAPAS, construir_mapa, rutas_por_asesor
from models import Asesor, Cliente, Devolucion, db

bp = Blueprint("main", __name__)


def clientes_filtrados():
    consulta = Cliente.query
    asesor = request.args.get("asesor", type=int)
    if request.args.get("sector"):
        consulta = consulta.filter_by(sector=request.args["sector"])
    if asesor:
        consulta = consulta.filter_by(asesor_id=asesor)
    return consulta.order_by(Cliente.id).all()


def devuelto_por_cliente():
    filas = db.session.query(Devolucion.cliente_id, func.sum(Devolucion.valor)).group_by(Devolucion.cliente_id).all()
    return dict(filas)


def resumen_devoluciones():
    ventas = dict(db.session.query(Cliente.sector, func.sum(Cliente.ventas)).group_by(Cliente.sector).all())
    filas = (
        db.session.query(Cliente.sector, func.count(Devolucion.id), func.sum(Devolucion.valor))
        .join(Devolucion, Devolucion.cliente_id == Cliente.id)
        .group_by(Cliente.sector)
        .order_by(func.sum(Devolucion.valor).desc())
        .all()
    )
    return [
        {"sector": s, "devoluciones": n, "valor": v, "tasa": round(v / ventas[s] * 100, 1) if ventas[s] else 0}
        for s, n, v in filas
    ]


def leer_payload():
    return request.get_json(silent=True) or request.form.to_dict()


def texto_seguro(valor):
    texto = str(valor or "")
    return "'" + texto if texto[:1] in "=+-@" else texto


@bp.get("/")
def index():
    clientes = clientes_filtrados()
    devuelto = devuelto_por_cliente()
    rutas = rutas_por_asesor(clientes)
    sectores = [s for (s,) in db.session.query(Cliente.sector).distinct().order_by(Cliente.sector)]
    return render_template(
        "index.html",
        clientes=clientes,
        devuelto=devuelto,
        rutas=rutas,
        sectores=sectores,
        asesores=Asesor.query.all(),
        capas=CAPAS,
        filtros=request.args,
        ventas=sum(c.ventas for c in clientes),
        total_devuelto=sum(devuelto.get(c.id, 0) for c in clientes),
        km=round(sum(r["km"] for r in rutas), 1),
        resumen=resumen_devoluciones(),
        query=request.query_string.decode(),
    )


@bp.get("/mapa")
def mapa():
    capa = request.args.get("capa", "ventas")
    if capa not in CAPAS:
        return "Capa no válida", 400
    descargar = bool(request.args.get("descargar"))
    html = construir_mapa(clientes_filtrados(), devuelto_por_cliente(), capa, descarga=descargar)
    if descargar:
        return Response(
            html,
            mimetype="text/html",
            headers={"Content-Disposition": "attachment; filename=mapa_clientes.html"},
        )
    return html


@bp.get("/api/clientes")
def listar_clientes():
    devuelto = devuelto_por_cliente()
    return jsonify([c.to_dict(devuelto.get(c.id, 0)) for c in clientes_filtrados()])


@bp.post("/api/clientes")
def crear_cliente():
    datos = leer_payload()
    try:
        cliente = Cliente(
            nombre=str(datos["nombre"]).strip(),
            sector=str(datos["sector"]).strip(),
            lat=float(datos["lat"]),
            lng=float(datos["lng"]),
            ventas=float(datos.get("ventas") or 0),
            asesor_id=int(datos["asesor_id"]) if datos.get("asesor_id") else None,
        )
    except (KeyError, ValueError):
        return jsonify(error="Datos incompletos o inválidos"), 400
    if not cliente.nombre or not cliente.sector:
        return jsonify(error="Nombre y sector son obligatorios"), 400
    if not (-90 <= cliente.lat <= 90 and -180 <= cliente.lng <= 180):
        return jsonify(error="Coordenadas fuera de rango"), 400
    if cliente.asesor_id and not db.session.get(Asesor, cliente.asesor_id):
        return jsonify(error="El asesor no existe"), 400
    db.session.add(cliente)
    db.session.commit()
    return jsonify(cliente.to_dict()), 201


@bp.delete("/api/clientes/<int:id>")
def eliminar_cliente(id):
    db.session.delete(db.get_or_404(Cliente, id))
    db.session.commit()
    return "", 204


@bp.post("/api/devoluciones")
def crear_devolucion():
    datos = leer_payload()
    try:
        devolucion = Devolucion(
            cliente_id=int(datos["cliente_id"]),
            valor=float(datos["valor"]),
            motivo=str(datos.get("motivo") or "").strip()[:120],
        )
    except (KeyError, ValueError):
        return jsonify(error="Datos incompletos o inválidos"), 400
    if devolucion.valor <= 0 or not db.session.get(Cliente, devolucion.cliente_id):
        return jsonify(error="Cliente inexistente o valor no válido"), 400
    db.session.add(devolucion)
    db.session.commit()
    return jsonify(id=devolucion.id), 201


@bp.get("/api/devoluciones/resumen")
def api_resumen():
    return jsonify(resumen_devoluciones())


@bp.get("/api/rutas")
def api_rutas():
    return jsonify(rutas_por_asesor(clientes_filtrados()))


@bp.get("/api/exportar.csv")
def exportar():
    devuelto = devuelto_por_cliente()
    salida = io.StringIO()
    escritor = csv.writer(salida)
    escritor.writerow(["id", "nombre", "sector", "asesor", "lat", "lng", "ventas", "devuelto"])
    for c in clientes_filtrados():
        escritor.writerow([
            c.id,
            texto_seguro(c.nombre),
            texto_seguro(c.sector),
            texto_seguro(c.asesor.nombre if c.asesor else ""),
            c.lat,
            c.lng,
            c.ventas,
            devuelto.get(c.id, 0),
        ])
    return Response(
        salida.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=clientes.csv"},
    )
