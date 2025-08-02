import streamlit as st
from src import db
from src.models import Post
from sqlalchemy import desc, func, or_
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from pathlib import Path
import math

POSTS_PER_PAGE = 10
st.set_page_config(page_title="Telegram · Streamlit", layout="centered", page_icon="data/tg-ico.png")
st_autorefresh(interval=30 * 1000, key="data_refresher")

def display_media(post):
    project_root = Path(__file__).parent.resolve()
    photo_paths = post.photo_paths or []
    video_paths = post.video_paths or []
    all_media = photo_paths + video_paths

    if not all_media:
        return

    if len(all_media) == 1:
        media_path_str = all_media[0]
        if not isinstance(media_path_str, str) or not media_path_str.strip(): return
        
        media_path = project_root / media_path_str
        if media_path.exists():
            try:
                if str(media_path).lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    st.image(str(media_path))
                elif str(media_path).lower().endswith('.mp4'):
                    st.video(str(media_path))
            except Exception as e:
                st.warning(f"Cant display media: {media_path_str}. ERROR: {e}")
    
    elif len(all_media) > 1:
        tab_titles = [f"File {i+1}" for i in range(len(all_media))]
        tabs = st.tabs(tab_titles)
        for i, tab in enumerate(tabs):
            with tab:
                media_path_str = all_media[i]
                if not isinstance(media_path_str, str) or not media_path_str.strip(): continue
                media_path = project_root / media_path_str
                if media_path.exists():
                    try:
                        if str(media_path).lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                            st.image(str(media_path))
                        elif str(media_path).lower().endswith('.mp4'):
                            st.video(str(media_path))
                    except Exception as e:
                        st.warning(f"Cant display media: {media_path_str}. ERROR: {e}")


def display_pagination(total_posts, current_page):
    total_pages = math.ceil(total_posts / POSTS_PER_PAGE)
    if total_pages <= 1:
        return

    st.divider()

    pages_to_show = set()
    pages_to_show.add(1)
    pages_to_show.add(total_pages)
    for i in range(max(1, current_page - 1), min(total_pages + 1, current_page + 2)):
        pages_to_show.add(i)

    sorted_pages = sorted(list(pages_to_show))
    _, center_col, _ = st.columns([1, 5, 1])
    with center_col:
        items_to_render = []
        last_page = 0
        for page in sorted_pages:
            if last_page != 0 and page - last_page > 1:
                items_to_render.append("...")
            items_to_render.append(page)
            last_page = page
        
        pagination_cols = st.columns(len(items_to_render))
        for i, item in enumerate(items_to_render):
            with pagination_cols[i]:
                if item == "...":
                    st.markdown("<div style='text-align: center; margin-top: 5px;'>...</div>", unsafe_allow_html=True)
                else:
                    btn_type = "primary" if item == current_page else "secondary"
                    if st.button(str(item), type=btn_type, key=f"page_btn_{item}", use_container_width=True):
                        st.session_state.page = item
                        st.rerun()


st.title("Telega news")
header_cols = st.columns([5, 5], vertical_alignment="center")
with header_cols[0]:
    now = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
    st.caption(f"Posts updated at: {now}")
with header_cols[1]:
    if "search_query" not in st.session_state:
        st.session_state.search_query = ""
    search_query = st.text_input(label="​", placeholder="🔍 Поиск постов...", value=st.session_state.search_query, label_visibility="collapsed")
    if search_query != st.session_state.search_query:
        st.session_state.page = 1
        st.rerun()

session = db.get_session()
if not session:
    st.error("No db connection...")
    st.stop()

if "page" not in st.session_state:
    st.session_state.page = 1

base_query = session.query(Post)
if st.session_state.search_query:
    search_term = f"%{st.session_state.search_query}%"
    base_query = base_query.filter(
        or_(
            Post.post_text.ilike(search_term),
            Post.channel_name.ilike(search_term)
        )
    )

total_posts = base_query.with_entities(func.count(Post.id)).scalar()
offset = (st.session_state.page - 1) * POSTS_PER_PAGE
posts = base_query.order_by(desc(Post.post_date)).limit(POSTS_PER_PAGE).offset(offset).all()

if not posts:
    st.warning("Cant find posts")
else:
    for post in posts:
        with st.container(border=True):
            channel_color = "rgb(214, 64, 115)"
            st.markdown(f"<h5 style='color: {channel_color}; margin-bottom: -10px;'>{post.channel_name}</h5>", unsafe_allow_html=True)
            
            display_media(post)

            if post.post_text:
                st.markdown(f"<div style='margin-top: 10px;'>{post.post_text}</div>", unsafe_allow_html=True)
            
            st.markdown("---")
            footer_cols = st.columns(2)
            with footer_cols[0]:
                if post.link:
                    st.markdown(f"<a href='{post.link}' target='_blank' style='text-decoration: none; font-size: 1.2em;'>🔗 Ссылка на пост</a>", unsafe_allow_html=True)
            with footer_cols[1]:
                date_str = post.post_date.strftime('%d.%m.%Y %H:%M:%S')
                reactions_html = f"&nbsp;&nbsp;<span>❤️ {post.reactions_count}</span>" if post.reactions_count >= 0 else ""
                st.markdown(f"<div style='text-align: right;'><span>🗓️ {date_str}</span>&nbsp;&nbsp;<span>👁️ {post.views or 0}</span>{reactions_html}</div>", unsafe_allow_html=True)

display_pagination(total_posts, st.session_state.page)
session.close()