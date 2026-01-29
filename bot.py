import os, re, asyncio, subprocess, requests, time
from pyrogram import Client, filters

# --- CONFIGURATION ---
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
AUTH_KEY = "Mohit"

app = Client("UploaderBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user_data = {}

async def progress_bar(current, total, reply, start_time):
    try:
        now = time.time()
        diff = now - start_time
        if round(diff % 5.00) == 0 or current == total:
            percentage = current * 100 / total
            speed = current / diff if diff > 0 else 0
            progress = "[{0}{1}]".format('●' * int(percentage / 10), '○' * (10 - int(percentage / 10)))
            await reply.edit_text(f"🚀 **Uploading...**\n\n**{progress}** {round(percentage, 2)}%\n**⚡ Speed:** {round(speed/1024, 2)} KB/s")
    except: pass

@app.on_message(filters.command("start"))
async def start(c, m):
    await m.reply_text("**Welcome to uploader bot**\nUse /ram to start downloading\nUse /stop to stop downloading\n\n**Let's start** 🚩")

@app.on_message(filters.command("stop"))
async def stop(c, m):
    user_data[m.chat.id] = {'step': 'STOPPED'}
    await m.reply_text("🚦 **Stopped!**")

@app.on_message(filters.command("ram"))
async def ram(c, m):
    user_data[m.chat.id] = {'step': 'AWAIT_FILE'}
    await m.reply_text("Please upload your **.txt** file now.")

@app.on_message(filters.document | filters.text)
async def handle_steps(c, m):
    chat_id = m.chat.id
    if chat_id not in user_data: return
    step = user_data[chat_id].get('step')

    if step == 'AWAIT_FILE' and m.document:
        path = await m.download()
        user_data[chat_id].update({'file': path, 'step': 'AWAIT_INDEX'})
        await m.reply_text("✅ File Received! Enter **Index Number**:")
        return

    if step == 'AWAIT_INDEX' and m.text:
        user_data[chat_id].update({'index': int(m.text), 'step': 'AWAIT_QUALITY'})
        await m.reply_text("Enter Quality (Just number: 240, 360, 480, 720):")
        return

    if step == 'AWAIT_QUALITY' and m.text:
        # CLEANING QUALITY: Sirf number nikalne ke liye
        quality_num = re.sub("[^0-9]", "", m.text)
        if not quality_num: quality_num = "360" # Default
        user_data[chat_id].update({'quality': quality_num, 'step': 'AWAIT_KEY'})
        await m.reply_text(f"✅ Quality set to {quality_num}p. Now Enter **Security Key**:")
        return

    if step == 'AWAIT_KEY' and m.text:
        if m.text == AUTH_KEY:
            user_data[chat_id]['step'] = 'PROCESSING'
            await m.reply_text("🚀 **Key Verified! Starting...**")
            await start_process(c, chat_id)
        else:
            await m.reply_text("❌ Wrong Key!")

async def start_process(c, cid):
    data = user_data[cid]
    quality = data['quality']
    with open(data['file'], "r") as f:
        content = f.read()
    
    pairs = re.findall(r"\]\s*(.+?)\s*:\s*(https?://[^\s]+)", content)
    start_idx = data['index'] - 1

    for i in range(start_idx, len(pairs)):
        if user_data.get(cid, {}).get('step') == 'STOPPED': break
        name, link = pairs[i]
        name = name.strip().replace("/", "-")[:50]
        prog = await c.send_message(cid, f"📥 **Downloading Index {i+1}:**\n`{name}`")

        try:
            if ".m3u8" in link:
                fn = f"{name}.mkv"
                # Added 'aria2c' specifically to the downloader arg to avoid the Warning
                cmd = f'yt-dlp -f "bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best" "{link}" -o "{fn}" --no-check-certificate --downloader aria2c --downloader-args "aria2c:-x 16 -s 16 -k 1M"'
                subprocess.run(cmd, shell=True)

                if os.path.exists(fn):
                    await prog.edit(f"📤 **Uploading Index {i+1}...**")
                    await c.send_video(cid, video=fn, caption=f"{name}\nQuality: {quality}p", progress=progress_bar, progress_args=(prog, time.time()))
                    os.remove(fn)
            elif ".pdf" in link:
                fn = f"{name}.pdf"
                r = requests.get(link)
                with open(fn, 'wb') as f: f.write(r.content)
                await c.send_document(cid, document=fn, caption=name)
                os.remove(fn)
        except Exception as e:
            await c.send_message(cid, f"Error at {i+1}: {e}")
        
        await prog.delete()
        await asyncio.sleep(1)
    await c.send_message(cid, "🏁 **Task Finished!**")

app.run()
