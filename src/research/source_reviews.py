"""Assistant source-reviewed cards for five hash-pinned public CC-BY papers.

These are explicit, authored review overlays, NOT generic automatic summaries,
independent expert gold, a model-service output, or a user's completed review.
"""
VERSION='assistant-source-review-v1'


def claim(text,*queries,**extra):return {'text':text,'source_queries':list(queries),**extra}


CATALOGUE={
'2501.00591v1':{
 'title_zh':'CoₓNbSe₂ 中共存的反铁磁相与结构', 'type_zh':'实验研究（助手对照摘要判断，类型待用户复核）',
 'question':[claim('Co 插层比例和结构对称性如何关联两种磁性相，并使它们在 Co₀.₂₈NbSe₂ 单晶中共存？','crystal symmetry, and cobalt site occupation','Single crystals of Co0.28NbSe2')],
 'objects':[claim('中心体系是 CoₓNbSe₂；单晶样品约为 Co₀.₂₈NbSe₂，并与 x≈1/4、x≈1/3 的相作关联。','In CoxNbSe2','Single crystals of Co0.28NbSe2')],
 'methods':[claim('结合单晶中子衍射和中子粉末衍射解析两类磁结构，不能把二者混为同一种测量。','Using single-crystal neutron diffraction'),claim('制备不同名义组分粉末及化学气相输运单晶，并用 X 射线、磁性和热容测量检查结构与相变。','We synthesized powder samples','chemical vapor transport','Magnetic susceptibility and bulk property measurements')],
 'steps':[claim('制备 x=1/3、x=1/4 的名义组分粉末；晶体生长采用化学气相输运。','We synthesized powder samples','chemical vapor transport'),claim('用单晶 XRD 与能量色散 X 射线谱检查单晶组成，并测量磁化率、热容和电输运。','We verified the composition','Electrical transport was done'),claim('用单晶中子衍射研究高温相，再以粉末衍射研究低温相及传播矢量。','Using single-crystal neutron diffraction','Given the absence of magnetic reflections')],
 'findings':[claim('x≈1/4 的中心对称结构与约 169 K 的高温反铁磁相联系；x≈1/3 的非中心对称结构与约 28 K 的低温相联系。','169 K','28 K',kind='作者报告的相变'),claim('Co₀.₂₈NbSe₂ 单晶的体性质显示两种磁转变；作者用两类中子衍射给出相应结构证据。','Single crystals of Co0.28NbSe2','Using single-crystal neutron diffraction',kind='观察与结构解析'),claim('低温粉末数据支持一个公度矢量和一个非公度矢量共存的双 q 描述。','a commensurate vector, q1',kind='作者结构解释')],
 'conclusion':[claim('作者将共存磁性与 Co 位点占据、结构对称性及两种子结构的共存联系起来；这不是跨体系的普适性能结论。','crystal symmetry, and cobalt site occupation','We report the coexistence')],
 'author_limitations':[],
 'boundaries':[claim('高温相与低温相的磁结构证据分别依赖单晶和粉末衍射；不要解读成在同一单晶测量中直接解析了全部结构。','Using single-crystal neutron diffraction','Given the absence of magnetic reflections',kind='助手适用边界提示')],
 'suggestions':[claim('可借鉴“组分—结构—体性质—磁衍射”的联合验证路线；具体相关性需由用户的研究问题决定。','Using single-crystal neutron diffraction','We verified the composition',kind='助手研究建议')],
 'numbers':[claim('高温磁转变','169 K',value='169',unit='K',quantity='磁转变温度',object='x≈1/4 中心对称相',conditions='组分与对称性条件见原文摘要',ownership='本文报告'),claim('低温磁转变','28 K',value='28',unit='K',quantity='磁转变温度',object='x≈1/3 非中心对称相',conditions='不得与高温相互换',ownership='本文报告')],
},
'2501.00561v1':{
 'title_zh':'β-Ga₂O₃ 中 Cr 杂质的结构、能级与发光', 'type_zh':'第一性原理计算＋生长与光谱实验（助手来源复核）',
 'question':[claim('Cr 在 β-Ga₂O₃ 中如何占位并产生可见发光，理论能级和谱形能否与测量对应？','In this work, we thoroughly characterize','We simulate the photoluminescence spectrum')],
 'objects':[claim('研究对象是宿主 β-Ga₂O₃ 中的 Cr 杂质及其占位/电荷态关系，而不是仅有 Ga₂O₃ 这一材料名称。','behavior of Cr in Ga2O3','neutral charge state')],
 'methods':[claim('采用含杂化泛函的第一性原理计算，研究形成能、占位、激发态和发光谱形。','density functional theory','Using first-principles calculations with a hybrid functional'),claim('使用浮区法生长样品，开展低温光致发光测量，并与计算谱形比较。','floating zone method','performed at 4.2 K','compare with explicit measurements')],
 'steps':[claim('浮区法生长 β-Ga₂O₃，检查相纯度与潜在 Cr 杂质来源。','floating zone method','two possible sources of Cr contamination'),claim('在 4.2 K 进行光致发光光谱测量，观察零声子线及偏振相关谱形。','performed at 4.2 K','polarization angle'),claim('以杂化泛函计算 Cr 的位点、形成能及激发态，再计算声子耦合与发光谱形。','Using first-principles calculations with a hybrid functional','calculate the photoluminescence lineshape'),claim('将计算与实测谱线对照，检查归属及 Franck–Condon 描述的边界。','We simulate the photoluminescence spectrum','beyond the Franck-Condon approximation')],
 'findings':[claim('计算支持中性 Cr 更倾向取代八面体 Ga 位；需要保留文中讨论的电荷态与生长/费米能条件。','Cr prefers incorporating as a substitutional impurity',kind='计算结果'),claim('计算的最低 ²E 激发态约高于基态 1.80 eV；文中实测零声子线约 1.79 eV。两者是理论与测量的对应，不应合并为同一个数值。','energy 1.80 eV','zero-phonon line is found',kind='计算与实验对照'),claim('作者报告约 0.05 的 Huang–Rhys 因子，并讨论谱形中超出简单 Franck–Condon 近似的特征。','Huang-Rhys factor','beyond the Franck-Condon approximation',kind='作者解释与边界')],
 'conclusion':[claim('联合计算和实验为八面体替位 Cr 的发光归属提供支持；量子缺陷用途属于候选潜力，不等于已实现单光子器件。','The agreement provides compelling evidence','compelling candidate for spin and photonic qubits')],
 'author_limitations':[claim('作者说明该光谱来自系综发射；由于总强度低，未能分离单个发射体。','isolating a single emitter was not possible',kind='作者明确限制')],
 'boundaries':[claim('原报告“约 1.8 eV 为背景”的标记需修正：该摘要句已处于本文工作语境；红宝石背景值 1.786 eV、理论 1.80 eV 和实测 1.79 eV 应分开。','Cr possesses a quartet','energy 1.80 eV','zero-phonon line is found',kind='助手来源归属核对')],
 'suggestions':[claim('可借鉴形成能/激发态计算与低温谱形的交叉验证；若目标是单发射体，还需独立的单中心实验。','We simulate the photoluminescence spectrum','isolating a single emitter was not possible',kind='助手研究建议')],
 'numbers':[claim('计算激发能','energy 1.80 eV',value='1.80',unit='eV',quantity='最低 ²E 激发态相对基态能量',object='八面体位中性 Cr',conditions='第一性原理激发态计算',ownership='本文计算'),claim('实测零声子线','zero-phonon line is found','performed at 4.2 K',value='1.79',unit='eV',quantity='零声子线能量',object='β-Ga₂O₃ 中 Cr 相关发光',conditions='低温 PL，4.2 K',ownership='本文测量；另有前人报道，分别保留')],
},
'2501.00423v1':{
 'title_zh':'卤化物双钙钛矿中缺陷介导的电子–声子耦合', 'type_zh':'晶体制备＋变温 Raman/PL 实验（助手来源复核）',
 'question':[claim('晶体生长引入的缺陷如何关联 Cs₂AgInCl₆、Cs₂NaInCl₆ 的电子–声子耦合及其温度演化？','Here, we report Raman spectroscopy study')],
 'objects':[claim('中心体系是 Cs₂AgInCl₆ 与 Cs₂NaInCl₆，并比较毫米级 Crystal A 与微米级 Crystal B。','Here, we report Raman spectroscopy study','millimeter-sized Crystal A and micrometer-sized Crystal B')],
 'methods':[claim('用两条制备路线得到 A/B 晶体，再联合 XRD、Raman 和 PL 比较缺陷相关差异。','following two methods','temperature-dependent Raman spectroscopy')],
 'steps':[claim('路线 A 采用单锅水热法制备毫米级晶体；路线 B 采用酸沉淀法得到微米级晶体。','one-pot hydrothermal','acid precipitation method'),claim('用 XRD 检查晶体结构，并比较室温 Raman 响应。','XRD cannot distinguish','temperature-dependent Raman spectroscopy'),claim('结合变温 Raman 与 PL，分析低频声子不对称和缺陷相关发射。','electron-phonon coupling shows an appreciable temperature dependence','both PL and Fano asymmetry')],
 'findings':[claim('缺陷相关体系的最低频声子模式约 51 cm⁻¹ 出现随温度演化的 Fano 不对称特征。','Fano anomaly in the lowest frequency phonon mode',kind='作者报告的谱学观察'),claim('缺陷相关样品中观察到宽带 PL，而所述无缺陷对照中未出现该宽带。','broad band in the photoluminescence',kind='有条件的对照观察'),claim('Fano 特征与 PL 的共同出现被作者解释为缺陷介导中间带隙态及电子–声子耦合的证据。','simultaneous observation of the Fano anomaly',kind='作者机制解释')],
 'conclusion':[claim('作者认为适当的生长方法可调节缺陷介导耦合；潜在光电用途仍属于应用展望。','Clearly, the synthesis method can significantly tailor')],
 'author_limitations':[],
 'boundaries':[claim('相近的 XRD 结构不等于缺陷和光谱响应相同；A/B 的尺寸与制备条件需与发现同时保留。','XRD cannot distinguish','millimeter-sized Crystal A and micrometer-sized Crystal B',kind='助手适用边界提示')],
 'suggestions':[claim('可借鉴“制备路线改变—结构表征—变温 Raman 与 PL 联合检查”的路线；不要把应用潜力升级成器件验证。','Clearly, the synthesis method can significantly tailor','temperature-dependent Raman spectroscopy',kind='助手研究建议')],
 'numbers':[claim('低频声子模式','Fano anomaly in the lowest frequency phonon mode',value='51',unit='cm⁻¹',quantity='最低频 Raman 声子波数',object='缺陷相关双钙钛矿体系',conditions='Fano 特征随温度变化；对照与制备路线见方法',ownership='本文观察')],
},
'2501.00680v1':{
 'title_zh':'BiFeO₃ 纳米颗粒的表面终止与极化构型', 'type_zh':'原子尺度分子动力学模拟（助手来源复核）',
 'question':[claim('不同表面终止和电荷分布如何影响 BiFeO₃ 纳米颗粒的极化排列与氧八面体转动？','This paper analyzes how the ferroelectric properties')],
 'objects':[claim('中心研究对象是 BiFeO₃ 纳米颗粒；MoS₂ 和 Bi₄Ti₃O₁₂ 仅为引言中的前人催化比较。','This paper analyzes how the ferroelectric properties','previous record observed with Bi4Ti3O12')],
 'methods':[claim('采用由第一性原理数据拟合参数的壳模型势，并用经典分子动力学比较表面终止条件。','interatomic potential with parameters','classical molecular dynamics simulations')],
 'steps':[claim('构建 40×40×40 个 BiFeO₃ 晶胞、约 32 万个原子的颗粒，比较不同表面终止。','40×40×40','different terminations'),claim('按设定的初始畴构型进行经典分子动力学弛豫，模拟温度为 1 K。','A temperature of 1 K was chosen'),claim('先热化 10 ps，再以额外 10 ps 计算平均构型，并分析局域偶极、八面体转动和体积。','10 ps thermalization','We evaluate the polarization')],
 'findings':[claim('在文中的低温模拟设定下，观察到从均匀单畴到含涡旋复杂构型的多种极化排列。','We observed various polarization arrangements','A temperature of 1 K was chosen',kind='模拟观察'),claim('对中性表面终止的颗粒，作者稳定了条纹状极化构型。','for nanoparticles with neutral terminations',kind='有条件的模拟观察')],
 'conclusion':[claim('模拟表明表面终止条件会影响颗粒内部的极化和氧八面体转动排列；这些结果不直接证明室温实际样品行为。','In summary, we have explored how different sets of terminations')],
 'author_limitations':[],
 'boundaries':[claim('1 K 是关键模拟边界，不能把该结果无条件推广到室温催化或真实纳米样品；引言的 97% 降解率属于前人工作。','A temperature of 1 K was chosen','successfully degraded 97%',kind='助手适用边界提示')],
 'suggestions':[claim('可借鉴把表面终止、电荷边界和初始构型设为显式比较变量，并检查初态与温度敏感性。','different terminations','A temperature of 1 K was chosen',kind='助手研究建议')],
 'numbers':[claim('模拟温度','A temperature of 1 K was chosen',value='1',unit='K',quantity='分子动力学温度',object='BiFeO₃ 纳米颗粒',conditions='恒应力/恒温弛豫，不是测量性能',ownership='模拟参数'),claim('热化与平均窗口','10 ps thermalization',value='10 + 10',unit='ps',quantity='热化时间＋平均采样时间',object='模拟轨迹',conditions='两个阶段应分别理解',ownership='模拟参数')],
},
'2501.00447v1':{
 'title_zh':'Quantum 2.0：理解量子物质面临的挑战', 'type_zh':'观点/综述型讨论（按摘要与行文核对，非期刊类型认证）',
 'question':[claim('理解涌现量子物质需要哪些组织原则、关键实验现象和新的理论方法？','We outline and discuss several outstanding challenges')],
 'objects':[claim('研究主题是量子物质的理论组织原则与未解问题，不是一组待填材料实验样品。','organisational principles that can guide')],
 'methods':[], 'steps':[],
 'arguments':[claim('文章讨论超出 Ginzburg–Landau–Wilson 范式的量子物质组织问题，并将现象、理论和方法挑战联系起来。','beyond the well-established Ginzburg-Landau-Wilson paradigm','We outline and discuss'),claim('作者强调需要能保留物理洞见的非微扰解析与数值方法，并讨论现有方法的尺度与适用限制。','non-perturbative analytic and numerical methods','exact diagonalisation methods are strongly limited'),claim('文章提出多体纠缠与实验可观测性质之间的联系等开放问题；这不是一组新实验发现。','connection between many-particle entanglement')],
 'findings':[],
 'conclusion':[claim('作者预计应对这些挑战有望支持新量子材料的预测和技术发展；这是研究展望，不是已验证器件性能。','efforts in meeting the challenges laid out here will likely enable')],
 'author_limitations':[claim('文中指出精确对角化受 Hilbert 空间随体系尺度指数增长的限制，并强调其他方法各有适用边界。','exact diagonalisation methods are strongly limited','Other methods have access to only perturbative regimes',kind='作者对现有方法的限制讨论')],
 'boundaries':[claim('实验操作步骤、样品制备参数和原创实验结果模板不适用；可提取内容是论点、方法挑战和开放问题。','We outline and discuss several outstanding challenges',kind='助手类型适配提示')],
 'suggestions':[claim('可把文章用作问题清单及进一步检索入口；未给定个人研究方向时，不生成精确相关性评分。','We end by outlining a few broad challenges',kind='助手研究建议')],
 'numbers':[],
}}

PINNED_HASHES={'2501.00680v1': '1f88d96cfa8bc36595ac00eaebd42db85fbcc1eb35733058e2399906aa0fb7cd', '2501.00591v1': 'a4b49de0f407be3444b089a4a9b7955319ad55634929f802c18044461c0060cf', '2501.00561v1': '5f1c9de042bdb4020a8977dc1889b9be906c24c1aea556d47994ce64a89d6f77', '2501.00447v1': 'c5f176d2ad680dbce590b751c2679bec832b313d1bb6d5fbcb2562a87c63106b', '2501.00423v1': '7bfd69c413d3aba5c14690b45e0b42f621f693d0cb9fa9cb64168d795f27e3d2'}


def attach_source_review(record):
    from copy import deepcopy
    from .reading import normalize_text
    if record.get('id') not in CATALOGUE:return record
    if record['pdf_hash']!=PINNED_HASHES[record['id']]:return record
    layer=record['reading_card']; evidence=layer['evidence']
    def key(text):
        import re
        return re.sub(r'(?<=[A-Za-z])-(?=[A-Za-z])','',normalize_text(text)).casefold()
    review=deepcopy(CATALOGUE[record['id']])
    missing=[]
    for field,items in review.items():
        if not isinstance(items,list):continue
        kept=[]
        for item in items:
            ids=[];unavailable=[]
            for query in item['source_queries']:
                matches=[s for s in evidence if key(query) in key(s['text'])]
                if not matches:unavailable.append(query)
                else:ids.append(matches[0]['id'])
            if unavailable:missing.append({'field':field,'text':item['text'],'unavailable_queries':unavailable})
            else:
                item['evidence_ids']=list(dict.fromkeys(ids));kept.append(item)
        review[field]=kept
    review.update({'status':'partial_sources' if missing else 'source_bound','unresolved_claims':missing,'version':VERSION,'origin':'assistant_source_review','independent_gold':False,
        'human_review_status':'unreviewed','pdf_hash':record['pdf_hash'],
        'notice':'中文卡片为助手对照本篇原PDF整理的来源复核层，不是规则自动摘要，也不是独立专家金标准；原自动结果及用户复核状态保留。'})
    layer['source_review']=review
    return record
