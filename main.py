import discord, sys, logging
from discord import app_commands
from configparser import ConfigParser

class Client(discord.Client):
    async def on_ready(self):
        print(f'Logged on as {self.user}!')
        # sync commands if 'sync' argument provided
        if 'sync' in sys.argv:
            print('Syncing slash commands globally...')
            await Bot.tree.sync()
            print('Exiting...')
            await self.close()
    async def on_raw_reaction_add(self, event:discord.RawReactionActionEvent):
        if has_restricted_role(event.member):
            return
        if str(event.emoji) != get_config_value('emoji'):
            return
        if event.channel_id != int(get_config_value('role_channel')):
            return
        logging_channel:discord.channel = await get_channel_from_id(self, int(get_config_value('logging_channel')))
        await logging_channel.send(f'{event.member.mention} would like restricted role access.')

# initialize bot instance
intents = discord.Intents.default()
Bot = Client(intents=intents)

# logging handler
Bot.log_handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

# slash command tree
Bot.tree = app_commands.CommandTree(Bot)

# edit configuration file through slash commands
@Bot.tree.command(name="configure", description="Bot configuration.")
@app_commands.choices(setting=[
    app_commands.Choice(name='Role Channel ID', value='role_channel'),
    app_commands.Choice(name='Reaction Emoji (Paste Emoji)', value='emoji'),
    app_commands.Choice(name='Logging Channel ID', value='logging_channel'),
    app_commands.Choice(name='Restricted Role ID', value='restricted_role')
])
async def slash(interaction:discord.Interaction, setting:app_commands.Choice[str], id:str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You have no admin", ephemeral=True) 
        return
    
    # check if ID exists
    if setting.value in ['logging_channel', 'role_channel']:
        if not validate_id(id):
            return
        if int(id) not in [channel.id for channel in interaction.guild.channels]:
            await interaction.response.send_message('I cannot find this channel!', ephemeral=True)
            return
    if setting.value in ['restricted_role']:
        if not validate_id(id):
            return
        if int(id) not in [role.id for role in interaction.guild.roles]:
            await interaction.response.send_message('I cannot find this role!', ephemeral=True)
            return

    # update configuration file and return success
    update_config(setting.value, id)
    await interaction.response.send_message(f'{setting.name} set to {id}', ephemeral=True)
    return

# initialize config 
Bot.config = ConfigParser()
Bot.config.read('config.ini')

def validate_id(id):
    # convert id to integer
    try:
        id = int(id)
        return True
    except ValueError:
        return False


# update config file
def update_config(name, value):
    value = str(value)
    config:ConfigParser = Bot.config
    if not config.has_section('main'):
        config.add_section('main')
    config.set('main', name, value)
    with open('config.ini', 'w') as f:
        config.write(f)

# return config value
def get_config_value(name):
    config:ConfigParser = Bot.config
    name = str(name)
    return config.get('main', name)

# check if user has restricted role
def has_restricted_role(member:discord.Member):
    return int(get_config_value('restricted_role')) in  [role.id for role in member.roles]

async def get_channel_from_id(bot:discord.Client, id:int):
    return await bot.fetch_channel(id)


# Run with token or prompt if one does not exist
try:
    with open('token', 'r') as token:
        Bot.run(token.read(), log_handler=Bot.log_handler)
except FileNotFoundError:
    print('Token not found. Input bot token and press enter or place it in a plaintext file named `token`.')
    token_text = input('Paste token: ')
    with open('token','w') as f:
        f.write(token_text)
        Bot.run(token_text, log_handler=Bot.log_handler)