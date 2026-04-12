from pathlib import Path

from jlesson.llm_cache import LlmCacheTrace
from jlesson.models import CanonicalItem, GeneralItem, PartialItem, Phase
from jlesson.rcm.store import RCMStore


def _build_general_item() -> GeneralItem:
    canonical = CanonicalItem(
        id="nouns_bread_abc123",
        text="bread",
        gloss="food",
        type=Phase.NOUNS,
    )
    return GeneralItem(
        id=canonical.id,
        canonical=canonical,
        source=PartialItem(display_text="bread", tts_text="bread"),
        target=PartialItem(display_text="パン", tts_text="パン"),
        phase=Phase.NOUNS,
        block_index=0,
    )


def test_record_item_llm_usage_links_usage_to_canonical_branch_and_partials(tmp_path):
    store = RCMStore(tmp_path / "rcm.db")
    item = _build_general_item()
    trace = LlmCacheTrace(
        prompt_hash="prompt-hash",
        response_hash="response-hash",
        cache_key="prompt-hash",
        cache_hit=False,
        prompt_file="prompt.txt",
        response_file="response.json",
        step_name="lesson_planner",
        step_index=3,
        prompt_tokens=120,
        completion_tokens=45,
        total_tokens=165,
    )

    usage_record_id = store.record_item_llm_usage(trace, "eng-jap", [item])

    assert usage_record_id > 0
    totals = store.usage_totals_for_item(item.id)
    assert totals["records"] == 1
    assert totals["prompt_tokens"] == 120
    assert totals["completion_tokens"] == 45
    assert totals["total_tokens"] == 165

    branch_totals = store.usage_totals_for_item(item.id, language_code="eng-jap", relation_type="branch")
    assert branch_totals["records"] == 1
    assert branch_totals["total_tokens"] == 165

    source_totals = store.usage_totals_for_item(
        item.id,
        language_code="eng-jap",
        relation_type="partial",
        partial_role="source",
    )
    assert source_totals["records"] == 1
    assert source_totals["total_tokens"] == 165

    records = store.usage_records_for_item(item.id, language_code="eng-jap")
    relation_types = {(record["relation_type"], record["partial_role"]) for record in records}
    assert ("branch", None) in relation_types
    assert ("partial", "source") in relation_types
    assert ("partial", "target") in relation_types


def test_stats_include_llm_usage_totals(tmp_path):
    store = RCMStore(tmp_path / "rcm.db")
    item = _build_general_item()
    trace = LlmCacheTrace(
        prompt_hash="prompt-hash",
        response_hash="response-hash",
        cache_key="prompt-hash",
        cache_hit=False,
        prompt_file="prompt.txt",
        response_file="response.json",
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
    )

    store.record_item_llm_usage(trace, "eng-jap", [item])

    stats = store.stats()
    assert stats["llm_usage_records"] == 1
    assert stats["llm_usage_links"] == 4
    assert stats["llm_prompt_tokens"] == 10
    assert stats["llm_completion_tokens"] == 5
    assert stats["llm_total_tokens"] == 15