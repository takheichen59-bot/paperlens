# C阶段真实语料回归

{"submitted": 10, "success": 4, "partial": 5, "failed": 0, "skipped": 1, "failed_internal_classification": 0, "failed_content_or_processing": 0}

methods长度200–3000：6/10（长度不等于语义可用）；sections含UNKNOWN：9/10，解析成功9篇；未解析篇不记作已判定无UNKNOWN。
P1为5篇unresolved；本次6篇unresolved。UNKNOWN同时承载Introduction和无标题前置文本，不等于全部都是标题漏识别。

C项需优先处理标题识别，而非仅多栏排序。

| paper_id | 原→新状态 | methods长度 | conclusions长度 | UNKNOWN标题 | caption标记数 |
|---|---|---:|---:|---|---:|
| arxiv:2501.00534 | partial→partial | 0 | 3684 | (untitled) | 4 |
| arxiv:2501.00561 | partial→success | 2240 | 1312 | (untitled), INTRODUCTION | 6 |
| arxiv:2501.00564 | partial→partial | 2511 | 688 | (untitled), 1. Introduction | 8 |
| arxiv:2501.00589 | partial→success | 2197 | 2318 | (untitled), INTRODUCTION | 13 |
| arxiv:2501.00591 | partial→partial | 0 | 0 | (untitled) | 4 |
| arxiv:2501.00600 | partial→partial | 0 | 185 | (untitled), 270 MPa, 270 MPa, 270 MPa | 24 |
| arxiv:2501.00620 | partial→partial | 2919 | 2046 | (untitled), INTRODUCTION, 2 Bαβ(x, t) | 14 |
| arxiv:2501.00679 | success→success | 1706 | 5205 | (untitled), INTRODUCTION, 3 (a–e) present the one-dimensional temperature proﬁles | 66 |
| arxiv:2501.00680 | success→success | 1676 | 405 | (untitled), 1 Introduction, 3.1 Nanoparticle with opposite faces terminated either with, 3.3 Nanoparticle with mixed termiations | 5 |

## 00589锚点对照

修复前methods开头：
```text
(空)
```
修复后methods开头：
```text
Lennard-Jones surrogate model— To develop the interac-
tion potential between elements of multicomponent alloys of
Cu0.46Zr0.46Al0.08 consisting of N = 150 atoms with unit mass
(m), we use a surrogate interaction described by the Lennard-
Jones (LJ) potential as

where ε and σ are the energy scale and interaction range,
respectively.
The potential is truncated and shifted at
the cutoff distance rcut, i j = 2σαi,βj.
We specify the
atom index by Roman indices and the type by Greek in-
dices.
We us
```
M14前methods候选 2197字符，开头：
```text
Lennard-Jones surrogate model— To develop the interac-
tion potential between elements of multicomponent alloys of
Cu0.46Zr0.46Al0.08 consisting of N = 150 atoms with unit mass
(m), we use a surrogate interaction described by the Lennard-
Jones (LJ) potential as

where ε and σ are the energy scale and interaction range,
respectively.
The potential is truncated and shifted at
the cutoff distance rcut, i j = 2σαi,βj.
We specify the
atom index by Roman indices and the type by Greek in-
dices.
We us
```
修复前conclusions开头：
```text
This work introduces an efﬁcient approach for developing
machine learning interatomic potentials (MLIPs) for metallic
glasses, applicable to any multicomponent system. As a test
case, we apply it to the ternary Cu-Zr-Al system. The method
combines a Lennard-Jones surrogate model for accelerated
swap Monte Carlo sampling of the potential energy landscape
(PEL) with single-point DFT corrections. Structural analysis
reveals that these DFT corrections do not signiﬁcantly alter
the underlying LJ-base
```
修复后conclusions开头：
```text
This work introduces an efﬁcient approach for developing
machine learning interatomic potentials (MLIPs) for metallic
glasses, applicable to any multicomponent system. As a test
case, we apply it to the ternary Cu-Zr-Al system. The method
combines a Lennard-Jones surrogate model for accelerated
swap Monte Carlo sampling of the potential energy landscape
(PEL) with single-point DFT corrections. Structural analysis
reveals that these DFT corrections do not signiﬁcantly alter
the underlying LJ-base
```

## 泄漏与范围

3篇全部片段可判定、6篇unresolved、1篇不适用；已判定范围检出0条泄漏。详见LEAKAGE.md，不覆盖未判定区间。

内容和状态变化分别记录在comparison.json；状态改善不能替代语义质量评估。
