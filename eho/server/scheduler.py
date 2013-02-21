import logging
import eventlet

pool = eventlet.GreenPool()


def test_job_fun(idx):
    logging.info("Test periodic job, iteration #%s", idx)
    eventlet.spawn_after(5, test_job_fun, idx + 1)


def setup_scheduler(app):
    eventlet.spawn(test_job_fun, 0)
