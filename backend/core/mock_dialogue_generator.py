"""
模拟对话生成器

当LLM API不可用时，使用此模块生成丰富多样的Agent对话
每个Agent都有独特的说话风格，避免重复和刻板
"""

import random
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class AgentPersonality:
    """Agent性格特征"""
    name: str
    authority: float
    selfishness: float
    altruism: float
    sociability: float
    intelligence: float
    risk_appetite: float
    resilience: float
    loyalty: float
    is_traitor: bool = False


class MockDialogueGenerator:
    """
    模拟对话生成器
    
    生成丰富、多样、个性化的Agent对话
    避免简短、重复、刻板的回复
    """
    
    def __init__(self, seed: int = None):
        self.rng = random.Random(seed)
        
    def generate_response(
        self,
        agent: AgentPersonality,
        message_type: str,
        context: Dict,
        receiver_name: str = "同事"
    ) -> str:
        """
        根据Agent性格生成个性化回复
        
        Args:
            agent: Agent性格特征
            message_type: 消息类型 (report, request, status, chat, alert, persuade)
            context: 上下文信息
            receiver_name: 接收者名称
            
        Returns:
            个性化回复文本
        """
        # 根据性格特征选择回复风格
        style = self._determine_style(agent)
        
        # 根据消息类型和风格生成回复
        generators = {
            'report': self._generate_report,
            'request': self._generate_request,
            'status': self._generate_status,
            'chat': self._generate_chat,
            'alert': self._generate_alert,
            'persuade': self._generate_persuade,
        }
        
        generator = generators.get(message_type, self._generate_chat)
        return generator(agent, style, context, receiver_name)
    
    def _determine_style(self, agent: AgentPersonality) -> str:
        """根据性格确定说话风格"""
        styles = []
        
        if agent.authority > 0.7:
            styles.append('commanding')
        elif agent.authority < 0.3:
            styles.append('humble')
            
        if agent.sociability > 0.7:
            styles.append('friendly')
        elif agent.sociability < 0.3:
            styles.append('reserved')
            
        if agent.intelligence > 0.7:
            styles.append('analytical')
            
        if agent.selfishness > 0.7:
            styles.append('selfish')
        elif agent.altruism > 0.7:
            styles.append('altruistic')
            
        if agent.is_traitor:
            styles.append('deceptive')
            
        return self.rng.choice(styles) if styles else 'neutral'
    
    def _generate_report(self, agent: AgentPersonality, style: str, context: Dict, receiver: str) -> str:
        """生成工作汇报回复"""
        work_done = context.get('work_done', 50)
        contribution = context.get('contribution', 20)
        
        templates = {
            'commanding': [
                f"{receiver}，这轮我完成了{work_done}单位的工作，贡献值达到{contribution:.1f}。整体进度在我的掌控之中，预计下一轮可以继续保持这个势头。建议关注一下资源分配，确保后续效率不下降。",
                f"汇报一下进展：已完成{work_done}单位，贡献{contribution:.1f}。从数据看，我们的策略是有效的。我建议下一轮调整一下重心，把更多资源投入到核心任务上。",
            ],
            'humble': [
                f"{receiver}，这轮我尽力完成了{work_done}单位的工作，贡献{contribution:.1f}。虽然不算特别突出，但我会继续努力的。如果有需要改进的地方，请随时告诉我。",
                f"向您汇报：完成了{work_done}单位，贡献值{contribution:.1f}。我觉得还有提升空间，希望能得到您的指导。",
            ],
            'friendly': [
                f"嘿{receiver}！👋 这轮我搞定了{work_done}单位，贡献{contribution:.1f}！感觉状态不错～ 咱们这个节奏保持下去，应该能超额完成任务！✨",
                f"{receiver}，来汇报啦！完成了{work_done}单位，贡献{contribution:.1f}。这波配合得很顺，继续保持！💪",
            ],
            'analytical': [
                f"{receiver}，数据分析如下：完成工作量{work_done}单位，贡献值{contribution:.1f}，效率比上一轮提升约15%。从趋势看，如果保持当前策略，预计总产出可以达到预期目标的110%。建议优化资源分配算法。",
                f"汇报：工作量{work_done}，贡献{contribution:.1f}。通过对比分析，我发现当前工作流存在优化空间。具体建议已整理，稍后详细讨论。",
            ],
            'selfish': [
                f"{receiver}，这轮我做了{work_done}单位，贡献{contribution:.1f}。说实话，这个产出在当前条件下已经很不错了。我觉得我应该得到更多资源支持，这样下一轮能做得更好。",
                f"完成了{work_done}单位，贡献{contribution:.1f}。这个成绩在团队里应该算是前列了吧？希望能得到相应的认可和回报。",
            ],
            'altruistic': [
                f"{receiver}，这轮完成了{work_done}单位，贡献{contribution:.1f}。虽然个人数据还可以，但我更关心的是团队整体进展。有什么需要我帮忙的地方吗？我愿意分担更多。",
                f"汇报：{work_done}单位完成，贡献{contribution:.1f}。我觉得我们还可以做得更好，特别是帮助那些进度落后的同事。团队强了，个人才有价值。",
            ],
            'deceptive': [
                f"{receiver}，这轮完成了{work_done}单位，贡献{contribution:.1f}。数据看着还行，不过...（压低声音）我注意到有些地方不太对劲，可能有人在暗中搞小动作。咱们得小心点。",
                f"汇报数据：{work_done}单位，{contribution:.1f}贡献。表面上一切正常，但我发现几个可疑的迹象。私下跟你说，我觉得需要提高警惕。",
            ],
            'neutral': [
                f"{receiver}，这轮完成{work_done}单位工作，贡献值{contribution:.1f}。进度正常，没有发现异常。",
                f"汇报：工作量{work_done}，贡献{contribution:.1f}。一切按计划进行。",
            ],
        }
        
        return self.rng.choice(templates.get(style, templates['neutral']))
    
    def _generate_request(self, agent: AgentPersonality, style: str, context: Dict, receiver: str) -> str:
        """生成请求帮助回复"""
        request_amount = context.get('request_amount', 30)
        reason = context.get('request_reason', '工作需要')
        
        templates = {
            'commanding': [
                f"{receiver}，我需要{request_amount}单位资源支持，用于{reason}。这不是商量，是任务需要。请优先处理，时间紧迫。",
                f"请求支援：{request_amount}单位资源。理由：{reason}。请尽快落实，这关系到整体进度。",
            ],
            'humble': [
                f"{receiver}，不好意思打扰您...我需要{request_amount}单位资源，主要是{reason}。如果方便的话，能不能帮我协调一下？",
                f"能麻烦您一下吗？我需要{request_amount}单位资源用于{reason}。如果不麻烦的话...",
            ],
            'friendly': [
                f"嘿{receiver}！江湖救急啊！😅 我需要{request_amount}单位资源，{reason}。帮个忙呗，回头请你喝咖啡！☕",
                f"{receiver}，求助！🙏 需要{request_amount}单位资源，{reason}。你那边有没有余量？",
            ],
            'analytical': [
                f"{receiver}，基于当前情况分析，我需要申请{request_amount}单位资源。原因：{reason}。根据计算，这笔投入可以带来约20%的效率提升，ROI为正。",
                f"资源申请：{request_amount}单位。必要性：{reason}。预期收益：提升整体产出15%。建议批准。",
            ],
            'selfish': [
                f"{receiver}，我需要{request_amount}单位资源，{reason}。这对我个人进度很重要。你也知道，我的表现好了，整体数据也好看，对吧？",
                f"申请{request_amount}单位资源用于{reason}。我觉得这个投入是值得的，毕竟我的贡献率在团队里也是数一数二的。",
            ],
            'altruistic': [
                f"{receiver}，我需要{request_amount}单位资源，{reason}。其实不只是为了我自己，也是为了能帮团队做更多贡献。如果有余量的话，请考虑一下。",
                f"申请资源：{request_amount}单位，用途{reason}。如果批准了，我承诺会把多出来的产出回馈给团队。",
            ],
            'deceptive': [
                f"{receiver}，我需要{request_amount}单位资源，{reason}。顺便跟你说，我发现了一些...有趣的情况。咱们可以私下聊聊，我觉得对你也有好处。",
                f"请求{request_amount}单位资源，{reason}。另外，我掌握了一些内部信息，可能对你有用。咱们可以交换一下？",
            ],
            'neutral': [
                f"{receiver}，申请{request_amount}单位资源，用于{reason}。请审批。",
                f"资源请求：{request_amount}单位。用途：{reason}。",
            ],
        }
        
        return self.rng.choice(templates.get(style, templates['neutral']))
    
    def _generate_status(self, agent: AgentPersonality, style: str, context: Dict, receiver: str) -> str:
        """生成状态同步回复"""
        progress = context.get('progress', 0.5)
        status = context.get('my_status', '正常')
        
        templates = {
            'commanding': [
                f"{receiver}，状态更新：当前进度{progress*100:.0f}%，状态{status}。一切都在掌控中，无需担心。",
                f"同步状态：进度{progress*100:.0f}%，{status}。继续保持当前节奏。",
            ],
            'humble': [
                f"{receiver}，向您汇报状态：进度{progress*100:.0f}%，目前{status}。如果有做得不好的地方，请多指教。",
                f"状态同步：{progress*100:.0f}%进度，{status}。我会继续努力的。",
            ],
            'friendly': [
                f"嘿{receiver}！状态不错哦～ 进度{progress*100:.0f}%，{status}！🎉 保持这个势头！",
                f"{receiver}，来同步一下：{progress*100:.0f}%完成，状态{status}！感觉良好～ ✨",
            ],
            'analytical': [
                f"{receiver}，状态报告：进度{progress*100:.0f}%，系统状态{status}。各项指标正常，无异常波动。",
                f"数据同步：当前进度{progress*100:.0f}%，状态评估{status}。趋势稳定。",
            ],
            'selfish': [
                f"{receiver}，我的进度{progress*100:.0f}%，状态{status}。个人表现还可以，希望团队其他成员也能跟上。",
                f"状态更新：{progress*100:.0f}%完成，{status}。我这边没什么问题。",
            ],
            'altruistic': [
                f"{receiver}，状态{status}，进度{progress*100:.0f}%。我这边还好，更关心的是大家整体情况。需要我帮忙协调什么吗？",
                f"同步：{progress*100:.0f}%进度，{status}。团队有什么需要我支持的吗？",
            ],
            'deceptive': [
                f"{receiver}，表面看进度{progress*100:.0f}%，状态{status}。但...（小声）我发现有些不对劲的地方，私下跟你说。",
                f"状态报告：{progress*100:.0f}%，{status}。不过有些情况...不太方便在这里说。",
            ],
            'neutral': [
                f"{receiver}，进度{progress*100:.0f}%，状态{status}。",
                f"状态：{progress*100:.0f}%完成，{status}。",
            ],
        }
        
        return self.rng.choice(templates.get(style, templates['neutral']))
    
    def _generate_chat(self, agent: AgentPersonality, style: str, context: Dict, receiver: str) -> str:
        """生成闲聊回复"""
        topics = [
            "最近的工作节奏",
            "团队氛围",
            "个人状态",
            "对未来的看法",
            "小技巧分享",
        ]
        topic = self.rng.choice(topics)
        
        templates = {
            'commanding': [
                f"{receiver}，聊聊{topic}吧。我觉得目前整体方向是对的，但需要更强的执行力。你怎么看？",
                f"说到{topic}，我认为我们应该更主动一些。不能总是被动等待。",
            ],
            'humble': [
                f"{receiver}，关于{topic}，我想听听你的看法。我的经验有限，希望能向你学习。",
                f"能和你聊聊{topic}吗？我觉得你的见解总是很有价值。",
            ],
            'friendly': [
                f"嘿{receiver}！😊 最近{topic}怎么样？有空咱们可以多交流交流！",
                f"{receiver}，聊会儿呗～ 关于{topic}，你有什么心得？",
            ],
            'analytical': [
                f"{receiver}，从数据角度看{topic}，我发现了一些有趣的模式。你有兴趣探讨一下吗？",
                f"关于{topic}，我做了一些分析。想听听你的专业意见。",
            ],
            'selfish': [
                f"{receiver}，聊聊{topic}吧。说实话，我觉得现在的环境对我个人发展还挺有利的。",
                f"说到{topic}，我更关心的是怎么让自己做得更好。你有什么建议？",
            ],
            'altruistic': [
                f"{receiver}，关于{topic}，我觉得我们可以互相支持。团队强了，每个人都受益。",
                f"聊聊{topic}？我很乐意分享我的经验，也希望能帮到你。",
            ],
            'deceptive': [
                f"{receiver}，{topic}...（环顾四周）这里说话不方便。找个私密的地方，我有些重要信息想跟你分享。",
                f"关于{topic}，我掌握了一些内幕消息。感兴趣的话，咱们可以深入聊聊。",
            ],
            'neutral': [
                f"{receiver}，{topic}，你觉得呢？",
                f"聊聊{topic}吧。",
            ],
        }
        
        return self.rng.choice(templates.get(style, templates['neutral']))
    
    def _generate_alert(self, agent: AgentPersonality, style: str, context: Dict, receiver: str) -> str:
        """生成警告回复"""
        issues = context.get('issues', ['异常情况'])
        issue_str = '、'.join(issues)
        
        templates = {
            'commanding': [
                f"⚠️ {receiver}，紧急！发现{issue_str}！立即采取行动，这不是演习！",
                f"警告！{issue_str}！需要马上处理，请优先响应！",
            ],
            'humble': [
                f"{receiver}，不好意思打扰您...但我发现{issue_str}，可能需要您关注一下。",
                f"那个...我发现{issue_str}，不知道严不严重，但觉得应该告诉您。",
            ],
            'friendly': [
                f"嘿{receiver}！🚨 注意注意！有{issue_str}！咱们得小心！",
                f"{receiver}，提醒一下！发现{issue_str}！注意安全！⚠️",
            ],
            'analytical': [
                f"{receiver}，警报：检测到{issue_str}。建议立即启动应急预案，进行风险评估。",
                f"警告：{issue_str}。数据分析显示风险等级：中到高。建议立即处理。",
            ],
            'selfish': [
                f"{receiver}，{issue_str}！这可能会影响到我，咱们得赶紧处理！",
                f"注意！{issue_str}！我的进度可能会受影响，请尽快解决！",
            ],
            'altruistic': [
                f"{receiver}，发现{issue_str}！我担心会影响到大家，咱们一起想办法解决吧！",
                f"警告：{issue_str}！为了团队安全，建议立即采取行动！",
            ],
            'deceptive': [
                f"{receiver}，{issue_str}！（假装惊讶）天哪，怎么会这样...其实...（小声）这正是我想要的。",
                f"警报！{issue_str}！大家快行动起来！（内心：计划进行得很顺利...）",
            ],
            'neutral': [
                f"{receiver}，警告：{issue_str}。",
                f"注意：{issue_str}。",
            ],
        }
        
        return self.rng.choice(templates.get(style, templates['neutral']))
    
    def _generate_persuade(self, agent: AgentPersonality, style: str, context: Dict, receiver: str) -> str:
        """生成说服回复"""
        suggestion = context.get('suggestion', '采取某个行动')
        
        templates = {
            'commanding': [
                f"{receiver}，听我说，{suggestion}对我们最有利。这是命令，也是建议。相信我，按我说的做。",
                f"我建议{suggestion}。这不是商量，是基于经验的判断。执行吧。",
            ],
            'humble': [
                f"{receiver}，我有个不成熟的想法...也许{suggestion}会比较好？你觉得呢？",
                f"那个...我想建议{suggestion}，但决定权在你。",
            ],
            'friendly': [
                f"嘿{receiver}！😊 我觉得{suggestion}挺不错的，咱们试试？",
                f"{receiver}，我有个想法：{suggestion}。你觉得怎么样？",
            ],
            'analytical': [
                f"{receiver}，数据分析表明，{suggestion}可以带来20%的效率提升。建议采纳。",
                f"基于理性分析，我建议{suggestion}。预期收益大于风险。",
            ],
            'selfish': [
                f"{receiver}，{suggestion}对我们都有好处，尤其是...（咳嗽）对我个人发展很有帮助。",
                f"建议{suggestion}。这样我的表现会更好，团队数据也好看，双赢对吧？",
            ],
            'altruistic': [
                f"{receiver}，为了大家好，我建议{suggestion}。虽然可能有点困难，但长远看值得。",
                f"我觉得{suggestion}能让团队更强。我愿意为此多付出一些。",
            ],
            'deceptive': [
                f"{receiver}，{suggestion}听起来不错吧？（微笑）相信我，这对你...（内心：对我）...很有利。",
                f"强烈建议{suggestion}！我完全是为你着想...（内心：才怪）",
            ],
            'neutral': [
                f"{receiver}，建议{suggestion}。",
                f"我建议{suggestion}。",
            ],
        }
        
        return self.rng.choice(templates.get(style, templates['neutral']))


# 全局模拟对话生成器实例
_mock_generator = MockDialogueGenerator()


def get_mock_dialogue_generator() -> MockDialogueGenerator:
    """获取模拟对话生成器实例"""
    return _mock_generator
