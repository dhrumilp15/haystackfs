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
    es_client.create_doc(message)

    if message.content[:7] == '!search' or message.content[:2] == '!s':
        content = ''.join(message.content.split()[1:])
        files = es_client.search(content)
        await message.channel.send("Found these:")

        file_buf = await download(files)
        print(file_buf)
        await message.channel.send(files=file_buf)
        for buf in file_buf:
            buf.close()


async def download(files: str):
    filebufs = []
    for file in files:
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
        filebufs.append(discord.File(file_buf, file['_source']['url']))
    return filebufs


client.run(TOKEN)
