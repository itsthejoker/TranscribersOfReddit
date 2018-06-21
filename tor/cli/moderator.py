import sys

from celery.bin import worker
from tor_core import CELERY_CONFIG_MODULE


def main():
    # override any options given after the fact
    argv = list(sys.argv)
    if argv[0].startswith('python'):
        # remove `python` from `python somescript.py`
        argv.pop(0)

    # Remove `./command-name` from `./command-name -my -args -here`
    argv.pop(0)

    # Set default options to occur first (in case overrides)
    argv = [
        '-A', CELERY_CONFIG_MODULE,
        '-Q', 'default',
        '-l', 'info',
        '--autoscale', '10,1'
    ] + argv

    worker.worker(app=None)\
        .execute_from_commandline(
            prog_name='tor-moderator',
            argv=argv)


if __name__ == '__main__':
    main()
