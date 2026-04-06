"""
YouTube Shorts uploader for tyxlar lesson shorts.

Uses the YouTube Data API v3 with OAuth2 authentication.

SETUP (one-time):
  1. Go to https://console.cloud.google.com/
  2. Create a project and enable "YouTube Data API v3"
  3. Create OAuth 2.0 credentials (Desktop app), download as client_secrets.json
  4. Place client_secrets.json in this directory (tools/) or pass --secrets path
  5. Run any upload command — a browser window opens for consent on first run.
     A token file is saved for reuse.

USAGE:
  # Upload all 5 shorts for one series
  python tools/upload_youtube_shorts.py upload --config "output/kiki/.../shorts/upload_config.json"

  # Upload only specific blocks
  python tools/upload_youtube_shorts.py upload --config "output/kiki/.../shorts/upload_config.json" --blocks 1 2

  # Dry-run (print what would be uploaded, no API calls)
  python tools/upload_youtube_shorts.py upload --config "..." --dry-run

  # Upload all three series at once
  python tools/upload_youtube_shorts.py upload-all

  # List your channel's recent uploads to verify
  python tools/upload_youtube_shorts.py list-uploads
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import click

# ---------------------------------------------------------------------------
# OAuth / API helpers
# ---------------------------------------------------------------------------

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
TOKEN_FILE = Path(__file__).parent / "youtube_token.json"
DEFAULT_SECRETS = Path(__file__).parent / "client_secrets.json"

# Category 27 = Education (YouTube category ID)
EDUCATION_CATEGORY = "27"

PINNED_COMMENT = (
    "👋 tyxlar is just getting started.\n"
    "We're building Japanese lessons around stories you already love — "
    "real vocabulary and grammar, straight from Ghibli scenes.\n\n"
    "These are our first videos. If something clicked (or didn't), "
    "a comment means a lot — you're shaping what comes next."
)

SERIES_CONFIGS = [
    "output/kiki/eng-jap/ghibli - Kiki's Delivery Service/lesson_001/shorts/upload_config.json",
    "output/ponyo/eng-jap/ghibli - Ponyo/lesson_001/shorts/upload_config.json",
    "output/totoro/eng-jap/my neighbor totoro/lesson_001/shorts/upload_config.json",
]


def _get_authenticated_service(secrets_path: Path):
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not secrets_path.exists():
                raise click.ClickException(
                    f"OAuth secrets file not found: {secrets_path}\n"
                    "Download it from Google Cloud Console → APIs & Services → Credentials."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), SCOPES)
            creds = flow.run_local_server(port=0)

        TOKEN_FILE.write_text(creds.to_json())

    return build(API_SERVICE_NAME, API_VERSION, credentials=creds)


def _post_comment(service, video_id: str, text: str) -> str | None:
    """Post a top-level comment and return its comment ID."""
    body = {
        "snippet": {
            "videoId": video_id,
            "topLevelComment": {
                "snippet": {"textOriginal": text}
            },
        }
    }
    response = service.commentThreads().insert(part="snippet", body=body).execute()
    comment_id = response["snippet"]["topLevelComment"]["id"]
    return comment_id


def _create_playlist(service, title: str, description: str, privacy_status: str) -> str:
    """Create a YouTube playlist and return its playlist ID."""
    body = {
        "snippet": {"title": title, "description": description, "defaultLanguage": "en"},
        "status": {"privacyStatus": privacy_status},
    }
    response = service.playlists().insert(part="snippet,status", body=body).execute()
    return response["id"]


def _add_to_playlist(service, playlist_id: str, video_id: str, position: int) -> None:
    """Add a video to a playlist at a specific position (0-indexed)."""
    body = {
        "snippet": {
            "playlistId": playlist_id,
            "position": position,
            "resourceId": {"kind": "youtube#video", "videoId": video_id},
        }
    }
    service.playlistItems().insert(part="snippet", body=body).execute()


def _make_vertical_thumbnail(source: Path) -> Path:
    """Return a 1080x1920 vertical version of the thumbnail, cached alongside the original."""
    from PIL import Image, ImageFilter
    dest = source.parent / (source.stem + "_vertical.jpg")
    if dest.exists():
        return dest
    img = Image.open(source).convert("RGB")
    # Scale to fill 1080 wide, keeping aspect ratio, then center-crop to 1920 tall
    target_w, target_h = 1080, 1920
    # Blurred background: scale to fill the full 1080×1920
    bg_scale = max(target_w / img.width, target_h / img.height)
    bg = img.resize(
        (int(img.width * bg_scale), int(img.height * bg_scale)),
        Image.LANCZOS,
    )
    bg = bg.crop((
        (bg.width - target_w) // 2,
        (bg.height - target_h) // 2,
        (bg.width - target_w) // 2 + target_w,
        (bg.height - target_h) // 2 + target_h,
    ))
    bg = bg.filter(ImageFilter.GaussianBlur(radius=30))
    # darken background
    from PIL import ImageEnhance
    bg = ImageEnhance.Brightness(bg).enhance(0.45)
    # Foreground: fit the square art to 900×900 centered
    art_size = 900
    art = img.resize((art_size, art_size), Image.LANCZOS)
    paste_x = (target_w - art_size) // 2
    paste_y = (target_h - art_size) // 2
    bg.paste(art, (paste_x, paste_y))
    bg.save(dest, "JPEG", quality=92)
    return dest


def _upload_video(
    service,
    video_path: Path,
    title: str,
    description: str,
    tags: list[str],
    thumbnail_path: Path | None,
    category_id: str,
    privacy_status: str,
    made_for_kids: bool,
    dry_run: bool,
) -> str | None:
    from googleapiclient.http import MediaFileUpload

    if dry_run:
        click.echo(f"  [DRY-RUN] Would upload: {video_path.name}")
        click.echo(f"            Title: {title}")
        if thumbnail_path:
            click.echo(f"            Thumbnail: {thumbnail_path.name}")
        return None

    click.echo(f"  Uploading: {video_path.name} ({video_path.stat().st_size // (1024*1024)} MB)")

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id,
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": made_for_kids,
        },
    }

    media = MediaFileUpload(str(video_path), chunksize=4 * 1024 * 1024, resumable=True)
    request = service.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            click.echo(f"    {pct}%", nl=False)
            click.echo("\r", nl=False)

    video_id = response["id"]
    click.echo(f"    Uploaded → https://youtu.be/{video_id}")

    # Set thumbnail — convert to vertical 9:16 for Shorts
    if thumbnail_path and thumbnail_path.exists():
        try:
            from googleapiclient.http import MediaFileUpload as MFU
            vertical_thumb = _make_vertical_thumbnail(thumbnail_path)
            thumb_media = MFU(str(vertical_thumb), mimetype="image/jpeg")
            service.thumbnails().set(videoId=video_id, media_body=thumb_media).execute()
            click.echo(f"    Thumbnail set (9:16): {vertical_thumb.name}")
        except Exception as e:
            click.echo(f"    WARN: thumbnail upload failed: {e}")

    return video_id


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.group()
def cli():
    """Upload tyxlar YouTube Shorts via the YouTube Data API v3."""


@cli.command()
@click.option(
    "--config", "config_path", required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to a shorts/upload_config.json file.",
)
@click.option(
    "--blocks", multiple=True, type=int, default=None,
    help="Block numbers to upload (default: all). Repeat: --blocks 1 --blocks 2",
)
@click.option(
    "--privacy", default=None,
    type=click.Choice(["public", "unlisted", "private"]),
    help="Override privacy status from config.",
)
@click.option(
    "--secrets", "secrets_path",
    default=str(DEFAULT_SECRETS),
    type=click.Path(path_type=Path),
    help="Path to client_secrets.json (default: tools/client_secrets.json).",
)
@click.option("--dry-run", is_flag=True, help="Print upload plan without making API calls.")
def upload(
    config_path: Path,
    blocks: tuple[int, ...],
    privacy: str | None,
    secrets_path: Path,
    dry_run: bool,
):
    """Upload Shorts for one series from its upload_config.json."""
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    shorts_dir = config_path.parent

    thumbnail_rel = cfg.get("thumbnail")
    thumbnail_path = (shorts_dir / thumbnail_rel).resolve() if thumbnail_rel else None

    target_blocks = set(blocks) if blocks else None
    service = None if dry_run else _get_authenticated_service(secrets_path)

    uploaded = []
    for short in cfg["shorts"]:
        if target_blocks and short["block"] not in target_blocks:
            continue

        video_path = shorts_dir / short["file"]
        if not video_path.exists():
            click.echo(f"  WARN: file not found, skipping: {video_path.name}")
            continue

        click.echo(f"\nBlock {short['block']}: {short['title'][:60]}...")

        vid_id = _upload_video(
            service=service,
            video_path=video_path,
            title=short["title"],
            description=short["description"],
            tags=cfg.get("tags", []),
            thumbnail_path=thumbnail_path,
            category_id=cfg.get("category_id", EDUCATION_CATEGORY),
            privacy_status=privacy or cfg.get("privacy_status", "public"),
            made_for_kids=cfg.get("made_for_kids", False),
            dry_run=dry_run,
        )
        if vid_id:
            entry = {"block": short["block"], "video_id": vid_id, "url": f"https://youtu.be/{vid_id}"}
            # Add to playlist if one exists in uploaded.json
            results_path = shorts_dir / "uploaded.json"
            existing = json.loads(results_path.read_text()) if results_path.exists() else []
            playlist_id = next((e.get("playlist_id") for e in existing if e.get("playlist_id")), None)
            if playlist_id:
                try:
                    position = short["block"] - 1
                    _add_to_playlist(service, playlist_id, vid_id, position)
                    click.echo(f"    Added to playlist (position {short['block']})")
                except Exception as e:
                    click.echo(f"    WARN: playlist add failed: {e}")
            # Post pinned comment
            try:
                comment_id = _post_comment(service, vid_id, PINNED_COMMENT)
                entry["comment_id"] = comment_id
                click.echo(f"    Comment posted (pin it in YouTube Studio: https://studio.youtube.com/video/{vid_id}/comments)")
            except Exception as e:
                click.echo(f"    WARN: comment post failed: {e}")
            uploaded.append(entry)
            time.sleep(2)  # polite pause between uploads

    if uploaded:
        results_path = shorts_dir / "uploaded.json"
        existing = json.loads(results_path.read_text()) if results_path.exists() else []
        existing.extend(uploaded)
        results_path.write_text(json.dumps(existing, indent=2))
        click.echo(f"\nSaved upload log → {results_path}")

    click.echo(f"\nDone. {len(uploaded)} video(s) uploaded.")


@cli.command("upload-all")
@click.option("--privacy", default=None, type=click.Choice(["public", "unlisted", "private"]))
@click.option("--secrets", "secrets_path", default=str(DEFAULT_SECRETS), type=click.Path(path_type=Path))
@click.option("--dry-run", is_flag=True)
@click.pass_context
def upload_all(ctx, privacy, secrets_path, dry_run):
    """Upload all three series (kiki, ponyo, totoro) in sequence."""
    root = Path(__file__).parent.parent
    for rel_path in SERIES_CONFIGS:
        cfg_path = root / rel_path
        if not cfg_path.exists():
            click.echo(f"WARN: config not found, skipping: {cfg_path}")
            continue
        click.echo(f"\n{'='*60}")
        click.echo(f"Series: {cfg_path.parent.parent.parent.parent.name.upper()}")
        click.echo(f"{'='*60}")
        ctx.invoke(upload, config_path=cfg_path, blocks=(), privacy=privacy, secrets_path=secrets_path, dry_run=dry_run)


@cli.command("update-metadata")
@click.option(
    "--config", "config_path", required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to the shorts/upload_config.json for the series.",
)
@click.option(
    "--secrets", "secrets_path",
    default=str(DEFAULT_SECRETS),
    type=click.Path(path_type=Path),
)
@click.option("--dry-run", is_flag=True)
def update_metadata(config_path: Path, secrets_path: Path, dry_run: bool):
    """Update title/description/tags of already-uploaded videos (reads uploaded.json)."""
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    shorts_dir = config_path.parent
    uploaded_path = shorts_dir / "uploaded.json"

    if not uploaded_path.exists():
        raise click.ClickException(f"No uploaded.json found at {uploaded_path}")

    uploaded = json.loads(uploaded_path.read_text())
    block_to_video_id = {entry["block"]: entry["video_id"] for entry in uploaded}
    block_to_short = {s["block"]: s for s in cfg["shorts"]}

    service = None if dry_run else _get_authenticated_service(secrets_path)

    for block_num, video_id in sorted(block_to_video_id.items()):
        short = block_to_short.get(block_num)
        if not short:
            click.echo(f"  WARN: no config entry for block {block_num}, skipping")
            continue

        click.echo(f"\nBlock {block_num} ({video_id}): {short['title'][:60]}...")

        if dry_run:
            click.echo(f"  [DRY-RUN] Would update title + description + tags")
            continue

        body = {
            "id": video_id,
            "snippet": {
                "title": short["title"],
                "description": short["description"],
                "tags": cfg.get("tags", []),
                "categoryId": cfg.get("category_id", EDUCATION_CATEGORY),
                "defaultLanguage": "en",
            },
        }
        service.videos().update(part="snippet", body=body).execute()
        click.echo(f"  Updated → https://youtu.be/{video_id}")
        # Re-set thumbnail as vertical 9:16
        thumbnail_rel = cfg.get("thumbnail")
        if thumbnail_rel:
            thumbnail_path = (config_path.parent / thumbnail_rel).resolve()
            try:
                from googleapiclient.http import MediaFileUpload as MFU
                vertical_thumb = _make_vertical_thumbnail(thumbnail_path)
                thumb_media = MFU(str(vertical_thumb), mimetype="image/jpeg")
                service.thumbnails().set(videoId=video_id, media_body=thumb_media).execute()
                click.echo(f"  Thumbnail updated (9:16): {vertical_thumb.name}")
            except Exception as e:
                click.echo(f"  WARN: thumbnail update failed: {e}")
        time.sleep(1)

    click.echo("\nDone.")


@cli.command("create-playlist")
@click.option(
    "--config", "config_path", required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to the shorts/upload_config.json for the series.",
)
@click.option(
    "--privacy", default="public",
    type=click.Choice(["public", "unlisted", "private"]),
    show_default=True,
)
@click.option(
    "--secrets", "secrets_path",
    default=str(DEFAULT_SECRETS),
    type=click.Path(path_type=Path),
)
@click.option("--dry-run", is_flag=True)
def create_playlist(config_path: Path, privacy: str, secrets_path: Path, dry_run: bool):
    """Create a YouTube playlist for a series and add all uploaded videos in block order."""
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    shorts_dir = config_path.parent
    uploaded_path = shorts_dir / "uploaded.json"

    if not uploaded_path.exists():
        raise click.ClickException(f"No uploaded.json found at {uploaded_path}")

    uploaded = json.loads(uploaded_path.read_text())

    # Build title from config title_template if available
    series_title = cfg.get("title_template", "").replace(" Block {block}", "").replace(" | tyxlar", "").strip()
    if not series_title:
        series_title = cfg["series"].title()
    playlist_title = f"{series_title} | Japanese Lesson | tyxlar"
    playlist_desc = (
        f"Learn Japanese through {series_title} — real vocabulary and grammar, "
        f"scene by scene.\n\n"
        f"Get the full lesson (30 blocks, audio flashcards, Anki deck):\n"
        f"{cfg.get('product_url', '')}"
    )

    click.echo(f"Playlist title: {playlist_title}")
    click.echo(f"Videos to add: {len(uploaded)} (in block order)")

    if dry_run:
        for entry in sorted(uploaded, key=lambda e: e["block"]):
            click.echo(f"  [{entry['block']}] {entry['video_id']} → {entry['url']}")
        click.echo("[DRY-RUN] No playlist created.")
        return

    service = _get_authenticated_service(secrets_path)
    playlist_id = _create_playlist(service, playlist_title, playlist_desc, privacy)
    click.echo(f"Created playlist: https://www.youtube.com/playlist?list={playlist_id}")

    for entry in sorted(uploaded, key=lambda e: e["block"]):
        position = entry["block"] - 1
        try:
            _add_to_playlist(service, playlist_id, entry["video_id"], position)
            click.echo(f"  Added block {entry['block']} at position {entry['block']}")
        except Exception as e:
            click.echo(f"  WARN: block {entry['block']} failed: {e}")
        time.sleep(0.5)

    # Save playlist_id into uploaded.json for future uploads to auto-add
    for entry in uploaded:
        entry["playlist_id"] = playlist_id
    uploaded_path.write_text(json.dumps(uploaded, indent=2))
    click.echo(f"\nPlaylist ID saved to uploaded.json for future auto-adds.")
    click.echo(f"Done: https://www.youtube.com/playlist?list={playlist_id}")
    # Playlist thumbnail must be set manually (YouTube API limitation)
    thumbnail_rel = cfg.get("thumbnail")
    if thumbnail_rel:
        thumb_abs = (config_path.parent / thumbnail_rel).resolve()
        click.echo(f"\n⚠️  Set playlist thumbnail manually in YouTube Studio:")
        click.echo(f"   Studio: https://studio.youtube.com/playlist/{playlist_id}/edit")
        click.echo(f"   Image : {thumb_abs}")


@cli.command("post-comments")
@click.option(
    "--config", "config_path", required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to the shorts/upload_config.json for the series.",
)
@click.option(
    "--secrets", "secrets_path",
    default=str(DEFAULT_SECRETS),
    type=click.Path(path_type=Path),
)
@click.option("--dry-run", is_flag=True)
def post_comments(config_path: Path, secrets_path: Path, dry_run: bool):
    """Post the pinned welcome comment on all already-uploaded videos (reads uploaded.json)."""
    shorts_dir = config_path.parent
    uploaded_path = shorts_dir / "uploaded.json"

    if not uploaded_path.exists():
        raise click.ClickException(f"No uploaded.json found at {uploaded_path}")

    uploaded = json.loads(uploaded_path.read_text())
    service = None if dry_run else _get_authenticated_service(secrets_path)

    for entry in uploaded:
        video_id = entry["video_id"]
        if entry.get("comment_id"):
            click.echo(f"  Block {entry['block']} ({video_id}): comment already posted, skipping")
            continue

        click.echo(f"  Block {entry['block']} ({video_id}): posting comment...")
        if dry_run:
            click.echo(f"    [DRY-RUN] Would post:\n    {PINNED_COMMENT[:80]}...")
            continue

        try:
            comment_id = _post_comment(service, video_id, PINNED_COMMENT)
            entry["comment_id"] = comment_id
            click.echo(f"    Posted → pin at: https://studio.youtube.com/video/{video_id}/comments")
        except Exception as e:
            click.echo(f"    WARN: failed: {e}")
        time.sleep(1)

    uploaded_path.write_text(json.dumps(uploaded, indent=2))
    click.echo("\nDone. Remember to pin comments manually in YouTube Studio.")


@cli.command("list-uploads")
@click.option("--secrets", "secrets_path", default=str(DEFAULT_SECRETS), type=click.Path(path_type=Path))
@click.option("--max-results", default=10, show_default=True)
def list_uploads(secrets_path: Path, max_results: int):
    """List your channel's most recent uploads."""
    service = _get_authenticated_service(secrets_path)

    channels = service.channels().list(part="contentDetails", mine=True).execute()
    uploads_playlist = channels["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    items = service.playlistItems().list(
        part="snippet",
        playlistId=uploads_playlist,
        maxResults=max_results,
    ).execute()

    click.echo(f"\nLast {max_results} uploads:")
    for item in items["items"]:
        snip = item["snippet"]
        vid_id = snip["resourceId"]["videoId"]
        click.echo(f"  [{snip['publishedAt'][:10]}] {snip['title']}")
        click.echo(f"           https://youtu.be/{vid_id}")


if __name__ == "__main__":
    cli()
