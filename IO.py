from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect
from typing import Dict, List
from pywebpush import webpush, WebPushException
import json

app = FastAPI()

push_subscriptions: Dict[str, List[dict]] = {}


class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str):
        await websocket.accept()
        if room not in self.rooms:
            self.rooms[room] = []
        self.rooms[room].append(websocket)

    def disconnect(self, websocket: WebSocket, room: str):
        if room in self.rooms and websocket in self.rooms[room]:
            self.rooms[room].remove(websocket)
            if not self.rooms[room]:
                del self.rooms[room]

    async def broadcast_to_room(self, message: str, room: str, sender_ws: WebSocket = None):
        if room in self.rooms:
            for connection in self.rooms[room]:
                # Если передан sender_ws, не отправляем сообщение обратно отправителю
                if sender_ws and connection == sender_ws:
                    continue
                try:
                    await connection.send_text(message)
                except:
                    pass


manager = ConnectionManager()


@app.get("/sw.js")
async def get_sw():
    return FileResponse("sw.js", media_type="application/javascript")


@app.post("/subscribe/{room}")
async def subscribe(room: str, request: Request):
    sub_data = await request.json()
    if room not in push_subscriptions:
        push_subscriptions[room] = []
    if sub_data not in push_subscriptions[room]:
        push_subscriptions[room].append(sub_data)
    return {"status": "ok"}


@app.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str):
    await manager.connect(websocket, room)
    try:
        while True:
            data = await websocket.receive_json()

            # Обработка пинга
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            # Отправляем сообщение всем в комнате, КРОМЕ отправителя
            # Это важно для сигналов звонка, чтобы не получать свои же сигналы
            await manager.broadcast_to_room(json.dumps(data), room, websocket)

            # Отправка фоновых пушей (только для текстовых сообщений, не для сигналов звонка)
            if data.get("type") not in ["call_signal", "ping", "pong"]:
                if room in push_subscriptions:
                    for sub in push_subscriptions[room]:
                        try:
                            webpush(
                                subscription_info=sub,
                                data=json.dumps({
                                    "title": "CYPHER // ALERT",
                                    "body": f"🔒 Новое сообщение от {data.get('sender', 'Аноним')}!"
                                }),
                                vapid_private_key="pVd5mLaHPjYJYA4c-L-2IaclWs_LTJux1nBZQSa9LPs",
                                vapid_claims={"sub": "mailto:admin@cypher.mesh"}
                            )
                        except WebPushException:
                            pass
    except WebSocketDisconnect:
        manager.disconnect(websocket, room)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket, room)


@app.get("/")
async def get():
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("IO:app", host="0.0.0.0", port=8000, reload=True)