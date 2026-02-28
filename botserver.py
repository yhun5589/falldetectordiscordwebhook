import discord
import asyncio
import threading
from fastapi import FastAPI, UploadFile, File, Form
from io import BytesIO
import uvicorn
import os
import requests
import time

# ================= CONFIG =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

# ================= FASTAPI =================
app = FastAPI()

# ================= DISCORD SETUP =================
intents = discord.Intents.default()
client = discord.Client(intents=intents)

# Create dedicated event loop for Discord
discord_loop = asyncio.new_event_loop()

# ================= HEALTH ROUTE =================
@app.get("/health")
async def health():
    return {"status": "ok"}

# ================= AUTO SELF PING =================
def self_ping():
    """
    Pings own health endpoint every 50 seconds.
    Helps reduce cold sleep on Render free tier.
    """
    if not RENDER_EXTERNAL_URL:
        return

    while True:
        try:
            requests.get(f"{RENDER_EXTERNAL_URL}/health", timeout=10)
        except Exception as e:
            print("Self ping error:", e)

        time.sleep(50)

# ================= DISCORD EVENTS =================
@client.event
async def on_ready():
    print(f"✅ Discord bot ready: {client.user}")

# ================= API ENDPOINT =================
@app.post("/send_alert")
async def send_alert(
    guild_id: int = Form(...),
    message: str = Form(...),
    image: UploadFile = File(None)
):
    guild = client.get_guild(guild_id)

    if not guild:
        return {"status": "Guild not found"}

    # Find first valid text channel
    channel = None
    for ch in guild.text_channels:
        if ch.permissions_for(guild.me).send_messages:
            channel = ch
            break

    if not channel:
        return {"status": "No valid channel found"}

    file = None

    if image is not None:
        contents = await image.read()

        if len(contents) > 0:
            file = discord.File(
                BytesIO(contents),
                filename=image.filename or "alert.jpg"
            )

    async def send():
        try:
            if file:
                await channel.send(content=message, file=file)
                file.close()  # prevent memory leak
            else:
                await channel.send(message)
        except Exception as e:
            print("Discord send error:", e)

    asyncio.run_coroutine_threadsafe(send(), discord_loop)

    return {"status": "Alert sent", "has_file": file is not None}

# ================= START FUNCTIONS =================
def start_discord():
    asyncio.set_event_loop(discord_loop)
    discord_loop.run_until_complete(client.start(BOT_TOKEN))

def start_self_ping():
    thread = threading.Thread(target=self_ping, daemon=True)
    thread.start()

# ================= MAIN ENTRY =================
if __name__ == "__main__":
    # Start Discord in background
    threading.Thread(target=start_discord, daemon=True).start()

    # Start self-ping
    start_self_ping()

    # Start FastAPI server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        workers=1
    )
