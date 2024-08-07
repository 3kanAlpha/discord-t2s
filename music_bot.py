from dotenv import load_dotenv
import os, asyncio, queue

import discord
from discord.ext import commands

import yt_dlp

load_dotenv()

ydl_ops = {
  'format': 'bestaudio/best',
  'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
  'restrictfilenames': True,
  'noplaylist': True,
  'nocheckcertificate': True,
  'ignoreerrors': False,
  'logtostderr': False,
  'quiet': True,
  'no_warnings': True,
  'default_search': 'auto',
}

ffmpeg_options = {
  'options': '-vn',
}

ydl = yt_dlp.YoutubeDL(ydl_ops)

class YTDLSource(discord.PCMVolumeTransformer):
  def __init__(self, source, *, data, volume=0.5):
    super().__init__(source, volume)

    self.data = data

    self.title = data.get('title')
    self.url = data.get('url')

  @classmethod
  async def from_url(cls, url, *, loop=None, stream=False):
      loop = loop or asyncio.get_event_loop()
      data = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=not stream))

      if 'entries' in data:
          # take first item from a playlist
          data = data['entries'][0]

      filename = data['url'] if stream else ydl.prepare_filename(data)
      return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class Music(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.playlist_queue = queue.Queue()

  @commands.command()
  async def join(self, ctx):
    """Joins a voice channel"""
    author = ctx.author
    
    if author.voice is not None:
      await author.voice.channel.connect()
      await ctx.send('\N{Speaker with Three Sound Waves} Connected to a voice channnel.')

  @commands.command()
  async def play(self, ctx, *, query):
    """Plays a file from the local filesystem"""

    source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(query))
    ctx.voice_client.play(source, after=lambda e: print(f'Player error: {e}') if e else None)

    await ctx.send(f'Now playing: {query}')

  @commands.command()
  async def yt(self, ctx, *, url):
    """Plays from a url (almost anything youtube_dl supports)"""

    async with ctx.typing():
      player = await YTDLSource.from_url(url, loop=self.bot.loop)
      ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)

    await ctx.send(f'Now playing: {player.title}')

  @commands.command()
  async def stream(self, ctx, *, url):
    """Streams from a url (same as yt, but doesn't predownload)"""

    async with ctx.typing():
      player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
      ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)

    await ctx.send(f'Now playing: {player.title}')

  @commands.command()
  async def volume(self, ctx, volume: int):
    """Changes the player's volume"""

    if ctx.voice_client is None:
      return await ctx.send("Not connected to a voice channel.")

    ctx.voice_client.source.volume = volume / 100
    await ctx.send(f"Changed volume to {volume}%")

  @commands.command()
  async def stop(self, ctx):
    """Stops and disconnects the bot from voice"""

    await ctx.voice_client.disconnect()
  
  @commands.command()
  async def q(self, ctx):
    message = ctx.message.content
    u = message[3:]
    self.playlist_queue.put(u)
  
  @commands.command()
  async def skip(self, ctx):
    if ctx.voice_client:
      ctx.voice_client.stop()

  @play.before_invoke
  @yt.before_invoke
  @stream.before_invoke
  async def ensure_voice(self, ctx):
    if ctx.voice_client is None:
      if ctx.author.voice:
        await ctx.author.voice.channel.connect()
      else:
        await ctx.send("You are not connected to a voice channel.")
        raise commands.CommandError("Author not connected to a voice channel.")
    elif ctx.voice_client.is_playing():
      ctx.voice_client.stop()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
  command_prefix="!",
  description='Relatively simple music bot example',
  intents=intents,
)

@bot.event
async def on_ready():
  print(f'Logged in as {bot.user} (ID: {bot.user.id})')
  print('------')
    
async def main():
  async with bot:
    await bot.add_cog(Music(bot))
    await bot.start(os.environ["BOT_TOKEN"])

if __name__ == '__main__':
  asyncio.run(main())
