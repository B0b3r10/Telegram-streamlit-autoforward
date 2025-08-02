import os
import shutil
import logging
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))
from src import db
from src.models import Post

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

def main():
    logging.info("Starting optimizing media...")
    session = db.get_session()
    if not session:
        logging.error("No db connection...")
        return

    all_posts = session.query(Post).all()
    logging.info(f"Found {len(all_posts)} posts to check path")

    updated_count = 0
    for post in all_posts:
        needs_update = False
        if post.photo_path and not post.photo_paths:
            old_path = Path(post.photo_path)
            new_dir = Path("media") / str(post.channel_id)
            new_path = new_dir / old_path.name
            
            if old_path.exists() and not new_path.exists():
                new_dir.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.move(str(old_path), str(new_path))
                    logging.info(f"Moved file: {old_path} -> {new_path}")
                except Exception as e:
                    logging.warning(f"Cant move {old_path}: {e}")
                    continue
            
            post.photo_paths = [str(new_path).replace('\\', '/')]
            needs_update = True

        if post.video_path and not post.video_paths:
            old_path = Path(post.video_path)
            new_dir = Path("media") / str(post.channel_id)
            new_path = new_dir / old_path.name

            if old_path.exists() and not new_path.exists():
                new_dir.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.move(str(old_path), str(new_path))
                    logging.info(f"Moved file: {old_path} -> {new_path}")
                except Exception as e:
                    logging.warning(f"Cant move {old_path}: {e}")
                    continue

            post.video_paths = [str(new_path).replace('\\', '/')]
            needs_update = True

        if needs_update:
            updated_count += 1

    if updated_count > 0:
        logging.info(f"Saving {updated_count} posts in db...")
        session.commit()
        logging.info("Finished uupdating...")
    else:
        logging.info("No posts to optimize")

    session.close()
    logging.info("Finished optimizing...")

if __name__ == "__main__":
    main()