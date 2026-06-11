---
title: Local LLM Tier 결정
date: 2026-06-11
author: System Architect
---

# Local LLM Tier 결정

Adaptive Memory Engine은 사용자의 RAM에 따라 로컬 LLM 모델을 자동 선택한다.

16GB 환경에서는 Qwen3 8B Q4를 사용한다.

32GB 환경에서는 Qwen3 14B Q4를 사용한다.

48GB 환경에서는 Qwen3 30B-A3B 또는 32B Q4를 사용한다.

64GB 이상에서는 Qwen3 32B Q4 또는 Q5를 사용한다.

사용자가 직접 모델을 고르는 것이 아니라 시스템이 자동 선택하는 것이 원칙이다.
