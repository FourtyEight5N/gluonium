
import os
import datetime
import threading

from flask import Flask
import discord
from discord import app_commands
from discord.ext import commands

# ----------------------------
# WEB SERVER / KEEP ALIVE
# ----------------------------

app = Flask(__name__)


@app.route("/")
def home():
    return "bot alive = true"


def run_webserver():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


def keep_alive():
    threading.Thread(target=run_webserver, daemon=True).start()


# ----------------------------
# BOT SETUP
# ----------------------------

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(
    command_prefix="%",  # No longer used for moderation commands
    intents=intents
)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} \\ {bot.user.id}")
    print("Gluonium online = true")


# Sync slash commands once during startup.
# Global commands can take some time to appear in Discord.
async def setup_hook():
    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} slash command(s).")


bot.setup_hook = setup_hook


# ----------------------------
# SHARED HELPERS
# ----------------------------

def can_moderate(author: discord.Member, target: discord.Member):
    # Preserve the original role hierarchy check.
    return author.id != target.id and author.top_role > target.top_role


async def hierarchy_error(interaction: discord.Interaction, target: discord.Member):
    if interaction.user.id == target.id:
        await interaction.response.send_message(
            "Perm Error: You can't use this command on yourself, dumbass.",
            ephemeral=True
        )
        return True

    if not can_moderate(interaction.user, target):
        await interaction.response.send_message(
            f"Perm Error: You can't use this command on {target.mention} "
            "due to your role.",
            ephemeral=True
        )
        return True

    if interaction.guild.me.top_role <= target.top_role:
        await interaction.response.send_message(
            "Perm Error: My highest role must be above the target's highest role.",
            ephemeral=True
        )
        return True

    return False


# ----------------------------
# BAN
# ----------------------------

@bot.tree.command(name="ban", description="Bans a member from the server")
@app_commands.guild_only()
@app_commands.default_permissions(ban_members=True)
@app_commands.checks.has_permissions(ban_members=True)
@app_commands.describe(
    member="The member to ban",
    delete_days="Days of recent messages to delete (0–14)",
    reason="Reason for the ban"
)
async def ban(
    interaction: discord.Interaction,
    member: discord.Member,
    delete_days: app_commands.Range[int, 0, 14] = 1,
    reason: str = "No reason provided"
):
    if await hierarchy_error(interaction, member):
        return

    try:
        await member.ban(
            delete_message_seconds=delete_days * 86400,
            reason=reason
        )

        await interaction.response.send_message(
            f"SUCCESS! {member.mention} has been banned.\n"
            f"Days of messages deleted: {delete_days}\n"
            f"Reason: {reason}"
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "Perm Error: I don't have permission to ban that member.",
            ephemeral=True
        )


# ----------------------------
# KICK
# ----------------------------

@bot.tree.command(name="kick", description="Kick a member from the server.")
@app_commands.guild_only()
@app_commands.default_permissions(kick_members=True)
@app_commands.checks.has_permissions(kick_members=True)
@app_commands.describe(
    member="The member to kick",
    reason="Reason for the kick"
)
async def kick(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason provided"
):
    if await hierarchy_error(interaction, member):
        return

    try:
        await member.kick(reason=reason)

        await interaction.response.send_message(
            f"SUCCESS! {member.mention} has been kicked.\n"
            f"Reason: {reason}"
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "Perm Error: I don't have permission to kick that member.",
            ephemeral=True
        )


# ----------------------------
# TIMEOUT
# ----------------------------

@bot.tree.command(name="timeout", description="Time out someone")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    member="The member to time out",
    minutes="Duration in minutes (1–40320)",
    reason="Reason for the timeout"
)
async def timeout(
    interaction: discord.Interaction,
    member: discord.Member,
    minutes: app_commands.Range[int, 1, 40320],
    reason: str = "No reason provided"
):
    if await hierarchy_error(interaction, member):
        return

    try:
        duration = datetime.timedelta(minutes=minutes)
        await member.timeout(duration, reason=reason)

        await interaction.response.send_message(
            f"SUCCESS! {member.mention} has been timed out "
            f"for {minutes} minute(s).\n"
            f"Reason: {reason}"
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "Perm Error: I don't have permission to time out that member.",
            ephemeral=True
        )


# ----------------------------
# NICKNAME
# ----------------------------

@bot.tree.command(name="nickname", description="Changes or resets someone's nickname")
@app_commands.guild_only()
@app_commands.default_permissions(manage_nicknames=True)
@app_commands.checks.has_permissions(manage_nicknames=True)
@app_commands.describe(
    member="The member whose nickname to change",
    new_name="New nickname (leave blank to reset it)"
)
async def nickname(
    interaction: discord.Interaction,
    member: discord.Member,
    new_name: str = None
):
    if await hierarchy_error(interaction, member):
        return

    try:
        await member.edit(nick=new_name)

        if new_name:
            message = (
                f"SUCCESS! Changed nickname for {member.mention} "
                f"to **{new_name}**."
            )
        else:
            message = f"SUCCESS! Reset nickname for {member.mention}."

        await interaction.response.send_message(message)

    except discord.Forbidden:
        await interaction.response.send_message(
            "Perm Error: I don't have permission to manage that nickname.",
            ephemeral=True
        )


# ----------------------------
# ADD ROLE
# ----------------------------

@bot.tree.command(name="addrole", description="Adds a role to a member")
@app_commands.guild_only()
@app_commands.default_permissions(manage_roles=True)
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.describe(
    member="The member getting the role",
    role="The role to add"
)
async def addrole(
    interaction: discord.Interaction,
    member: discord.Member,
    role: discord.Role
):
    if await hierarchy_error(interaction, member):
        return

    if role >= interaction.guild.me.top_role or role.is_default() or role.managed:
        await interaction.response.send_message(
            "Perm Error: I can't assign that role because of its position "
            "or because it is managed.",
            ephemeral=True
        )
        return

    try:
        await member.add_roles(role, reason=f"Added by {interaction.user}")

        await interaction.response.send_message(
            f"SUCCESS! Added **{role.name}** to {member.mention}."
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "Perm Error: I don't have permission to manage that role.",
            ephemeral=True
        )


# ----------------------------
# REMOVE ROLE
# ----------------------------

@bot.tree.command(name="removerole", description="Removes a role from a member")
@app_commands.guild_only()
@app_commands.default_permissions(manage_roles=True)
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.describe(
    member="The member losing the role",
    role="The role to remove"
)
async def removerole(
    interaction: discord.Interaction,
    member: discord.Member,
    role: discord.Role
):
    if await hierarchy_error(interaction, member):
        return

    if role >= interaction.guild.me.top_role or role.is_default() or role.managed:
        await interaction.response.send_message(
            "Perm Error: I can't remove that role because of its position "
            "or because it is managed.",
            ephemeral=True
        )
        return

    try:
        await member.remove_roles(role, reason=f"Removed by {interaction.user}")

        await interaction.response.send_message(
            f"SUCCESS! Removed **{role.name}** from {member.mention}."
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "Perm Error: I don't have permission to manage that role.",
            ephemeral=True
        )


# ----------------------------
# HELP
# ----------------------------

@bot.tree.command(name="help", description="Shows the list of commands")
@app_commands.guild_only()
async def help_command(interaction: discord.Interaction):
    await interaction.response.send_message(
        "## Gluonium Commands"
        "`/ban member delete_days reason`\n"
        "`/kick member reason`\n"
        "`/timeout member minutes reason`\n"
        "`/nickname member new_name`\n"
        "`/addrole member role`\n"
        "`/removerole member role`\n"
        "`/help`"
    )


# ----------------------------
# SLASH COMMAND ERROR HANDLING
# ----------------------------

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):
    if isinstance(error, app_commands.MissingPermissions):
        message = "Perm Error: You don't have permission to use that command."

    elif isinstance(error, app_commands.NoPrivateMessage):
        message = "Server Error: This command can only be used in a server."

    elif isinstance(error, app_commands.CommandOnCooldown):
        message = "Pls wait before using this command again."

    else:
        print(f"Unlisted Slash Command Error: {error}")
        message = "An error occurred while running that command."

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


# ----------------------------
# START BOT
# ----------------------------

if __name__ == "__main__":
    keep_alive()

    TOKEN = os.environ.get("DISCORD_TOKEN")

    if TOKEN:
        bot.run(TOKEN)
    else:
        print("Var Error: DISCORD_TOKEN not found.")
