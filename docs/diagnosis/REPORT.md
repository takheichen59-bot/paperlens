# 诊断报告：success=0 与三处字段异常

本轮仅诊断，未修实现、未改规则/配置/测试/示例，未联网、未调用模型。读取同批冻结输出、匹配哈希/版本的SectionView缓存、原始raw_blocks，并渲染PDF作版面核对。分级为助手逐段内容审阅，不是领域专家金标准，不评价论文科学结论的真伪。

## 1. success=0 的字段级根因

### 1.1 状态规则与内容质量是两层问题

`src/extractors/composite.py:9–12`：只有三个字段非空且 warnings 为空才返回 success。状态函数不检查完整句、图注或科学相关性；真实语义问题本身未必产生 warning。

8篇partial中，2501.00589、2501.00679、2501.00680三个字段均非空，其持久化warnings全部是possible_multicolumn。因此这3篇在形式上被版面告警挡住success；这不意味着移除告警就能得到3篇有效结果。其余5篇methods为空，其中2篇chemicals也空、1篇conclusions空。

字段存在组合：三字段均有3篇；chemicals+conclusions有2篇；仅conclusions有2篇；仅chemicals有1篇。没有证据支持“三个字段在全部论文中同时差”的解释。主导缺口是方法摘录，结论也有碎片/错栏污染，化学物相对更可用。

### 1.2 可用性分级与统计

- **可用**：可直接作为该字段摘录；允许常规排版换行/行末连字，不要求实体标准化。
- **部分可用**：有正确核心事实，但需要补齐语境或清除污染；不直接交作最终字段。
- **不可用**：空，或主体为错误类型内容，或只有不能构成摘录的残句。
- 空化学物字段在理论论文中可能合理；此处不可用只表示无法提供该字段，不自动判漏检。边界化学概念不是确定误报。

| 字段 | 可用 | 部分可用 | 不可用 |
|---|---:|---:|---:|
| chemicals | 4 | 2 | 2 |
| conclusions | 1 | 4 | 3 |
| methods | 0 | 2 | 6 |

分母均为8篇partial。methods有2篇包含方法事实，但严格按整字段可直接使用的口径，没有1篇完全可用：00679是断句/表注拼接，00680有开头残句。这解释了此前“有效约2篇”与本次严格分级的差异。

| arXiv | chemicals | conclusions | methods |
|---|---|---|---|
| 2501.00534 | 可用 | 部分可用 | 不可用 |
| 2501.00564 | 不可用 | 部分可用 | 不可用 |
| 2501.00589 | 可用 | 不可用 | 不可用 |
| 2501.00591 | 部分可用 | 不可用 | 不可用 |
| 2501.00600 | 可用 | 不可用 | 不可用 |
| 2501.00620 | 不可用 | 部分可用 | 不可用 |
| 2501.00679 | 可用 | 部分可用 | 部分可用 |
| 2501.00680 | 部分可用 | 可用 | 部分可用 |

### 1.3 chemicals 明细

| arXiv | 非空/数量 | 晶面、编号、单位或口径问题 |
|---|---|---|
| 2501.00534 | 是 / 1 | BiFeO3；未见晶面、编号或单位误报。 |
| 2501.00564 | 否 / 0 | 空列表；没有可供使用的化学物摘录，不能据此断言原文应有化学物。 |
| 2501.00589 | 是 / 3 | CuZrAl、ZrCuAl、CuZr均有材料语境；前两者存在命名/排序冗余，未做标准化，不按误报计。 |
| 2501.00591 | 是 / 5 | CrI3、NbSe2、CoI2有材料语境；HK0/HK1是晶面索引，2/5明确误报；未见基金号或单位误报。 |
| 2501.00600 | 是 / 1 | Li6PS5Cl有固态电解质语境；未见所列噪声。 |
| 2501.00620 | 否 / 0 | 空列表；该理论流体论文未必需要化学物字段，空值不自动等于漏检。 |
| 2501.00679 | 是 / 2 | MgO、MgSiO3是文中材料组成；未见所列噪声。 |
| 2501.00680 | 是 / 5 | 3个明确材料名BiFeO3/MoS2/Bi4Ti3O12；BiO、FeO2是表面终止层组成，属于待裁定口径，不作为已确认误报。 |

### 1.4 conclusions 明细

| arXiv | 非空/字符 | 完整句 | 错序/类型混合 | 致谢或参考文献 | 证据 |
|---|---|---|---|---|
| 2501.00534 | 是 / 3684 | 否，首尾残句 | 未证实倒序；局部总结、定义和讨论被混入同一字段 | 未见 | p3-b4 + p4-b3；首为domain wall.残片，尾止于among the R180◦。 |
| 2501.00564 | 是 / 1715 | 混合：真正结论段完整，前段不是结论 | 不是倒序；跨栏边界把左栏结果/公式解释归入右栏Conclusions | 未见 | 1025字结果段 + 688字真正结论 + 分隔符。 |
| 2501.00589 | 是 / 11036 | 部分句子完整，但字段整体类型错误 | 明确跨栏错序，详见第4节 | 有致谢续段；未见引用列表段 | 18条片段；实际结论、方法、资金支持、作者贡献、代码可用性混合。 |
| 2501.00591 | 否 / 0 | 不适用，空 | 不适用 | 不适用 | 没有输出结论；不能据此判定原文没有结论。 |
| 2501.00600 | 是 / 185 | 否，两段均为截断短句 | 不是页码倒序；从不同正文位置拼接 | 未见 | 185字：第一段止于These findings highlight；第二段止于inter-。 |
| 2501.00620 | 是 / 2046 | 主体结论大体完整，公式/连字有排版损伤 | 主体顺序基本连续，尾混入后置数据声明 | 未见致谢/参考文献；含DATA AVAILABILITY | p27–28，末两条p28-b26/b27不属于结论。 |
| 2501.00679 | 是 / 5205 | 大部分可读，但至少漏掉短块conduction. | 章节及页码顺序正常；存在短块过滤缺词 | 未见 | p20-b25句末应接p20-b26(conduction.)，后者因len<=20被遗漏。 |
| 2501.00680 | 是 / 405 | 是，3个完整总结句，只有原文行末连字 | 顺序正确 | 未见 | p8-b4一条405字；与PDF第8页4 Conclusion正文吻合，致谢不在本字段。 |

**重要限定**：修复报告的“泄漏0”只复核了8个参考文献化学实体+3个基金编号。本次00589的conclusions发现真实致谢续段，不能继续将“0”解释为全部字段的后置内容泄漏为0。

00679短块丢失的具体证据：p20-b25以 `a comprehensive theory of thermal` 结束，本应接p20-b26的 `conduction.`，但后者只有11字符，被结论抽取的 `len(b.text)>20` 排除。输出直接跳到p20-b27下一段；这是内容缺词，不只是空白样式。

### 1.5 methods 明细

| arXiv | 非空/字符 | 图注或表注 | 判断依据 |
|---|---|---|---|
| 2501.00534 | 否 / 0 | 否 | 空；methods_fallback_truncated |
| 2501.00564 | 否 / 0 | 否 | 空；methods_fallback_rejected |
| 2501.00589 | 是 / 925 | 是，FIG.6 | 2条均在左栏结果区；其中图注占515字，详见第4节。 |
| 2501.00591 | 否 / 0 | 否 | 空；methods_fallback_truncated |
| 2501.00600 | 否 / 0 | 否 | 空；methods_fallback_rejected |
| 2501.00620 | 否 / 0 | 否，当前为空 | 历史候选2018字含图注/零散行，详见第3节。 |
| 2501.00679 | 是 / 815 | 无FIG图注；有TABLE I表注 | 含DFT/时间步等方法事实，但从句中开始、漏掉后续行，混入小节标题和表注。 |
| 2501.00680 | 是 / 1330 | 否 | 主体为参数、分子动力学和弛豫方法；开头well-suited...是前一段残句，需补齐语境或删去。 |

## 2. 2501.00561：M14整条拒绝是否过激

默认规则重建的候选：methods=8229字符，chemicals=9项，conclusions=2763字符。完整原始候选保存为 `00561_candidate.json`。所有片段的raw切片与允许视图范围均核验通过；默认M14仍返回VALIDATION_FAILED。

### methods 前500字符（原样）

```text
phases making up less than 1% of the crystal.
Addi-
tionally, single-crystal Laue diffraction was collected us-
ing the horizontal Laue System AK261, manufactured by
Photonic Science, to determine the crystal orientation.
Any incorporation of Cr in the sample was uninten-
tional.
We believe there are two possible sources of
Cr contamination during the growth. X-ray diffraction
shows evidence for the presence of CrO2 in the polycrys-
talline Ga2O3 source material. In addition, the alumina
seed ro
```

### methods 后200字符（原样）

```text
unctions, allowing us to
attribute most of the lower-energy peaks to the phonon
sideband of the transition. We calculate a total Huang-
Rhys factor S of 0.05, indicating weak electron-phonon
coupling.
```

候选不只是长：开头是前一句残片，末尾已是光谱结果解释。8229字符不能直接当作一段干净的方法。M12的3000回退上限没有处理它，因为它走已识别METHODS章节分支；随后M14第38行用同一上限拒绝。pipeline/single.py第74–78行把任何抽取异常转成整条空failed，因而其他字段一起丢失。

chemicals原候选：`["Ga2O3", "Al2O3", "CrO2", "CrGa", "Cr2O3", "GaO4", "GaO6", "GaN", "AlN"]`。6项是明确材料/化合物，CrGa、GaO4、GaO6为缺陷/配位口径边界；不是9项均无问题。无已确认基金编号或晶面误报。

conclusions原候选：前1451字符为讨论/机制解释，其后才进入`In summary`总结。实际总结与PDF第6–7页结论区相符（第6页版面见figures/00561-page6.png），但整字段混合，因此属于部分可用，不宜称完全有效。

**判断：就避免信息损失而言，整条failed过激；可以有依据地清空methods并保留其他字段为partial，而不能据此升级success。** 本轮仅做内存反事实：清空methods及其证据，其他原候选保留，所有既有检查仍开启、上限仍3000；默认M14与现有JSONL校验均通过，状态partial。结果见 `00561_counterfactual_check.json`。没有写回数据库或results.jsonl。

## 3. 2501.00620：2018字methods被清空是否合理

完整历史字段保存为 `00620_historical_methods.txt`。前800字符：

```text
ids are recovered. We validate our method using several benchmark simulations.

where v is the microscopic velocity, x is position in space, and t is time. The equilibrium

invariance in LBM simulations of fluids. Note that the dirac delta function has only two

difference schemes of reference18. For the applications shown in Section III all simulations

section, we measure the physical properties of our fluid. We also compare these results to

In this section, we measure the shear viscosity in a Poiseuille flow and compare it to the

relaxation times τ = 1µs and τ = 2µs, respectively.
For these simulations, we observe

where τ is the relaxation time. To confirm this relation, we measure the viscosity η from

Fig. 3(c) shows the measured η as a function of temperature for both relaxation t
```

实际共23个snippet、13个不同PDF页，跨度第1–28页；旧缓存全部属于一个UNKNOWN section（snippet.section为null）。按当前冻结SectionView映射跨3个section：s1未命名、s2 INTRODUCTION、s3 CONCLUSION。后者仍是机器粗分，不等于论文真实只有3章。

关键词共24次命中，只有3个不同词族：simulation=14、measurement=9、microscopy=1。其中microscopic velocity被microscopy规则误当方法提示。每个原块都只有1个不同词族，满足至少2词族的块为0。按当前允许正文序列计，22段非连续串，最长只有2块；该双块串也各只有一个词族。

| 顺序 | 页 | raw block | 当前section | 方法词族及原词 | 正文索引 |
|---:|---:|---|---|---|---:|
| 1 | 1 | p1-b15 | s1:未命名 | simulation:simulations | 15 |
| 2 | 2 | p2-b16 | s2:INTRODUCTION | microscopy:microscopic | 33 |
| 3 | 8 | p8-b4 | s2:INTRODUCTION | simulation:simulations | 236 |
| 4 | 15 | p15-b21 | s2:INTRODUCTION | simulation:simulations | 497 |
| 5 | 17 | p17-b31 | s2:INTRODUCTION | measurement:measure | 567 |
| 6 | 18 | p18-b1 | s2:INTRODUCTION | measurement:measure | 570 |
| 7 | 18 | p18-b31 | s2:INTRODUCTION | simulation:simulations | 600 |
| 8 | 19 | p19-b0 | s2:INTRODUCTION | measurement:measure | 604 |
| 9 | 19 | p19-b4 | s2:INTRODUCTION | measurement:measured | 608 |
| 10 | 19 | p19-b14 | s2:INTRODUCTION | measurement:measured | 615 |
| 11 | 19 | p19-b20 | s2:INTRODUCTION | measurement:measure | 621 |
| 12 | 20 | p20-b25 | s2:INTRODUCTION | measurement:measure | 652 |
| 13 | 21 | p21-b10 | s2:INTRODUCTION | simulation:simulations | 663 |
| 14 | 21 | p21-b12 | s2:INTRODUCTION | simulation:simulation | 665 |
| 15 | 21 | p21-b13 | s2:INTRODUCTION | simulation:simulation | 666 |
| 16 | 21 | p21-b17 | s2:INTRODUCTION | measurement:measured | 670 |
| 17 | 21 | p21-b25 | s2:INTRODUCTION | measurement:measured | 678 |
| 18 | 23 | p23-b4 | s2:INTRODUCTION | simulation:simulations | 705 |
| 19 | 24 | p24-b9 | s2:INTRODUCTION | simulation:simulations | 742 |
| 20 | 24 | p24-b11 | s2:INTRODUCTION | simulation:simulations | 744 |
| 21 | 26 | p26-b15 | s2:INTRODUCTION | simulation:simulations,simulations | 779 |
| 22 | 26 | p26-b17 | s2:INTRODUCTION | simulation:simulations | 781 |
| 23 | 28 | p28-b25 | s3:CONCLUSION | simulation:simulations | 817 |

**判断：旧2018字字段确实零散，清空这个字段本身合理，不能将其当作一段原本可用的方法被误删。** 它包含速度定义、图注、结果句和结论收尾，不是连续方法叙述；原长度符合200–3000并不构成可用性证据。但这不证明论文无方法：PyMuPDF将大量正文切成单行，section粗分未覆盖真实小节，逐块至少2关键词会进一步降低覆盖。因此“旧候选应拒绝”和“现规则可能漏掉有用方法”可以同时成立；本轮不修改规则。

## 4. 2501.00589：错序发生在哪里、为什么图注进入方法

### 4.1 页码没有倒序，列内阅读顺序被破坏

版面证据：第6页与第8页见本目录 `figures/00589-page6.png`、`figures/00589-page8.png`。

18条conclusions证据的页码序列为：6×3、7×11、8×4，单调非降。不能把此问题诊断为页码倒排。实际错误是同页左右栏交错，以及错误section归属延续到后续页。PDF第6、8页已视觉核对。

| 输出序号 | 页 | raw block | 栏 | bbox顶部y | 源内容角色 |
|---:|---:|---|---|---:|---|
| 1 | 6 | p6-b31 | 右 | 459.3 | 方法：LJ参数 |
| 2 | 6 | p6-b32 | 左 | 506.2 | 真正结论左栏段落 |
| 3 | 6 | p6-b33 | 右 | 632.2 | 方法：邻域变化 |
| 4 | 7 | p7-b1 | 左 | 52.9 | 方法：邻域续段 |
| 5 | 7 | p7-b4 | 右 | 52.9 | 方法：DFT参数 |
| 6 | 7 | p7-b5 | 左 | 141.7 | 方法：邻域公式解释 |
| 7 | 7 | p7-b9 | 左 | 202.8 | 方法公式 |
| 8 | 7 | p7-b10 | 左 | 250.4 | 方法：平均量解释 |
| 9 | 7 | p7-b11 | 右 | 144.6 | 方法：AIMD |
| 10 | 7 | p7-b12 | 右 | 396.6 | 方法：黏度计算 |
| 11 | 7 | p7-b17 | 右 | 483.3 | 方法：公式参数 |
| 12 | 7 | p7-b18 | 左 | 273.7 | 方法：swap-MC |
| 13 | 7 | p7-b19 | 左 | 546.9 | 方法：时间尺度 |
| 14 | 7 | p7-b20 | 右 | 552.1 | 方法：NEP训练 |
| 15 | 8 | p8-b1 | 右 | 52.9 | 致谢续段：资助信息 |
| 16 | 8 | p8-b2 | 左 | 52.9 | 方法：NEP训练续段 |
| 17 | 8 | p8-b5 | 右 | 312.2 | 作者贡献 |
| 18 | 8 | p8-b6 | 左 | 306.5 | 代码可用性 |

关键位置对照：

- 原PDF第6页正常阅读为：左栏结果与FIG.6 → 左栏 IV. CONCLUSIONS → 右栏上部结论续段 → 右栏 V. METHODS。
- 当前raw顺序先到p6-b19（右栏V. METHODS，bbox y=329.1–338.1），再到p6-b20（左栏FIG.6，y=264.6–358.5），之后才到p6-b30（左栏IV. CONCLUSIONS，y=482.1–491.1）。原始几何排序没有按栏串读；从这些bbox可见，不能简单把sort=True等同于从左栏读完再读右栏。
- 因V先于IV，p6-b20/p6-b29被标为METHODS；IV之后，p6-b31右栏LJ参数先于p6-b32真正结论进入conclusions。这是第一处明确错误，表中序号1→2→3呈右→左→右。
- 第7页序号4–14继续左右栏交错，大部分属于V. METHODS。第8页序号15的右栏资金支持续段在左栏ACKNOWLEDGEMENTS标题之前进入raw序列，因此未被后置排除规则拦住。作者贡献和代码可用性也进入结论。
- 逻辑视图正确保留了raw偏移，却继承了错误的raw阅读序列；证据可回溯并不保证章节语义归属正确。

### 4.2 methods中的图注原文

```text
FIG. 6.
The predicted MLIP PEL aligns more closely with
DFT than EAM for different supercooling. a) Shear modulus G
and b) potential energy from MLIP and EAM vs the energy of a
DFT-minimized structure. The shear modulus G systematically in-
creases with the degree of supercooling. Compared with EAM, the
MLIP shows a relatively better description of the potential energy
with the DFT, i.e., e(MLIP) ≃e(DFT). Note that to show the en-
ergy data within a single plot, the EAM dataset is shifted downwards
by 1.11 eV.
```

该图注为独立raw block p6-b20，PDF第6页左栏，515字符；methods总925字符，另一个片段p6-b29是结果解释。因此问题不是没有分出物理文本块，而是没有把这个块识别为caption并从方法视图排除。

M09只配置章节标题/后置边界，没有caption类别或FIG./TABLE.的排除标记；FIG.6不匹配章节词表，沿用当时错误的METHODS状态。M12命名方法章节分支只要求至少1个方法关键词，该图注中的DFT命中，因此被选入；同类现象还出现在00679的TABLE I表注。本轮只记录因果链，没有加入caption规则。

## 5. HK0/HK1：词典误收还是正则过宽

结论：**正则过宽，不是词典误收。** `src/extractors/chemicals.json` 不含HK0或HK1。当前规则位于chemicals.py第24–26行：

```text
\b(?:[A-Z][a-z]?\d*){2,}\b
symbols = re.findall(r'[A-Z][a-z]?', match)
all(symbol in ELEMENTS) and (存在数字 or 存在小写字母)
```

H、K都在元素表；HK0/HK1被拆成H+K并满足有数字条件。规则不判断这是倒易空间晶面索引，也没有排除系数0的检查。这里的原文明确写Precession images ... planes，属于衍射图注，不是氢钾化合物。

### HK0：PDF第3页，p3-b4，raw[107:110]

匹配前100字符：
```text

Single crystal X-ray diffraction results showing
lattice coexistence. Precession images along the (
```
匹配后100字符：
```text
) (a),
(HK1) (b), (H0L) (c), and (HHL) (d) planes.
Green
arrows indicate the host unit cell of 2H-Nb
```

### HK1：PDF第3页，p3-b4，raw[118:121]

匹配前100字符：
```text
stal X-ray diffraction results showing
lattice coexistence. Precession images along the (HK0) (a),
(
```
匹配后100字符：
```text
) (b), (H0L) (c), and (HHL) (d) planes.
Green
arrows indicate the host unit cell of 2H-NbSe2 and the
```

## 6. 诊断结论与边界

1. success=0既有形式状态门槛（任何warning都阻success），也有真实内容缺陷。3篇三字段非空不等于可用；主要系统性问题是methods空/碎片化，结论受阅读顺序和短块过滤影响。
2. 00561可从数据保留角度支持字段级partial，但保留字段仍需复核；没有依据升级success。
3. 00620旧候选应拒绝，不能把拒绝直接当方法召回正确；当前逐行粒度与关键词阈值存在覆盖风险。
4. 00589应诊断为同页跨栏阅读顺序/章节归属错误及caption语义缺失，非页码倒序。致谢续段泄漏说明原11项实体回归不能替代全字段泄漏验收。
5. HK0/HK1来自公式正则和上下文缺失；不需要假设词典包含错误条目。

本轮暂停在诊断：未修代码、未改规则、未关闭检查、未接模型，也未写入新的流水线结果。分级与反事实分析仅用于用户决定下一轮优先级。

## 证据文件

- availability_matrix.json：8篇字段矩阵、实际warnings与分布。
- 00561_candidate.json / 00561_counterfactual_check.json：原候选与只读反事实校验记录。
- 00620_historical_methods.txt / 00620_chunks.json：历史2018字及23块页码、章节、命中词、连续性。
- 00589_order.json / 00589_caption.txt：18条证据顺序、坐标及图注原文。
- hk_evidence.json：精确正则、raw偏移、前后100字符。
- UNCHANGED.json：实现、验收、脚本、示例文件的哈希比对。
