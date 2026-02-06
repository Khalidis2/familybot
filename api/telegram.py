# api/telegram.py
import json
import asyncio
from http.server import BaseHTTPRequestHandler

from telegram import Update

from familybot.bot import application


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("content-length", 0))
        body = self.rfile.read(length)
        data = json.loads(body.decode("utf-8"))
        update = Update.de_json(data, application.bot)

        async def process():
            if not getattr(application, "_initialized", False):
                await application.initialize()
                application._initialized = True
            await application.process_update(update)

        asyncio.run(process())
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"OK")

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"OK")
