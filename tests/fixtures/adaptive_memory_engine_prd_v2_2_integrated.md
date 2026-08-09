---
title: Adaptive Memory Engine PRD v2.2 Integrated
project: Adaptive Memory Engine
---

# Adaptive Memory Engine PRD v2.2 Integrated

## Executive Summary

Adaptive Memory Engine은 분산된 원본을 Bronze, Silver, Gold의 3계층 Memory Pipeline으로 구조화하고 LightRAG 저장·검색 코어를 통해 장기 기억으로 조회하는 Local-First Memory Infrastructure다.

## Product Definition

제품의 핵심 자산은 교체 가능한 LightRAG 자체가 아니라 Bronze → Silver → Gold Memory Pipeline과 공통 Memory Schema다. Memory API는 OpenClaw와 Hermes 같은 에이전트가 이 기억을 사용하게 한다.

## Problem Statement

여러 도구에 정보가 남아 있어도 시간이 지나면 결정의 근거와 맥락이 사라진다. Adaptive Memory Engine은 분산된 정보를 출처가 있는 장기 기억으로 변환한다.

## Product Goals

원본 보존, 검증 가능한 구조화, 현재 결정과 과거 결정의 구분, 근거가 있는 답변, 로컬 데이터 통제를 목표로 한다.

## Core Principles

Local First를 결정한다. 개인 데이터, 회사 데이터, 프로젝트 히스토리를 보호하고 민감 데이터가 클라우드에 기본 저장되지 않게 하며 사용자가 로컬 데이터 통제권을 유지한다.

Validation First를 결정한다. LLM 환각을 줄이고 원문 span 기반 검증과 검증된 사실만 Memory에 저장하는 정책을 사용한다.

## 8. Memory Architecture

## 8.1 Bronze Layer

Bronze는 원본 저장 계층이다. 원본과 출처를 보존하고 재추출 가능성, 검증 기준, 감사 가능성을 제공한다.

## 8.2 Silver Layer

Silver는 원본에서 Entity, Relation, Decision, Meeting, Issue, Action을 추출하여 구조화된 Fact를 만든다.

## 8.3 Gold Layer

Gold는 검증된 Entity, Relation, Decision, Rationale을 정규화하여 그래프와 타임라인으로 구성한다. Gold Memory는 current와 supersedes를 보존한다.

## 9. Knowledge Storage

### 9.2 LightRAG Integration

LightRAG는 저장·검색 코어로 채택한다. 16GB 환경 대응, 검증된 OSS 활용, GraphRAG 직접 구현 대비 구현 범위 축소, 빠른 MVP 검증이 근거다. 저장·검색은 LightRAG에 맡기고 AME는 추출·검증 계층에 집중한다. Gold 데이터는 custom_kg로 변환한다.

## 10. Hardware-Adaptive Local LLM Strategy

RAM에 따라 로컬 LLM을 선택한다. 16GB는 Qwen3 8B Q4, 32GB 이상은 더 큰 모델을 사용할 수 있으며 로컬 실행을 기본으로 한다.

## 11. Extraction Engine

LightRAG 내장 추출에만 의존하지 않는다. 저사양 환경에서도 Grounding, Type Gate, Confidence Validation을 적용하는 자체 추출 파이프라인이 필요하다.

### 11.4 Validation Gate

Validation Gate는 원문 span Grounding, Type Gate, confidence threshold를 통과한 사실만 Gold에 반영한다.

## 12. Obsidian Export

Obsidian Export 필요 결정을 유지한다. 사용자는 그래프DB를 직접 보지 않으므로 Gold Memory를 사람이 검토 가능한 Markdown 노트와 Obsidian Vault로 제공한다.

## 13. OpenClaw Integration Spec

OpenClaw는 Adaptive Memory Engine을 장기 기억 계층으로 사용하고 LightRAG를 통해 현재 정책과 근거를 조회한다.

### 13.3 OpenClaw Memory Tools

OpenClaw Memory API는 search, query, graph, decisions, timeline, why 도구를 제공한다.

## 14. Hermes Integration Spec

Hermes는 동일한 Memory API와 Memory Schema를 사용해 Bronze, Silver, Gold, LightRAG 기억을 조회한다.

## 15. MVP Scope

MVP 범위는 Markdown, Obsidian, Bronze, Silver, Gold, LightRAG와 Obsidian Export까지다. Slack Connector MVP 제외 결정을 유지하고 Memory Pipeline 검증과 Markdown/Obsidian 기반 수직 슬라이스 검증을 먼저 수행한다. Connector Expansion 단계에서 Slack Connector, Jira, GitHub를 추가한다.

## 16. Success Criteria

원본 출처를 보존하고, 검증된 Gold를 구축하며, LightRAG custom_kg와 Memory API를 통해 근거와 현재성을 포함한 답을 반환해야 한다.
