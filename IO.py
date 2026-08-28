from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect
from typing import Dict, List
from pywebpush import webpush, WebPushException
import json
import asyncio
import os

app = FastAPI()

push_subscriptions: Dict[str, List[dict]] = {}

# VAPID ключи (сгенерируйте свои или используйте эти для теста)
VAPID_PRIVATE_KEY = "pVd5mLaHPjYJYA4c-L-2IaclWs_LTJux1nBZQSa9LPs"
VAPID_PUBLIC_KEY = "BC_wVc9umyXQ8uPwJ7HJ0jXeT1BKAubZrLNmgd8rVzgjpVd5mLaHPjYJYA4c-L-2IaclWs_LTJux1nBZQSa9LPs"


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

    async def broadcast_to_room(self, message: str, room: str, sender_ws: WebSocket = None,
                                include_sender: bool = False):
        if room in self.rooms:
            for connection in self.rooms[room]:
                if sender_ws and connection == sender_ws and not include_sender:
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
    # Проверяем, нет ли уже такой подписки
    exists = False
    for existing in push_subscriptions[room]:
        if existing.get('endpoint') == sub_data.get('endpoint'):
            exists = True
            break
    if not exists:
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

            # Для сигналов звонка - отправляем ВСЕМ в комнате, включая отправителя
            # Это важно, чтобы все участники получали сигналы
            if data.get("type") == "call_signal":
                await manager.broadcast_to_room(json.dumps(data), room, None, True)
                continue

            # Для сообщений типа 'delete' и 'edit' отправляем всем, ВКЛЮЧАЯ отправителя
            if data.get("type") in ["delete", "edit"]:
                await manager.broadcast_to_room(json.dumps(data), room, None, True)
                continue

            # Отправляем сообщение всем в комнате, КРОМЕ отправителя
            await manager.broadcast_to_room(json.dumps(data), room, websocket, False)

            # Отправка фоновых пушей (только для текстовых сообщений)
            if data.get("type") in ["text", "image", "video", "audio", "file"]:
                if room in push_subscriptions and push_subscriptions[room]:
                    sender = data.get('sender', 'Аноним')
                    # Определяем тип сообщения для уведомления
                    msg_type = data.get('type', 'сообщение')
                    type_names = {
                        'text': 'текстовое сообщение',
                        'image': 'изображение',
                        'video': 'видео',
                        'audio': 'аудиосообщение',
                        'file': 'файл'
                    }
                    type_name = type_names.get(msg_type, 'сообщение')

                    for sub in push_subscriptions[room]:
                        try:
                            webpush(
                                subscription_info=sub,
                                data=json.dumps({
                                    "title": "VEGA // MESH",
                                    "body": f"📨 {sender}: {type_name}"
                                }),
                                vapid_private_key=VAPID_PRIVATE_KEY,
                                vapid_claims={"sub": "mailto:admin@vega.mesh"}
                            )
                        except WebPushException as e:
                            print(f"Push error: {e}")
                            # Удаляем невалидную подписку
                            if "expired" in str(e) or "410" in str(e):
                                if room in push_subscriptions and sub in push_subscriptions[room]:
                                    push_subscriptions[room].remove(sub)
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