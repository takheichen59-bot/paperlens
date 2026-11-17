# B阶段真实语料回归

{"submitted": 10, "success": 2, "partial": 7, "failed": 0, "skipped": 1, "failed_internal_classification": 0, "failed_content_or_processing": 0}

methods长度200–3000：2/10（长度不等于语义可用）；sections含UNKNOWN：9/10，解析成功9篇；未解析篇不记作已判定无UNKNOWN。
P1为5篇unresolved；本次5篇unresolved。UNKNOWN同时承载Introduction和无标题前置文本，不等于全部都是标题漏识别。

C项需优先处理标题识别，而非仅多栏排序。

| paper_id | 原→新状态 | methods长度 | conclusions长度 | UNKNOWN标题 | caption标记数 |
|---|---|---:|---:|---|---:|
| arxiv:2501.00534 | partial→partial | 0 | 3684 | (untitled) | 4 |
| arxiv:2501.00561 | partial→partial | 0 | 1312 | (untitled), INTRODUCTION | 6 |
| arxiv:2501.00564 | partial→partial | 0 | 688 | (untitled), 1. Introduction | 8 |
| arxiv:2501.00589 | success→partial | 0 | 2318 | (untitled), INTRODUCTION | 13 |
| arxiv:2501.00591 | partial→partial | 0 | 0 | (untitled) | 4 |
| arxiv:2501.00600 | partial→partial | 0 | 185 | (untitled) | 24 |
| arxiv:2501.00620 | partial→partial | 0 | 2046 | (untitled), INTRODUCTION | 14 |
| arxiv:2501.00679 | success→success | 727 | 5205 | (untitled), INTRODUCTION | 66 |
| arxiv:2501.00680 | success→success | 1330 | 405 | (untitled), 1 Introduction | 5 |

## 00589锚点对照

修复前methods开头：
```text
FIG. 6.
The predicted MLIP PEL aligns more closely with
DFT than EAM for different supercooling. a) Shear modulus G
and b) potential energy from MLIP and EAM vs the energy of a
DFT-minimized structure. The shear modulus G systematically in-
creases with the degree of supercooling. Compared with EAM, the
MLIP shows a relatively better description of the potential energy
with the DFT, i.e., e(MLIP) ≃e(DFT). Note that to show the en-
ergy data within a single plot, the EAM dataset is shifted downwa
```
修复后methods开头：
```text
(空；见M14前候选及长度)
```
M14前methods候选 6879字符，开头：
```text
where ε and σ are the energy scale and interaction range,
respectively.
The potential is truncated and shifted at
the cutoff distance rcut, i j = 2σαi,βj.
We specify the
atom index by Roman indices and the type by Greek in-
dices.
We use interaction diameter as σ Zr, Zr=2.932 Å,
σCu, Cu=2.338 Å
and σAl, Al=2.620 Å; also energies as
εZr, Zr=0.409 eV, εCu, Cu= 0.739 eV and εAl, Al=0.392 eV, re-
spectively.
These LJ-equivalent interaction parameters are
estimated from the corresponding crystalline 
```
修复前conclusions开头：
```text
where ε and σ are the energy scale and interaction range,
respectively.
The potential is truncated and shifted at
the cutoff distance rcut, i j = 2σαi,βj.
We specify the
atom index by Roman indices and the type by Greek in-
dices.
We use interaction diameter as σ Zr, Zr=2.932 Å,
σCu, Cu=2.338 Å
and σAl, Al=2.620 Å; also energies as
εZr, Zr=0.409 eV, εCu, Cu= 0.739 eV and εAl, Al=0.392 eV, re-
spectively.
These LJ-equivalent interaction parameters are
estimated from the corresponding crystalline 
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

4篇全部片段可判定、5篇unresolved、1篇不适用；已判定范围检出0条泄漏。详见LEAKAGE.md，不覆盖未判定区间。

内容和状态变化分别记录在comparison.json；状态改善不能替代语义质量评估。
