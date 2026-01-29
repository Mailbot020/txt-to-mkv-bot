import os, re, asyncio, subprocess, requests, time
from pyrogram import Client, filters

# --- CONFIGURATION ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
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
            await reply.edit_text(f"**📤 Uploading...**\n\n**{progress}** {round(percentage, 2)}%")
    except: pass

@app.on_message(filters.command("start"))
async def start(c, m):
    await m.reply_text("Bot is Active! Use /ram")

@app.on_message(filters.command("ram"))
async def ram(c, m):
    user_data[m.chat.id] = {'step': 'AWAIT_FILE'}
    await m.reply_text("Upload .txt file")

@app.on_message(filters.document | filters.text)
async def handle_steps(c, m):
    chat_id = m.chat.id
    if chat_id not in user_data: return
    step = user_data[chat_id].get('step')

    if step == 'AWAIT_FILE' and m.document:
        path = await m.download()
        user_data[chat_id].update({'file': path, 'step': 'AWAIT_INDEX'})
        await m.reply_text("✅ File OK! Enter Index:")
        return

    if step == 'AWAIT_INDEX' and m.text:
        user_data[chat_id].update({'index': int(m.text), 'step': 'AWAIT_QUALITY'})
        await m.reply_text("Enter Quality (e.g. 360, 480, 720):")
        return

    if step == 'AWAIT_QUALITY' and m.text:
        user_data[chat_id].update({'quality': m.text, 'step': 'AWAIT_KEY'})
        await m.reply_text("Enter Key:")
        return

    if step == 'AWAIT_KEY' and m.text:
        if m.text == AUTH_KEY:
            user_data[chat_id]['step'] = 'PROCESSING'
            await start_process(c, chat_id)
        else:
            await m.reply_text("Wrong Key!")

async def start_process(c, cid):
    data = user_data[cid]
    quality = data['quality']
    with open(data['file'], "r") as f:
        content = f.read()
    
    pairs = re.findall(r"\]\s*(.+?)\s*:\s*(https?://[^\s]+)", content)
    start_idx = data['index'] - 1

    for i in range(start_idx, len(pairs)):
        if user_data.get(cid, {}).get('step') != 'PROCESSING': break
        name, link = pairs[i]
        name = name.strip().replace("/", "-") # Safety for filename
        prog = await c.send_message(cid, f"📥 **Downloading {quality}p:**\n`{name}`")

        try:
            if ".m3u8" in link:
                fn = f"{name}.mkv"
                # Best Quality Command using yt-dlp inside FFmpeg
                # Isse 0.00 wali problem nahi aayegi
                cmd = f'yt-dlp -f "bestvideo[height<={quality}]+bestaudio/best[height<={quality}]" "{link}" -o "{fn}" --no-check-certificate'
                
                print(f"Running: {cmd}", flush=True)
                os.system(cmd)
                
                if os.path.exists(fn) and os.path.getsize(fn) > 1000:
                    await c.send_video(cid, video=fn, caption=f"{name}\nQuality: {quality}p", progress=progress_bar, progress_args=(prog, time.time()))
                    os.remove(fn)
                else:
                    await c.send_message(cid, f"❌ Failed to download: {name} (0 byte file)")

            elif ".pdf" in link:
                fn = f"{name}.pdf"
                r = requests.get(link)
                with open(fn, 'wb') as f: f.write(r.content)
                await c.send_document(cid, document=fn)
                os.remove(fn)

        except Exception as e:
            await c.send_message(cid, f"Error at {i+1}: {e}")
        
        await prog.delete()
        await asyncio.sleep(2)

app.run()
            
