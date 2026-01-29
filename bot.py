import os
import re
import asyncio
import subprocess
import requests
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from pyrogram.errors import FloodWait

# Configuration (Colab ke Secrets se automatic uthayega)
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
AUTH_KEY = "Mohit"

app = Client("UploaderBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Temporary Storage
user_data = {}

# Progress Bar Function
async def progress_bar(current, total, reply, start_time):
    try:
        now = time.time()
        diff = now - start_time
        if round(diff % 5.00) == 0 or current == total:
            percentage = current * 100 / total
            speed = current / diff
            elapsed_time = round(diff)
            eta = round((total - current) / speed)
            
            progress = "[{0}{1}]".format(
                '●' * int(percentage / 10),
                '○' * (10 - int(percentage / 10))
            )
            
            tmp = f"**🚀 Processing...**\n\n" \
                  f"**{progress}** {round(percentage, 2)}%\n" \
                  f"**⚡ Speed:** {round(speed / 1024, 2)} KB/s\n" \
                  f"**⏳ ETA:** {eta}s"
            
            await reply.edit_text(tmp)
    except Exception:
        pass

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        "**Welcome to uploader bot**\n\n"
        "Use /ram to start downloading\n"
        "Use /stop to stop process\n\n"
        "For any type of help please contact **🚩Ram Bhakt🚩**"
    )

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

    # Step 1: Index selection
    if "index number" in message.reply_to_message.text:
        user_data[chat_id]["index"] = int(message.text)
        await message.delete() 
        await message.reply_text("Please choose quality: 240, 360, 480, 720", reply_markup=ForceReply(True))

    # Step 2: Quality selection
    elif "quality" in message.reply_to_message.text:
        user_data[chat_id]["quality"] = message.text
        await message.delete()
        await message.reply_text("Enter security key", reply_markup=ForceReply(True))

    # Step 3: Key & Start
    elif "security key" in message.reply_to_message.text:
        await message.delete()
        if message.text == AUTH_KEY:
            await message.reply_text("✅ Key Verified! Starting...")
            await start_processing(client, chat_id)
        else:
            await message.reply_text("❌ Wrong Key!")

async def start_processing(client, chat_id):
    data = user_data.get(chat_id)
    file_path = data["file"]
    start_idx = data["index"] - 1
    
    with open(file_path, "r") as f:
        lines = f.readlines()

    for i in range(start_idx, len(lines)):
        if chat_id not in user_data: break
            
        line = lines[i].strip()
        if not line or ":" not in line: continue
        
        name_part, link_part = line.split(":", 1)
        name = name_part.strip()
        link = re.findall(r'https?://[^\s"]+', link_part)[0]
        
        caption = f"{name}\n\n**Index : {i+1}**"
        prog_msg = await client.send_message(chat_id, f"📥 **Preparing:** `{name}`")

        try:
            if ".m3u8" in link:
                filename = f"{name}.mkv"
                # FFmpeg for high quality conversion
                cmd = f'ffmpeg -i "{link}" -c copy -bsf:a aac_adtstoasc "{filename}" -y -loglevel quiet'
                subprocess.run(cmd, shell=True)
                
                if os.path.exists(filename):
                    start_time = time.time()
                    await client.send_video(
                        chat_id, video=filename, caption=caption,
                        progress=progress_bar, progress_args=(prog_msg, start_time)
                    )
                    os.remove(filename) # Server cleanup

            elif ".pdf" in link:
                filename = f"{name}.pdf"
                r = requests.get(link)
                with open(filename, 'wb') as f_pdf:
                    f_pdf.write(r.content)
                await client.send_document(chat_id, document=filename, caption=caption)
                os.remove(filename)

        except Exception as e:
            await client.send_message(chat_id, f"⚠️ Error at Index {i+1}: {e}")
        
        await prog_msg.delete()

    await client.send_message(chat_id, "🏁 **index out of range.... Task Finished!**")
    if os.path.exists(file_path): os.remove(file_path)

@app.on_message(filters.command("stop"))
async def stop_process(client, message):
    user_data.pop(message.chat.id, None)
    await message.reply_text("🚦 **Stopped** 🚦")

app.run()
