import os
import random
from datetime import date

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine

db = SQLAlchemy()

SECTORES = {
    "Compartir": (4.5790, -74.2160),
    "San Mateo": (4.5914, -74.2256),
    "Ciudad Verde": (4.5568, -74.2347),
    "Soacha Centro": (4.5794, -74.2168),
    "Altos de Cazucá": (4.5730, -74.1900),
    "San Humberto": (4.5990, -74.2010),
}
NEGOCIOS = ["Tienda La Esquina", "Mini Mercado", "Supertienda", "Víveres", "Abarrotes", "Autoservicio"]
MOTIVOS = ["Producto vencido", "Empaque dañado", "Error de pedido", "Cambio de referencia"]


def resolver_url(defecto):
    url = os.getenv("DATABASE_URL")
    if url:
        try:
            with create_engine(url).connect():
                return url
        except Exception as error:
            print(f"No se pudo conectar a DATABASE_URL ({type(error).__name__}), se usa SQLite local")
    return defecto


class Asesor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False)
    color = db.Column(db.String(20), default="#0d6efd")
    clientes = db.relationship("Cliente", backref="asesor")


class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    sector = db.Column(db.String(60), nullable=False, index=True)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    ventas = db.Column(db.Float, default=0)
    asesor_id = db.Column(db.Integer, db.ForeignKey("asesor.id"))
    devoluciones = db.relationship("Devolucion", backref="cliente", cascade="all, delete-orphan")

    def to_dict(self, devuelto=0):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "sector": self.sector,
            "asesor": self.asesor.nombre if self.asesor else None,
            "lat": self.lat,
            "lng": self.lng,
            "ventas": self.ventas,
            "devuelto": devuelto,
        }


class Devolucion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    motivo = db.Column(db.String(120))
    fecha = db.Column(db.Date, default=date.today)


def sembrar():
    if Asesor.query.first():
        return
    azar = random.Random(7)
    asesores = [
        Asesor(nombre="Carlos Rojas", color="#0a2a5e"),
        Asesor(nombre="Marcela Díaz", color="#f08c00"),
        Asesor(nombre="Andrés Pérez", color="#20a39e"),
    ]
    db.session.add_all(asesores)
    db.session.flush()
    for i, (sector, (lat, lng)) in enumerate(SECTORES.items()):
        for j in range(4):
            cliente = Cliente(
                nombre=f"{azar.choice(NEGOCIOS)} {i * 4 + j + 1}",
                sector=sector,
                lat=lat + azar.uniform(-0.006, 0.006),
                lng=lng + azar.uniform(-0.006, 0.006),
                ventas=azar.randint(8, 60) * 100000,
                asesor_id=asesores[(i + j) % 3].id,
            )
            db.session.add(cliente)
            db.session.flush()
            if azar.random() < 0.5:
                db.session.add(Devolucion(
                    cliente_id=cliente.id,
                    valor=azar.randint(1, 12) * 10000,
                    motivo=azar.choice(MOTIVOS),
                ))
    db.session.commit()
