# -*- coding: utf-8 -*-
"""志业镜的分析核心（在 _majors_src.py 里内联使用）。

【初心，抄在代码里免得忘】
script.py 原文：
  「它不推荐专业。它做三件事：
    1. 从你讲的具体经历里，找出你真正做过什么（并如实标出证据有多硬）
    2. 先让你说清「你确定不能接受什么」——选专业主要是排雷，不是找最优
    3. 把结果组织成「值得验证的假设 + 你能马上做的小实验」」

【但用户要好玩，怎么共存】
早期版本是**问卷**：先问一堆，再出结论。用户说「访谈太慢了」，
而且「完全不是我想要的」。
现在的做法：**先看牌，挑的过程本身就是访谈。**
  收下 = 你说「这个我行」
  翻过去 + 说理由 = 你说「这个我不行」← **排除理由信号更强**
志业镜不再是入口，是**挑完之后的镜子**。

【三条不许破的底线（从 script.py 搬过来）】
  · 现实条件（家里条件、地域、成绩）只能影响「可行性」和「时间表」，
    绝对不能影响对你这个人的判断
    —— 原文："不做限制的话，很容易算出一个「家里没钱所以不该学艺术」
       的结论。那不是智能，那是把偏见自动化。"
  · 低证据 ≠ 低能力。没验证过的标「待验证」，不标「不擅长」
  · 不给唯一的「最佳答案」。给一个方向 + 下一步做什么
"""

# ── 7 个需求维度（顺序来自 script.py 的 dims 字段）──
DIM_NAMES = ["认知负荷", "记忆量", "细节分辨", "动手要求",
             "自驱要求", "挫折耐受", "慢反馈耐受"]
# 权重来自 script.py 的 DIM_WEIGHT。原注释：
# 「自驱和扛得住，比聪明更决定你能走多远，所以它们权重更高」
DIM_WEIGHT = [1.0, 0.7, 0.9, 0.9, 1.3, 1.2, 1.1]
# 面向用户的说法。数字是给机器的，**这句话是给人的**——
# 人认得出「没人给你划重点」，认不出「自驱要求 5」。
DIM_PLAIN = {
    "认知负荷": "要同时想很多件事",
    "记忆量": "要背的东西多",
    "细节分辨": "要抠细节、一次做对",
    "动手要求": "要动手做、要手上有活",
    "自驱要求": "没人给你划重点，得自己找路",
    "挫折耐受": "会反复失败，还得继续",
    "慢反馈耐受": "很久看不到成果，也要撑住",
}
# 排除理由标签 → 命中的维度。**这是把「我不行」翻译成维度的地方。**
REASON_DIM = {
    "背不下来": "记忆量",
    "太抠细节": "细节分辨",
    "不想动手": "动手要求",
    "没人带我不行": "自驱要求",
    "怕反复失败": "挫折耐受",
    "等不了那么久": "慢反馈耐受",
    "想不过来": "认知负荷",
    "太卷/太累": None,          # 现实条件，**不许进对人的判断**
    "家里不支持": None,          # 同上
    "成绩够不上": None,          # 同上
    "学费太贵": None,            # 同上
}
# 上面这几个 None 不是「没想好」，是**故意留白**：
# 它们是现实条件，只能谈「可行性/时间表」，不能谈「你适合什么」。
REALITY_REASONS = [k for k, v in REASON_DIM.items() if v is None]


def _avg(vals):
    return sum(vals) / len(vals) if vals else 0.0


def read_mirror(collected, rejected):
    """从「收下的」和「翻过去的」读出偏好。

    参数：
      collected : [major dict]  —— 收下的卡（含 dims / cost_*）
      rejected  : [(major dict, [理由标签])] —— 翻过去的卡 + 理由

    返回一个 dict，界面自己决定怎么画。**这里不做结论，只给结构。**
    """
    have = [m for m in collected if m.get("dims")]
    rej_have = [(m, r) for m, r in rejected if m.get("dims")]
    out = {"n_collected": len(collected), "n_with_dims": len(have),
           "n_rejected": len(rejected)}

    if not have:
        out["enough"] = False
        out["why"] = ("你收下的卡里还没有带「需求画像」的。"
                      "带画像的有 94 个，多挑几张就能读了。")
        return out

    # ── 1. 收下的卡在他们身上的需求合起来长什么样 ──
    prof = [_avg([m["dims"][i] for m in have]) for i in range(7)]
    # 加权后的「总负担」——用 script.py 的原始权重
    burden = sum(prof[i] * DIM_WEIGHT[i] for i in range(7))
    out["profile"] = prof
    out["burden"] = burden

    # ── 2. 一致的那一维 vs 分歧最大的那一维 ──
    # 「一致」= 你收的卡在这一点上都高 → 这是你的硬需求
    # 「分歧」= 有的高有的低 → 说明你还没定，或这一维不是你的筛选标准
    spread = []
    for i in range(7):
        vals = [m["dims"][i] for m in have]
        spread.append((_avg(vals), max(vals) - min(vals), i))
    high = sorted(spread, key=lambda x: (-x[0], x[1]))
    out["consistent_high"] = [DIM_NAMES[i] for _, _, i in high[:3]
                              if _avg([m["dims"][i] for m in have]) >= 3.5]
    out["divisive"] = [DIM_NAMES[i]
                       for _, (_a, sd, i) in
                       sorted([(0, s) for s in spread],
                              key=lambda x: -x[1][1])[:2]
                       if sd >= 2]

    # ── 3. 排除理由命中的维度：这是**信号最强的一块** ──
    hits = {}
    for _m, reasons in rejected:
        for r in reasons:
            d = REASON_DIM.get(r)
            if d:
                hits[d] = hits.get(d, 0) + 1
    # 对比：收下的卡在这些维度上的平均值
    out["reject_hits"] = hits
    out["reject_vs_collected"] = {
        d: (_avg([m["dims"][DIM_NAMES.index(d)] for m in have]), n)
        for d, n in hits.items()}
    out["reality_reasons"] = sorted(
        {r for _m, rs in rejected for r in rs if r in REALITY_REASONS})

    # ── 4. 代价：收下的卡让你承诺了什么 ──
    hrs = [m["cost_hours"] for m in have if m.get("cost_hours")]
    yrs = [m["cost_years"] for m in have if m.get("cost_years")]
    rev = [m.get("cost_reversible") for m in have
           if m.get("cost_reversible") is not None]
    out["cost"] = {
        "hours_avg": _avg(hrs) if hrs else None,
        "years_avg": _avg(yrs) if yrs else None,
        "n_reversible": sum(1 for r in rev if r),
        "n_irreversible": sum(1 for r in rev if not r),
    }

    # ── 5. 只给「值得验证的假设」，不给推荐 ──
    # script.py 原文：这个类「不叫推荐，叫值得验证的假设」
    #
    # 【先定够不够，再决定要不要开口】
    # 原来我先算假设、后判 enough，结果只收 1 张卡时
    # enough=False **却照样吐 3 条假设**——用一张卡下结论，那就是编。
    # 现在样本不够就一条都不给。
    out["enough"] = len(have) >= 3
    if not out["enough"]:
        out["why"] = (f"你收下的卡里只有 {len(have)} 张带需求画像。"
                      f"再多挑两张，读出来的东西才站得住。")
        out["hypotheses"] = []
        return out

    hyp = []
    if out["consistent_high"]:
        picks = "、".join(out["consistent_high"])
        hyp.append({
            "t": f"你收的 {len(have)} 张卡，在「{picks}」上都偏高。",
            "why": "这可能是你真正在意的，也可能只是热门专业恰好都这样——"
                   "得靠下一步验证。",
            "test": f"找两个在「{out['consistent_high'][0]}」上差别很大的"
                    f"专业，各花二十分钟看看它们大一在干什么，"
                    f"看你对哪个更坐得住。",
        })
    for d, n in sorted(hits.items(), key=lambda x: -x[1])[:2]:
        col_avg = out["reject_vs_collected"][d][0]
        hyp.append({
            "t": f"你 {n} 次用「{d}」当排除理由。",
            "why": (f"你收下的卡在这一维平均是 {col_avg:.1f}/5。"
                    f"{'你确实一直在躲它。' if col_avg < 3 else '但你收的卡其实也不低——可能是别的因素在起作用。'}"),
            "test": f"找一个「{d}」特别高的专业（卡片上能看到），"
                    f"花一个下午真做一次里面那种事，"
                    f"看你是真受不了，还是只是没试过。",
        })
    if out["cost"]["n_irreversible"]:
        hyp.append({
            "t": f"你收的卡里，{out['cost']['n_irreversible']} 张"
                 f"「很难回头」。",
            "why": "难回头本身不是坏事，但要在知道的情况下选。",
            "test": "挑其中一张，只看它的「代价」那栏，问自己："
                    "这个代价我现在能不能接受？",
        })
    out["hypotheses"] = hyp
    return out


def mirror_lines(r):
    """把 read_mirror 的结果变成给人看的话。**话要短。**"""
    L = []
    if not r.get("enough") and r.get("why"):
        L.append(r["why"])
        return L
    p = r["profile"]
    top = sorted(range(7), key=lambda i: -p[i])[:2]
    low = sorted(range(7), key=lambda i: p[i])[:1]
    L.append("你收下的卡，合起来是这样一份「要求」：")
    L.append("　" + "　".join(f"{DIM_NAMES[i]} {p[i]:.1f}"
                              for i in range(7)))
    L.append("")
    L.append(f"**最重的是**：{DIM_PLAIN[DIM_NAMES[top[0]]]}"
             f"（{p[top[0]]:.1f}/5）、{DIM_PLAIN[DIM_NAMES[top[1]]]}"
             f"（{p[top[1]]:.1f}/5）")
    L.append(f"**最轻的是**：{DIM_PLAIN[DIM_NAMES[low[0]]]}"
             f"（{p[low[0]]:.1f}/5）")
    L.append("")
    L.append(f"加权总负担 {r['burden']:.1f}"
             f"（自驱和挫折耐受权重最高——"
             f"自驱和扛得住，比聪明更决定你能走多远）")
    return L


# ==================================================================
# 访谈：七问、选项、对照
# ==================================================================
# 【为什么这一段放在共享核心里】
# 牌局和对话要问**同一套问题、同一套选项**——不然两边对照出来的数
# 根本不可比（牌上 1—5，对话那边按别的尺子，用户看到两个互相矛盾的答案）。
# 复制两份再靠检查同步，是把一致性寄托在「以后每次都记得跑检查」上。
# _mirror_core.py 本来就被两个应用内联，放这儿就是**一处定义**。
#
# 【这一层最容易出的错】
#   ① 把「没答」当成低分——那等于替用户判他的能力
#   ② 「落差」和「证据不足」混成一堆——两件事意思相反
#   ③ 七问和七维对不上——题面问的和它记的不是一件事
DIM_SHORT = ["想不想得过来", "背不背得下来", "抠不抠得住细节",
             "动不动得了手", "自己推不推得动", "扛不扛得住反复失败",
             "等不等得起"]

# (题目, 这一问真正问的是哪一维)
# 把「问的是哪一维」写出来，是为了以后好复查：
# **题目一旦和维度脱节，下面整张对照表就都错了。**
ASK = [
    ("说件真事：你为了一个东西，最长连着熬了多久？",
     "认知负荷"),

    ("再一件：你有没有过「硬背下来、当时还不懂，后来才明白」的经历？"
     "最近一次是什么时候？", "记忆量"),

    ("下面这句话你更像哪一种——"
     "「我们那组，最后细节都是我在抠」，"
     "还是「差不多能过就行，我不太在意那点差别」？",
     "细节分辨"),

    ("你上一次亲手做出一件东西是什么时候？"
     "（写的、画的、修的、拍的、装的、算的都算）", "动手要求"),

    ("一件事没老师、没作业、没人检查，你自己推得动吗？",
     "自驱要求"),

    ("做一件事连着失败好几回，你会怎么样？", "挫折耐受"),

    ("你有没有做过一件「很久以后才知道有没有用」的事？", "慢反馈耐受"),
]

# 每题三个选项 → (这一维的分数 或 None, 选项文字, 选完它说什么)
# None = 不知道。**「没试过」只能是 None。**
OPTIONS = {
    "认知负荷": [
        (2, "没有过。作业和考试之外，我没为别的事通宵过",
         "「没有过」不是缺点——是**我手上还没有你这方面的证据**。"
         "这一维我记「不知道」，不当 1 分算。"),
        (4, "有，一两个通宵，缓两天就回来了",
         "一次通宵缓过来——这一项我记 4/5。"),
        (5, "有，连着熬过，而且是常态",
         "连着熬是常态。这一项记 5/5。"
         "**这不是夸你能吃苦**，是说这条路上你确实走得动。"),
        (None, "说不好，我熬过但没注意过缓不缓得回来",
         "「说不好」就是不知道。这一维我记「不知道」，不猜。"),
    ],
    "记忆量": [
        (1, "基本没有。我很少靠硬背，理解完就算了",
         "你不太靠硬背——这一项记 1/5。"
         "**意思是「要大量背」的专业对你不是不行，是会比别人慢。**"),
        (3, "有过，但得反复好几遍才记住",
         "反复几遍能记住——记 3/5。"
         "这是最常见的状态，**不丢人**。"),
        (5, "经常这样，背下来之后再慢慢懂，我习惯了",
         "你把「先背下来再懂」当成习惯了——记 5/5。"),
        (None, "想不起来有没有过，说不好",
         "想不起来就是不知道。这一维我记「不知道」。"),
    ],
    "细节分辨": [
        (1, "差不多能过就行，我不太在意那点差别",
         "你不在意细节差别——这一项记 1/5。"
         "**记账、审计、手术这种「差一点就出事」的活，"
         "这个分数会一直是落差。**"),
        (3, "看情况。要紧的地方我会抠，不要紧的地方就算了",
         "你会分轻重——记 3/5。"),
        (5, "细节都是我在抠，别人做的我不放心",
         "细节是你在抠——记 5/5。"),
        (None, "没人跟我说过这个，我自己也说不准",
         "「没人跟我说过」——**这件事本来就靠别人反馈才知道**。"
         "这一维我记「不知道」，不当低分。"),
    ],
    "动手要求": [
        (1, "想不起来。我基本是看和想，很少上手做",
         "你很少上手——记 1/5。"
         "**动手要求高的专业这一项会一直亮落差。**"),
        (3, "有，但要有人带着才做得下去",
         "有人带能坐下去——记 3/5。"),
        (5, "有，而且不用人催，自己就能鼓捣半天",
         "不用人催就能鼓捣——记 5/5。"),
        (None, "说不好，我想不出算不算",
         "想不出算不算，就是不知道。这一维我记「不知道」。"),
    ],
    "自驱要求": [
        (1, "推不动。没人催我基本不会开始",
         "没人催就推不动——记 1/5。"
         "**这一条很重要：大学和以后大部分时间都没人催。**"),
        (2, "得有个明确目标才推得动，没目标就散",
         "要有明确目标才动——记 2/5。"),
        (5, "推得动，没什么人管也一样干",
         "没人管也一样干——记 5/5。"),
        (None, "看什么事，我说不准一个数",
         "「看什么事」是实话——**但也说明这一项还没有一个稳定的数**。"
         "我记「不知道」。"),
    ],
    "挫折耐受": [
        (1, "几次下来就不想碰了",
         "几次就不想碰——记 1/5。"),
        (3, "会烦，但歇一下还能接着来",
         "会烦，歇一下还能来——记 3/5。"),
        (5, "失败了反而更想弄明白为什么",
         "失败了更想弄明白——记 5/5。"),
        (None, "看是什么事，不一样",
         "不一样就是不知道。这一维我记「不知道」。"),
    ],
    "慢反馈耐受": [
        (1, "没做过，或者做了几次没动静就放下了",
         "「几次没动静就放下」——记 1/5。"
         "**注意这一条在下面会亮很多落差**："
         "医学、建筑、基础理科都是「几年后才知道有没有用」。"),
        (3, "做过，中间断过，后来还是接着做了",
         "中间断过又接上——记 3/5。"),
        (5, "做过，而且当时完全看不出有什么用，我也做完了",
         "看不出用也做完了——记 5/5。"),
        (None, "想不起来有没有过，说不好",
         "想不起来就是不知道。这一维我记「不知道」。"),
    ],
}
# 把题面文字映射到维度，方便按维度取答案
Q_OF = {q: dim for q, dim in ASK}


# ==================================================================
# 问**专业**的那套题（访谈工作台用）
# ==================================================================
# 【和 ASK 的区别，这是最容易搞错的地方】
#   ASK  —— 问**人**：「你为了一个东西最长连着熬了多久？」
#           答案是他对自己的描述，结果是**这个人的七维**。
#   下面 —— 问**专业**：「这个专业要你背多少？」
#           答案是它的培养要求，结果是**这个专业的七维**。
#
# 两者都是 7 个 1—5，**方向相反**。
# 拿 ASK 去问一个专业，或者拿这套去问一个人，都会得到
# 一堆看似能用、其实量错对象的数据——**而且它不会报错。**
#
# 所以两套题**分开定义、分开命名**，靠名字就看得出来在问谁。
DEMAND_ASK = [
    ("认知负荷", "这个专业要你一次坐得住多久？"
                 "（一学期几门硬课、作业和实验压不压得过来）"),
    ("记忆量", "它有多依赖硬背？"
               "（名词、条文、方剂、解剖、公式，是理解为主还是要背下来）"),
    ("细节分辨", "它有多抠细节？"
                 "（差一点就算错的地方多不多：规范、剂量、代码边界、标点精度）"),
    ("动手要求", "它有多依赖动手？"
                 "（实验、上机、实操、画图、临床、下地、拆装）"),
    ("自驱要求", "它有多依赖你自己推？"
                 "（有没有人给你排好、有没有明确目标，还是得自己找题做）"),
    ("挫折耐受", "它要你扛多少次失败？"
                 "（调不出来、被否、做废、重做，是不是常态）"),
    ("慢反馈耐受", "它多久才给你一次像样的正反馈？"
                   "（一个学期、几年，还是做完就知道好不好）"),
]

# 五个档的统一说法。**同一把尺子，七维共用**——
# 这样专业之间的数字才比得了。
DEMAND_LEVELS = [
    (1, "很低", "基本不需要／很少"),
    (2, "不高", "偶尔要，但不是重点"),
    (3, "中等", "是常规要求，绕不开"),
    (4, "较高", "占用大量时间，是主要门槛之一"),
    (5, "很高", "是它最硬的那道门槛"),
]

# 允许「说不好」——和 ASK 一样，**不知道是合法答案**。
# 工作台里填「不知道」的维度会被记成 None，不写进 dims。
DEMAND_ALLOW_UNKNOWN = True


def demand_questions():
    """七道「问专业」的题，带维度名和五档说法。"""
    out = []
    for dim, q in DEMAND_ASK:
        out.append({"dimension": dim, "question": q,
                    "levels": [{"score": s, "label": lb, "means": m}
                               for s, lb, m in DEMAND_LEVELS]})
    return out


def check_demand_answers(vals):
    """校验一份专业七维答案。**错了要当场说清楚错在哪。**"""
    errs = []
    if not isinstance(vals, list):
        return [f"要 7 个数组成的 list，给的是 {type(vals).__name__}"]
    if len(vals) != 7:
        errs.append(f"要 7 个数，给了 {len(vals)}")
    for i, v in enumerate(vals):
        nm = DIM_NAMES[i] if i < len(DIM_NAMES) else f"第{i + 1}项"
        if v is None:
            continue                       # 不知道是合法答案
        if not isinstance(v, int) or isinstance(v, bool):
            errs.append(f"{nm} 要整数或 null，给了 {v!r}")
        elif not 1 <= v <= 5:
            errs.append(f"{nm} 要 1—5，给了 {v}")
    return errs


def check_interview_record(rec, names=None):
    """一条访谈记录能不能用。**校验只有这一份，谁都别另写一套。**

    【为什么必须共用】
    写这个文件的有两个地方：工作台（录入）和装配器（并进牌堆）。
    第一版只有工作台在校验，装配器**全盘信任**。
    于是一份被工作台拒收、但仍然躺在文件里的坏记录，
    被装配器**直接并进了牌堆**——越界的 9、只有 3 个数的、
    连署名都没有的，四条全进去了。
    **同一份数据有两个写入方、两套规则，就一定有一边是漏的。**
    """
    errs = []
    nm = rec.get("major")
    if not nm:
        errs.append("没有 major")
    elif names is not None and nm not in names:
        errs.append(f"库里没有「{nm}」这个专业")
    errs += [f"dims：{e}" for e in check_demand_answers(rec.get("dims"))]
    if not str(rec.get("who") or "").strip():
        errs.append("没有 who（问的是谁，写明身份）")
    if not str(rec.get("on") or "").strip():
        errs.append("没有 on（哪天问的）")
    ev = rec.get("evidence")
    if ev is not None and not isinstance(ev, list):
        errs.append("evidence 要是 list")
    return errs


def interview_result(ans, majors=None):
    """拿用户答的 7 个数（可能含 None），和专业的需求画像个个比。

    【返回三种结果，不含第四条】
      agree  —— 你说的每一项都 ≥ 它要的（**它要的你都说你受得了**）
      gap    —— 有至少一项它要的比你受得了的多（落差）
      unknown——它有的项你答「不知道」

    【为什么必须把 unknown 单列】
    不然「你没答」和「你答了但不够」会混成同一堆，
    而这两件事的意思完全相反——一个是**我没证据**，
    一个是**有证据而且对不上**。

    【dims 里也可能有 None，这一条是后补的】
    访谈工作台允许「这一维没聊到 → 记不知道」，
    所以专业的 dims 里**会留白**。
    原来的写法是 `ans[i] < d[i]` 和 `sum(dims)`——
    **两处遇到 None 都直接抛 TypeError**，整个访谈页白屏。
    它之前没被发现，是因为手写的 94 个 dims 恰好全是 1—5，
    **样本太干净，等于没测。**
    现在：只有**两边都知道**的那一项才参与比大小。
    """
    res = {"agree": [], "gap": [], "unknown": []}
    # 【默认值已经撤掉了——这里欠过一笔账】
    # 原来的写法是 `(MAJORS if majors is None else majors)`。
    # 它在应用里跑得动，只因为那时的全局命名空间里恰好有 `MAJORS`；
    # **换个上下文跑就是 `NameError`。**
    # 这一笔是 `_审计/_check_chat_interview.py` 替共享核心跑的时候露出来的：
    # 它拿 `_mirror_core.py` 本体执行，然后 `interview_result` 直接崩。
    # 靠全局变量拿数据，正是「换个地方跑就静默拿错一批专业」的那类 bug——
    # 所以不退回全局，也不静默当成空名单，**缺了就报清楚**。
    if majors is None:
        raise TypeError(
            "interview_result 必须显式传入 majors（专业名单）。"
            "它以前会退回一个只存在于应用里的全局 MAJORS，"
            "那样独立跑会 NameError、换个上下文会静默拿错名单。")
    for m in majors:
        d = m.get("dims")
        if not d or all(x is None for x in d):
            # 一个数都没有的专业不进对照——**没有画像 ≠ 证据不足**。
            # 它是「这个专业我们还没做」，不该混进「你没答」那一堆，
            # 否则覆盖率一涨，那一堆看起来反而更糟。
            continue
        both = [i for i in range(7)
                if ans[i] is not None and d[i] is not None]
        gaps = [(i, ans[i], d[i]) for i in both if ans[i] < d[i]]
        # 答了、但这个专业那一维是空白 → 不是他的问题，也不进 unknown
        unknown = [i for i in range(7)
                   if ans[i] is None and d[i] is not None]
        rec = (m, len(gaps), gaps, unknown)
        if gaps:
            res["gap"].append(rec)
        elif unknown:
            res["unknown"].append(rec)
        else:
            res["agree"].append(rec)
    # 落差小的排前面（更接近）；一致的按「要得越多越靠前」排，
    # 因为**要求越高的专业还全对得上，信息量越大**。
    # 求和时跳过 None——**一行留白就能把整页带崩。**
    def _sum(mj):
        return sum(x for x in (mj.get("dims") or []) if x is not None)
    res["gap"].sort(key=lambda r: r[1])
    res["agree"].sort(key=lambda r: -_sum(r[0]))
    res["unknown"].sort(key=lambda r: -_sum(r[0]))
    return res


def spread_of_dim(i, majors=None):
    """这一维跨全部有画像专业的标准差——**它有多少区分力的底数**。

    【这个数不参与推荐，只用来坦白】
    实测（94 份人工画像）：
      动手要求 1.49、细节分辨 0.97、记忆量 0.81 —— 用了 1—5 全档
      慢反馈耐受 0.56、挫折耐受 0.54、认知负荷 0.50
        —— **1 分和 2 分是 0 个专业**，下半段是空的
    所以「认知负荷」这一维问出来的东西比「动手要求」粗得多。
    这不是算法问题，是那 94 份画像的来源问题——**数据就是那样**，
    我把它量出来，不假装它很细。

    【曾经用它做过什么，为什么又不做了】
    我一度想用它来挑「再问哪一维最能切开长名单」。
    那个做法**不可达**：名单长恰恰因为七项都答了。
    详见 `_审计/_check_interview_power.py` 里那段推演。
    现在它只服务于「坦白这一维有多粗」。
    """

    # 【和 interview_result 同一个理由，见那里的注释】
    if majors is None:
        raise TypeError(
            "spread_of_dim 必须显式传入 majors（专业名单）。"
            "它以前会退回一个只存在于应用里的全局 MAJORS。")
    vals = [m["dims"][i] for m in majors
            if m.get("dims") and m["dims"][i] is not None]
    if len(vals) < 2:
        return 0.0
    mu = sum(vals) / len(vals)
    return (sum((v - mu) ** 2 for v in vals) / len(vals)) ** 0.5
