---
name: gemini-image-generator
description: Generate images using Google Gemini NanoBanana via browser automation. Use this skill for general-purpose AI image generation from text prompts. Includes persistent authentication and automatic environment setup.
---

# Gemini Image Generator

Gemini NanoBananaを使った汎用AI画像生成スキル。

## When to Use This Skill

Trigger when user:
- Asks to generate/create images with AI
- Mentions "Gemini image", "generate picture", "create artwork"
- Requests visual content from text descriptions
- Wants to produce illustrations or graphics

**For specific use cases, use specialized skills:**
- **LP/セールスレター画像** → `gemini-lp-generator`
- **ウェビナースライド** → `gemini-slide-generator`

## Quick Start

```bash
cd /path/to/gemini-image-generator

# 1. Check authentication
python scripts/run.py auth_manager.py status

# 2. Authenticate (if needed)
python scripts/run.py auth_manager.py setup

# 3. Generate image
python scripts/run.py image_generator.py \
  --prompt "sunset over mountains, watercolor style" \
  --output output/my_image.png
```

## How It Works

1. Navigate to `gemini.google.com`
2. Click "ツール" (Tools) button
3. Select "画像を作成" (Create Image) - Activates NanoBanana
4. Enter prompt and generate
5. Download generated image

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--prompt` | Yes | - | Image generation prompt |
| `--output` | No | `output/generated_image.png` | Output file path |
| `--show-browser` | No | False | Show browser for debugging |
| `--timeout` | No | 180 | Max wait time in seconds |

## Prompt Examples

```bash
# Landscape
python scripts/run.py image_generator.py \
  --prompt "serene sunset over snow-capped mountains, warm orange sky, photorealistic"

# Art style
python scripts/run.py image_generator.py \
  --prompt "watercolor painting of a cat sitting by window, soft colors"

# Product photo
python scripts/run.py image_generator.py \
  --prompt "professional product photography, white background, soft lighting"
```

## Authentication

This skill manages browser authentication for all Gemini-based skills:
- `gemini-slide-generator` (shares browser profile)
- `gemini-lp-generator` (shares browser profile)

```bash
# Check status
python scripts/run.py auth_manager.py status

# Setup (opens browser for Google login)
python scripts/run.py auth_manager.py setup

# Clear session
python scripts/run.py auth_manager.py clear
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Not authenticated | Run `auth_manager.py setup` |
| Timeout | Increase with `--timeout 300` |
| UI not found | Use `--show-browser` to debug |
| Generation refused | Modify prompt (avoid restricted content) |

## Data Storage

- `data/browser_profile/` - Browser session (shared with other Gemini skills)
- `data/state.json` - Authentication state
- `output/` - Generated images

## Architecture

```
scripts/
├── config.py           # Centralized settings
├── browser_utils.py    # BrowserFactory and StealthUtils
├── auth_manager.py     # Authentication management
├── image_generator.py  # Image generation
└── run.py              # Wrapper script for venv
```

## Notes

- **First generation takes longer** (browser startup)
- **Subsequent generations faster** (session reuse)
- **Authentication persists** ~7 days
- **UI selectors may break** when Gemini updates
