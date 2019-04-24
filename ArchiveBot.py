#Discord ArchiveBot v1.0.0
#Copyright (c) 2019 DJVoxel
#Distributed under the MIT License

from concurrent.futures import ThreadPoolExecutor

import os.path

import discord
from discord.ext import commands
from discord.ext.commands import bot
import asyncio

from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from apiclient.http import MediaFileUpload

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

SCOPES = 'https://www.googleapis.com/auth/drive.file'
CLIENT_SECRET = 'client_secret.json'

store = file.Storage('token.json')
credz = store.get()
if not credz or credz.invalid:
    flow = client.flow_from_clientsecrets(CLIENT_SECRET, SCOPES)
    credz = tools.run_flow(flow, store, flags)
service = build('drive', 'v3', http=credz.authorize(Http()))

command_prefix = ']'

bot_key = '<Bot key goes here>'

bot = commands.Bot(command_prefix)

def upload_file(filename, folder_id = 'root'):
    try:
        metadata = {'name' : "{}.txt".format(filename), 'mimetype' : 'application/vnd.google.apps.document', 'parents' : ['{}'.format(folder_id)]}
        media = MediaFileUpload('{}.txt'.format(filename), mimetype='text/plain')
        return service.files().create(body=metadata, media_body=media).execute()
    except Exception as e:
        return e

def get_file(filename, folder_id = 'root'):
    try:
        response = service.files().list(q = "'{}' in parents and name = '{}.txt' and mimeType = 'text/plain' and trashed = false".format(folder_id, filename), fields="files(name, id)").execute()
        return response.get('files')
    except Exception as e:
        return e

def get_folder(folder_name, parent):
    try:
        folder = service.files().list(q = "'{}' in parents and name = '{}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false".format(parent, folder_name), fields="files/id").execute()
        folder = folder.get('files')
        return folder[0].get('id')
    except Exception as e:
        return e

def create_folder(folder_name, parent):
    try:
        metadata = {'name' : folder_name, 'mimeType' : 'application/vnd.google-apps.folder', 'parents' : ['{}'.format(parent)]}
        folder = service.files().create(body=metadata, fields='id').execute()
        return folder.get('id')
    except Exception as e:
        return e

def share_folder(folder_id):
    try:
        res = service.permissions().create(body={"role":"reader", "type":"anyone"}, fileId=folder_id).execute()
        print(res)
        return service.files().get(fileId = folder_id, fields='webViewLink').execute().get('webViewLink')
    except Exception as e:
        return e

@bot.event
async def on_ready():
    print (bot.user.name, "is ready!")
    print ("Id:", bot.user.id)
    for guild in bot.guilds:
        role_check = discord.utils.get(guild.roles, name="Archivist")
        if role_check is None:
            guild.create_role(name="Archivist")
    print ("Ready to Archive!")

@bot.command()
async def ping(ctx):
    await ctx.send("Pong")

@bot.command()
async def archives(ctx):
    with ThreadPoolExecutor() as pool: 
            folder_id = await bot.loop.run_in_executor(
                pool, get_folder, 'Archive Bot Beta', 'root'
            )
            if folder_id is None or isinstance(folder_id, Exception):
                folder_id = await bot.loop.run_in_executor(
                    pool, create_folder, 'Archive Bot Beta', 'root'
                )
            print(folder_id)
            subfolder_id = await bot.loop.run_in_executor(
                pool, get_folder, 'Server ID: {}'.format(ctx.guild.id), folder_id
            )
            if subfolder_id is None or isinstance(subfolder_id, Exception):
                subfolder_id = await bot.loop.run_in_executor(
                    pool, create_folder, 'Server ID: {}'.format(ctx.guild.id), folder_id
                )
                await ctx.send("Server Folder Created.")
            link = await bot.loop.run_in_executor(
                    pool, share_folder, subfolder_id
                    )
            await ctx.send("Archive Link: {}".format(link))
            print(subfolder_id)


@bot.command()
@commands.has_role('Archivist')
async def archive(ctx, channel : discord.TextChannel, filename, start, end):
    await ctx.send("Archiving....")
    try:
        with open("{}.txt".format(filename), "w") as openfile:
            lines = []
            startmessage = await channel.fetch_message(start)
            endmessage = await channel.fetch_message(end)
            print("<{}> {}#{}: {}".format(startmessage.created_at, startmessage.author.name, startmessage.author.discriminator, startmessage.content))
            lines.append("<{}> {}#{}: {}\n".format(startmessage.created_at, startmessage.author.name, startmessage.author.discriminator, startmessage.content))
            async for message in channel.history(limit=500, before=endmessage, after=startmessage):
                if not (message.author.bot or message.content.startswith(command_prefix)):
                    print ("<{}> {}#{}: {}".format(message.created_at, message.author.name, message.author.discriminator, message.content))
                    lines.append("<{}> {}#{}: {}\n".format(message.created_at, message.author.name, message.author.discriminator, message.content))
            print("<{}> {}#{}: {}".format(endmessage.created_at, endmessage.author.name, endmessage.author.discriminator, endmessage.content))
            lines.append("<{}> {}#{}: {}\n".format(endmessage.created_at, endmessage.author.name, endmessage.author.discriminator, endmessage.content))
            openfile.writelines(lines)
            await ctx.send("Archive Complete!")
        await ctx.send("Uploading....")
        with ThreadPoolExecutor() as pool: 
            folder_id = await bot.loop.run_in_executor(
                pool, get_folder, 'Archive Bot Beta', 'root'
            )
            if folder_id is None or isinstance(folder_id, Exception):
                folder_id = await bot.loop.run_in_executor(
                    pool, create_folder, 'Archive Bot Beta', 'root'
                )
            print(folder_id)
            subfolder_id = await bot.loop.run_in_executor(
                pool, get_folder, 'Server ID: {}'.format(ctx.guild.id), folder_id
            )
            if subfolder_id is None or isinstance(subfolder_id, Exception):
                subfolder_id = await bot.loop.run_in_executor(
                    pool, create_folder, 'Server ID: {}'.format(ctx.guild.id), folder_id
                )
                link = await bot.loop.run_in_executor(
                    pool, share_folder, subfolder_id
                    )
                await ctx.send("Server Folder Created. Archive Link: {}".format(link))
            print(subfolder_id)
            filecheck = await bot.loop.run_in_executor(
                pool, get_file, filename, subfolder_id
            )
            print(filecheck)
            if not filecheck:
                res = await bot.loop.run_in_executor(
                    pool, upload_file, filename, subfolder_id
                    )
                if not isinstance(res, Exception) and res is not None:
                    await ctx.send("Upload Complete!")
                else:
                    await ctx.send("Upload Failed: {}".format(res))
            else:
                await ctx.send("Upload Failed: Filename already exists.")
    except IOError:
        await ctx.send("Error: IOException")
    except Exception as e:
        print (e)
    
@archive.error
async def archive_error(error, ctx):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("You do not have the Archivist role.")

@bot.command()
@commands.has_role('Archivist')
async def archivechannel(ctx, channel : discord.TextChannel, filename):
    await ctx.send("Archiving....")
    try:
        with open("{}.txt".format(filename), "w") as openfile:
            lines = []
            async for message in channel.history(limit=500, oldest_first=True):
                if not (message.author.bot or message.content.startswith(command_prefix)):
                    print ("<{}> {}#{}: {}".format(message.created_at, message.author.name, message.author.discriminator, message.content))
                    lines.append("<{}> {}#{}: {}\n".format(message.created_at, message.author.name, message.author.discriminator, message.content))
            openfile.writelines(lines)
            await ctx.send("Archive Complete!")
        await ctx.send("Uploading....")
        with ThreadPoolExecutor() as pool: 
            folder_id = await bot.loop.run_in_executor(
                pool, get_folder, 'Archive Bot Beta', 'root'
            )
            if folder_id is None or isinstance(folder_id, Exception):
                folder_id = await bot.loop.run_in_executor(
                    pool, create_folder, 'Archive Bot Beta', 'root'
                )
            print(folder_id)
            subfolder_id = await bot.loop.run_in_executor(
                pool, get_folder, 'Server ID: {}'.format(ctx.guild.id), folder_id
            )
            if subfolder_id is None or isinstance(subfolder_id, Exception):
                subfolder_id = await bot.loop.run_in_executor(
                    pool, create_folder, 'Server ID: {}'.format(ctx.guild.id), folder_id
                )
                link = await bot.loop.run_in_executor(
                    pool, share_folder, subfolder_id
                    )
                await ctx.send("Server Folder Created. Archive Link: {}".format(link))
            print(subfolder_id)
            filecheck = await bot.loop.run_in_executor(
                pool, get_file, filename, subfolder_id
            )
            print(filecheck)
            if not filecheck:
                res = await bot.loop.run_in_executor(
                    pool, upload_file, filename, subfolder_id
                    )
                if not isinstance(res, Exception) and res is not None:
                    await ctx.send("Upload Complete!")
                else:
                    await ctx.send("Upload Failed: {}".format(res))
            else:
                await ctx.send("Upload Failed: Filename already exists.")
    except IOError:
        await ctx.send("Error: IOException")
    except Exception as e:
        print(e)
    
@archivechannel.error
async def archivechannel_error(error, ctx):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("You do not have the Archivist role.")

bot.run(bot_key)
