"""追加第二卷对话标注"""
import sys, json
sys.stdout.reconfigure(encoding='utf-8')

v2_dialogues = [
    # 序曲 - 春日不相信阿虚说的真相
    {"speaker": "阿虚", "text": "我有重要的事情要跟你说，你好好听著。", "vol": 2, "ch": "序曲"},
    {"speaker": "凉宫春日", "text": "干嘛？", "vol": 2, "ch": "序曲"},
    {"speaker": "阿虚", "text": "你不是一直希望有外星人或未来人，或者超能力者的存在吗？", "vol": 2, "ch": "序曲"},
    {"speaker": "凉宫春日", "text": "没错啊，那又怎样？", "vol": 2, "ch": "序曲"},
    {"speaker": "阿虚", "text": "也就是说，我们SOS团的目的就是找出这样的人，对吧？你有没有想过那些人会不会根本就出乎意料的近在眼前呢？", "vol": 2, "ch": "序曲"},
    {"speaker": "凉宫春日", "text": "啊？你指的是谁？你说的该不会是有希或实玖瑠，或者是古泉吧？如果是他们，那可一点都不算是『出乎意料』。", "vol": 2, "ch": "序曲"},
    {"speaker": "阿虚", "text": "那个长门有希就是外星人。朝比奈她是未来人。古泉是超能力者。", "vol": 2, "ch": "序曲"},
    {"speaker": "凉宫春日", "text": "耍什么白痴啊！", "vol": 2, "ch": "序曲"},
    {"speaker": "凉宫春日", "text": "不管是外星人、未来人、还是超能力者，他们是不可能随随便便出现在我们眼前的！我随便挑选的团员怎么可能全部都是那样的人！", "vol": 2, "ch": "序曲"},
    {"speaker": "凉宫春日", "text": "我不想再听你讲这种无聊的笑话了。我们走吧！", "vol": 2, "ch": "序曲"},
    # 第一章 - 决定拍电影
    {"speaker": "凉宫春日", "text": "什么问卷发表？简直蠢到极点！那种事有什么好玩的？", "vol": 2, "ch": "第一章"},
    {"speaker": "凉宫春日", "text": "校庆是校庆，我们SOS团要做更有趣的事！", "vol": 2, "ch": "第一章"},
    {"speaker": "凉宫春日", "text": "喂，阿虚，你有没有在听啊？", "vol": 2, "ch": "第一章"},
    {"speaker": "阿虚", "text": "我没听到，怎样？", "vol": 2, "ch": "第一章"},
    {"speaker": "凉宫春日", "text": "我在说校庆、校庆啦！", "vol": 2, "ch": "第一章"},
    {"speaker": "朝比奈实玖瑠", "text": "啊……两位好。我马上去泡茶。", "vol": 2, "ch": "第一章"},
    {"speaker": "凉宫春日", "text": "古泉呢？", "vol": 2, "ch": "第一章"},
    {"speaker": "朝比奈实玖瑠", "text": "那、那个……他还没到。", "vol": 2, "ch": "第一章"},
    {"speaker": "凉宫春日", "text": "实玖瑠，我记得之前跟你说过了，端茶来时，每三次至少要有一次不小心把茶杯打翻才行！", "vol": 2, "ch": "第一章"},
    {"speaker": "古泉一树", "text": "对不起，我来迟了。因为课外辅导的时间延长了。", "vol": 2, "ch": "第一章"},
    {"speaker": "古泉一树", "text": "看来我是最后一个到的。", "vol": 2, "ch": "第一章"},
    {"speaker": "凉宫春日", "text": "我们SOS团将举办电影试映会！", "vol": 2, "ch": "第一章"},
    {"speaker": "古泉一树", "text": "原来如此。也就是说，我们自行拍摄电影，然后吸引客人前来观赏，对吧？", "vol": 2, "ch": "第一章"},
    {"speaker": "凉宫春日", "text": "连那种无聊的电影都有了。那我一定可以拍得比他更好！你们有什么意见吗？", "vol": 2, "ch": "第一章"},
    {"speaker": "凉宫春日", "text": "角色分配就如上面所写。女主角是朝比奈实玖瑠，男主角是古泉一树。", "vol": 2, "ch": "第一章"},
    {"speaker": "朝比奈实玖瑠", "text": "由我主演吗？……我不会演戏。", "vol": 2, "ch": "第一章"},
    {"speaker": "凉宫春日", "text": "不用担心，我会好好地指导你的。", "vol": 2, "ch": "第一章"},
    # 第二章 - 调度器材
    {"speaker": "凉宫春日", "text": "现在我们去调度摄影机。", "vol": 2, "ch": "第二章"},
    {"speaker": "朝比奈实玖瑠", "text": "那、那个……凉、凉宫同学，我想起来我还有事。", "vol": 2, "ch": "第二章"},
    {"speaker": "凉宫春日", "text": "别担心。这次我不会拿实玖瑠的身体抵付货款的。", "vol": 2, "ch": "第二章"},
    {"speaker": "凉宫春日", "text": "我要去跟赞助者调度啦，带女主角同行应该比较容易得到好印象吧？你也一起来吧！来搬运货物。", "vol": 2, "ch": "第二章"},
    {"speaker": "古泉一树", "text": "这样不是很好吗？我对凉宫同学想拍什么电影倒是挺有兴趣的。", "vol": 2, "ch": "第二章"},
    {"speaker": "凉宫春日", "text": "第一步算是成功了。现在到下一家店去！", "vol": 2, "ch": "第二章"},
    {"speaker": "谷口", "text": "哟，阿虚！你抱着什么东西啊？能够担任守护凉宫任务的，古往今来就只有你一人了。", "vol": 2, "ch": "第二章"},
]

result_path = r'F:\Extra Learning\github\haruhi-skill\reference\novel_dialogues_annotated.json'
with open(result_path, 'r', encoding='utf-8') as f:
    existing = json.load(f)
existing.extend(v2_dialogues)
with open(result_path, 'w', encoding='utf-8') as f:
    json.dump(existing, f, ensure_ascii=False, indent=2)
print(f"追加 {len(v2_dialogues)} 条，总计 {len(existing)} 条")

from collections import Counter
vols = Counter(d.get('vol', 0) for d in existing)
print(f"各卷分布: {dict(sorted(vols.items()))}")
