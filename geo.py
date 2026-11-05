from math import asin, cos, radians, sin, sqrt

import folium
from branca.colormap import LinearColormap, linear
from markupsafe import escape

CENTRO_SOACHA = [4.579, -74.216]

MOSAICOS_DESCARGA = {
    "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
    "attr": "Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ",
}

CAPAS = {
    "ventas": {
        "nombre": "Ventas (COP)",
        "valor": lambda cliente, devuelto: cliente.ventas,
        "escala": LinearColormap(["#bcd4ff", "#0d6efd", "#0a2a5e"]),
    },
    "devoluciones": {
        "nombre": "Devoluciones (COP)",
        "valor": lambda cliente, devuelto: devuelto.get(cliente.id, 0),
        "escala": linear.YlOrRd_09,
    },
}


def distancia(a, b):
    dlat = radians(b.lat - a.lat)
    dlng = radians(b.lng - a.lng)
    h = sin(dlat / 2) ** 2 + cos(radians(a.lat)) * cos(radians(b.lat)) * sin(dlng / 2) ** 2
    return 12742 * asin(sqrt(h))


def ordenar_ruta(clientes):
    if not clientes:
        return [], 0
    pendientes = list(clientes)
    actual = pendientes.pop(0)
    ruta = [actual]
    while pendientes:
        actual = min(pendientes, key=lambda c: distancia(actual, c))
        pendientes.remove(actual)
        ruta.append(actual)
    km = sum(distancia(a, b) for a, b in zip(ruta, ruta[1:]))
    return ruta, km


def agrupar_por_asesor(clientes):
    grupos = {}
    for c in clientes:
        grupos.setdefault(c.asesor, []).append(c)
    return grupos


def rutas_por_asesor(clientes):
    rutas = []
    for asesor, grupo in agrupar_por_asesor(clientes).items():
        ruta, km = ordenar_ruta(grupo)
        rutas.append({
            "asesor": asesor.nombre if asesor else "Sin asignar",
            "color": asesor.color if asesor else "#6c757d",
            "km": round(km, 1),
            "paradas": [c.nombre for c in ruta],
        })
    return rutas


def construir_mapa(clientes, devuelto, capa, descarga=False):
    if clientes:
        centro = [sum(c.lat for c in clientes) / len(clientes), sum(c.lng for c in clientes) / len(clientes)]
    else:
        centro = CENTRO_SOACHA
    mapa = folium.Map(location=centro, zoom_start=13, tiles=None)
    if descarga:
        folium.TileLayer(**MOSAICOS_DESCARGA, control=False).add_to(mapa)
    else:
        folium.TileLayer("OpenStreetMap", control=False).add_to(mapa)

    valores = {c.id: CAPAS[capa]["valor"](c, devuelto) for c in clientes}
    escala = None
    if valores:
        menor, mayor = min(valores.values()), max(valores.values())
        if menor == mayor:
            mayor = menor + 1
        escala = CAPAS[capa].get("escala", linear.YlOrRd_09).scale(menor, mayor)
        escala.caption = CAPAS[capa]["nombre"]
        escala.max_labels = 4
        escala.width = 300
        escala.add_to(mapa)

    grupos = sorted(agrupar_por_asesor(clientes).items(), key=lambda par: par[0].nombre if par[0] else "~")
    for asesor, grupo in grupos:
        ruta, km = ordenar_ruta(grupo)
        color = asesor.color if asesor else "#6c757d"
        nombre = escape(asesor.nombre if asesor else "Sin asignar")
        capa_asesor = folium.FeatureGroup(name=f"<span style='color:{color}'>&#9679;</span> {nombre} · {km:.1f} km")
        if len(ruta) > 1:
            folium.PolyLine(
                [[c.lat, c.lng] for c in ruta],
                color=color,
                weight=3,
                opacity=0.7,
                tooltip=f"{nombre} · {km:.1f} km",
            ).add_to(capa_asesor)
        for c in ruta:
            popup = (
                f"<b>{escape(c.nombre)}</b><br>{escape(c.sector)}<br>"
                f"Ventas: ${c.ventas:,.0f}<br>Devuelto: ${devuelto.get(c.id, 0):,.0f}"
            )
            folium.CircleMarker(
                [c.lat, c.lng],
                radius=9,
                color="#0a2a5e",
                weight=1,
                fill=True,
                fill_color=escala(valores[c.id]),
                fill_opacity=0.85,
                popup=folium.Popup(popup, max_width=240),
            ).add_to(capa_asesor)
        capa_asesor.add_to(mapa)

    if grupos:
        folium.LayerControl(position="bottomleft", collapsed=False).add_to(mapa)

    return mapa.get_root().render()
