import discord
from discord.ext import commands
import yt_dlp
import asyncio
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.voice_states = True
intents.message_content = True

# Bot setup
bot = commands.Bot(command_prefix="m!", intents=intents)

# Join command
@bot.command(name="join")
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
    else:
        await ctx.send("You need to be in a voice channel to use this command.")

# Leave command
@bot.command(name="leave")
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    else:
        await ctx.send("I'm not in a voice channel.")

# Play command
@bot.command(name="play")
async def play(ctx, *, search: str):
    if not ctx.voice_client:
        await ctx.invoke(join)

    YDL_OPTIONS = {
        'format': 'bestaudio/best',
        'noplaylist': 'True',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    }
    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch:{search}", download=False)['entries'][0]
        except Exception as e:
            await ctx.send("Could not find the video.")
            return

    url = info['url']

    ctx.voice_client.stop()
    ctx.voice_client.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS), after=lambda e: print(f"Finished playing: {e}"))
    ctx.voice_client.source = discord.PCMVolumeTransformer(ctx.voice_client.source)
    ctx.voice_client.source.volume = 0.5  # Adjust volume to prevent distortion
    await ctx.send(f"Now playing: {info['title']}")

# Stop command
@bot.command(name="stop")
async def stop(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Music stopped.")
    else:
        await ctx.send("No music is playing.")

# Run the bot
bot.run(BOT_TOKEN)
