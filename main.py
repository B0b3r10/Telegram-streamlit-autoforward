import asyncio
import logging
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient, events
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc
from src import config, db, telegram
from src.models import Post, SyncedChannel

logging.basicConfig(level=logging.INFO, format="[%(levelname)s/%(asctime)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)
logging.getLogger("telethon").setLevel(logging.WARNING)

GROUPED_MESSAGE_BUFFER = {}
DEBOUNCE_DELAY = 2.0

SMART_UPDATE_INTERVAL_SECONDS = 300
HOT_POST_AGE_HOURS = 2
WARM_POST_AGE_DAYS = 2
UPDATE_BATCH_SIZE = 25

async def save_post(message_data: dict):
    session = db.get_session()
    if not session:
        logger.error("No db session while connecting...")
        return
    try:
        exists = session.query(Post.id).filter_by(channel_id=message_data['channel_id'], message_id=message_data['message_id']).first()
        if exists:
            return
            
        post_obj = Post(**message_data)
        session.add(post_obj)
        session.commit()
        logger.info(f"Saved post [ID: {message_data['message_id']}] channel «{message_data['channel_name']}»")
    except IntegrityError:
        session.rollback()
    except Exception as e:
        logger.error(f"ERROR saving: {e}")
        session.rollback()
    finally:
        session.close()

async def process_grouped_message(grouped_id, client):
    if grouped_id in GROUPED_MESSAGE_BUFFER:
        group_info = GROUPED_MESSAGE_BUFFER.pop(grouped_id, None)
        if not group_info: return
        messages = group_info['messages']
        logger.info(f"Albom {grouped_id} with {len(messages)} parts")
        post_data = await telegram.parse_grouped_message_data(messages)
        await save_post(post_data)

async def realtime_event_handler(event):
    message = event.message
    grouped_id = message.grouped_id
    if grouped_id:
        if grouped_id not in GROUPED_MESSAGE_BUFFER:
            GROUPED_MESSAGE_BUFFER[grouped_id] = {'messages': [], 'timer': None}
        GROUPED_MESSAGE_BUFFER[grouped_id]['messages'].append(message)
        if GROUPED_MESSAGE_BUFFER[grouped_id]['timer']:
            GROUPED_MESSAGE_BUFFER[grouped_id]['timer'].cancel()
        loop = asyncio.get_running_loop()
        timer = loop.call_later(DEBOUNCE_DELAY, lambda: asyncio.create_task(process_grouped_message(grouped_id, event.client)))
        GROUPED_MESSAGE_BUFFER[grouped_id]['timer'] = timer
    else:
        logger.info(f"New message «{event.chat.title}»")
        post_data = await telegram.parse_grouped_message_data([message])
        await save_post(post_data)

async def historical_sync(client: TelegramClient, channel: str):
    logger.info(f"Start historic synth: {channel}")
    session = db.get_session()
    if not session:
        logger.error(f"Cant start synth {channel}: no bd session")
        return
    try:
        start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        entity = await client.get_entity(channel)
        async for message in client.iter_messages(entity, limit=None):
            if message.date < start_date: break
            if message.grouped_id: continue
            post_data = await telegram.parse_grouped_message_data([message])
            await save_post(post_data)
            await asyncio.sleep(config.SAFE_DELAY_SECONDS)
        
        new_synced = SyncedChannel(channel_id=entity.id)
        session.add(new_synced)
        session.commit()
        logger.info(f"Channel «{entity.title}» synthed")
    except Exception as e:
        logger.error(f"ERROR hystorical synth {channel}: {e}")
        session.rollback()
    finally:
        session.close()

async def update_posts_task(client: TelegramClient):
    logger.info("Dynamic update stats...")
    loop_counter = 0
    while True:
        await asyncio.sleep(SMART_UPDATE_INTERVAL_SECONDS)
        loop_counter += 1
        logger.info("Start updating stats... [HOT POSTS]")
        session = db.get_session()
        if not session: continue
        
        try:
            hot_threshold = datetime.now(timezone.utc) - timedelta(hours=HOT_POST_AGE_HOURS)
            hot_posts = session.query(Post).filter(Post.post_date >= hot_threshold).order_by(desc(Post.post_date)).all()
            
            if hot_posts:
                updated_count = await process_posts_batch(hot_posts, client, session)
                if updated_count > 0:
                    logger.info(f"Stats updated for {updated_count} HOT posts.")
            
        except Exception as e:
            logger.error(f"ERROR update [HOT]: {e}")
            session.rollback()
        finally:
            session.close()

        if loop_counter % 3 == 0:
            logger.info("Start updating stats... [WARM POSTS]")
            session = db.get_session()
            if not session: continue

            try:
                warm_threshold = datetime.now(timezone.utc) - timedelta(days=WARM_POST_AGE_DAYS)
                warm_posts = session.query(Post).filter(Post.post_date >= warm_threshold, Post.post_date < hot_threshold).order_by(desc(Post.post_date)).all()

                if warm_posts:
                    logger.info(f"Found {len(warm_posts)} WARM posts to check...")
                    total_updated_count = 0
                    for i in range(0, len(warm_posts), UPDATE_BATCH_SIZE):
                        batch = warm_posts[i:i + UPDATE_BATCH_SIZE]
                        updated_in_batch = await process_posts_batch(batch, client, session)
                        total_updated_count += updated_in_batch
                    
                    if total_updated_count > 0:
                        logger.info(f"stats updated for {total_updated_count} WARM posts.")
                    else:
                        logger.info("No new stats for WARM posts...")
                
            except Exception as e:
                logger.error(f"ERROR update [WARM]: {e}")
                session.rollback()
            finally:
                session.close()
async def process_posts_batch(posts: list, client: TelegramClient, session) -> int:
    """
    Updating posts stats. Returns amount of updated posts
    """
    updated_count = 0
    for post in posts:
        try:
            if post.reactions_count == -1:
                continue

            fresh_message = await client.get_messages(post.channel_id, ids=post.message_id)
            if not fresh_message:
                continue

            fresh_views = fresh_message.views or 0
            fresh_reactions = sum(r.count for r in fresh_message.reactions.results) if fresh_message.reactions else 0

            if post.views != fresh_views or post.reactions_count != fresh_reactions:
                post.views = fresh_views
                post.reactions_count = fresh_reactions
                updated_count += 1
        except Exception as e:
            logger.warning(f"Cant update post ID {post.message_id}: {e}")
        await asyncio.sleep(1.5) # Задержка между запросами к API

    if updated_count > 0:
        session.commit()
    
    return updated_count
async def main():
    client = TelegramClient("anon_session", config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)
    client.add_event_handler(realtime_event_handler, events.NewMessage(chats=config.SOURCE_CHANNELS))
    
    await client.start()
    logger.info("TG start...")
    session = db.get_session()
    if not session:
        logger.critical("No db session")
        return
    
    synced_ids = {c.channel_id for c in session.query(SyncedChannel).all()}
    session.close()
    
    tasks_to_run = []
    for channel_name in config.SOURCE_CHANNELS:
        try:
            entity = await client.get_entity(channel_name)
            if entity.id not in synced_ids:
                logger.info(f"Channel «{entity.title}» added to synth")
                tasks_to_run.append(historical_sync(client, channel_name))
        except Exception as e:
            logger.error(f"No entity {channel_name}: {e}")
    tasks_to_run.append(client.run_until_disconnected())
    tasks_to_run.append(update_posts_task(client))

    logger.info(f"Run {len(tasks_to_run)} tasks in parallel...")
    await asyncio.gather(*tasks_to_run)

if __name__ == "__main__":
    asyncio.run(main())