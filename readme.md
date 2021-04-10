# System monitor

I run cronjobs which append system stats to a local postgres DB every five minutes. This flask app
plots those metrics via bokeh. It is set up to deploy over my local systemd so that the app
is always available.

If rebuilding from scratch, make sure to:

1. Set up pyenv local
2. Set up a blank .env
3. pip install -e. 
