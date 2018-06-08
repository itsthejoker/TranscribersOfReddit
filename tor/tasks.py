from celery import current_app as app


app.autodiscover_tasks(packages=[
    'tor.role_anyone',
    'tor.role_moderator',
])
