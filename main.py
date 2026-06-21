import os
import datetime
import threading
from flask import Flask
import discord
from discord.ext import commands
app = Flask(__name__)

@app.route("/")
def home():
    return "bot alive = yes alive"
def run_webserver():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
def keep_alive():
    threading.Thread(target=run_webserver, daemon=True).start()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="%", intents=intents)
bot.remove_command("help")

def can_moderate(author, target):
    return author.top_role > target.top_role

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Gluonium online = yes online")

# ----------------------------
# BAN
# ----------------------------

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, delete_days: int = 1, *, reason="No reason provided"):

    if not can_moderate(ctx.author, member):
        return await ctx.send(f"Perm Error: You can't use this command on {member.mention} due to your role.")

    delete_days = max(0, min(delete_days, 14))
    seconds = delete_days * 86400

    try:
        await member.ban(
            delete_message_seconds=seconds,
            reason=reason
        )

        await ctx.send(
            f"SUCCESS! {member.mention} has been banned.\n"
            f"Delete Days: {delete_days}\n"
            f"Reason: {reason}"
        )

    except discord.Forbidden:
        await ctx.send("I don't have permission to ban that member.")

# ----------------------------
# KICK
# ----------------------------

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):

    if not can_moderate(ctx.author, member):
        return await ctx.send(f"Perm Error: You can't use this command on {member.mention} due to your role.")

    try:
        await member.kick(reason=reason)
        await ctx.send(
            f"SUCCESS! {member.mention} has been kicked.\n"
            f"Reason: {reason}"
        )

    except discord.Forbidden:
        await ctx.send("Perm Error: I don't have the permission (kick_members) needed for this.")

# ----------------------------
# TIMEOUT
# ----------------------------

@bot.command()
@commands.has_permissions(administrator=True)
async def timeout(ctx, member: discord.Member, minutes: int, *, reason="No reason provided"):

    if not can_moderate(ctx.author, member):
        return await ctx.send(f"Perm Error: You can't use this command on {member.mention} due to your role.")

    duration = datetime.timedelta(minutes=minutes)

    try:
        await member.timeout(duration, reason=reason)

        await ctx.send(
            f"SUCCESS! {member.mention} has been timed out for {minutes} minute(s).\n"
            f"Reason: {reason}"
        )

    except discord.Forbidden:
        await ctx.send("Perm Error: ...Did you not add administrator to me? How? My OAuth2 LITERALLY adds adminstrator.")

# ----------------------------
# NICKNAME
# ----------------------------

@bot.command()
@commands.has_permissions(manage_nicknames=True)
async def nickname(ctx, member: discord.Member, *, new_name=None):

    if not can_moderate(ctx.author, member):
        return await ctx.send("Perm Error: You can't use this command due to your role.")

    try:
        await member.edit(nick=new_name)

        if new_name:
            await ctx.send(
                f"SUCCESS! Changed nickname for {member.mention} to **{new_name}**."
            )
        else:
            await ctx.send(
                f"SUCCESS! Reset nickname for {member.mention}."
            )

    except discord.Forbidden:
        await ctx.send("Perm Error: I don't have the permision (manage_nicknames) needed for this.")

# ----------------------------
# ADD ROLE
# ----------------------------

@bot.command()
@commands.has_permissions(manage_roles=True)
async def addrole(ctx, member: discord.Member, role: discord.Role):

    if not can_moderate(ctx.author, member):
        return await ctx.send("Perm Error: That person can't get a role added.")

    try:
        await member.add_roles(role)

        await ctx.send(
            f"SUCCESS! Added **{role.name}** to {member.mention}."
        )

    except discord.Forbidden:
        await ctx.send("Perm Error: I don't have the permission (manage_roles) needed for this.")

# ----------------------------
# REMOVE ROLE
# ----------------------------

@bot.command()
@commands.has_permissions(manage_roles=True)
async def removerole(ctx, member: discord.Member, role: discord.Role):

    if not can_moderate(ctx.author, member):
        return await ctx.send("Perm Error: That person can't get a role removed.")

    try:
        await member.remove_roles(role)

        await ctx.send(
            f"SUCCESS! Removed **{role.name}** from {member.mention}."
        )

    except discord.Forbidden:
        await ctx.send("Perm Error: I don't have the permission (manage_roles) needed for this.")

# ----------------------------
# HELP
# ----------------------------

@bot.command()
async def help(ctx):

    await ctx.send(
        "**Gluonium Command List**\n\n"
        "`%ban @user [days] [reason]`\n"
        "`%kick @user [reason]`\n"
        "`%timeout @user [minutes] [reason]`\n"
        "`%nickname @user [new name]`\n"
        "`%addrole @user @role`\n"
        "`%removerole @user @role`"
    )

# ----------------------------
# Error Handling
# ----------------------------

@bot.event
async def on_command_error(ctx, error):

    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            "**Perm Error:** You don't have permission to use that command."
        )

    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            "**Arg Error:** Missing required argument(s)."
        )

    elif isinstance(error, commands.MemberNotFound):
        await ctx.send(
            "**User Error:** Member not found."
        )

    elif isinstance(error, commands.RoleNotFound):
        await ctx.send(
            "**Role Error:** Role not found."
        )

    else:
        print(f"Unlisted Error: {error}")

# ----------------------------
# Start Bot
# ----------------------------

if __name__ == "__main__":

    keep_alive()

    TOKEN = os.environ.get("DISCORD_TOKEN")

    if TOKEN:
        bot.run(TOKEN)
    else:
        print("Var Error: DISCORD_TOKEN not found.")