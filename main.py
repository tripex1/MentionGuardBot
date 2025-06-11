from flask import Flask
import asyncio
import os
import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta
from threading import Thread

# === Flask Server ===
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

# === Discord Bot Setup ===
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

BLOCKED_NAMES = ["tripex", "ma1eja", "owner"]
TARGET_ROLE_NAME = "Members"
TIMEOUT_SECONDS = 1800
TICKET_CATEGORY_ID = 1337877093735731291
GUILD_ID = 688729972109475843  # Your actual server ID

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if DISCORD_BOT_TOKEN is None:
    raise ValueError("No bot token found! Set DISCORD_BOT_TOKEN env variable.")

@bot.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"✅ Bot ready: {bot.user} ({bot.user.id})")
    print("✅ Slash commands synced.")

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
                await member.timeout(
                    discord.utils.utcnow() + timedelta(seconds=TIMEOUT_SECONDS),
                    reason="Mentioned protected user or role"
                )
                await message.delete()
                await message.channel.send(
                    f"{member.display_name} has been timed out for 30 minutes for mentioning a protected user or role."
                )
                print(f"⛔ Timed out {member.display_name}")
            except Exception as e:
                print(f"❌ Failed to timeout user: {e}")

    await bot.process_commands(message)

@bot.event
async def on_guild_channel_create(channel):
    if isinstance(channel, discord.TextChannel) and channel.category_id == TICKET_CATEGORY_ID:
        try:
            await asyncio.sleep(2)
            await channel.send("Hello! Please tell us your problem here. Tripex will reply as soon as he can.")
            print(f"📩 Sent ticket greeting in {channel.name}")
        except Exception as e:
            print(f"❌ Failed to send ticket greeting: {e}")

# === Slash Command: /clean ===
@tree.command(name="clean", description="Delete messages by user or user ID", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(
    user="User to delete messages from (mentionable, optional)",
    user_id="User ID to delete messages from (used if user is not selected)",
    amount="Number of messages to scan (default 100)"
)
async def clean(
    interaction: discord.Interaction,
    user: discord.User | None = None,
    user_id: str | None = None,
    amount: int = 100
):
    if not interaction.channel.permissions_for(interaction.user).manage_messages:
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return

    if not user and not user_id:
        await interaction.response.send_message("❌ You must provide either a user or a user ID.", ephemeral=True)
        return

    target_id = user.id if user else user_id

    try:
        deleted = await interaction.channel.purge(
            limit=amount,
            check=lambda m: str(m.author.id) == str(target_id)
        )
        await interaction.response.send_message(
            f"🧹 Deleted {len(deleted)} messages from user ID `{target_id}`.",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to delete messages: {e}", ephemeral=True)


@tree.command(name="clearslash", description="Clear global slash commands", guild=discord.Object(id=688729972109475843))
async def clearslash(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You must be an admin to use this.", ephemeral=True)
        return

    await bot.tree.clear_commands(guild=None)  # Clear global commands
    await bot.tree.sync()
    await interaction.response.send_message("🧹 Global slash commands cleared!", ephemeral=True)


# === Start ===
keep_alive()
print("🟡 Starting bot...")
bot.run(DISCORD_BOT_TOKEN)
