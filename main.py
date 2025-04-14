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
        def request_stream():
            while True:
                chunk = request.stream.read(1024 * 1024)  # 1MB
                if not chunk:
                    break
                yield GetNotesRequest(video=chunk, presentation=b"")
        responses: Iterator[GetNotesResponse] = grpc_stub.GetNotes(request_stream())

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

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# Optional: serve result.pdf if needed
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory('download', filename)

def run():
    webbrowser.open_new_tab(f'http://localhost:8000')
    app.run(port=8000, debug=False)

if __name__ == '__main__':
    threading.Thread(target=run).start()