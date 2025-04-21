from flask import Flask, send_from_directory, request, jsonify, send_file
import grpc
from munch import munchify
from yaml import safe_load
from backend_service.backend_service_pb2_grpc import BackendServiceStub
from backend_service.backend_service_pb2 import GetNotesRequest, GetNotesResponse
import webbrowser
import threading
from grpc import RpcError
from werkzeug.exceptions import BadRequest
from io import BytesIO


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
    # 1) Validate upload
    if 'video' not in request.files:
        raise BadRequest('No video file part in request')

    vid_file = request.files['video']
    if not vid_file or vid_file.filename == '':
        raise BadRequest('No selected file')

    # 2) Generator that reads straight from the in‑memory upload
    def video_stream(file_obj):
        # rewind to start
        try:
            file_obj.seek(0)
        except Exception:
            pass

        while True:
            chunk = file_obj.read(4096)
            if not chunk:
                break
            yield GetNotesRequest(video=chunk)

    try:
        # 3) Call gRPC with our in‑memory stream
        responses = grpc_stub.GetNotes(video_stream(vid_file.stream), timeout=3600)

        # 4) Collect into an in‑memory buffer
        pdf_buffer = BytesIO()
        for resp in responses:
            pdf_buffer.write(resp.notes)
        pdf_buffer.seek(0)

        # 5) Return as PDF download
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='result.pdf'
        ), 200

    except RpcError as e:
        app.logger.error("gRPC RpcError code=%s, details=%s", e.code(), e.details())
        app.logger.debug("gRPC debug_error_string:\n%s", e.debug_error_string())
        return jsonify({
            'status': 'error',
            'grpc_code': e.code().name,
            'message': e.details()
        }), 502

    except Exception:
        app.logger.exception("Unexpected error in /api/process")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

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
