import os, re, asyncio, subprocess, requests, time
from pyrogram import Client, filters

# --- CONFIGURATION ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
AUTH_KEY = "Mohit"

app = Client("UploaderBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user_data = {}

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

    # STEP 1: File Receive karna
    if step == 'AWAIT_FILE' and m.document:
        if m.document.file_name.endswith(".txt"):
            path = await m.download()
            user_data[chat_id].update({'file': path, 'step': 'AWAIT_INDEX'})
            await m.reply_text("✅ File Received!\n\nAb **Index Number** likh kar bhejo (e.g. 1):")
        return

    # STEP 2: Index Receive karna
    if step == 'AWAIT_INDEX' and m.text:
        user_data[chat_id].update({'index': int(m.text), 'step': 'AWAIT_QUALITY'})
        await m.delete() # User ka message hide/delete
        await m.reply_text("Choose Quality (240, 360, 480, 720):")
        return

    # STEP 3: Quality Receive karna
    if step == 'AWAIT_QUALITY' and m.text:
        user_data[chat_id].update({'quality': m.text, 'step': 'AWAIT_KEY'})
        await m.delete()
        await m.reply_text("Enter Security Key:")
        return

    # STEP 4: Key Receive aur Process shuru
    if step == 'AWAIT_KEY' and m.text:
        await m.delete()
        if m.text == AUTH_KEY:
            await m.reply_text("🚀 **Key Verified! Starting Extraction...**")
            user_data[chat_id]['step'] = 'PROCESSING'
            await start_process(c, chat_id)
        else:
            await m.reply_text("❌ Wrong Key! Try again.")
        return

async def start_process(c, cid):
    data = user_data[cid]
    with open(data['file'], "r") as f:
        content = f.read()
    
    # Aapki file ke format ke liye special filter
    pairs = re.findall(r"\]\s*(.+?)\s*:\s*(https?://[^\s]+)", content)
    
    if not pairs:
        await c.send_message(cid, "❌ File format match nahi hua! Check regex.")
        return

    start_idx = data['index'] - 1
    for i in range(start_idx, len(pairs)):
        if user_data.get(cid, {}).get('step') != 'PROCESSING': break
        
        name, link = pairs[i]
        caption = f"{name}\n\n**Index : {i+1}**"
        prog = await c.send_message(cid, f"📥 **Downloading:** {name}")

        try:
            if ".m3u8" in link:
                fn = f"{name}.mkv"
                subprocess.run(f'ffmpeg -i "{link}" -c copy -bsf:a aac_adtstoasc "{fn}" -y -loglevel quiet', shell=True)
                if os.path.exists(fn):
                    await c.send_video(cid, video=fn, caption=caption)
                    os.remove(fn)
            elif ".pdf" in link:
                fn = f"{name}.pdf"
                r = requests.get(link)
                with open(fn, 'wb') as f_pdf: f_pdf.write(r.content)
                await c.send_document(cid, document=fn, caption=caption)
                os.remove(fn)
        except Exception as e:
            await c.send_message(cid, f"Error at {i+1}: {e}")
        
        await prog.delete()
        await asyncio.sleep(2) # Telegram limit se bachne ke liye

    await c.send_message(cid, "🏁 **Index out of range... Finished!**")

@app.on_message(filters.command("stop"))
async def stop(c, m):
    user_data[m.chat.id] = {'step': 'STOPPED'}
    await m.reply_text("🚦 **Stopped** 🚦")

app.run()
