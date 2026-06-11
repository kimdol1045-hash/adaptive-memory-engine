---
title: 추출 품질 이슈
date: 2026-06-15
author: QA
---

# 추출 품질 이슈

현재 LLM 기반 Relation Extraction에서 잘못된 관계가 생성될 수 있다.

예를 들어 Person이 Tool을 USES 한다는 잘못된 관계가 생성될 수 있다.

이 이슈의 우선순위는 high이며, MVP 이전에 Validation Gate로 방지해야 한다.

관련 컴포넌트: [[Relation Extraction]]
관련 컴포넌트: [[Validation Gate]]
