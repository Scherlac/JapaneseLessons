"""
Spike 02: Generate demo cards with the current generic card renderer.

Produces a few representative sample cards, including a long-text case to
verify Pillow multiline wrapping in the production CardRenderer.
"""

from pathlib import Path

from jlesson.models import GeneralItem, Phase, Touch, TouchIntent, TouchType
from jlesson.video.cards import CardRenderer

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def _make_item(
    source: str,
    target: str,
    pronunciation: str = "",
    extra: dict | None = None,
) -> GeneralItem:
    return GeneralItem.model_validate(
        {
            "source": {"display_text": source},
            "target": {
                "display_text": target,
                "pronunciation": pronunciation,
                "extra": extra or {},
            },
        }
    )


def _make_touch(intent: TouchIntent) -> Touch:
    return Touch.model_validate(
        {
            "touch_index": 1,
            "phase": Phase.NOUNS,
            "item": _make_item("demo", "デモ").model_dump(),
            "touch_type": TouchType.SOURCE_TARGET,
            "intent": intent,
        }
    )


def main():
    print("=== Spike 02: Generic card renderer demos ===\n")

    renderer = CardRenderer()

    cards = [
        (
            "card_intro_demo.png",
            renderer.render_card(
                item=_make_item("water", "水", "みず · mizu"),
                touch=_make_touch(TouchIntent.INTRODUCE),
                label="1/30",
                progress=0.03,
            ),
        ),
        (
            "card_recall_demo.png",
            renderer.render_card(
                item=_make_item("fish", "魚", "さかな · sakana"),
                touch=_make_touch(TouchIntent.RECALL),
                label="2/30",
                progress=0.07,
            ),
        ),
        (
            "card_long_text_demo.png",
            renderer.render_card(
                item=_make_item(
                    "This is a deliberately long English prompt to demonstrate automatic text wrapping in the generic Pillow card renderer.",
                    "これは自動改行を確認するためのかなり長い日本語テキストで、描画前に幅を測ってカード内に収める必要があります。",
                    "Kore wa jidou kaigyou o kakunin suru tame no kanari nagai nihongo tekisuto de, byouga mae ni haba o hatte kaado nai ni osameru hitsuyou ga arimasu.",
                    extra={
                        "note": "Extra fields also wrap when they exceed the safe drawing width."
                    },
                ),
                touch=None,
                label="wrap demo",
                progress=0.75,
            ),
        ),
    ]

    for name, img in cards:
        path = OUTPUT_DIR / name
        img.save(path)
        print(f"  ✓ {path.name} ({img.size[0]}x{img.size[1]})")

    print(f"\nAll cards in: {OUTPUT_DIR.resolve()}")
    print("Open them to check visual quality!")


if __name__ == "__main__":
    main()
