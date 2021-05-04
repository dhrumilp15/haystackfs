import os
from pathlib import Path
import requests
from io import BytesIO
from typing import List, Dict

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
    if not message.content:
        return
    content = message.content.split()
    print(content)
    query = content.pop(0)
    content = ' '.join(content)

    if query == '!all' or query == '!a':
        await send_files_as_message(message, es_client.get_all_docs(), content)

    elif query == '!delete' or query == '!del':
        files = es_client.search(content)
        if not files:
            await message.author.send(
                f"Couldn't delete files related to `{content}`")
            return

        del_str = []
        for file in files:
            es_client.delete_doc(file['_id'])
            msg = await message.channel.fetch_message(
                file['_source']['message_id'])
            try:
                await msg.delete()
                del_str.append(file['_source']['file_name'])
            except discord.Forbidden:
                await message.channel.send(
                    f"Couldn't delete `{file['_source']['file_name']}`")
        if del_str:
            await message.author.send(f"Deleted: `{' '.join(del_str)}`")

    elif query == '!remove' or query == '!rm':
        files = es_client.search(content)
        if not files:
            await message.author.send(
                f"Couldn't remove files related to `{content}`")
            return

        output_filenames = []
        for file in files:
            es_client.delete_doc(file['_id'])
            output_filenames.append(file['_source']['file_name'])
        if output_filenames:
            await message.author.send(
                f"Removed: `{' '.join(output_filenames)}`")

    elif query == '!search' or query == '!s':
        await send_files_as_message(message, es_client.search(content), content)


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


def check_if_author_can_view_message(author: discord.User,
                                     message: discord.Message, file: List[Dict]):
    """Checks if the author can view the file

    Args:
        author: The discord.User querying for files
        files: A list of dicts returned from ElasticSearch.
    """
    file_message_id = file['_source']['message_id']
    file_message_chan = message.channel.fetch_message(file_message_id).channel


async def send_files_as_message(search_message, files, content):
    """Sends files to the author of the message

    Args:
        search_message: The original search message
        files: The files returned from ElasticSearch
    """
    if not files:
        await search_message.author.send(
            f"Couldn't find files related to `{content}` :(")
        return
    # if search_message.channel

    file_buf = download(files)
    await search_message.author.send("Here's what I found:", files=file_buf)
    for buf in file_buf:
        buf.close()


def download(files: str):
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
