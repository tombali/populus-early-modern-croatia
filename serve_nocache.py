import http.server, socketserver, sys
class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control","no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma","no-cache"); self.send_header("Expires","0")
        super().end_headers()
    def log_message(self,*a): pass
port=int(sys.argv[1]) if len(sys.argv)>1 else 8137
socketserver.TCPServer.allow_reuse_address=True
with socketserver.TCPServer(("",port),H) as s:
    print("no-cache server on",port); s.serve_forever()
