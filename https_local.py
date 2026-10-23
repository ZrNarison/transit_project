
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ssl
import sys

HOST = "0.0.0.0"
PORT = 8443

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000

CERT_FILE = r"D:\transit_project\certificats\transit-local.crt"
KEY_FILE = r"D:\transit_project\certificats\transit-local.key"

HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


class HTTPSProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        self.proxy_request()

    def do_HEAD(self):
        self.proxy_request()

    def do_POST(self):
        self.proxy_request()

    def do_PUT(self):
        self.proxy_request()

    def do_PATCH(self):
        self.proxy_request()

    def do_DELETE(self):
        self.proxy_request()

    def do_OPTIONS(self):
        self.proxy_request()

    def proxy_request(self):
        connection = None

        try:
            length = int(self.headers.get("Content-Length", "0"))

            if length < 0:
                self.send_error(400, "Taille de requête invalide.")
                return

            body = self.rfile.read(length) if length else None

            headers = {
                name: value
                for name, value in self.headers.items()
                if name.lower() not in HOP_BY_HOP
                and name.lower() != "expect"
            }

            # Django doit reconnaître la connexion HTTPS.
            headers["X-Forwarded-Proto"] = "https"
            headers["X-Forwarded-For"] = self.client_address[0]
            headers["Host"] = self.headers.get(
                "Host", "192.168.43.12:8443"
            )

            connection = HTTPConnection(
                BACKEND_HOST,
                BACKEND_PORT,
                timeout=120,
            )

            connection.request(
                self.command,
                self.path,
                body=body,
                headers=headers,
            )

            response = connection.getresponse()
            response_body = response.read()

            self.send_response(response.status, response.reason)

            response_length_sent = False

            for name, value in response.getheaders():
                if name.lower() in HOP_BY_HOP:
                    continue

                if name.lower() == "content-length":
                    if not response_length_sent:
                        self.send_header(
                            "Content-Length",
                            str(len(response_body)),
                        )
                        response_length_sent = True
                    continue

                self.send_header(name, value)

            if not response_length_sent:
                self.send_header(
                    "Content-Length",
                    str(len(response_body)),
                )

            self.send_header("Connection", "close")
            self.end_headers()

            if self.command != "HEAD" and response_body:
                self.wfile.write(response_body)

            self.close_connection = True

        except Exception as exc:
            print(
                f"Erreur du relais HTTPS : {exc}",
                file=sys.stderr,
                flush=True,
            )

            try:
                self.send_error(
                    502,
                    "Le serveur Django local est indisponible.",
                )
            except Exception:
                pass

        finally:
            if connection is not None:
                connection.close()

    def log_message(self, fmt, *args):
        print(
            f"[HTTPS] {self.client_address[0]} - {fmt % args}",
            flush=True,
        )


def main():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(CERT_FILE, KEY_FILE)

    server = ThreadingHTTPServer(
        (HOST, PORT),
        HTTPSProxyHandler,
    )

    server.socket = context.wrap_socket(
        server.socket,
        server_side=True,
    )

    print(
        f"Relais HTTPS : https://192.168.43.12:{PORT}/",
        flush=True,
    )
    print(
        f"Django : http://{BACKEND_HOST}:{BACKEND_PORT}/",
        flush=True,
    )
    print("Ctrl+C pour arrêter le relais.", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du relais HTTPS.", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
