"""
LemonSqueezy upload tool for lesson_001 — Totoro. In Japanese. From Zero.

WORKFLOW
--------
LemonSqueezy does not support creating products via API.
Follow these steps:

  Step 1 (dashboard) — Create the product manually:
    1. Go to https://app.lemonsqueezy.com
    2. Create a new product using the values in product_config.json
    3. Set price to $9.90
    4. Upload images via the Media tab:
         - Thumbnail:   thumbnail_gpt-image-1.5_watercolor-kids_20260405_105109.png
         - Cover large: cover-large_gpt-image-1.5_watercolor-kids_20260405_221550.png
         - Gallery:     cards/grammar_it_is_the_catbus_4a74da_card_en_ja.png
    5. Note the Variant ID from the URL or via: python upload_lemonsqueezy.py list

  Step 2 (this script) — Upload the MP4 file to the variant:
    python upload_lemonsqueezy.py upload --variant-id <ID>

  Step 3 (dashboard) — Review and publish.

SETUP
-----
Add to .env in the project root (or alongside this script):

    LEMONSQUEEZY_API_KEY=your_api_key_here
    LEMONSQUEEZY_STORE_ID=your_store_id_here   # optional, used for filtering

Get your API key at: https://app.lemonsqueezy.com/settings/api

REQUIREMENTS
------------
    pip install requests python-dotenv
"""

import argparse
import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

try:
    import requests
except ImportError:
    sys.exit("ERROR: 'requests' is not installed. Run: pip install requests")

try:
    from dotenv import load_dotenv
except ImportError:
    sys.exit("ERROR: 'python-dotenv' is not installed. Run: pip install python-dotenv")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parents[4]  # output/totoro/eng-jap/my neighbor totoro/lesson_001 → root

BASE_URL = "https://api.lemonsqueezy.com/v1"

# Load .env from project root, then fall back to script directory
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(SCRIPT_DIR / ".env", override=False)

VIDEO_FILE = SCRIPT_DIR / "jp_lesson_001_totor.mp4"
CONFIG_FILE = SCRIPT_DIR / "product_config.json"


def _api_key() -> str:
    key = os.environ.get("LEMONSQUEEZY_API_KEY", "").strip()
    if not key:
        sys.exit(
            "ERROR: LEMONSQUEEZY_API_KEY not set.\n"
            "Add it to .env in the project root or alongside this script:\n"
            "  LEMONSQUEEZY_API_KEY=your_key_here"
        )
    return key


def _headers(api_key: str) -> dict:
    return {
        "Accept": "application/vnd.api+json",
        "Authorization": f"Bearer {api_key}",
    }


def _json_headers(api_key: str) -> dict:
    return {**_headers(api_key), "Content-Type": "application/vnd.api+json"}


def _check(response: requests.Response, action: str) -> dict:
    if not response.ok:
        print(f"ERROR: {action} failed — HTTP {response.status_code}")
        try:
            print(json.dumps(response.json(), indent=2))
        except Exception:
            print(response.text)
        sys.exit(1)
    return response.json()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_list(args):
    """List stores, then products and variants for each store."""
    api_key = _api_key()
    store_id = os.environ.get("LEMONSQUEEZY_STORE_ID", "").strip()

    # Stores
    url = f"{BASE_URL}/stores"
    data = _check(requests.get(url, headers=_headers(api_key)), "List stores")
    stores = data.get("data", [])
    if not stores:
        print("No stores found.")
        return

    print(f"\n{'ID':<8} {'Name':<30} Slug")
    print("-" * 60)
    for s in stores:
        a = s["attributes"]
        print(f"{s['id']:<8} {a['name']:<30} {a['slug']}")

    # Products
    params = {}
    if store_id:
        params["filter[store_id]"] = store_id

    url = f"{BASE_URL}/products"
    data = _check(requests.get(url, headers=_headers(api_key), params=params), "List products")
    products = data.get("data", [])

    print(f"\n--- PRODUCTS {'(store ' + store_id + ')' if store_id else '(all stores)'} ---")
    print(f"\n{'ID':<8} {'Name':<40} Status")
    print("-" * 60)
    for p in products:
        a = p["attributes"]
        print(f"{p['id']:<8} {a['name']:<40} {a['status']}")

    # Variants for each product
    print(f"\n--- VARIANTS ---")
    print(f"\n{'ID':<8} {'Product ID':<12} {'Name':<30} {'Price':>8}  Status")
    print("-" * 70)
    for p in products:
        url = f"{BASE_URL}/variants"
        data = _check(
            requests.get(url, headers=_headers(api_key), params={"filter[product_id]": p["id"]}),
            f"List variants for product {p['id']}",
        )
        for v in data.get("data", []):
            a = v["attributes"]
            price_cents = a.get("price", 0)
            price_str = f"${price_cents / 100:.2f}" if price_cents else "—"
            print(f"{v['id']:<8} {p['id']:<12} {a['name']:<30} {price_str:>8}  {a['status']}")


def cmd_upload(args):
    """Upload the MP4 file to a LemonSqueezy variant."""
    api_key = _api_key()
    variant_id = args.variant_id

    if not VIDEO_FILE.exists():
        sys.exit(f"ERROR: Video file not found: {VIDEO_FILE}")

    file_size_mb = VIDEO_FILE.stat().st_size / (1024 * 1024)
    print(f"Uploading: {VIDEO_FILE.name} ({file_size_mb:.1f} MB)")
    print(f"  → Variant ID: {variant_id}")
    print(f"  → Endpoint:   POST {BASE_URL}/files")

    with open(VIDEO_FILE, "rb") as f:
        response = requests.post(
            f"{BASE_URL}/files",
            headers=_headers(api_key),
            data={"variant_id": variant_id},
            files={"file": (VIDEO_FILE.name, f, "video/mp4")},
        )

    result = _check(response, "Upload file")
    file_data = result.get("data", {})
    attrs = file_data.get("attributes", {})

    print("\nUpload successful.")
    print(f"  File ID:   {file_data.get('id')}")
    print(f"  Name:      {attrs.get('name')}")
    print(f"  Size:      {attrs.get('size_formatted')}")
    print(f"  Status:    {attrs.get('status')}")
    if attrs.get("download_url"):
        print(f"  URL:       {attrs.get('download_url')}")


def cmd_config(args):
    """Print the product_config.json contents."""
    if not CONFIG_FILE.exists():
        sys.exit(f"ERROR: Config file not found: {CONFIG_FILE}")
    with open(CONFIG_FILE, encoding="utf-8") as f:
        print(f.read())


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="LemonSqueezy upload tool — lesson_001 Totoro",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    p_list = sub.add_parser("list", help="List stores, products, and variants")
    p_list.set_defaults(func=cmd_list)

    # upload
    p_upload = sub.add_parser("upload", help="Upload the MP4 file to a variant")
    p_upload.add_argument(
        "--variant-id",
        required=True,
        help="LemonSqueezy variant ID (find with: python upload_lemonsqueezy.py list)",
    )
    p_upload.set_defaults(func=cmd_upload)

    # config
    p_config = sub.add_parser("config", help="Print product_config.json")
    p_config.set_defaults(func=cmd_config)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
