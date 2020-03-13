#!/usr/bin/env bash

echo "Starting Jetty"
sudo service jetty8 restart

sudo netstat -ntlp

python setup.py nosetests