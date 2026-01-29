import os
import re
import asyncio
import subprocess
import requests
import time
from pyrogram import Client, filters
from pyrogram.types import ForceReply

# --- CONFIGURATION (Colab Input se lega) ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
AUTH_KEY = "Mohit"

app = Client("UploaderBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user_data = {}

# Progress Bar for Upload Monitoring
async def progress_bar(current, total, reply, start_time):
    try:
        now = time.time()
        diff = now - start_time
        if round(diff % 4.00) == 0 or current == total:
            percentage = current * 100 / total
            speed = current / diff if diff > 0 else 0
            eta = round((total - current) / speed) if speed > 0 else 0
            progress = "[{0}{1}]".format('●' * int(percentage / 10), '○' * (10 - int(percentage / 10)))
            tmp = f"**📤 Uploading...**\n\n**{progress}** {round(percentage, 2)}%\n**⚡ Speed:** {round(speed/1024, 2)} KB/s\n**⏳ ETA:** {eta}s"
            await reply.edit_text(tmp)
    except: pass

@app.on_message(filters.command("start"))
async def start(c, m):
    await m.reply_text("Welcome to uploader bot\nUse /ram to start\nFor help contact **🚩Ram Bhakt🚩**")

@app.on_message(filters.command("ram"))
async def ram(c, m):
    await m.reply_text("Please upload your **.txt** file")

@app.on_message(filters.document)
async def doc(c, m):
    if m.document.file_name.endswith(".txt"):
        path = await m.download()
        user_data[m.chat.id] = {"file": path}
        await m.reply_text("✅ File Received!\nKaunse **index number** se start karna hai?", reply_markup=ForceReply(True))

@app.on_message(filters.reply)
async def replies(c, m):
    cid = m.chat.id
    if cid not in user_data: return
    
    if "index number" in m.reply_to_message.text:
        user_data[cid]["index"] = int(m.text)
        await m.delete()
        await m.reply_text("Choose quality: 240, 360, 480, 720", reply_markup=ForceReply(True))
        
    elif "quality" in m.reply_to_message.text:
        user_data[cid]["quality"] = m.text
        await m.delete()
        await m.reply_text("Enter security key", reply_markup=ForceReply(True))
        
    elif "security key" in m.reply_to_message.text:
        await m.delete()
        if m.text == AUTH_KEY:
            await m.reply_text("🚀 Process Started...")
            await process(c, cid)
        else:
            await m.reply_text("❌ Wrong Key!")

async def process(c, cid):
    data = user_data.get(cid)
    with open(data["file"], "r") as f:
        content = f.read()
    
    # [span_1](start_span)Advanced Regex to find Name and Link in your specific format[span_1](end_span)
    # Format: [Class Name] : http://link
    pairs = re.findall(r"(.+?)\s*:\s*(https?://[^\s]+)", content)
    
    start_idx = data["index"] - 1
    
    for i in range(start_idx, len(pairs)):
        if cid not in user_data: break
        
        name, link = pairs[i]
        name = name.strip()
        link = link.strip()
        caption = f"{name}\n\n**Index : {i+1}**"
        
        prog = await c.send_message(cid, f"📥 **Processing {i+1}:**\n`{name}`")

        try:
            if ".m3u8" in link:
                fn = f"{name}.mkv"
                # [span_2](start_span)Using FFmpeg to convert m3u8 to mkv[span_2](end_span)
                cmd = f'ffmpeg -i "{link}" -c copy -bsf:a aac_adtstoasc "{fn}" -y -loglevel quiet'
                subprocess.run(cmd, shell=True)
                if os.path.exists(fn):
                    await c.send_video(cid, video=fn, caption=caption, progress=progress_bar, progress_args=(prog, time.time()))
                    os.remove(fn) # Server Cleanup
            elif ".pdf" in link:
                fn = f"{name}.pdf"
                r = requests.get(link)
                with open(fn, 'wb') as f_pdf: f_pdf.write(r.content)
                await c.send_document(cid, document=fn, caption=caption)
                os.remove(fn)
        except Exception as e:
            await c.send_message(cid, f"⚠️ Error Index {i+1}: {e}")
        
        await prog.delete()

    await c.send_message(cid, "🏁 **index out of range.... Task Finished!**")
    if os.path.exists(data["file"]): os.remove(data["file"])

@app.on_message(filters.command("stop"))
async def stop(c, m):
    user_data.pop(m.chat.id, None)
    await m.reply_text("🚦 **Stopped** 🚦")

app.run()
