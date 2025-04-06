from http.server import SimpleHTTPRequestHandler, HTTPServer
import webbrowser
import threading
import os
import json
from urllib.parse import unquote, urlparse

PORT = 8000
DIRECTORY = "."

class MyHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def translate_path(self, path):
        path = unquote(path)
        parsed = urlparse(path)
        path = parsed.path
        
        if path.startswith('/static/'):
            return os.path.join(DIRECTORY, path[1:])
        elif path == '/' or path == '/index.html':
            return os.path.join(DIRECTORY, 'templates/index.html')
        return super().translate_path(path)
    
    def do_POST(self):
        if self.path == '/api/process':
            content_length = int(self.headers['Content-Length'])
            post_data = json.loads(self.rfile.read(content_length).decode('utf-8'))
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                "status": "success",
                "message": "Обработка завершена",
                "download_url": "/download/result.pdf"
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

def run_server():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, MyHandler)
    print(f'Сервер запущен: http://localhost:{PORT}')
    httpd.serve_forever()

if __name__ == '__main__':
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    webbrowser.open_new_tab(f'http://localhost:{PORT}')
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\nСервер остановлен")