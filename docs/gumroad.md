# Gumroad — Marketing & Upload Reference

This document covers the complete Gumroad workflow for the Japanese Lesson series: what the API supports, what it does not, how to upload manually, and how the automation tooling is structured.

---

## Current Products

| Product Name | Permalink | Published | Price |
|---|---|---|---|
| Totoro. In Japanese. From Zero. | `nMlFJXnv3ie7siPpoMdS-A==` | Yes | 99¢ |
| Ponyo. In Japanese. From Zero. | `OxfWP_LwwvqRHOJcLKINfQ==` | Yes | 99¢ |
| Kiki. In Japanese. From Zero. | `m7YK1Bcy528XXRlkEahRvw==` | No | 99¢ |

Dashboard: https://app.gumroad.com/products
Store: https://scherlac.gumroad.com

---

## API Capabilities (Confirmed April 2026)

Authentication uses a Bearer token in the `Authorization` header or `access_token` query parameter.

### What Works

| Endpoint | Method | Status |
|---|---|---|
| `GET /v2/products` | List all products | ✅ Working |
| `GET /v2/products/:id` | Get product details | ✅ Working |
| `GET /v2/sales` | List sales | ✅ Working |
| `GET /v2/user` | Get account info | ✅ Working |
| Ping webhooks | Fire on purchase | ✅ Working |

### What Does Not Work

| Endpoint | Method | Status |
|---|---|---|
| `POST /v2/products` | Create product | ❌ 404 — not implemented |
| `PUT /v2/products/:id` | Update product | ❌ 404 — not implemented |
| `PUT /v2/products/:id` (multipart) | Upload thumbnail | ❌ 404 — not implemented |
| `POST /v2/products/:id/product_files` | Upload file | ❌ 404 — not implemented |
| `PUT /v2/products/:id/enable` | Publish product | ❌ 404 — not implemented |
| `PUT /v2/products/:id/disable` | Unpublish product | ❌ 404 — not implemented |

**Confirmed by Gumroad support (April 2026):** Write endpoints are intentionally unimplemented and there is no timeline to restore them. No partner tier or private API access exists. Product creation and all upload operations must be done through the dashboard.

---

## Manual Upload Workflow (Per Release)

For each new lesson product, complete these steps in the Gumroad dashboard:

### 1. Create the product
1. Go to https://app.gumroad.com/products/new
2. Set **Name** — use the format: `[Film]. In Japanese. From Zero.`
3. Set **Price** — 99¢ (`0.99`)
4. Leave unpublished until all assets are uploaded

### 2. Set the description
Copy **Variant 4 (Minimalist Pitch)** from the lesson's `README_marketing.md`.

The text should follow this structure:
```
[Film]. In Japanese. From Zero.

30 blocks. 6 grammar points. 120 words. One story.

You know the movie. Now learn the language.

Every noun, every verb, every sentence comes from the world of *[Film]*...

You'll learn to say:
- [sentence 1]
- [sentence 2]
...

Beginner-level. Story-driven. Yours to keep.

Buy once → Download → Learn at your own pace.
```

### 3. Upload the thumbnail
- File: `thumbnail_gpt-image-1.5_watercolor-kids_[date].png`
- Location: `output/[film]/eng-jap/[theme]/lesson_001/`
- Size: 600×600 px
- Upload via: **Product → Edit → Thumbnail**

### 4. Upload the cover image
- File: `cover-large_gpt-image-1.5_watercolor-kids_[date].png`
- Location: `output/[film]/eng-jap/[theme]/lesson_001/`
- Size: 1920×1080 px
- Upload via: **Product → Edit → Cover images → Add cover**

### 5. Attach the video file
- File: `jp_lesson_001_[film].mp4`
- Location: `output/[film]/eng-jap/[theme]/lesson_001/`
- Upload via: **Product → Edit → Content → Add a file**

### 6. Publish
Toggle published state in the dashboard once all assets are confirmed.

---

## Upload Config File

Each lesson folder contains a `gumroad_upload.json` that records all upload parameters. Once a product is created in the dashboard, set `product_id` in the config and the automation tool will handle metadata updates and file uploads if/when the API supports write operations.

**File location:** `output/[film]/eng-jap/[theme]/lesson_001/gumroad_upload.json`

**Example config:**
```json
{
  "product_id": "m7YK1Bcy528XXRlkEahRvw==",
  "name": "Kiki. In Japanese. From Zero.",
  "description": "...",
  "price_cents": 99,
  "published": false,
  "thumbnail": "thumbnail_gpt-image-1.5_watercolor-kids_20260406_082014.png",
  "files": [
    "jp_lesson_001_kiki.mp4"
  ]
}
```

### Fields

| Field | Type | Purpose |
|---|---|---|
| `product_id` | string or null | Gumroad product ID. Set after manual creation. `null` triggers the create prompt. |
| `name` | string | Product display name |
| `description` | string | Product description (plain text or Markdown) |
| `price_cents` | integer | Price in cents (99 = 99¢) |
| `published` | boolean | Target publish state |
| `thumbnail` | string | Filename of the thumbnail image (relative to config) |
| `files` | array | List of downloadable file filenames (relative to config) |

---

## Automation Tool

**Script:** `tools/upload_to_gumroad.py`

### Commands

```powershell
# List all products with IDs and status
python tools/upload_to_gumroad.py list

# Get full JSON details for a product
python tools/upload_to_gumroad.py get <product_id>

# Run full upload sequence from config (metadata + thumbnail + files)
# Currently: metadata and file upload endpoints return 404
# Will work automatically if Gumroad restores write API
python tools/upload_to_gumroad.py from-config "path/to/gumroad_upload.json"
```

### Authentication

Set `GUMROAD_ACCESS_TOKEN` in the project `.env` file:
```
GUMROAD_ACCESS_TOKEN=your_token_here
```

Get the token from: https://app.gumroad.com/settings/advanced → **Applications**

---

## Asset Generation

Thumbnails and cover images are generated with the OpenAI image API via `tools/generate_thumbnail.py`.

### Available content presets for Ghibli series

| Key | Description | Output folder |
|---|---|---|
| `totoro` | Forest creature at bus stop in rain | `output/totoro/...` |
| `totoro-sky` | Girls riding over countryside | `output/totoro/...` |
| `cat-bus` | Cat bus running at night | `output/totoro/...` |
| `ponyo` | Girl in jar on rocky shore | `output/ponyo/...` |
| `ponyo-waves` | Girl running on storm waves | `output/ponyo/...` |
| `kiki` | Witch on broomstick over city | `output/kiki/...` |
| `kiki-night` | Witch silhouetted against full moon | `output/kiki/...` |

### Commands

```powershell
# Generate thumbnail (600x600)
python tools/generate_thumbnail.py --content kiki --format thumbnail

# Generate cover image (1920x1080)
python tools/generate_thumbnail.py --content kiki --format cover-large

# Use watercolor-kids style (recommended for Ghibli series)
python tools/generate_thumbnail.py --content kiki --format thumbnail --style watercolor-kids
```

---

## Per-Product Asset Checklist

| Asset | Totoro | Ponyo | Kiki |
|---|---|---|---|
| Marketing README | ✅ | ✅ | ✅ |
| Thumbnail (600×600) | ✅ | ✅ | ✅ |
| Cover image (1920×1080) | ✅ | ✅ | ✅ |
| Upload config JSON | ✅ | — | ✅ |
| MP4 uploaded to Gumroad | ✅ | ✅ | ❌ pending |
| Thumbnail uploaded to Gumroad | ✅ | ✅ | ❌ pending |
| Published | ✅ | ✅ | ❌ pending |

---

## Gumroad Discover — Search Eligibility

Products published to Gumroad are **not automatically visible** in the Gumroad Discover search. The search index only includes products from accounts that meet eligibility requirements.

### Account-level requirements

1. **Complete payout settings** — bank or PayPal payout info must be configured
2. **Earn $100 in genuine sales** — single-product or cumulative across store
3. **Pass the risk review** — Gumroad manually reviews accounts, typically ~3 weeks after reaching $100

### Per-product requirements (after account is eligible)

1. **At least one successful sale** on that specific product
2. **Select a product category** — set via **Product → Edit → Share tab → Category**
3. **Enable ratings** — toggle on per product

### What this means for the Japanese Lesson series

Until the $100 threshold is reached, products will not appear in Gumroad search for any keyword. Customers can still purchase via direct link (e.g., `https://scherlac.gumroad.com/l/ljnia`). Promotion must be done externally (social, email, YouTube description links, etc.).

**Confirmed by Gumroad support (April 6, 2026).**

---

## Notes & Limitations

- **Product ID format** — Gumroad IDs contain `==` (base64 padding). The `upload_to_gumroad.py` tool uses `urllib.parse.quote()` to encode them correctly in URLs.
- **Webhook (Ping)** — Gumroad fires a POST to a configured URL on purchase. Useful for triggering post-purchase delivery of dynamically generated content. Configure at: **Product → Edit → Ping URL**.
- **Membership alternative** — Gumroad support suggested publishing new lessons as content posts inside a single Membership product to reduce per-release dashboard work. This changes the pricing model to subscription.
- **Future platform** — For automated product management, **Lemon Squeezy** is the recommended next platform (full write API, Stripe-backed, handles global tax).
