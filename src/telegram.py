import logging
import os
from pathlib import Path
import json
from . import config
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

s3_client = None
if config.IS_S3_ENABLED:
    try:
        s3_client = boto3.client(
            's3',
            endpoint_url=config.S3_ENDPOINT_URL,
            aws_access_key_id=config.S3_ACCESS_KEY_ID,
            aws_secret_access_key=config.S3_SECRET_ACCESS_KEY,
            config=Config(signature_version='s3v4')
        )
        logger.info("S3 initialize...")
    except Exception as e:
        logger.critical(f"Cant initialize S3: {e}")

async def download_media_if_needed(message, channel_id: int) -> tuple:
    photo_path, video_path = None, None
    channel_media_dir = Path("media") / str(channel_id)
    channel_media_dir.mkdir(parents=True, exist_ok=True)
    try:
        if message.photo:
            path = await message.download_media(file=channel_media_dir / f"{message.id}.jpg")
            if path and os.path.getsize(path) > 0:
                photo_path = str(path).replace('\\', '/')
        if message.video:
            path = await message.download_media(file=channel_media_dir / f"{message.id}.mp4")
            if path and os.path.getsize(path) > 0:
                video_path = str(path).replace('\\', '/')
    except Exception as e:
        logger.error("Download ERROR %d: %s", message.id, e)
    return photo_path, video_path

async def parse_grouped_message_data(messages: list) -> dict:
    main_message = next((m for m in messages if m.text), messages[0])
    all_photo_paths, all_video_paths = [], []
    for msg in messages:
        photo_path, video_path = await download_media_if_needed(msg, msg.chat.id)
        if photo_path: all_photo_paths.append(photo_path)
        if video_path: all_video_paths.append(video_path)
    
    channel_username = main_message.chat.username if main_message.chat.username else str(main_message.chat.id)
    link = f"https://t.me/{channel_username}/{main_message.id}" if channel_username else None

    if main_message.reactions is None:
        reactions_count = -1
    else:
        reactions_count = sum(r.count for r in main_message.reactions.results)

    return {
        "message_id": main_message.id, "grouped_id": main_message.grouped_id,
        "channel_id": main_message.chat.id, "channel_name": main_message.chat.title,
        "post_text": main_message.text or "", "post_date": main_message.date,
        "views": main_message.views,
        "reactions_count": reactions_count,
        "link": link, "raw_data": json.dumps([m.to_dict() for m in messages], default=str),
        "photo_paths": all_photo_paths, "video_paths": all_video_paths,
    }