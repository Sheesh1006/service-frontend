from typing import Iterator
import os
from flask import Flask, send_from_directory, request, jsonify
import grpc
from munch import munchify
from yaml import safe_load
from backend_service.backend_service_pb2_grpc import BackendServiceStub
from backend_service.backend_service_pb2 import GetNotesRequest, GetNotesResponse
import webbrowser
import threading
from grpc import RpcError


# Load gRPC client config
def create_client() -> BackendServiceStub:
    with open('config.yml') as cfg:
        config = munchify(safe_load(cfg))
    channel = grpc.insecure_channel(config.backend_client.addr)
    stub = BackendServiceStub(channel)
    return stub

app = Flask(__name__, static_folder='static')
grpc_stub = create_client()

# Serve index.html
@app.route('/')
def index():
    return send_from_directory('templates', 'index.html')

# Serve other static files
@app.route('/static/<path:path>')
def static_files(path):
    return send_from_directory('static', path)

# API endpoint that talks to gRPC
@app.route('/api/process', methods=['POST'])
def process():
    try:
        def video_stream(path):
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    yield GetNotesRequest(video=chunk)

        responses: Iterator[GetNotesResponse] = grpc_stub.GetNotes(video_stream('input_video.mp4'), timeout=3600)

        # Collect streamed responses into a single result
        notes_combined = b''.join(resp.notes for resp in responses)

        # Optional: save the result
        os.makedirs("download", exist_ok=True)
        with open("download/result.pdf", "wb") as f:
            f.write(notes_combined)

        return jsonify({
            "status": "success",
            "message": "Обработка завершена",
            "download_url": "/download/result.pdf"
        })

    except RpcError as e:
        # this will print to your console:
        app.logger.error("gRPC RpcError ‑ code=%s, details=%s", e.code(), e.details())
        # return those details to the HTTP client for visibility:
        return jsonify({
            "status": "error",
            "grpc_code": e.code().name,
            "message": e.details()
        }), 500
    except Exception:
        app.logger.exception("General error in /api/process")
        raise

# Optional: serve result.pdf if needed
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory('download', filename)

def open_browser():
    webbrowser.open_new_tab('http://localhost:8000')

if __name__ == '__main__':
    # open browser shortly after the server starts
    threading.Timer(1.0, open_browser).start()
    # this runs in the main thread, so reloader + signals work fine
    app.run(host="0.0.0.0",port=8000, debug=True)
