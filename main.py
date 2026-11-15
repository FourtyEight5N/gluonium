
import os
import json
import uuid
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
    command_prefix="%",
    intents=intents
)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} \\ {bot.user.id}")
    print("Gluonium online = true")


async def setup_hook():
    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} slash command(s).")


bot.setup_hook = setup_hook


# ----------------------------
# ALERT SYSTEM CONFIGURATION
# ----------------------------

ALERT_ADMIN_IDS = {
    1253782244430970972,
    1559219425612144733,
}

ALERTS_FILE = os.environ.get(
    "ALERTS_FILE",
    "alerts.json"
)

ALERT_DATA = {
    "channel_id": None,
    "announcements": {}
}


def load_alert_data():
    global ALERT_DATA

    try:
        with open(ALERTS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, dict):
            ALERT_DATA.update(data)

    except FileNotFoundError:
        print("Alert storage not found. Creating new storage.")

    except (json.JSONDecodeError, OSError) as error:
        print(f"Alert storage error: {error}")


def save_alert_data():
    directory = os.path.dirname(os.path.abspath(ALERTS_FILE))
    os.makedirs(directory, exist_ok=True)

    temporary_file = ALERTS_FILE + ".tmp"

    with open(temporary_file, "w", encoding="utf-8") as file:
        json.dump(ALERT_DATA, file, indent=4)

    os.replace(temporary_file, ALERTS_FILE)


def is_alert_admin(interaction: discord.Interaction):
    return interaction.user.id in ALERT_ADMIN_IDS


async def require_alert_admin(interaction: discord.Interaction):
    if not is_alert_admin(interaction):
        await interaction.response.send_message(
            "Perm Error: You are not authorized to manage Gluonium alerts.",
            ephemeral=True
        )
        return False

    return True


# ----------------------------
# ALERT EMBED BUILDER
# ----------------------------

ALERT_STYLES = {
    "info": {
        "name": "Information",
        "color": discord.Color.blue()
    },
    "warning": {
        "name": "Warning",
        "color": discord.Color.orange()
    },
    "critical": {
        "name": "Critical",
        "color": discord.Color.red()
    }
}


def create_alert_embed(title, message, severity, alert_id):
    style = ALERT_STYLES[severity]

    embed = discord.Embed(
        title=title,
        description=message,
        color=style["color"],
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )

    embed.set_footer(
        text=f"Gluonium Global Alert • ID: {alert_id}"
    )

    embed.add_field(
        name="Severity",
        value=style["name"],
        inline=True
    )

    return embed


# ----------------------------
# GLOBAL ALERT COMMAND GROUP
# ----------------------------

alert_group = app_commands.Group(
    name="alert",
    description="Manage Gluonium global announcements"
)


# ----------------------------
# /ALERT CHANNEL
# ----------------------------

@alert_group.command(
    name="channel",
    description="Sets the global announcement channel"
)
@app_commands.guild_only()
@app_commands.describe(
    channel="The channel where global announcements will be posted"
)
async def alert_channel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    if not await require_alert_admin(interaction):
        return

    permissions = channel.permissions_for(channel.guild.me)

    if not permissions.view_channel or not permissions.send_messages:
        await interaction.response.send_message(
            "Perm Error: I need permission to view and send messages "
            "in that channel.",
            ephemeral=True
        )
        return

    if not permissions.embed_links:
        await interaction.response.send_message(
            "Perm Error: I need permission to embed links in that channel.",
            ephemeral=True
        )
        return

    ALERT_DATA["channel_id"] = channel.id
    save_alert_data()

    await interaction.response.send_message(
        f"SUCCESS! Global announcement channel set to {channel.mention}.",
        ephemeral=True
    )


# ----------------------------
# /ALERT PREVIEW
# ----------------------------

@alert_group.command(
    name="preview",
    description="Previews a global announcement without publishing it"
)
@app_commands.describe(
    title="Announcement title",
    message="Announcement message",
    severity="Announcement severity"
)
@app_commands.choices(
    severity=[
        app_commands.Choice(name="Information", value="info"),
        app_commands.Choice(name="Warning", value="warning"),
        app_commands.Choice(name="Critical", value="critical")
    ]
)
async def alert_preview(
    interaction: discord.Interaction,
    title: str,
    message: str,
    severity: app_commands.Choice[str]
):
    if not await require_alert_admin(interaction):
        return

    if len(title) > 256 or len(message) > 4000:
        await interaction.response.send_message(
            "Error: Title must be at most 256 characters and "
            "message must be at most 4000 characters.",
            ephemeral=True
        )
        return

    embed = create_alert_embed(
        title,
        message,
        severity.value,
        "PREVIEW"
    )

    await interaction.response.send_message(
        content="**Global alert preview:**",
        embed=embed,
        ephemeral=True
    )


# ----------------------------
# /ALERT CREATE
# ----------------------------

@alert_group.command(
    name="create",
    description="Publishes a global announcement"
)
@app_commands.describe(
    title="Announcement title",
    message="Announcement message",
    severity="Announcement severity"
)
@app_commands.choices(
    severity=[
        app_commands.Choice(name="Information", value="info"),
        app_commands.Choice(name="Warning", value="warning"),
        app_commands.Choice(name="Critical", value="critical")
    ]
)
async def alert_create(
    interaction: discord.Interaction,
    title: str,
    message: str,
    severity: app_commands.Choice[str]
):
    if not await require_alert_admin(interaction):
        return

    if len(title) > 256 or len(message) > 4000:
        await interaction.response.send_message(
            "Error: Title must be at most 256 characters and "
            "message must be at most 4000 characters.",
            ephemeral=True
        )
        return

    channel_id = ALERT_DATA.get("channel_id")

    if not channel_id:
        await interaction.response.send_message(
            "Config Error: No global announcement channel has been set. "
            "Use `/alert channel` first.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    channel = bot.get_channel(channel_id)

    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except discord.NotFound:
            await interaction.followup.send(
                "Config Error: The configured announcement channel "
                "no longer exists.",
                ephemeral=True
            )
            return
        except discord.Forbidden:
            await interaction.followup.send(
                "Perm Error: I cannot access the configured channel.",
                ephemeral=True
            )
            return

    if not isinstance(channel, discord.TextChannel):
        await interaction.followup.send(
            "Config Error: The configured destination is not a text channel.",
            ephemeral=True
        )
        return

    alert_id = uuid.uuid4().hex[:8].upper()

    embed = create_alert_embed(
        title,
        message,
        severity.value,
        alert_id
    )

    try:
        sent_message = await channel.send(
            embed=embed,
            allowed_mentions=discord.AllowedMentions.none()
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "Perm Error: I cannot send announcements to the configured channel.",
            ephemeral=True
        )
        return

    except discord.HTTPException as error:
        print(f"Alert publishing error: {error}")

        await interaction.followup.send(
            "Error: Discord rejected the announcement.",
            ephemeral=True
        )
        return

    ALERT_DATA["announcements"][alert_id] = {
        "title": title,
        "message": message,
        "severity": severity.value,
        "channel_id": channel.id,
        "message_id": sent_message.id,
        "created_at": datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),
        "created_by": interaction.user.id
    }

    try:
        save_alert_data()
    except OSError as error:
        print(f"Alert storage error: {error}")

        await interaction.followup.send(
            f"WARNING: Announcement was published, but its data "
            f"could not be saved. Alert ID: `{alert_id}`",
            ephemeral=True
        )
        return

    await interaction.followup.send(
        f"SUCCESS! Global announcement published in {channel.mention}.\n"
        f"Announcement ID: `{alert_id}`",
        ephemeral=True
    )


# ----------------------------
# /ALERT DELETE
# ----------------------------

@alert_group.command(
    name="delete",
    description="Deletes a previously published global announcement"
)
@app_commands.describe(
    announcement_id="The ID of the announcement to delete"
)
async def alert_delete(
    interaction: discord.Interaction,
    announcement_id: str
):
    if not await require_alert_admin(interaction):
        return

    announcement_id = announcement_id.upper()

    announcement = ALERT_DATA["announcements"].get(announcement_id)

    if announcement is None:
        await interaction.response.send_message(
            "ID Error: No announcement with that ID was found.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    channel_id = announcement["channel_id"]
    message_id = announcement["message_id"]

    channel = bot.get_channel(channel_id)

    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except (discord.NotFound, discord.Forbidden):
            channel = None

    if channel is not None:
        try:
            message = await channel.fetch_message(message_id)
            await message.delete()

        except discord.NotFound:
            pass

        except discord.Forbidden:
            await interaction.followup.send(
                "Perm Error: I cannot delete that announcement. "
                "Check my channel permissions.",
                ephemeral=True
            )
            return

        except discord.HTTPException as error:
            print(f"Alert deletion error: {error}")

            await interaction.followup.send(
                "Error: Discord rejected the deletion request.",
                ephemeral=True
            )
            return

    del ALERT_DATA["announcements"][announcement_id]
    save_alert_data()

    await interaction.followup.send(
        f"SUCCESS! Announcement `{announcement_id}` has been deleted.",
        ephemeral=True
    )


bot.tree.add_command(alert_group)


# ----------------------------
# SHARED HELPERS
# ----------------------------

def can_moderate(author: discord.Member, target: discord.Member):
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
        "## Gluonium's commands\n"
        "-# [text] - required\n"
        "-# (text) - optional\n"
        "`/ban [member] (delete_days) (reason)` - Bans someone\n"
        "`/kick [member] (reason)` - Kicks someone\n"
        "`/timeout [member] [minutes] (reason)` - Times out someone\n"
        "`/nickname [member] (new_name)` - Nicknames someone (leave `new_name` field blank to reset nickname)\n"
        "`/addrole [member] (role)` - Gives someone a role\n"
        "`/removerole [member] (role)` - Removes a role\n"
        "`/alert channel` - Sets the channel for announcements\n"
        "`/help` - Shows this prompt"
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
        message = "Cooldown Error: Pls wait before using this command again."

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
    load_alert_data()

    keep_alive()

    TOKEN = os.environ.get("DISCORD_TOKEN")

    if TOKEN:
        bot.run(TOKEN)
    else:
        print("Var Error: DISCORD_TOKEN not found.")
