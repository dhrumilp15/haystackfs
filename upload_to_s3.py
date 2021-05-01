import requests
import os
from datetime import datetime
from botocore.exceptions import ClientError
from elasticsearch_conn import ElasticSearchConnector


async def upload_to_s3(s3_client, es_client, message):
    if not message.attachments:
        return
    try:
        for file in message.attachments:
            file_id = file.id
            file_name = file.filename
            created = message.created_at
            ts = datetime.now()
            content_type = file.content_type
            author = message.author
            size = file.size
            proxy_url = file.proxy_url
            file_bytes = await file.read()
            url = file.url
            s3_client.put_object(
                Body=file_bytes,
                Bucket='testbucket',
                ContentType=content_type,
                Metadata={
                    "author": str(author.id),
                    "author_name": str(author.name),
                    "file_id": str(file_id),
                    "file_name": str(file_name),
                    "created": str(created),
                    "timestamp": str(ts),
                    "mimetype": str(content_type),
                    "size": str(size),
                    "proxy_url": str(proxy_url),
                    "url": str(url)
                },
                Key=file_name
            )
            print("Sent req to S3")
            es_client.create_doc(file, message)

            print("File uploaded to S3 with key {}".format(file_name))

    except ClientError as e:
        print("Couldn't upload to s3")
        print(e)
        return False
    except Exception as e:
        print(e)
        return False
    return True
