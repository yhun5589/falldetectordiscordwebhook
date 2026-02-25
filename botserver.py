import discord
import asyncio
import cv2
from fastapi import FastAPI, UploadFile, File, Form
from io import BytesIO
import uvicorn
import os

# ================= DISCORD SETUP =================
BOT_TOKEN = os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
client = discord.Client(intents=intents)

loop = None

# ================= FASTAPI =================
app = FastAPI()

# ================= DISCORD READY =================
@client.event
async def on_ready():
    global loop
    loop = asyncio.get_running_loop()
    print("✅ Discord bot ready")

# ================= API ENDPOINT =================
@app.post("/send_alert")
async def send_alert(
    guild_id: int = Form(...),
    message: str = Form(...),
    image: UploadFile = File(None)
):
    if loop is None:
        return {"status": "Discord not ready"}

    guild = client.get_guild(guild_id)
    if not guild:
        return {"status": "Guild not found"}

    # Find first text channel with permission
    channel = None
    for ch in guild.text_channels:
        if ch.permissions_for(guild.me).send_messages:
            channel = ch
            break

    if not channel:
        return {"status": "No valid channel found"}

    async def send():
        await channel.send(message)

        if image:
            data = await image.read()
            file = discord.File(BytesIO(data), filename="alert.jpg")
            await channel.send(file=file)

    asyncio.run_coroutine_threadsafe(send(), loop)

    return {"status": "Alert sent"}

# ================= START BOTH =================
def start():
    import threading
    threading.Thread(target=lambda: client.run(BOT_TOKEN)).start()
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    start()
