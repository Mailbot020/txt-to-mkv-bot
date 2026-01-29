import os
import re
import asyncio
import subprocess
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply

# --- CONFIGURATION ---
API_ID = 1234567  # Apna ID daalein
API_HASH = "your_api_hash"
BOT_TOKEN = "your_bot_token"
AUTH_KEY = "Mohit"

app = Client("UploaderBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Temporary Storage
user_data = {}

@app.on_message(filters.command("start"))
async def start(client, message):
    text = (
        "**Welcome to uploader bot**\n\n"
        "Use /ram to start downloading\n"
        "Use /stop to stop process\n\n"
        "For any type of help please contact **🚩Ram Bhakt🚩**"
    )
    await message.reply_text(text)

@app.on_message(filters.command("ram"))
async def ram_cmd(client, message):
    await message.reply_text("Please upload a **.txt** file to continue")

@app.on_message(filters.document & filters.private)
async def handle_document(client, message):
    if message.document.file_name.endswith(".txt"):
        file_path = await message.download()
        user_data[message.chat.id] = {"file": file_path}
        await message.reply_text("Please choose index number where to start", reply_markup=ForceReply(True))

@app.on_message(filters.reply & filters.private)
async def handle_replies(client, message):
    chat_id = message.chat.id
    msg_text = message.text

    # Step 1: Index selection
    if "index number" in message.reply_to_message.text:
        user_data[chat_id]["index"] = int(msg_text)
        await message.reply_text("Please choose quality you want : 240, 360, 480, 720", reply_markup=ForceReply(True))
        # Delete user reply for privacy
        await message.delete()

    # Step 2: Quality selection
    elif "quality" in message.reply_to_message.text:
        user_data[chat_id]["quality"] = msg_text
        await message.reply_text("Enter security key", reply_markup=ForceReply(True))
        await message.delete()

    # Step 3: Security Key & Process Start
    elif "security key" in message.reply_to_message.text:
        await message.delete()
        if msg_text == AUTH_KEY:
            await message.reply_text("🚀 Starting Process...")
            await start_processing(client, message)
        else:
            await message.reply_text("❌ Wrong Key! Access Denied.")

async def start_processing(client, message):
    chat_id = message.chat.id
    data = user_data.get(chat_id)
    
    with open(data["file"], "r") as f:
        lines = f.readlines()

    start_idx = data["index"] - 1
    quality = data["quality"]

    for i in range(start_idx, len(lines)):
        if chat_id not in user_data: # Stop check
            break
            
        line = lines[i].strip()
        if not line: continue
        
        # Parsing: Math class-01 : "link"
        name, link = line.split(':', 1)
        name = name.strip()
        link = link.replace('"', '').strip()
        caption = f"{name}\nIndex : {i+1}"

        prog_msg = await client.send_message(chat_id, f"📥 Downloading: {name}")

        try:
            if ".m3u8" in link:
                filename = f"{name}.mkv"
                # FFmpeg download logic
                cmd = f'ffmpeg -i "{link}" -c copy -bsf:a aac_adtstoasc "{filename}" -y'
                process = subprocess.run(cmd, shell=True)
                await client.send_video(chat_id, video=filename, caption=caption)
                os.remove(filename) # Server cleanup
            
            elif ".pdf" in link:
                filename = f"{name}.pdf"
                # PDF download logic
                import requests
                r = requests.get(link)
                with open(filename, 'wb') as f_pdf:
                    f_pdf.write(r.content)
                await client.send_document(chat_id, document=filename, caption=caption)
                os.remove(filename)

        except Exception as e:
            await client.send_message(chat_id, f"Error on index {i+1}: {str(e)}")
        
        await prog_msg.delete()

    await client.send_message(chat_id, "✅ Index out of range. Task Completed!")

@app.on_message(filters.command("stop"))
async def stop_process(client, message):
    user_data.pop(message.chat.id, None)
    await message.reply_text("🚦 **Stopped** 🚦")

app.run()
