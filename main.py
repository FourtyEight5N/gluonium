import os
import datetime
import threading
from flask import Flask
import discord
from discord.ext import commands

app = Flask('')
@app.route('/')
def home():
    return "bot alive = yes alive"

def run_webserver():
    # Render automatically assigns a PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_webserver)
    t.start()
# --------------------------------------

intents = discord.Intents.default()
intents.members = True          
intents.message_content = True  

bot = commands.Bot(command_prefix="%", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, delete_days: int = 1, *, reason=None):
    seconds = delete_days * 86400
    await member.ban(delete_message_seconds=seconds, reason=reason)
    await ctx.send(f"SUCCESS! Banned {member.mention}.")

if __name__ == "__main__":
    keep_alive()
    
    # Start the Discord Bot
    TOKEN = os.environ.get("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("ERROR: 'DISCORD_TOKEN' environment variable missing.")


# 1. Setup bot with required privileged intents
intents = discord.Intents.default()
intents.members = True          # Required to manage members, nicknames, and timeouts
intents.message_content = True  # Required to read text commands

bot = commands.Bot(command_prefix="%", intents=intents)
bot.remove_command(help)

@bot.event
async def on_ready():
    print(f"logged or somethingged in successfully as {bot.user.name} (ID: {bot.user.id})")
    print("bot online = yes online")

# 2. BAN COMMAND (With delete messages history)
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, delete_days: int = 1, *, reason=None):
    """Bans a member and deletes their message history for X days."""
    # 86400 seconds = 1 day
    seconds = delete_days * 86400
    await member.ban(delete_message_seconds=seconds, reason=reason)
    await ctx.send(f"SUCCESS! {member.mention} has been banned. Reason: {reason}")

# 3. KICK COMMAND
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    """Kicks a member from the server."""
    await member.kick(reason=reason)
    await ctx.send(f"SUCCESS! {member.mention} has been kicked. Reason: {reason}")

# 4. TIMEOUT COMMAND
@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, minutes: int, *, reason=None):
    """Times out someone for the specified amount of minutes."""
    duration = datetime.timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    await ctx.send(f"SUCCESS! {member.mention} has been timed out for {minutes} minutes. Reason: {reason}")

# 5. CHANGE NICKNAME COMMAND
@bot.command()
@commands.has_permissions(manage_nicknames=True)
async def nickname(ctx, member: discord.Member, *, new_name=None):
    """Changes or resets a member's nickname."""
    await member.edit(nick=new_name)
    if new_name:
        await ctx.send(f"SUCCESS! Changed nickname for {member.mention} to {new_name}.")
    else:
        await ctx.send(f"SUCCESS! Reset the nickname for {member.mention}.")

# 6. ADD ROLE COMMAND
@bot.command()
@commands.has_permissions(manage_roles=True)
async def addrole(ctx, member: discord.Member, role: discord.Role):
    """Adds a role to a member."""
    await member.add_roles(role)
    await ctx.send(f"SUCCESS! Added the role **{role.name}** to {member.mention}.")

# 7. REMOVE ROLE COMMAND
@bot.command()
@commands.has_permissions(manage_roles=True)
async def removerole(ctx, member: discord.Member, role: discord.Role):
    """Removes a role from someone."""
    await member.remove_roles(role)
    await ctx.send(f"SUCCESS! Removed the role **{role.name}** from {member.mention}.")

# 8. HELP COMMAND
@bot.command()
async def help(ctx):
    """Types the command list ;)"""
    await ctx.send(f" **Gluonium Command List**\n\nCommand prefix is **%**.\n!ban [member] [delete days] [reason]: Bans a member!")

# Error handling to catch missing permissions safely
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("**Perm Error:** You don't have the required permission(s).")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("**Arg Error:** The command you typed is missing (an) argument(s).")
    else:
        print(f"Error: {error}")

TOKEN = os.environ.get("DISCORD_TOKEN")

if TOKEN:
    bot.run(TOKEN)
else:
    print("Envvar Error: 'DISCORD_TOKEN' environment variable not found. Please add it in Render!")
