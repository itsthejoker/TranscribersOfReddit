from tor.celeryconfig import Config
from tor_core import __BROKER_URL__
from celery import Celery


"""
This is for testing purposes only. This file should not be used in production
"""

cfg = Config()
cfg.beat_schedule = {}

app = Celery("tor", broker=__BROKER_URL__)
app.config_from_object(cfg)
app.autodiscover_tasks(force=True, packages=["tor"])
