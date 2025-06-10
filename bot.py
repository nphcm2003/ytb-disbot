import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

keep_alive()  # ⚡ Giữ bot luôn chạy bằng web server

ydl_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'default_search': 'ytsearch'
}

ffmpeg_opts = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

music_queue = asyncio.Queue()
is_playing = False

async def search_youtube(query):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        if "entries" in info:
            return [{'url': entry['url'], 'title': entry.get('title', 'Không rõ')} for entry in info['entries']]
        else:
            return [{'url': info['url'], 'title': info.get('title', 'Không rõ')}]

async def play_next(ctx):
    global is_playing
    if music_queue.empty():
        is_playing = False
        await ctx.send("✅ Hết bài trong hàng đợi.")
        return
    is_playing = True
    song = await music_queue.get()
    url = song['url']
    title = song['title']
    requester = song['requester']
    ctx = song['ctx']

    vc = ctx.voice_client
    if not vc:
        await ctx.author.voice.channel.connect()
        vc = ctx.voice_client

    def after_playing(e):
        asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

    vc.play(
        discord.FFmpegPCMAudio(url, executable="./ffmpeg/ffmpeg", **ffmpeg_opts),  # ⚠️ ffmpeg path Glitch
        after=after_playing
    )
    await ctx.send(f"▶️ Đang phát: **{title}** | Yêu cầu bởi: <@{requester}>")

@bot.event
async def on_ready():
    print(f"✅ Bot đăng nhập: {bot.user}")

@bot.command()
async def play(ctx, *, search: str):
    if not ctx.author.voice:
        await ctx.send("❌ Bạn cần vào kênh thoại trước.")
        return
    infos = await search_youtube(search)
    for info in infos:
        await music_queue.put({'url': info['url'], 'title': info['title'], 'requester': ctx.author.id, 'ctx': ctx})
    await ctx.send(f"✅ Đã thêm {len(infos)} bài vào hàng đợi.")
    global is_playing
    if not is_playing:
        await play_next(ctx)

@bot.command()
async def skip(ctx):
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await ctx.send("⏭️ Đã bỏ qua bài hát.")

@bot.command()
async def queue(ctx):
    if music_queue.empty():
        await ctx.send("📭 Hàng đợi đang trống.")
    else:
        items = list(music_queue._queue)
        msg = "\n".join([f"{i+1}. {item['title']}" for i, item in enumerate(items)])
        await ctx.send(f"📃 Hàng đợi:\n{msg}")

@bot.command()
async def clear(ctx):
    while not music_queue.empty():
        music_queue.get_nowait()
    await ctx.send("🧹 Đã xóa hàng đợi.")

@bot.command()
async def pause(ctx):
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await ctx.send("⏸️ Tạm dừng phát nhạc.")

@bot.command()
async def resume(ctx):
    vc = ctx.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await ctx.send("▶️ Tiếp tục phát nhạc.")

@bot.command()
async def stop(ctx):
    vc = ctx.voice_client
    if vc:
        await vc.disconnect()
        await ctx.send("⏹️ Đã rời khỏi kênh thoại.")
        global is_playing
        is_playing = False
        while not music_queue.empty():
            music_queue.get_nowait()

bot.run(os.getenv("TOKEN"))
