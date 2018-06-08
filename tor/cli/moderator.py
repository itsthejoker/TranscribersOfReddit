from celery import current_app
from celery.bin import worker

from tor_core import __BROKER_URL__


def main():
    app = current_app._get_current_object()
    wrk = worker.worker(app=app)

    options = {
        'broker': __BROKER_URL__,
        'logLevel': 'INFO',
        'traceback': True,
    }

    wrk.run(**options)


if __name__ == '__main__':
    main()
