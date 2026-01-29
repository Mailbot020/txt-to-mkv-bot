import os
import re
import asyncio
import subprocess
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply

# --- CONFIGURATION ---
API_ID = 1234567  # Apna API ID yahan dalein
API_HASH = "your_api_hash" # Apna API Hash yahan dalein
BOT_TOKEN = "your_bot_token" # Apna Bot Token yahan dalein
AUTH_KEY = "Mohit"

app = Client("UploaderBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Temporary Storage for sessions
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
    if chat_id not in user_data: return

    # Index Selection
    if "index number" in message.reply_to_message.text:
        user_data[chat_id]["index"] = int(message.text)
        await message.delete() # User reply hide
        await message.reply_text("Please choose quality you want : 240, 360, 480, 720", reply_markup=ForceReply(True))

    # Quality Selection
    elif "quality" in message.reply_to_message.text:
        user_data[chat_id]["quality"] = message.text
        await message.delete()
        await message.reply_text("Enter security key", reply_markup=ForceReply(True))

    # Security Key & Execution
    elif "security key" in message.reply_to_message.text:
        await message.delete()
        if message.text == AUTH_KEY:
            await message.reply_text("🚀 **Key Verified! Starting Extraction...**")
            await start_processing(client, chat_id)
        else:
            await message.reply_text("❌ Wrong Key!")

async def start_processing(client, chat_id):
    data = user_data.get(chat_id)
    file_path = data["file"]
    start_idx = data["index"] - 1
    quality = data["quality"]

    with open(file_path, "r") as f:
        lines = f.readlines()

    for i in range(start_idx, len(lines)):
        if chat_id not in user_data: # Stop check
            await client.send_message(chat_id, "🚦 **Stopped** 🚦")
            break
            
        line = lines[i].strip()
        if not line or ":" not in line: continue
        
        # Regex to extract Name and Link
        parts = line.split(":", 1)
        name = parts[0].strip()
        link = re.findall(r'https?://[^\s"]+', parts[1])[0]
        
        caption = f"{name}\n\n**Index : {i+1}**"
        prog_msg = await client.send_message(chat_id, f"📥 **Processing Index {i+1}:**\n`{name}`")

        try:
            if ".m3u8" in link:
                filename = f"{name}.mkv"
                # FFmpeg command for m3u8 to mkv
                cmd = f'ffmpeg -i "{link}" -c copy -bsf:a aac_adtstoasc "{filename}" -y -loglevel quiet'
                os.system(cmd)
                if os.path.exists(filename):
                    await client.send_video(chat_id, video=filename, caption=caption)
                    os.remove(filename) # Clear server data
            
            elif ".pdf" in link:
                filename = f"{name}.pdf"
                res = requests.get(link)
                with open(filename, 'wb') as f_pdf:
                    f_pdf.write(res.content)
                await client.send_document(chat_id, document=filename, caption=caption)
                os.remove(filename)

        except Exception as e:
            await client.send_message(chat_id, f"⚠️ Error at Index {i+1}: {e}")
        
        await prog_msg.delete()

    await client.send_message(chat_id, "🏁 **index out of range.... Task Finished!**")
    if os.path.exists(file_path): os.remove(file_path) # Cleanup text file

@app.on_message(filters.command("stop"))
async def stop_process(client, message):
    user_data.pop(message.chat.id, None)

app.run()
