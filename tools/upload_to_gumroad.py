"""Gumroad content uploader — list products, update metadata, and upload preview images."""

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BASE_URL = "https://api.gumroad.com/v2"


def product_url(product_id: str, suffix: str = "") -> str:
    """Build a product URL with the ID properly percent-encoded."""
    return f"{BASE_URL}/products/{quote(product_id, safe='')}{suffix}"


def get_token() -> str:
    token = os.environ.get("GUMROAD_ACCESS_TOKEN", "")
    if not token:
        print("ERROR: GUMROAD_ACCESS_TOKEN not set in .env", file=sys.stderr)
        sys.exit(1)
    return token


def _raise_for_gumroad(resp: requests.Response) -> dict:
    """Parse JSON and raise on API-level failure."""
    try:
        data = resp.json()
    except Exception:
        print(f"[debug] HTTP {resp.status_code}  URL: {resp.url}", file=sys.stderr)
        print(f"[debug] Response body: {resp.text[:500]!r}", file=sys.stderr)
        resp.raise_for_status()
        raise
    if not data.get("success"):
        print(f"ERROR: {data.get('message', 'Unknown error')} (HTTP {resp.status_code})", file=sys.stderr)
        sys.exit(1)
    return data


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_list(args) -> None:
    """List all products with their IDs and names."""
    resp = requests.get(
        f"{BASE_URL}/products",
        params={"access_token": get_token()},
        timeout=30,
    )
    data = _raise_for_gumroad(resp)
    products = data.get("products", [])
    if not products:
        print("No products found.")
        return
    width = max(len(p["name"]) for p in products)
    print(f"{'Name':<{width}}  {'ID':<30}  {'Published':<10}  {'Price'}")
    print("-" * (width + 55))
    for p in products:
        published = "yes" if p.get("published") else "no"
        price = p.get("formatted_price", "?")
        print(f"{p['name']:<{width}}  {p['id']:<30}  {published:<10}  {price}")


def cmd_get(args) -> None:
    """Print full JSON detail for a product."""
    resp = requests.get(
        product_url(args.product_id),
        params={"access_token": get_token()},
        timeout=30,
    )
    data = _raise_for_gumroad(resp)
    print(json.dumps(data["product"], indent=2))


def cmd_update(args) -> None:
    """Update product fields (name, description, price_cents, published)."""
    payload: dict = {}
    if args.name:
        payload["name"] = args.name
    if args.description:
        payload["description"] = args.description
    if args.price_cents is not None:
        payload["price"] = args.price_cents
    if args.published is not None:
        payload["published"] = "true" if args.published else "false"

    if not payload:
        print("Nothing to update — provide at least one of: --name, --description, --price-cents, --published")
        sys.exit(1)

    resp = requests.put(
        product_url(args.product_id),
        params={"access_token": get_token()},
        data=payload,
        timeout=30,
    )
    data = _raise_for_gumroad(resp)
    print(f"Updated: {data['product']['name']}  ({data['product']['id']})")
    if args.verbose:
        print(json.dumps(data["product"], indent=2))


def cmd_description_from_file(args) -> None:
    """Set a product description from a Markdown file."""
    path = Path(args.file)
    if not path.exists():
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        sys.exit(1)
    description = path.read_text(encoding="utf-8")

    payload = {"description": description}
    resp = requests.put(
        product_url(args.product_id),
        params={"access_token": get_token()},
        data=payload,
        timeout=30,
    )
    data = _raise_for_gumroad(resp)
    print(f"Description updated for: {data['product']['name']}  ({data['product']['id']})")


def cmd_create(args) -> None:
    """Create a new Gumroad product and print its ID."""
    payload: dict = {
        "access_token": get_token(),
        "name": args.name,
    }
    if args.description:
        payload["description"] = args.description
    if args.price_cents is not None:
        payload["price"] = args.price_cents
    if args.published is not None:
        payload["published"] = "true" if args.published else "false"

    resp = requests.post(
        f"{BASE_URL}/products",
        data=payload,
        timeout=30,
    )
    data = _raise_for_gumroad(resp)
    product = data["product"]
    print(f"Created: {product['name']}")
    print(f"ID: {product['id']}")
    if args.verbose:
        print(json.dumps(product, indent=2))


def cmd_upload_file(args) -> None:
    """Attach a downloadable file (PDF, MP4, ZIP, …) to a product."""
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    import mimetypes
    mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"

    print(f"Uploading {file_path.name} ({file_path.stat().st_size // 1024} KB) …")
    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f, mime)}
        resp = requests.post(
            product_url(args.product_id, "/product_files"),
            params={"access_token": get_token()},
            files=files,
            timeout=300,
        )

    data = _raise_for_gumroad(resp)
    pf = data.get("product_file", {})
    print(f"File uploaded: {pf.get('file_name', file_path.name)}  (file_id: {pf.get('id', '?')})")


def cmd_upload_preview(args) -> None:
    """Upload a preview/thumbnail image to a product.

    Gumroad accepts a multipart 'preview' file on PUT /v2/products/:id.
    """
    image_path = Path(args.image)
    if not image_path.exists():
        print(f"ERROR: Image not found: {image_path}", file=sys.stderr)
        sys.exit(1)

    suffix = image_path.suffix.lower()
    mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
    mime = mime_map.get(suffix, "application/octet-stream")

    with open(image_path, "rb") as f:
        files = {"preview": (image_path.name, f, mime)}
        resp = requests.put(
            product_url(args.product_id),
            params={"access_token": get_token()},
            files=files,
            timeout=60,
        )

    data = _raise_for_gumroad(resp)
    product = data["product"]
    thumbnail_url = product.get("thumbnail_url", "(none)")
    print(f"Preview uploaded to: {product['name']}  ({product['id']})")
    print(f"Thumbnail URL: {thumbnail_url}")


def cmd_from_config(args) -> None:
    """Run a full create-or-update + thumbnail + file upload from a JSON config file."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"ERROR: Config not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    base_dir = config_path.parent
    token = get_token()

    # ── 1. Resolve product ID ────────────────────────────────────────────────
    product_id: str | None = cfg.get("product_id") or None

    if product_id is None:
        # Try to create a new product
        name = cfg.get("name", "Untitled")
        payload: dict = {"access_token": token, "name": name}
        if "description" in cfg:
            payload["description"] = cfg["description"]
        if "price_cents" in cfg:
            payload["price"] = cfg["price_cents"]
        if "published" in cfg:
            payload["published"] = "true" if cfg["published"] else "false"

        print(f"Creating product: {name} …")
        resp = requests.post(f"{BASE_URL}/products", data=payload, timeout=30)
        try:
            data = _raise_for_gumroad(resp)
            product_id = data["product"]["id"]
            print(f"Created — ID: {product_id}")
            # Write back the product_id so subsequent runs are idempotent
            cfg["product_id"] = product_id
            config_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"product_id written back to {config_path.name}")
        except (SystemExit, Exception):
            print(
                "\n──────────────────────────────────────────────────────────────\n"
                "ACTION REQUIRED: Gumroad does not support product creation via API.\n\n"
                "  1. Go to https://app.gumroad.com/products/new and create the product manually.\n"
                f"     Name: {name}\n"
                "  2. Copy the product ID from the URL or dashboard.\n"
                f"  3. Set \"product_id\" in:\n"
                f"     {config_path}\n"
                "  4. Re-run this command — it will update metadata, upload the\n"
                "     thumbnail, and attach the download files automatically.\n"
                "──────────────────────────────────────────────────────────────",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        print(f"Using existing product ID: {product_id}")
        # Update metadata if provided
        payload = {}
        if "name" in cfg:
            payload["name"] = cfg["name"]
        if "description" in cfg:
            payload["description"] = cfg["description"]
        if "price_cents" in cfg:
            payload["price"] = cfg["price_cents"]
        if "published" in cfg:
            payload["published"] = "true" if cfg["published"] else "false"
        if payload:
            print("Updating product metadata …")
            resp = requests.put(product_url(product_id), params={"access_token": token}, data=payload, timeout=30)
            _raise_for_gumroad(resp)
            print("Metadata updated.")

    # ── 2. Upload thumbnail ──────────────────────────────────────────────────
    thumbnail = cfg.get("thumbnail")
    if thumbnail:
        thumb_path = base_dir / thumbnail
        if not thumb_path.exists():
            print(f"WARNING: Thumbnail not found, skipping: {thumb_path}", file=sys.stderr)
        else:
            import mimetypes
            mime = mimetypes.guess_type(thumb_path.name)[0] or "image/png"
            print(f"Uploading thumbnail: {thumb_path.name} …")
            with open(thumb_path, "rb") as f:
                files = {"preview": (thumb_path.name, f, mime)}
                resp = requests.put(
                    product_url(product_id),
                    params={"access_token": token},
                    files=files,
                    timeout=60,
                )
            data = _raise_for_gumroad(resp)
            print(f"Thumbnail uploaded. URL: {data['product'].get('thumbnail_url', '?')}")

    # ── 3. Upload downloadable files ─────────────────────────────────────────
    import mimetypes
    for rel_file in cfg.get("files", []):
        file_path = base_dir / rel_file
        if not file_path.exists():
            print(f"WARNING: File not found, skipping: {file_path}", file=sys.stderr)
            continue
        mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        size_mb = file_path.stat().st_size / (1024 * 1024)
        print(f"Uploading file: {file_path.name} ({size_mb:.1f} MB) …")
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, mime)}
            resp = requests.post(
                product_url(product_id, "/product_files"),
                params={"access_token": token},
                files=files,
                timeout=600,
            )
        data = _raise_for_gumroad(resp)
        pf = data.get("product_file", {})
        print(f"File uploaded: {pf.get('file_name', file_path.name)}  (file_id: {pf.get('id', '?')})")

    print("\nDone.")


def cmd_enable(args) -> None:
    resp = requests.put(
        product_url(args.product_id, "/enable"),
        params={"access_token": get_token()},
        timeout=30,
    )
    data = _raise_for_gumroad(resp)
    print(f"Enabled: {data['product']['name']}")


def cmd_disable(args) -> None:
    resp = requests.put(
        product_url(args.product_id, "/disable"),
        params={"access_token": get_token()},
        timeout=30,
    )
    data = _raise_for_gumroad(resp)
    print(f"Disabled: {data['product']['name']}")


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="upload_to_gumroad",
        description="Gumroad content uploader — manage products via the Gumroad REST API.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # from-config
    p_cfg = sub.add_parser("from-config", help="Run full create/update + thumbnail + file upload from a JSON config.")
    p_cfg.add_argument("config", help="Path to the JSON config file (e.g. gumroad_upload.json).")

    # create
    p_create = sub.add_parser("create", help="Create a new product.")
    p_create.add_argument("name", help="Product name.")
    p_create.add_argument("--description", help="Description text (inline).")
    p_create.add_argument("--price-cents", dest="price_cents", type=int, help="Price in cents (0 = free).")
    p_create.add_argument("--published", type=lambda x: x.lower() == "true",
                          metavar="true|false", help="Publish immediately.")
    p_create.add_argument("--verbose", "-v", action="store_true")

    # list
    sub.add_parser("list", help="List all products with IDs and status.")

    # get
    p_get = sub.add_parser("get", help="Print full JSON details for a product.")
    p_get.add_argument("product_id", help="Product ID (from 'list' command).")

    # update
    p_update = sub.add_parser("update", help="Update product metadata.")
    p_update.add_argument("product_id", help="Product ID.")
    p_update.add_argument("--name", help="New product name.")
    p_update.add_argument("--description", help="New description text (inline).")
    p_update.add_argument("--price-cents", dest="price_cents", type=int, help="New price in cents (e.g. 1000 = $10).")
    p_update.add_argument("--published", type=lambda x: x.lower() == "true",
                          metavar="true|false", help="Set published state.")
    p_update.add_argument("--verbose", "-v", action="store_true")

    # description-from-file
    p_desc = sub.add_parser("description-from-file", help="Set description from a Markdown file.")
    p_desc.add_argument("product_id", help="Product ID.")
    p_desc.add_argument("--file", required=True, help="Path to Markdown file.")

    # upload-preview
    p_prev = sub.add_parser("upload-preview", help="Upload a preview/thumbnail image to a product.")
    p_prev.add_argument("product_id", help="Product ID.")
    p_prev.add_argument("--image", required=True, help="Path to the image file (PNG/JPG/WEBP).")

    # upload-file
    p_uf = sub.add_parser("upload-file", help="Attach a downloadable file (MP4, PDF, ZIP, …) to a product.")
    p_uf.add_argument("product_id", help="Product ID.")
    p_uf.add_argument("--file", required=True, help="Path to the file to upload.")

    # enable / disable
    p_en = sub.add_parser("enable", help="Publish a product.")
    p_en.add_argument("product_id")

    p_dis = sub.add_parser("disable", help="Unpublish a product.")
    p_dis.add_argument("product_id")

    args = parser.parse_args()

    dispatch = {
        "from-config": cmd_from_config,
        "create": cmd_create,
        "list": cmd_list,
        "get": cmd_get,
        "update": cmd_update,
        "description-from-file": cmd_description_from_file,
        "upload-preview": cmd_upload_preview,
        "upload-file": cmd_upload_file,
        "enable": cmd_enable,
        "disable": cmd_disable,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
