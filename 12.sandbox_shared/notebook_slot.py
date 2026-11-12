"""Run a JupyterHub single-user server when this member slot has a session."""
import http.server
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import threading
import time


SESSION = Path("/var/run/notebook-session/session.json")
HOME = Path(os.environ["HOME"])
PORT = int(os.environ["NOTEBOOK_PORT"])
ready_revision = ""


class Status(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        revision = ready_revision
        self.send_response(200 if self.path == "/live" or revision else 503)
        self.end_headers()
        self.wfile.write(revision.encode())

    def log_message(self, *args):
        pass


def terminate(process):
    if process is not None and process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()


def stop(_signal, _frame):
    raise SystemExit


def main():
    global ready_revision
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    if shutil.which("jupyterhub-singleuser") is None:
        raise SystemExit("The approved image must provide jupyterhub-singleuser on PATH")
    HOME.mkdir(parents=True, exist_ok=True)
    if not os.access(HOME, os.W_OK | os.X_OK):
        raise SystemExit(f"Notebook home is not writable: {HOME}")
    with http.server.ThreadingHTTPServer(("0.0.0.0", PORT + 112), Status) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        current = None
        process = None
        try:
            while True:
                try:
                    requested = json.loads(SESSION.read_text())
                except FileNotFoundError:
                    requested = None
                if requested != current:
                    ready_revision = ""
                    terminate(process)
                    process = None
                    current = requested
                    if current:
                        process = subprocess.Popen(
                            ["jupyterhub-singleuser", "--ip=0.0.0.0", f"--port={PORT}",
                             f"--ServerApp.root_dir={HOME}", "--ServerApp.default_url=/lab"],
                            env={**os.environ, **current["env"]}, cwd=HOME, start_new_session=True,
                        )
                if process is not None:
                    if process.poll() is not None:
                        raise SystemExit(f"Jupyter server exited with status {process.returncode}")
                    try:
                        with socket.create_connection(("127.0.0.1", PORT), timeout=0.5):
                            ready_revision = current["revision"]
                    except OSError:
                        ready_revision = ""
                time.sleep(1)
        finally:
            ready_revision = ""
            terminate(process)
            server.shutdown()


if __name__ == "__main__":
    main()
