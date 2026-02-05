#!/usr/bin/env python3
"""
Diagnostic script to test each step of the Topic Analyzer pipeline.
This script times each function call to identify bottlenecks.
"""

import asyncio
import time
import sys

# Test timeout in seconds (30s as threshold)
TIMEOUT = 30

def timed(name):
    """Decorator to time async functions."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            print(f"\n{'='*60}")
            print(f"⏱️  Testing: {name}")
            print(f"{'='*60}")
            start = time.time()
            try:
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=TIMEOUT)
                elapsed = time.time() - start
                print(f"✅ {name} completed in {elapsed:.2f}s")
                return result, elapsed, None
            except asyncio.TimeoutError:
                elapsed = time.time() - start
                print(f"❌ {name} TIMEOUT after {elapsed:.2f}s (limit: {TIMEOUT}s)")
                return None, elapsed, "TIMEOUT"
            except Exception as e:
                elapsed = time.time() - start
                print(f"❌ {name} ERROR after {elapsed:.2f}s: {e}")
                return None, elapsed, str(e)
        return wrapper
    return decorator


async def main():
    print("=" * 60)
    print("🔍 TOPIC ANALYZER PIPELINE DIAGNOSTIC")
    print("=" * 60)
    print(f"Timeout per step: {TIMEOUT}s")
    
    # Test abstract
    abstract = """This study investigates a novel deep learning algorithm for lung cancer detection from CT scans. We collected 5,000 CT images from Cho Ray Hospital, Vietnam (2020-2023). Our CNN achieved 94.5% sensitivity and 92.3% specificity."""
    
    results = {}
    
    # Test 1: LLM Router basic call
    @timed("Step 0: LLM Router Basic")
    async def test_llm_basic():
        from app.core.llm_router import llm_router
        return await llm_router.call("Say 'OK'", json_output=False)
    
    results["llm_basic"], _, _ = await test_llm_basic()
    
    # Test 2: LLM Router JSON call
    @timed("Step 1: LLM Router JSON")
    async def test_llm_json():
        from app.core.llm_router import llm_router
        return await llm_router.call('{"test": true}', json_output=False)
    
    results["llm_json"], _, _ = await test_llm_json()
    
    # Test 3: assess_completeness
    @timed("Step 2: assess_completeness")
    async def test_assess():
        from app.skills.input_clarifier.functions import assess_completeness
        return await assess_completeness(abstract)
    
    results["assess"], time_assess, err = await test_assess()
    
    if err:
        print(f"\n⚠️  Stopping at assess_completeness due to: {err}")
        print_summary(results)
        return
    
    # Test 4: score_novelty
    @timed("Step 3: score_novelty")
    async def test_novelty():
        from app.skills.topic_analyzer.functions import score_novelty
        return await score_novelty(abstract)
    
    results["novelty"], _, err = await test_novelty()
    
    if err:
        print(f"\n⚠️  Stopping at score_novelty due to: {err}")
        print_summary(results)
        return
    
    # Test 5: analyze_gaps
    @timed("Step 4: analyze_gaps")
    async def test_gaps():
        from app.skills.topic_analyzer.functions import analyze_gaps
        return await analyze_gaps(abstract)
    
    results["gaps"], _, err = await test_gaps()
    
    if err:
        print(f"\n⚠️  Stopping at analyze_gaps due to: {err}")
        print_summary(results)
        return
    
    # Test 6: perform_swot
    @timed("Step 5: perform_swot")
    async def test_swot():
        from app.skills.topic_analyzer.functions import perform_swot
        novelty_score = results["novelty"].get("novelty_score", 50) if results["novelty"] else 50
        return await perform_swot(abstract, novelty_score, 0, "Q2")
    
    results["swot"], _, err = await test_swot()
    
    if err:
        print(f"\n⚠️  Stopping at perform_swot due to: {err}")
        print_summary(results)
        return
    
    # Test 7: predict_publishability
    @timed("Step 6: predict_publishability")
    async def test_publish():
        from app.skills.topic_analyzer.functions import predict_publishability
        novelty_score = results["novelty"].get("novelty_score", 50) if results["novelty"] else 50
        gaps = results["gaps"].get("gaps", []) if results["gaps"] else []
        strengths = results["swot"].get("strengths", []) if results["swot"] else []
        weaknesses = results["swot"].get("weaknesses", []) if results["swot"] else []
        return await predict_publishability(abstract, novelty_score, gaps, strengths, weaknesses)
    
    results["publish"], _, err = await test_publish()
    
    if err:
        print(f"\n⚠️  Stopping at predict_publishability due to: {err}")
        print_summary(results)
        return
    
    # Test 8: suggest_improvements
    @timed("Step 7: suggest_improvements")
    async def test_suggest():
        from app.skills.topic_analyzer.functions import suggest_improvements
        novelty_score = results["novelty"].get("novelty_score", 50) if results["novelty"] else 50
        weaknesses = results["swot"].get("weaknesses", []) if results["swot"] else []
        target_tier = results["publish"].get("target_tier", "Q2") if results["publish"] else "Q2"
        return await suggest_improvements(abstract, novelty_score, weaknesses, target_tier)
    
    results["suggest"], _, _ = await test_suggest()
    
    print_summary(results)


def print_summary(results):
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    for key, val in results.items():
        status = "✅" if val else "❌"
        print(f"  {status} {key}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
