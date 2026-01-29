import os, re, asyncio, subprocess, requests, time, sys
from pyrogram import Client, filters

# --- CONFIGURATION ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
AUTH_KEY = "Mohit"

app = Client("UploaderBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user_data = {}

# Progress Bar for Uploading
async def progress_bar(current, total, reply, start_time):
    try:
        now = time.time()
        diff = now - start_time
        if round(diff % 5.00) == 0 or current == total:
            percentage = current * 100 / total
            speed = current / diff if diff > 0 else 0
            eta = round((total - current) / speed) if speed > 0 else 0
            progress = "[{0}{1}]".format('●' * int(percentage / 10), '○' * (10 - int(percentage / 10)))
            tmp = f"**📤 Uploading...**\n\n**{progress}** {round(percentage, 2)}%\n**⚡ Speed:** {round(speed/1024, 2)} KB/s\n**⏳ ETA:** {eta}s"
            await reply.edit_text(tmp)
    except: pass

@app.on_message(filters.command("start"))
async def start(c, m):
    await m.reply_text("**Welcome!**\nUse /ram to start downloading.\n\nSupport: **🚩Ram Bhakt🚩**")

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
        await m.reply_text("✅ File Received!\n\nAb **Index Number** bhejo:")
        return

    if step == 'AWAIT_INDEX' and m.text:
        user_data[chat_id].update({'index': int(m.text), 'step': 'AWAIT_QUALITY'})
        await m.delete()
        await m.reply_text("Choose Quality (240, 360, 480, 720):")
        return

    if step == 'AWAIT_QUALITY' and m.text:
        user_data[chat_id].update({'quality': m.text, 'step': 'AWAIT_KEY'})
        await m.delete()
        await m.reply_text("Enter Security Key:")
        return

    if step == 'AWAIT_KEY' and m.text:
        await m.delete()
        if m.text == AUTH_KEY:
            await m.reply_text("🚀 **Key Verified! Starting...**")
            user_data[chat_id]['step'] = 'PROCESSING'
            await start_process(c, chat_id)
        else:
            await m.reply_text("❌ Wrong Key!")
        return

async def start_process(c, cid):
    data = user_data[cid]
    with open(data['file'], "r") as f:
        content = f.read()
    
    # Updated Regex for your specific file format
    pairs = re.findall(r"\]\s*(.+?)\s*:\s*(https?://[^\s]+)", content)
    
    if not pairs:
        print("❌ Error: No links found in file!", flush=True)
        await c.send_message(cid, "❌ File format error!")
        return

    start_idx = data['index'] - 1
    for i in range(start_idx, len(pairs)):
        if user_data.get(cid, {}).get('step') != 'PROCESSING': break
        
        name, link = pairs[i]
        name = name.strip()[:60] # Name limit for safety
        caption = f"{name}\n\n**Index : {i+1}**"
        
        print(f"\n▶️ Starting Index {i+1}: {name}", flush=True)
        prog = await c.send_message(cid, f"📥 **Downloading Index {i+1}:**\n`{name}`")

        try:
            if ".m3u8" in link:
                fn = f"{name}.mkv"
                # FFmpeg with visible logs in Colab
                cmd = f'ffmpeg -i "{link}" -c copy -bsf:a aac_adtstoasc "{fn}" -y'
                print(f"DEBUG: Running Command -> {cmd}", flush=True)
                subprocess.run(cmd, shell=True)
                
                if os.path.exists(fn):
                    print(f"✅ Downloaded. Now Uploading: {fn}", flush=True)
                    start_time = time.time()
                    await c.send_video(cid, video=fn, caption=caption, progress=progress_bar, progress_args=(prog, start_time))
                    os.remove(fn)
                    print(f"🗑️ Server Cleaned: {fn}", flush=True)

            elif ".pdf" in link:
                fn = f"{name}.pdf"
                r = requests.get(link)
                with open(fn, 'wb') as f_pdf: f_pdf.write(r.content)
                await c.send_document(cid, document=fn, caption=caption)
                os.remove(fn)
                print(f"✅ PDF Sent: {name}", flush=True)

        except Exception as e:
            print(f"⚠️ ERROR at Index {i+1}: {str(e)}", flush=True)
            await c.send_message(cid, f"Error at {i+1}: {e}")
        
        await prog.delete()
        await asyncio.sleep(2)

    await c.send_message(cid, "🏁 **Task Finished! Index Out of Range.**")

@app.on_message(filters.command("stop"))
async def stop(c, m):
    user_data[m.chat.id] = {'step': 'STOPPED'}
    await m.reply_text("🚦 **Stopped** 🚦")

print("🤖 Bot is Online and Logging is Enabled!", flush=True)
app.run()
