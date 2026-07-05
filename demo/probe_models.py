#!/usr/bin/env python3
"""
probe_models.py — find which candidate models your Together account can actually serve.

Being listed by models.list() does NOT mean a model is serverless; the list includes
dedicated-only and fine-tuning-base ids. This script calls each candidate with a 1-token
request and reports OK (serverless, usable now) or FAIL (with the reason).

Run:  python probe_models.py
Then set the two working ids you want (one large, one small) in run_live.py MODELS.
"""

import os
from together import Together

# Chat/instruct candidates spanning large -> small. Reasoning/vision/image models excluded
# (verbose CoT clutters the auditor parsing). Edit freely.
CANDIDATES = [
    # larger / stronger
    "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "Qwen/Qwen2.5-72B-Instruct-Turbo",
    "deepseek-ai/DeepSeek-V3.1",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "google/gemma-3-27b-it",
    "google/gemma-2-27b-it",
    "mistralai/Mistral-Small-24B-Instruct-2501",
    "meta-llama/Llama-4-Scout-17B-16E-Instruct",
    # smaller / cheaper
    "google/gemma-2-9b-it",
    "Qwen/Qwen2.5-7B-Instruct-Turbo",
    "Qwen/Qwen3-4B-Instruct-2507",
    "google/gemma-3-4b-it",
]


def main():
    if not os.environ.get("TOGETHER_API_KEY"):
        print("TOGETHER_API_KEY not set in this session.")
        return
    client = Together()
    working = []
    for mid in CANDIDATES:
        try:
            client.chat.completions.create(
                model=mid,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            print(f"OK    {mid}")
            working.append(mid)
        except Exception as e:
            msg = str(e)
            short = "not serverless" if "non-serverless" in msg or "model_not_available" in msg \
                else msg.split("\n")[0][:80]
            print(f"FAIL  {mid}  ({short})")
    print("\n--- serverless & usable now ---")
    for w in working:
        print(" ", w)
    if working:
        print("\nPick one larger + one smaller from the OK list and put them in run_live.py MODELS.")
    else:
        print("\nNone worked. Your account may need credits, or paste the full models.list() and I'll re-pick.")


if __name__ == "__main__":
    main()
