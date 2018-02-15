
export ADMIN_EMAIL=swat@soe.ucsc.edu
export ALLOWABLE_VIEWERS=https://hexdev.sdsc.edu:8222,https://hexdev.sdsc.edu:8229,http://hexdev.sdsc.edu:8222,https://hexdev.sdsc.edu:8229
export BACK_OR_FOREGROUND=BACK
export CA=/cluster/home/swat/certs/hexcalc/chain.crt
export CERT=/cluster/home/swat/certs/hexcalc/server.crt
export DATA_ROOT=/hive/groups/hexmap/dev/data
export DEBUG=1
export DEV=1
export DRL_PATH=/cluster/home/swat/packagesHexcalc/drl-graph-layout/bin
export FLASK_DEBUG=1
export HUB_PATH=/cluster/home/swat/dev/compute
export KEY=/cluster/home/swat/certs/hexcalc/server.key
export PYENV=$HUB_PATH/../envHexcalc
export TEST_DATA_ROOT=$HUB_PATH/tests/in/dataRoot
export USE_HTTPS=1
export VIEWER_URL=https://hexdev.sdsc.edu:8222
export WWW_SOCKET=hexcalc.ucsc.edu:8442

# If the python environment is present then open it up.
if [ -e $PYENV/bin/activate ]; then
    echo 'entering virtualenv:' $PYENV
    source $PYENV/bin/activate
fi
