import datetime
import hashlib
import hmac
import os
import re
import smtplib
import ssl
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MAX_BYTES = 15 * 1024 * 1024
FIELDS = {"excel": ".xlsx", "banca": ".pdf", "zucchetti": ".pdf"}
PAGE = Path(__file__).with_name("index.html").read_bytes()


class Portal(BaseHTTPRequestHandler):
    def reply(self, status, body, kind="text/plain; charset=utf-8"):
        self.send_response(status)
        if status == 401:
            self.send_header("WWW-Authenticate", 'Basic realm="Prima nota", charset="UTF-8"')
        self.send_header("Content-Type", kind)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body if isinstance(body, bytes) else body.encode())

    def authorized(self):
        import base64
        try:
            scheme, token = self.headers.get("Authorization", "").split()
            if scheme.lower() != "basic":
                return False
            user, password = base64.b64decode(token, validate=True).split(b":", 1)
            return hmac.compare_digest(user, b"prima-nota") and hmac.compare_digest(
                hashlib.scrypt(password, salt=SALT, n=32768, r=8, p=1, maxmem=64*1024*1024).hex(), HASH
            )
        except ValueError:
            return False

    def do_GET(self):
        if self.path != "/":
            self.reply(404, "Pagina non trovata.")
        elif self.authorized():
            self.reply(200, PAGE, "text/html; charset=utf-8")
        else:
            self.reply(401, "Accedi al portale prima nota.")

    def do_POST(self):
        if self.path != "/":
            return self.reply(404, "Pagina non trovata.")
        if self.headers.get("Origin") != os.environ["PORTAL_ORIGIN"]:
            return self.reply(403, "Apri il portale dal suo indirizzo ufficiale.")
        if not self.authorized():
            return self.reply(401, "Accedi al portale prima nota.")
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BYTES:
                return self.reply(413, "Il totale deve essere inferiore a 15 MB.")
            mime = self.headers.get("Content-Type", "")
            if not mime.startswith("multipart/form-data;") or "\n" in mime or "\r" in mime:
                raise ValueError
            payload = BytesParser(policy=policy.default).parsebytes(
                b"Content-Type: " + mime.encode("ascii") + b"\r\n\r\n" + self.rfile.read(length)
            )
            parts = {}
            for part in payload.iter_parts():
                field = part.get_param("name", header="content-disposition")
                if field in parts or field not in {*FIELDS, "data"}:
                    raise ValueError
                parts[field] = part
            day = datetime.date.fromisoformat(parts["data"].get_payload(decode=True).decode())
            message = EmailMessage()
            message["Subject"] = f"Prima nota | {day.isoformat()}"
            message["From"] = os.environ["SMTP_FROM"]
            message["To"] = os.environ["PRIMA_NOTA_TO"]
            message.set_content(f"Documenti di prima nota per il {day:%d/%m/%Y}.")
            for field, suffix in FIELDS.items():
                part = parts[field]
                filename = part.get_filename() or ""
                data = part.get_payload(decode=True)
                signature = b"PK\x03\x04" if field == "excel" else b"%PDF-"
                if not filename.lower().endswith(suffix) or not data or not data.startswith(signature):
                    raise ValueError
                subtype = "vnd.openxmlformats-officedocument.spreadsheetml.sheet" if field == "excel" else "pdf"
                message.add_attachment(data, maintype="application", subtype=subtype, filename=f"{day}-{field}{suffix}")
        except (ValueError, KeyError, TypeError):
            return self.reply(400, "Controlla la data e seleziona un Excel e due PDF. Torna alla pagina per riprovare.")
        try:
            with smtplib.SMTP_SSL(os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT", "465")), timeout=25,
                                  context=ssl.create_default_context()) as smtp:
                smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException):
            return self.reply(502, "Invio non confermato. Contatta il destinatario prima di riprovare.")
        self.reply(200, "Documenti accettati dal servizio email. Puoi chiudere la pagina.")

    def setup(self):
        super().setup()
        self.connection.settimeout(35)


if __name__ == "__main__":
    for key in ("PORTAL_ORIGIN", "SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM", "PRIMA_NOTA_TO"):
        if not os.environ.get(key):
            raise SystemExit(f"Configurazione mancante: {key}")
    salt, HASH = os.environ["PORTAL_PASSWORD_HASH"].split(":", 1)
    if not re.fullmatch(r"[a-f0-9]{32}", salt) or not re.fullmatch(r"[a-f0-9]{128}", HASH):
        raise SystemExit("Hash password non valido.")
    SALT = bytes.fromhex(salt)
    ThreadingHTTPServer(("0.0.0.0", int(os.getenv("PORT", "8080"))), Portal).serve_forever()
