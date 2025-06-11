from flask import Flask
import asyncio
import os
import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta
from threading import Thread

# === Flask server ===
app = Flask(__name__)

@app.route('/')
def home():
    return "MentionGuardBot is running!"

def start_server():
    port = int(os.environ.get("PORT", 3000))
    print(f"🚀 Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    thread = Thread(target=start_server)
    thread.start()

# === Discord Bot ===
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

BLOCKED_NAMES = ["tripex", "ma1eja", "owner"]
TARGET_ROLE_NAME = "Members"
TIMEOUT_SECONDS = 1800

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if DISCORD_BOT_TOKEN is None:
    raise ValueError("No bot token found! Set DISCORD_BOT_TOKEN env variable.")

@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot is ready. Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    triggered = False
    for mention in message.mentions:
        if mention.name.lower() in BLOCKED_NAMES:
            triggered = True

    for role in message.role_mentions:
        if role.name.lower() in BLOCKED_NAMES:
            triggered = True

    if triggered:
        member = message.author
        has_target_role = any(role.name == TARGET_ROLE_NAME for role in member.roles)

        if has_target_role:
            try:
                await member.timeout(discord.utils.utcnow() + timedelta(seconds=TIMEOUT_SECONDS),
                                     reason="Mentioned protected user or role")
                await message.delete()
                await message.channel.send(
                    f"{member.display_name} has been timed out for 30 minutes for mentioning a protected user or role."
                )
                print(f"⛔ Timed out {member.display_name}")
            except Exception as e:
                print(f"❌ Failed to timeout user: {e}")

    await bot.process_commands(message)

TICKET_CATEGORY_ID = 1337877093735731291

@bot.event
async def on_guild_channel_create(channel):
    if isinstance(channel, discord.TextChannel):
        if channel.category_id == TICKET_CATEGORY_ID:
            try:
                await asyncio.sleep(2)
                await channel.send("Hello! Please tell us your problem here. Tripex will reply as soon as he can.")
                print(f"📩 Sent ticket greeting in {channel.name}")
            except Exception as e:
                print(f"❌ Failed to send ticket greeting: {e}")

# === /clean Slash Command ===
@tree.command(name="clean", description="Delete recent messages, optionally from a specific user or user ID.")
@app_commands.describe(
    amount="How many messages to delete (max 100)",
    user="User to delete messages from (optional)",
    user_id="User ID to delete messages from (optional, for users who left)"
)
async def clean(interaction: discord.Interaction, amount: int, user: discord.User = None, user_id: str = None):
    await interaction.response.defer(thinking=True, ephemeral=True)

    if amount < 1 or amount > 100:
        await interaction.followup.send("❌ Amount must be between 1 and 100.")
        return

    def check(msg):
        if user:
            return msg.author.id == user.id
        if user_id:
            return str(msg.author.id) == user_id
        return True

    deleted = await interaction.channel.purge(limit=amount, check=check)
    await interaction.followup.send(f"✅ Deleted {len(deleted)} messages.", ephemeral=True)

# === Start ===
keep_alive()
print("🟡 Starting bot...")
bot.run(DISCORD_BOT_TOKEN)
