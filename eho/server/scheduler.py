import eventlet

POOL = eventlet.GreenPool()


def setup_scheduler(app):
    app.pool = POOL
