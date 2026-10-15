"""Locked structure for phase A: 5 people, 3 spots (2 campus + 1 park)."""

PERSON_COUNT = 5
CAMPUS_SPOT_COUNT = 2
PARK_SPOT_COUNT = 1
TOTAL_SPOT_COUNT = CAMPUS_SPOT_COUNT + PARK_SPOT_COUNT
CAMPUS_PLATE_COUNT = CAMPUS_SPOT_COUNT * 2  # 4

SPOT_TYPE_CAMPUS = "campus"
SPOT_TYPE_PARK = "park"

DEFAULT_PEOPLE = [
    {"id": "p1", "name": "张三"},
    {"id": "p2", "name": "李四"},
    {"id": "p3", "name": "王五"},
    {"id": "p4", "name": "赵六"},
    {"id": "p5", "name": "钱七"},
]

DEFAULT_SPOTS = [
    {"type": SPOT_TYPE_CAMPUS, "label": "园区车位", "count": CAMPUS_SPOT_COUNT},
    {"type": SPOT_TYPE_PARK, "label": "公园车位", "count": PARK_SPOT_COUNT},
]

DEFAULT_RULES_TEXT = """【停车轮换抽签规则】

一、基本设定
• 参与人数固定 5 人，车位固定 3 个：园区车位 2 个、公园车位 1 个。
• 每半年轮换一次；每人中签后占用对应车位一个半年周期。
• 园区 2 个车位可录 4 个车牌（不与具体车位绑定）：录了牌的人都能进园区；有固定园区车位的按抽签结果停车，无固定车位者可临停。抽中公园车位者不录园区车牌。

二、抽签池
• 必中池：上一轮未中签的人，本轮必定获得车位。
• 轮空池：连续两轮都中签的人，本轮不参与抽签。
• 候选池（保留池）：上一轮中签且本轮不轮空的人；从中随机抽取「保留名额」继续占用车位。
• 首轮：必中池与轮空池为空，候选池为全体 5 人，从中随机抽取 3 人。

三、非首轮如何产生 3 名中签者
1. 必中池 2 人全部进入中签。
2. 从候选池中随机抽取 1 人保留车位。
3. 轮空池不参与。
4. 3 名中签者再随机分配：2 个园区车位 + 1 个公园车位。

四、连续中签与轮空
• 「连续两次抽中」指同一人连续两轮获得车位（不区分园区/公园）。
• 达到连续 2 次后，下一轮进入轮空池。
• 轮空当轮视为未中，连胜次数清零；之后从下一次中签重新计为第 1 次。

五、园区录牌名单
• 每轮结果确定后：园区录牌 = 全体 5 人减去抽中公园车位的那 1 人（共 4 人姓名）。
• 系统只展示姓名，不维护真实车牌号。

六、历史与撤销
• 每次抽签会记录分配结果，以及分配前后的必中/轮空/候选池状态。
• 周期命名格式为「日期 #第几次」（如 2026-10-15 #1）。
• 支持撤销最近一次抽签，状态回滚到该次抽签之前。
"""
