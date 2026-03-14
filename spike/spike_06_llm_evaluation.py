#!/usr/bin/env python3
"""
Spike 06: LLM Integration Evaluation

Tests the LLM client with different providers and models to evaluate:
- Response quality for Japanese sentence generation
- Speed and reliability
- Error handling and fallbacks
- Cost estimation for different providers

Usage:
    python spike/spike_06_llm_evaluation.py

Requires:
- openai package installed
- Ollama server running (for local tests)
- Optional: OpenAI API key for cloud tests
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from llm_client import ask_llm_json, LLMClient
from config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL

def test_sentence_generation(client: LLMClient, verb: Dict, noun: Dict, person: str, tense: str, polarity: str) -> Dict[str, Any]:
    """Test generating a single natural sentence."""
    prompt = f"""
Generate a natural Japanese sentence using the following vocabulary and grammar pattern.

Vocabulary:
- Verb: {verb['english']} ({verb['japanese']}, {verb['romaji']})
- Noun: {noun['english']} ({noun['kanji']}, {noun['romaji']})
- Person: {person}

Grammar requirements:
- Tense: {tense}
- Polarity: {polarity}
- Use polite form (ます-form)
- Make it a natural, contextual sentence (not just "I eat fish")

Return a JSON object with:
{{
  "english": "Natural English sentence",
  "japanese": "自然な日本語の文",
  "romaji": "Nihongo na bun",
  "context": "Brief explanation of grammar point or context"
}}

Make the sentence natural and varied - avoid formulaic patterns.
""".strip()

    start_time = time.time()
    try:
        response = client.generate_json(prompt)
        elapsed = time.time() - start_time
        return {
            "success": True,
            "response": response,
            "time": elapsed,
            "error": None
        }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "success": False,
            "response": None,
            "time": elapsed,
            "error": str(e)
        }

def evaluate_provider(provider_name: str, base_url: str, api_key: str, model: str, test_cases: List[Dict]) -> Dict[str, Any]:
    """Evaluate a specific LLM provider."""
    print(f"\n🔬 Testing {provider_name} ({model})")
    print("=" * 50)

    # Create client with specific config
    client = LLMClient()
    client.client.base_url = base_url
    client.client.api_key = api_key
    client.model = model

    results = []
    total_time = 0
    success_count = 0

    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}/{len(test_cases)}: {test_case['verb']['english']} + {test_case['noun']['english']} ({test_case['person']}/{test_case['tense']}/{test_case['polarity']})")

        result = test_sentence_generation(
            client,
            test_case['verb'],
            test_case['noun'],
            test_case['person'],
            test_case['tense'],
            test_case['polarity']
        )

        results.append(result)
        total_time += result['time']

        if result['success']:
            success_count += 1
            print("  ✅ Success"            print(f"     English: {result['response']['english']}")
            print(f"     Japanese: {result['response']['japanese']}")
            print(f"     Romaji: {result['response']['romaji']}")
            print(f"     Context: {result['response'].get('context', 'N/A')}")
        else:
            print(f"  ❌ Failed: {result['error']}")

        print(".2f"
    # Summary
    avg_time = total_time / len(test_cases) if test_cases else 0
    success_rate = success_count / len(test_cases) * 100 if test_cases else 0

    summary = {
        "provider": provider_name,
        "model": model,
        "total_tests": len(test_cases),
        "success_count": success_count,
        "success_rate": success_rate,
        "total_time": total_time,
        "avg_time": avg_time,
        "results": results
    }

    print("
📊 Summary:"    print(f"   Success Rate: {success_rate:.1f}%")
    print(".2f"    print(".2f"
    return summary

def main():
    """Run LLM evaluation spike."""
    print("🚀 Spike 06: LLM Integration Evaluation")
    print("Testing different LLM providers for Japanese sentence generation\n")

    # Test vocabulary
    test_vocab = {
        "verbs": [
            {"english": "eat", "japanese": "たべる", "romaji": "taberu", "type": "る-verb", "masu_form": "たべます"},
            {"english": "drink", "japanese": "のむ", "romaji": "nomu", "type": "う-verb", "masu_form": "のみます"},
            {"english": "cook", "japanese": "りょうりする", "romaji": "ryouri suru", "type": "irregular", "masu_form": "りょうりします"},
        ],
        "nouns": [
            {"english": "fish", "kanji": "魚", "romaji": "sakana"},
            {"english": "water", "kanji": "水", "romaji": "mizu"},
            {"english": "meat", "kanji": "肉", "romaji": "niku"},
        ]
    }

    # Test cases
    test_cases = []
    persons = ["I", "you (polite)", "he/she"]
    tenses = ["present", "past"]
    polarities = ["affirmative", "negative"]

    for verb in test_vocab["verbs"][:2]:  # Test first 2 verbs
        for noun in test_vocab["nouns"][:2]:  # Test first 2 nouns
            for person in persons[:2]:  # Test first 2 persons
                for tense in tenses:
                    for polarity in polarities:
                        test_cases.append({
                            "verb": verb,
                            "noun": noun,
                            "person": person,
                            "tense": tense,
                            "polarity": polarity
                        })

    print(f"📋 Test Plan: {len(test_cases)} sentence generation tests")
    print(f"   Verbs: {len(test_vocab['verbs'][:2])}")
    print(f"   Nouns: {len(test_vocab['nouns'][:2])}")
    print(f"   Persons: {len(persons[:2])}")
    print(f"   Tenses: {len(tenses)}")
    print(f"   Polarities: {len(polarities)}")

    # Test providers
    providers = []

    # 1. Ollama (local, default)
    providers.append({
        "name": "Ollama (Local)",
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",
        "model": "qwen2.5:14b"
    })

    # 2. OpenAI (if API key available)
    import os
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        providers.append({
            "name": "OpenAI (Cloud)",
            "base_url": "https://api.openai.com/v1",
            "api_key": openai_key,
            "model": "gpt-4o-mini"
        })
    else:
        print("⚠️  OpenAI API key not found, skipping OpenAI tests")

    # 3. Alternative Ollama model
    providers.append({
        "name": "Ollama (Gemma)",
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",
        "model": "gemma3:12b"
    })

    # Run evaluations
    all_results = []
    for provider in providers:
        try:
            result = evaluate_provider(
                provider["name"],
                provider["base_url"],
                provider["api_key"],
                provider["model"],
                test_cases
            )
            all_results.append(result)
        except Exception as e:
            print(f"❌ Failed to test {provider['name']}: {e}")
            all_results.append({
                "provider": provider["name"],
                "error": str(e),
                "results": []
            })

    # Overall comparison
    print("\n" + "="*60)
    print("🏆 OVERALL COMPARISON")
    print("="*60)

    successful_providers = [r for r in all_results if "error" not in r]

    if successful_providers:
        # Sort by success rate, then by speed
        successful_providers.sort(key=lambda x: (-x["success_rate"], x["avg_time"]))

        print("<10")
        print("-" * 60)
        for result in successful_providers:
            print("<10")
    else:
        print("❌ No providers completed successfully")

    # Save detailed results
    output_dir = Path("spike/output")
    output_dir.mkdir(exist_ok=True)

    results_file = output_dir / "spike_06_llm_evaluation.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Detailed results saved to: {results_file}")

    # Recommendations
    print("\n" + "="*60)
    print("💡 RECOMMENDATIONS")
    print("="*60)

    if successful_providers:
        best = successful_providers[0]
        print(f"🏅 Best Overall: {best['provider']}")
        print(f"   Success Rate: {best['success_rate']:.1f}%")
        print(".2f"
        if best['success_rate'] >= 90:
            print("   ✅ Excellent performance - ready for production")
        elif best['success_rate'] >= 75:
            print("   ⚠️  Good performance - consider as backup")
        else:
            print("   ❌ Poor performance - needs improvement")

        # Cost analysis
        if "OpenAI" in best['provider']:
            estimated_cost = len(test_cases) * 0.001  # Rough estimate for gpt-4o-mini
            print(".4f"        elif "Ollama" in best['provider']:
            print("   💰 Cost: Free (local hardware)")
    else:
        print("❌ No working providers found")
        print("   🔧 Check Ollama installation and model downloads")
        print("   🔑 Verify API keys for cloud providers")

if __name__ == "__main__":
    main()