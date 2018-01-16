#!/bin/bash

set -e

false && {
    bash ./clean.sh

    # Always run an update so there are no surprises later on when it actually
    # comes to fetching the packages from repositories.
    sudo apt-get update

    sudo apt-get install -y git bzr gfortran haproxy \
        libatlas-dev libatlas3-base libblas3 \
        libbz2-dev libev4 libev-dev \
        libevent-dev libgfortran3 liblapack-dev liblapack3 libldap2-dev \
        libmemcached-dev libpq-dev libsasl2-dev libyaml-dev libxml2-dev libxslt1-dev \
        libumfpack* openssl python2.7-dev python-numpy python-pip \
        python-scipy python-zdaemon swig uuid-dev uuid-runtime libffi-dev libssl-dev

    # On Debian and Ubuntu the binary goes to /usr/sbin/haproxy so we need to symlink it
    # to a directory that can be easily found on PATH so that starting the load-balancer
    # is possible without tweaking its configuration file.
    out=$(lsb_release -si)
    if [ $out == "Debian" ] || [ $out == "Ubuntu" ]; then
        sudo ln -sf /usr/sbin/haproxy /usr/bin/haproxy
    fi

    sudo pip install virtualenv==15.1.0
}


virtualenv .

cat > bin/py <<-EOF
#!/bin/sh
exec "$(pwd)/bin/python" "\$@"
EOF

chmod +x bin/py
#ln -fs python bin/py

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
