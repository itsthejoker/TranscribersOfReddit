FROM python:3.8.0-alpine

RUN python -m pip install --upgrade pip
COPY ./dist/tor-*.whl /tmp/

RUN python -m pip install /tmp/tor-*.whl
RUN command -v tor-moderator

WORKDIR /app
USER 1000

ENV praw_username=""
ENV praw_password=""
ENV praw_client_id=""
ENV praw_client_secret=""
ENV praw_user_agent="praw:org.grafeas.tor.debug:v3.6.0 (by u/personal_opinions)"

CMD ["/usr/local/bin/tor-moderator"]
