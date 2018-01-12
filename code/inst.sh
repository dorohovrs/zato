#!/bin/bash

set -e

virtualenv .
ln -fs python bin/py

./bin/pip install --upgrade pip
./bin/pip install cython==0.22 distribute==0.7.3
ln -fs lib/python*/site-packages eggs

export CYTHON=`pwd`/bin/cython
./bin/pip install -r third-party-reqs.txt -r dev-reqs.txt

patch -p0 -d eggs < patches/anyjson/__init__.py.diff
patch -p0 -d eggs < patches/butler/__init__.py.diff
patch -p0 -d eggs < patches/gunicorn/workers/base.py.diff
patch -p0 -d eggs < patches/gunicorn/arbiter.py.diff
patch -p0 -d eggs < patches/gunicorn/glogging.py.diff
patch -p0 -d eggs < patches/gunicorn/config.py.diff
patch -p0 -d eggs < patches/gunicorn/workers/geventlet.py.diff
patch -p0 -d eggs < patches/gunicorn/workers/ggevent.py.diff
patch -p0 -d eggs < patches/gunicorn/workers/sync.py.diff
patch -p0 -d eggs < patches/hvac/__init__.py.diff
patch -p0 -d eggs < patches/jsonpointer/jsonpointer.py.diff
patch -p0 -d eggs < patches/oauth/oauth.py.diff
patch -p0 -d eggs < patches/redis/redis/connection.py.diff
patch -p0 -d eggs < patches/requests/models.py.diff
patch -p0 -d eggs < patches/requests/sessions.py.diff
patch -p0 -d eggs < patches/requests/packages/urllib3/connectionpool.py.diff
patch -p0 -d eggs < patches/springpython/jms/factory.py.diff
patch -p0 -d eggs < patches/outbox/outbox.py.diff
patch -p0 -d eggs < patches/outbox/outbox.py2.diff
patch -p0 -d eggs < patches/outbox/outbox.py3.diff
patch -p0 -d eggs < patches/outbox/outbox.py4.diff
patch -p0 -d eggs < patches/ws4py/server/geventserver.py.diff
