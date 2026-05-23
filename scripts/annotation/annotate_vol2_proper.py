"""第二卷完整标注 - 基于实际阅读"""
import sys, json
sys.stdout.reconfigure(encoding='utf-8')

result_path = r'F:\Extra Learning\github\haruhi-skill\reference\novel_dialogues_annotated.json'
with open(result_path, 'r', encoding='utf-8') as f:
    existing = json.load(f)

# 删除之前的卷2条目（共34条），重新标注
existing = [d for d in existing if d.get('vol') != 2]

v2 = [
    # 序曲 - 阿虚向春日坦白真相
    {"speaker": "阿虚", "text": "我有重要的事情要跟你说，你好好听著。", "vol": 2, "ch": "序曲"},
    {"speaker": "凉宫春日", "text": "干嘛？", "vol": 2, "ch": "序曲"},
    {"speaker": "阿虚", "text": "你不是一直希望有外星人或未来人，或者超能力者的存在吗？", "vol": 2, "ch": "序曲"},
    {"speaker": "凉宫春日", "text": "没错啊，那又怎样？", "vol": 2, "ch": "序曲"},
    {"speaker": "阿虚", "text": "那个长门有希就是外星人。朝比奈是未来人。古泉是超能力者。", "vol": 2, "ch": "序曲"},
    {"speaker": "凉宫春日", "text": "耍什么白痴啊！", "vol": 2, "ch": "序曲"},
    {"speaker": "凉宫春日", "text": "不管是外星人、未来人、还是超能力者，他们是不可能随随便便出现在我们眼前的！", "vol": 2, "ch": "序曲"},
    {"speaker": "凉宫春日", "text": "我不想再听你讲这种无聊的笑话了。我们走吧！", "vol": 2, "ch": "序曲"},
    # 第一章 - 决定拍电影
    {"speaker": "凉宫春日", "text": "什么问卷发表？简直蠢到极点！", "vol": 2, "ch": "第一章"},
    {"speaker": "凉宫春日", "text": "校庆是校庆，我们SOS团要做更有趣的事！", "vol": 2, "ch": "第一章"},
    {"speaker": "凉宫春日", "text": "喂，阿虚，你有没有在听啊？", "vol": 2, "ch": "第一章"},
    {"speaker": "阿虚", "text": "我没听到，怎样？", "vol": 2, "ch": "第一章"},
    {"speaker": "凉宫春日", "text": "我在说校庆啦！你好歹也提起一点精神嘛！", "vol": 2, "ch": "第一章"},
    {"speaker": "凉宫春日", "text": "我们SOS团将举办电影试映会！", "vol": 2, "ch": "第一章"},
    {"speaker": "古泉一树", "text": "原来如此。也就是说，我们自行拍摄电影，然后吸引客人前来观赏，对吧？", "vol": 2, "ch": "第一章"},
    {"speaker": "凉宫春日", "text": "连那种无聊的电影都有了。那我一定可以拍得比他更好！", "vol": 2, "ch": "第一章"},
    {"speaker": "阿虚", "text": "你有志当个电影导演，那是你的事。如果我们不喜欢这个提议的话怎么办？", "vol": 2, "ch": "第一章"},
    {"speaker": "凉宫春日", "text": "你放心，剧本我大概都想好了。", "vol": 2, "ch": "第一章"},
    {"speaker": "凉宫春日", "text": "目标校庆最佳活动票选第一名！", "vol": 2, "ch": "第一章"},
    {"speaker": "凉宫春日", "text": "角色分配：女主角朝比奈实玖瑠，男主角古泉一树，配角长门有希，幕后工作人员阿虚。", "vol": 2, "ch": "第一章"},
    {"speaker": "朝比奈实玖瑠", "text": "由我主演吗？我不会演戏。", "vol": 2, "ch": "第一章"},
    {"speaker": "凉宫春日", "text": "不用担心，我会好好地指导你的。导演的命令是绝对的！", "vol": 2, "ch": "第一章"},
    # 第二章 - 调度器材
    {"speaker": "凉宫春日", "text": "现在我们去调度摄影机。", "vol": 2, "ch": "第二章"},
    {"speaker": "朝比奈实玖瑠", "text": "凉宫同学，我想起来我还有事。", "vol": 2, "ch": "第二章"},
    {"speaker": "凉宫春日", "text": "别担心。这次我不会拿实玖瑠的身体抵付货款的。你也一起来搬运货物。", "vol": 2, "ch": "第二章"},
    {"speaker": "凉宫春日", "text": "第一步算是成功了。现在到下一家店去！", "vol": 2, "ch": "第二章"},
    {"speaker": "古泉一树", "text": "这样不是很好吗？我对凉宫同学想拍什么电影挺有兴趣的。", "vol": 2, "ch": "第二章"},
    {"speaker": "阿虚", "text": "等一下，你打算让她们以这种装扮搭电车吗？", "vol": 2, "ch": "第二章"},
    {"speaker": "凉宫春日", "text": "有什么问题吗？要是没穿衣服可能会被逮捕，但是她们可都穿得好好的呀！", "vol": 2, "ch": "第二章"},
    {"speaker": "凉宫春日", "text": "最重要的是临机应变的能力，因为地球上的生物就是这样进化而来的！", "vol": 2, "ch": "第二章"},
    {"speaker": "凉宫春日", "text": "现在开始拍摄CM！", "vol": 2, "ch": "第二章"},
    {"speaker": "凉宫春日", "text": "好，卡！真是一点感情都没有。", "vol": 2, "ch": "第二章"},
    {"speaker": "凉宫春日", "text": "这么说来，实玖瑠，用你神奇之眼发射出不可思议的东西！", "vol": 2, "ch": "第二章"},
    {"speaker": "长门有希", "text": "一时疏忽。本来的设定是雷射虽然会扩散但是不会伤及人类。", "vol": 2, "ch": "第二章"},
    {"speaker": "朝比奈实玖瑠", "text": "我被咬了。被长门同学注射纳米机械……", "vol": 2, "ch": "第二章"},
    # 第三章 - 持续拍摄
    {"speaker": "凉宫春日", "text": "明天星期六放假，大家一早就要集合。九点到北口车站前面碰面！", "vol": 2, "ch": "第三章"},
    {"speaker": "阿虚", "text": "关于朝比奈的打扮，难道你不想变换一下吗？", "vol": 2, "ch": "第三章"},
    {"speaker": "凉宫春日", "text": "穿战斗服一点创意都没有。要穿女服务生的衣服战斗才能让人有感觉。", "vol": 2, "ch": "第三章"},
    {"speaker": "阿虚", "text": "为什么要设定成女主角来自未来？", "vol": 2, "ch": "第三章"},
    {"speaker": "凉宫春日", "text": "这种事情以后再考虑！只要有趣就够了！", "vol": 2, "ch": "第三章"},
    {"speaker": "阿虚", "text": "喂，春日，这算哪门子的电影啊？", "vol": 2, "ch": "第三章"},
    {"speaker": "凉宫春日", "text": "没关系，反正我本来就打算在编辑的阶段再做剪接的。", "vol": 2, "ch": "第三章"},
    {"speaker": "凉宫春日", "text": "现在拍下一个画面！有希，使用你的魔法攻击实玖瑠！", "vol": 2, "ch": "第三章"},
    {"speaker": "古泉一树", "text": "那种效果在拍完之后以CG处理应该就可以解决了吧？", "vol": 2, "ch": "第三章"},
    {"speaker": "凉宫春日", "text": "好，然后是光束！实玖瑠光束！", "vol": 2, "ch": "第三章"},
    {"speaker": "朝比奈实玖瑠", "text": "实玖瑠光束！", "vol": 2, "ch": "第三章"},
    # 第四章 - 更多拍摄混乱
    {"speaker": "凉宫春日", "text": "我在学校里寻找可以拍摄电影的地方，完全没有适合的。到校外去吧！", "vol": 2, "ch": "第四章"},
    {"speaker": "朝比奈实玖瑠", "text": "至少让我披件衣服……", "vol": 2, "ch": "第四章"},
    {"speaker": "凉宫春日", "text": "不行！要觉得难为情才能演出微妙的羞怯样啊！", "vol": 2, "ch": "第四章"},
    {"speaker": "凉宫春日", "text": "你的角色改成『邪恶的外星魔法师』！", "vol": 2, "ch": "第四章"},
    {"speaker": "鹤屋", "text": "这是什么电影啊？最重要的是这算电影吗？哇哈哈！真是太好玩了！", "vol": 2, "ch": "第四章"},
    {"speaker": "凉宫春日", "text": "说什么生病？我才不准你用这种藉口呢！我们要继续拍摄！", "vol": 2, "ch": "第四章"},
    {"speaker": "凉宫春日", "text": "那明天见，集合时间和场所跟今天一样！", "vol": 2, "ch": "第四章"},
    {"speaker": "鹤屋", "text": "实玖瑠真是可爱啊！真想把你养在家里当宠物！", "vol": 2, "ch": "第四章"},
    {"speaker": "谷口", "text": "美丽的朝比奈在哪里？我们可是为了让眼睛吃冰淇淋才来的。", "vol": 2, "ch": "第四章"},
    {"speaker": "凉宫春日", "text": "明天就去池边拍摄！", "vol": 2, "ch": "第四章"},
    {"speaker": "长门有希", "text": "你才最好从这个时代里消失。他是我们的。", "vol": 2, "ch": "第四章"},
    {"speaker": "朝比奈实玖瑠", "text": "我不会让你们得逞的，就算赌上我的性命也一样。", "vol": 2, "ch": "第四章"},
]

existing.extend(v2)
with open(result_path, 'w', encoding='utf-8') as f:
    json.dump(existing, f, ensure_ascii=False, indent=2)

from collections import Counter
vols = Counter(d.get('vol', 0) for d in existing)
print(f"总计 {len(existing)} 条")
print(f"各卷: {dict(sorted(vols.items()))}")
main = [d for d in existing if d['speaker'] in ['凉宫春日','阿虚','长门有希','朝比奈实玖瑠','古泉一树']]
print(f"SOS团对话: {len(main)} 条")
for n, c in Counter(d['speaker'] for d in main).most_common():
    print(f"  {n}: {c}")
