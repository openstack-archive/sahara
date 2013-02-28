from flask.ext.sqlalchemy import SQLAlchemy

DB = SQLAlchemy()


def setup_storage(app):
    DB.app = app
    DB.init_app(app)

    if app.config.get('RESET_DB', False):
        DB.drop_all()

    DB.create_all()
