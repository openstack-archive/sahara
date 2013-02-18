from flask.ext.sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def setup_storage(app):
    global db
    db.app = app
    db.init_app(app)
    db.drop_all()
    db.create_all()
