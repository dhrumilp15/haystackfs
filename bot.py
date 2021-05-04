import os
from pathlib import Path
import requests
from io import BytesIO

import discord
from dotenv import load_dotenv
# import boto3
# from upload_to_s3 import upload_to_s3
from elasticsearch_conn import ElasticSearchConnector

env_path = Path('.') / '.env'

load_dotenv(dotenv_path=env_path)

TOKEN = os.getenv('DISCORD_TOKEN')

client = discord.Client()

# s3_client = boto3.client(
#     's3', endpoint_url=str(os.getenv('ENDPOINT_URL')),
#     aws_access_key_id=str(os.getenv('AWS_ACCESS_KEY_ID')),
#     aws_secret_access_key=str(os.getenv('AWS_SECRET_ACCESS_KEY'))
# )

es_client = ElasticSearchConnector(
    elastic_domain=os.getenv("ELASTIC_DOMAIN"),
    elastic_port=os.getenv("ELASTIC_PORT"),
    index='file_index'
)


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')


@client.event
async def on_message(message):
    '''Send all message attachments to the CORTX s3 bucket'''
    if message.author == client.user:
        return

    # since cortx has been terminated, we won't be using it anymore :(
    await es_client.create_doc(message)

    if message.content[:4] == '!all':
        all_docs = es_client.get_all_docs()
        file_buf = await download(all_docs)
        if file_buf:
            await message.author.send("All documents:", files=file_buf)
        else:
            await message.author.send("The archives are empty...")
        for buf in file_buf:
            buf.close()

    if message.content[:7] == '!delete' or message.content[:4] == '!del':
        content = ''.join(message.content.split()[1:])
        files = es_client.search(content)
        if not files:
            await message.author.send("Couldn't find the files to delete")
            return
        del_str = ["Deleted"]
        for file in files:
            es_client.delete_doc(file['_id'])
            message = await message.channel.fetch_message(file['_source']['message_id'])
            try:
                await message.delete()
                del_str.append(file['_source']['file_name'])
            except discord.Forbidden:
                await message.channel.send("Can't delete {}".format(file['_source']['file_name']))
        if len(del_str) > 1:
            await message.author.send(del_str)

    if message.content[:7] == '!remove' or message.content[:3] == '!rm':
        content = ''.join(message.content.split()[1:])
        files = es_client.search(content)
        if not files:
            await message.author.send("Couldn't find the files to remove")
            return
        for file in files:
            es_client.delete_doc(file['_id'])
        await message.author.send("Removed {}".format(' '.join([file['_source']['file_name'] for file in files])))

    if message.content[:7] == '!search' or message.content[:2] == '!s':
        content = ''.join(message.content.split()[1:])
        files = es_client.search(content)
        await message.channel.send("I'll dm you what I find")
        if not files:
            await message.author.send("Couldn't find anything related to `{}` :(".format(content))
            return

        file_buf = await download(files)
        await message.author.send("Here's what I found:", files=file_buf)
        for buf in file_buf:
            buf.close()


@client.event
async def on_raw_message_delete(payload):
    if payload.cached_message is None:
        onii_chan_id = payload.channel_id
        onii_chan = client.get_channel(onii_chan_id)

        if not onii_chan:
            return
        message = await onii_chan.fetch_message(payload.message_id)
    else:
        message = payload.cached_message
    for file in message.attachments:
        es_client.delete_doc(file.id)


async def download(files: str):
    filebufs = []
    for idx, file in enumerate(files):
        url = file['_source']['url']
        response = requests.get(url, stream=True)
        if not response.ok:
            print(response)
        file_buf = BytesIO()
        for blk in response.iter_content(1024):
            if not blk:
                break
            file_buf.write(blk)
        file_buf.seek(0)
        filename = file['_source']['file_name']
        if len(files) > 1:
            ext = filename.rindex('.')
            filename = filename[:ext] + str(idx) + filename[ext:]
        filebufs.append(discord.File(file_buf, filename))
    return filebufs


client.run(TOKEN)
