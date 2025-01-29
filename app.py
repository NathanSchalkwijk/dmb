import discord
from discord.ext import commands
import yt_dlp
import asyncio
from dotenv import load_dotenv
import os
import time

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.voice_states = True
intents.message_content = True

bot = commands.Bot(command_prefix="m!", intents=intents)

music_queues = {}

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot is Running as {bot.user} and slash commands are synced.")

async def join_voice_channel(interaction: discord.Interaction):
    if interaction.user.voice:
        channel = interaction.user.voice.channel
        if not interaction.guild.voice_client:
            await channel.connect()

@bot.tree.command(name="join", description="Make the bot join your voice channel.")
async def join(interaction: discord.Interaction):
    asyncio.create_task(join_voice_channel(interaction))
    await interaction.response.send_message("Joining your voice channel...")

@bot.tree.command(name="leave", description="Make the bot leave the voice channel.")
async def leave(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        if interaction.guild.id in music_queues:
            music_queues[interaction.guild.id] = []
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("Disconnected from the voice channel and cleared the queue.")
    else:
        await interaction.response.send_message("I'm not in a voice channel.", ephemeral=True)

async def play_next(guild):
    if guild.id in music_queues and music_queues[guild.id]:
        next_song = music_queues[guild.id].pop(0)
        await play_song(guild, next_song)

async def play_song(guild, song):
    try:
        url = song["url"]
        title = song["title"]
        interaction = song["interaction"]

        interaction.guild.voice_client.play(
            discord.FFmpegPCMAudio(url, **song["ffmpeg_options"]),
            after=lambda e: asyncio.run_coroutine_threadsafe(play_next(guild), bot.loop)
        )
        interaction.guild.voice_client.source = discord.PCMVolumeTransformer(interaction.guild.voice_client.source)
        interaction.guild.voice_client.source.volume = 0.5

        await interaction.followup.send(f"Now playing: {title}")
    except Exception as e:
        await interaction.followup.send("An error occurred while trying to play the audio.")
        print(f"Error: {e}")

@bot.tree.command(name="play", description="Search and play a song.")
async def play(interaction: discord.Interaction, search: str):
    await interaction.response.send_message("Downloading the song...")

    if not interaction.guild.voice_client:
        await join_voice_channel(interaction)
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
    if interaction.guild.voice_client.is_playing():
        await interaction.followup.send("A song is already playing. Your request has been added to the queue.")
    
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(f"ytsearch:{search}", download=False)['entries'][0]
            url = info['url']
            title = info['title']
    except Exception as e:
        await interaction.followup.send("Could not find the video.")
        return

    song = {
        "url": url,
        "title": title,
        "interaction": interaction,
        "ffmpeg_options": FFMPEG_OPTIONS
    }

    if interaction.guild.id not in music_queues:
        music_queues[interaction.guild.id] = []
    music_queues[interaction.guild.id].append(song)

    queue_number = len(music_queues[interaction.guild.id])
    await interaction.followup.send(f"Song added to queue as #{queue_number}.")

    if not interaction.guild.voice_client.is_playing():
        asyncio.create_task(play_next(interaction.guild))

@bot.tree.command(name="stop", description="Stop the music.")
async def stop(interaction: discord.Interaction):
    if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
        if interaction.guild.id in music_queues:
            music_queues[interaction.guild.id] = []
        interaction.guild.voice_client.stop()
        await interaction.response.send_message("Music stopped.")
    else:
        await interaction.response.send_message("No music is playing.", ephemeral=True)

@bot.tree.command(name="skip", description="Skip the current song.")
async def skip(interaction: discord.Interaction):
    if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.stop()
        await interaction.response.send_message("Skipped current song.")
    else:
        await interaction.response.send_message("No music is playing.", ephemeral=True)
        
@bot.tree.command(name="volume", description="Set the volume of the music.")
async def volume(interaction: discord.Interaction, level: int):
    if level < 0 or level > 100:
        await interaction.response.send_message("Please provide a volume level between 0 and 100.", ephemeral=True)
        return

    if interaction.guild.voice_client:
        voice_client = interaction.guild.voice_client
        voice_client.source.volume = level / 150
        await interaction.response.send_message(f"Volume set to {level}%.", ephemeral=False)
    else:
        await interaction.response.send_message("I'm not in a voice channel.", ephemeral=True)   

@bot.tree.command(name="help", description="Show help information for bot commands.")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Music Bot Help",
        description="Here's a list of commands!",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="🔊 /join",
        value="Make the bot join your voice channel.",
        inline=False
    )
    embed.add_field(
        name="🔊 /leave",
        value="Make the bot leave the voice channel.",
        inline=False
    )
    embed.add_field(
        name="🎶 /play <search>",
        value="Search and play a song by name.",
        inline=False
    )
    embed.add_field(
        name="⏸️ /stop",
        value="Stop the music and clear the queue.",
        inline=False
    )
    embed.add_field(
        name="⏭️ /skip",
        value="Skip the current song.",
        inline=False
    )
    embed.add_field(
        name="🔊 /volume",
        value="Set the volume.",
        inline=False
    )
    
    embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.avatar.url)

    await interaction.response.send_message(embed=embed)

bot.run(BOT_TOKEN)
