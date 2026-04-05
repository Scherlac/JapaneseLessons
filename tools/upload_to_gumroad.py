"""Gumroad content uploader — list products, update metadata, and upload preview images."""

import argparse
import json
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BASE_URL = "https://api.gumroad.com/v2"


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
        f"{BASE_URL}/products/{args.product_id}",
        params={"access_token": get_token()},
        timeout=30,
    )
    data = _raise_for_gumroad(resp)
    print(json.dumps(data["product"], indent=2))


def cmd_update(args) -> None:
    """Update product fields (name, description, price_cents, published)."""
    payload: dict = {"access_token": get_token()}
    if args.name:
        payload["name"] = args.name
    if args.description:
        payload["description"] = args.description
    if args.price_cents is not None:
        payload["price"] = args.price_cents
    if args.published is not None:
        payload["published"] = "true" if args.published else "false"

    if len(payload) == 1:
        print("Nothing to update — provide at least one of: --name, --description, --price-cents, --published")
        sys.exit(1)

    resp = requests.put(
        f"{BASE_URL}/products/{args.product_id}",
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

    payload = {
        "access_token": get_token(),
        "description": description,
    }
    resp = requests.put(
        f"{BASE_URL}/products/{args.product_id}",
        data=payload,
        timeout=30,
    )
    data = _raise_for_gumroad(resp)
    print(f"Description updated for: {data['product']['name']}  ({data['product']['id']})")


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
            f"{BASE_URL}/products/{args.product_id}",
            data={"access_token": get_token()},
            files=files,
            timeout=60,
        )

    data = _raise_for_gumroad(resp)
    product = data["product"]
    thumbnail_url = product.get("thumbnail_url", "(none)")
    print(f"Preview uploaded to: {product['name']}  ({product['id']})")
    print(f"Thumbnail URL: {thumbnail_url}")


def cmd_enable(args) -> None:
    resp = requests.put(
        f"{BASE_URL}/products/{args.product_id}/enable",
        data={"access_token": get_token()},
        timeout=30,
    )
    data = _raise_for_gumroad(resp)
    print(f"Enabled: {data['product']['name']}")


def cmd_disable(args) -> None:
    resp = requests.put(
        f"{BASE_URL}/products/{args.product_id}/disable",
        data={"access_token": get_token()},
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

    # enable / disable
    p_en = sub.add_parser("enable", help="Publish a product.")
    p_en.add_argument("product_id")

    p_dis = sub.add_parser("disable", help="Unpublish a product.")
    p_dis.add_argument("product_id")

    args = parser.parse_args()

    dispatch = {
        "list": cmd_list,
        "get": cmd_get,
        "update": cmd_update,
        "description-from-file": cmd_description_from_file,
        "upload-preview": cmd_upload_preview,
        "enable": cmd_enable,
        "disable": cmd_disable,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
