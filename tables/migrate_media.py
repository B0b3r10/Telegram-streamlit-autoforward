import logging
from datetime import timedelta
from sqlalchemy import desc
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))
from src import db
from src.models import Post
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

def main():
    logging.info("Merge alboms...")
    session = db.get_session()
    if not session:
        logging.error("No db connection...")
        return

    posts_by_channel = defaultdict(list)
    all_posts = session.query(Post).order_by(Post.post_date).all()
    for post in all_posts:
        posts_by_channel[post.channel_id].append(post)

    posts_to_delete_ids = []
    main_posts_to_update = []

    logging.info("Analyze dublicate alboms...")
    for channel_id, posts in posts_by_channel.items():
        i = 0
        while i < len(posts):
            current_post = posts[i]
            album_group = [current_post]
            
            j = i + 1
            while j < len(posts) and (posts[j].post_date - current_post.post_date) < timedelta(seconds=3):
                if posts[j].post_text and not current_post.post_text:
                    album_group.append(current_post)
                    current_post = posts[j]
                else:
                    album_group.append(posts[j])
                j += 1
            
            if len(album_group) > 1:
                logging.info(f"Group {len(album_group)} posts from channel_id {channel_id} (post ID: {current_post.id})")
                
                all_photos = []
                all_videos = []
                
                for p in album_group:
                    if p.photo_paths: all_photos.extend(p.photo_paths)
                    if p.video_paths: all_videos.extend(p.video_paths)
                    if p.id != current_post.id:
                        posts_to_delete_ids.append(p.id)
                
                current_post.photo_paths = list(set(all_photos))
                current_post.video_paths = list(set(all_videos))
                main_posts_to_update.append(current_post)

            i = j

    if main_posts_to_update:
        logging.info(f"Updating {len(main_posts_to_update)} posts...")
        session.commit()
    
    if posts_to_delete_ids:
        logging.info(f"Deleting {len(posts_to_delete_ids)} dublicates...")
        session.query(Post).filter(Post.id.in_(posts_to_delete_ids)).delete(synchronize_session=False)
        session.commit()

    logging.info("Finishing...")
    session.close()

if __name__ == "__main__":
    main()