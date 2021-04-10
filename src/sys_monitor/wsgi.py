"""Run the production WSGI server."""
import argparse
import os

from gevent.pywsgi import WSGIServer

from .app import create_app

parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=None)

if __name__ == "__main__":
    args = parser.parse_args()

    app = create_app()
    port = args.port if args.port is not None else int(os.getenv("PORT", "5000"))

    http_server = WSGIServer(("0.0.0.0", port), app)
    http_server.serve_forever()
