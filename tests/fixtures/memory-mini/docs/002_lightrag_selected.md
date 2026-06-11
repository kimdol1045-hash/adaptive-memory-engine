---
title: LightRAG 도입 결정
date: 2026-06-09
author: Product Architect
---

# LightRAG 도입 결정

Adaptive Memory Engine에서는 저장·검색 코어로 LightRAG를 사용하기로 결정했다.

GraphRAG 직접 구현은 MVP 범위에서 제외한다.

이유는 16GB Mac에서도 동작해야 하고, 저장·검색은 검증된 OSS를 활용하는 것이 더 현실적이기 때문이다.

관련 프로젝트: [[Adaptive Memory Engine]]
관련 도구: [[LightRAG]]
이전 검토: [[RAG Core 검토]]
