import asyncio
import argparse
import logging

from telethon import TelegramClient
from sqlalchemy.exc import IntegrityError

from . import config, telegram
from .db import get_session, get_latest_post_id
from .models import Post

logging.basicConfig(level=logging.INFO, format="[%(levelname)s/%(asctime)s] %(message)s")
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

SAFE_DELAY_SECONDS = 1.5

async def main(channel_username: str):
    session = get_session()
    if not session:
        logger.error("ERROR. Check config")
        return

    async with TelegramClient("importer_session", config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH) as client:
        logger.info(f"Starting import: @{channel_username}...")
        try:
            entity = await client.get_entity(channel_username)
            channel_id = entity.id

            latest_saved_id = get_latest_post_id(session, channel_id)
            logger.info(f"Last saved ID'{channel_username}' (ID: {channel_id}): {latest_saved_id}.")
            logger.info("Checking new posts...")

        except Exception as e:
            logger.error(f"No info {channel_username}, last ID from db: {e}")
            session.close()
            return

        saved_count = 0
        processed_count = 0
        try:
            async for message in client.iter_messages(channel_username, min_id=latest_saved_id):
                processed_count += 1
                
                if not message.id or (not message.text and not message.media):
                    continue

                post_data = await telegram.parse_message_data(message)
                
                new_post = Post(**post_data)
                
                try:
                    session.add(new_post)
                    session.commit()
                    saved_count += 1
                except IntegrityError:
                    session.rollback()
                except Exception as e:
                    logger.error(f"Cant save post {new_post.message_id}: {e}")
                    session.rollback()

                if processed_count > 0 and processed_count % 50 == 0:
                    logger.info(f"Updated new: {processed_count}. Saved: {saved_count}.")
                
                await asyncio.sleep(SAFE_DELAY_SECONDS)
        except Exception as e:
            logger.error(f"ERROR import: {e}", exc_info=True)
        finally:
            logger.info("SYNTH finished...")
            if processed_count > 0:
                logger.info(f"Updated new posts: {processed_count}...")
                logger.info(f"Saved in db: {saved_count}...")
            else:
                logger.info("No new posts to save")
            session.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import posts in postgres")
    parser.add_argument("channel", type=str, help="Channel to save (for example, 'durov_russia')")
    args = parser.parse_args()
    asyncio.run(main(args.channel))