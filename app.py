import os

from dotenv import load_dotenv
from flask import Flask

from models import db, resolver_url, sembrar
from routes import bp

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = resolver_url("sqlite:///logistica.db")
    app.template_filter("cop")(lambda v: "${:,.0f}".format(v or 0).replace(",", "."))
    db.init_app(app)
    app.register_blueprint(bp)
    with app.app_context():
        db.create_all()
        if os.getenv("CARGAR_EJEMPLOS", "1") == "1":
            sembrar()
    return app


app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG") == "1",
    )
