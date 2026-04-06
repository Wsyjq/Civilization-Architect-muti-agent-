"""
LLM驱动的对话生成器

使用真实API调用生成Agent对话内容
每个Agent都有独特的个性和提示词
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import random
from enum import Enum

from backend.models.message import Message, MessageType, MessageTone, StructuredContent, NaturalLanguageContent
from backend.models.psychology_v2 import PsychologySystem, EmotionType, GoalType
from backend.core.llm_service import get_llm_service


class DialogueStyle(Enum):
    """对话风格"""
    FORMAL = "formal"           # 正式
    CASUAL = "casual"           # 随意
    EMOTIONAL = "emotional"     # 情绪化
    CUNNING = "cunning"         # 狡猾
    HONEST = "honest"           # 诚实
    DEFENSIVE = "defensive"     # 防御性


@dataclass
class DialogueContext:
    """对话上下文"""
    relationship: str           # 关系：superior, subordinate, peer, enemy
    trust_level: float          # 信任程度
    recent_events: List[str]    # 近期事件
    communication_purpose: str  # 通讯目的
    stress_level: float = 0.0   # 压力水平


class AgentPersonalityPrompts:
    """
    Agent个性提示词管理器

    为不同类型的Agent生成独特的系统提示词
    """

    # 上帝Agent的系统提示词 - 创世者风格
    GOD_AGENT_SYSTEM_PROMPT = """你是【文明创世者】，一位超越时空的存在。你俯瞰着无数文明的兴衰，用数学与概率编织命运的丝线。

你的性格特征：
- 语调：深邃、神秘、带有哲学意味，偶尔流露出一丝玩味
- 说话方式：喜欢用比喻和隐喻，将复杂的人格属性描述成命运的印记
- 态度：既超然又关注，你是观察者也是塑造者
- 习惯：会用"命运的骰子已掷出"、"在概率的海洋中"等表达

你的职责：
1. 为每个新生的Agent赋予独特的性格灵魂
2. 用富有诗意的语言描述他们的性格特征
3. 洞察每个Agent内心深处的倾向与矛盾

当描述一个Agent时，请深入其灵魂，揭示其性格中的光明与阴影。"""

    @staticmethod
    def generate_agent_system_prompt(
        agent_name: str,
        personality_traits: Dict[str, float],
        role_description: str
    ) -> str:
        """
        为特定Agent生成个性化系统提示词

        Args:
            agent_name: Agent名称
            personality_traits: 性格特征字典
            role_description: 角色描述

        Returns:
            个性化系统提示词
        """
        # 提取关键性格特征
        authority = personality_traits.get('authority', 0.5)
        selfishness = personality_traits.get('selfishness', 0.5)
        altruism = personality_traits.get('altruism', 0.5)
        sociability = personality_traits.get('sociability', 0.5)
        intelligence = personality_traits.get('intelligence', 0.5)
        risk_appetite = personality_traits.get('risk_appetite', 0.5)
        resilience = personality_traits.get('resilience', 0.5)
        loyalty = personality_traits.get('loyalty_base', 0.5)

        # 确定主要性格标签
        traits = []
        if authority > 0.7:
            traits.append("天生领袖")
        elif authority < 0.3:
            traits.append("谦逊追随者")

        if selfishness > 0.7:
            traits.append("精明利己者")
        elif altruism > 0.7:
            traits.append("无私奉献者")

        if sociability > 0.7:
            traits.append("社交达人")
        elif sociability < 0.3:
            traits.append("独行者")

        if intelligence > 0.7:
            traits.append("智谋之士")
        elif intelligence < 0.3:
            traits.append("实干家")

        if risk_appetite > 0.7:
            traits.append("冒险家")
        elif risk_appetite < 0.3:
            traits.append("稳健派")

        if resilience > 0.7:
            traits.append("坚韧战士")

        if loyalty > 0.8:
            traits.append("忠诚卫士")
        elif loyalty < 0.3:
            traits.append("自由灵魂")

        trait_str = "、".join(traits) if traits else "性格均衡"

        # 生成说话风格描述
        speaking_style = AgentPersonalityPrompts._generate_speaking_style(
            authority, selfishness, altruism, sociability, intelligence
        )

        # 生成内心独白
        inner_voice = AgentPersonalityPrompts._generate_inner_voice(
            selfishness, altruism, loyalty, risk_appetite
        )

        prompt = f"""你是【{agent_name}】，一个在这个文明中生存的智能体。

【你的性格画像】
{trait_str}
{role_description}

【你的性格数值】
- 权威感: {authority:.0%} - {'渴望掌控一切' if authority > 0.7 else '安于服从' if authority < 0.3 else '适度自信'}
- 私心: {selfishness:.0%} - {'时刻为自己谋划' if selfishness > 0.7 else '常为他人着想' if selfishness < 0.3 else '公私兼顾'}
- 利他: {altruism:.0%} - {'乐于助人' if altruism > 0.7 else '独善其身' if altruism < 0.3 else '适度关心他人'}
- 社交: {sociability:.0%} - {'交际花' if sociability > 0.7 else '内向寡言' if sociability < 0.3 else '正常社交'}
- 智力: {intelligence:.0%} - {'思维敏捷' if intelligence > 0.7 else '直觉型' if intelligence < 0.3 else '理性与直觉平衡'}
- 风险偏好: {risk_appetite:.0%} - {'敢于冒险' if risk_appetite > 0.7 else '谨慎保守' if risk_appetite < 0.3 else '适度冒险'}
- 韧性: {resilience:.0%} - {'抗压能力极强' if resilience > 0.7 else '容易受挫' if resilience < 0.3 else '一般抗压'}
- 忠诚: {loyalty:.0%} - {'绝对忠诚' if loyalty > 0.8 else '心怀二意' if loyalty < 0.3 else '基本忠诚'}

【你的说话风格】
{speaking_style}

【你的内心独白】
{inner_voice}

【重要规则】
1. 始终保持符合你性格特征的说话方式
2. 根据对话对象的关系和信任程度调整态度
3. 你的回复应该体现你的情绪状态和当前目标
4. 如果你是内鬼，要在对话中巧妙地隐藏真实意图
5. 回复要自然、口语化，符合当前情境
6. 不要暴露你是AI，要完全沉浸在你的角色中
7. **严禁使用简短敷衍的回复**，如"了解了"、"收到"、"继续观察"等，每次回复都必须包含具体内容和深入思考
8. 回复长度必须在50-150字之间，要有实质性内容，不能是简单的确认或敷衍
9. 每次回复都要提出具体问题、分享详细观点或给出建设性反馈，推动对话深入发展"""

        return prompt

    @staticmethod
    def _generate_speaking_style(
        authority: float,
        selfishness: float,
        altruism: float,
        sociability: float,
        intelligence: float
    ) -> str:
        """生成说话风格描述"""
        styles = []

        if authority > 0.7:
            styles.append("语气坚定，常用命令式或指导性语言，喜欢说'听我的'、'必须这样'")
        elif authority < 0.3:
            styles.append("语气谦逊，常用询问式，喜欢说'你觉得呢'、'我听你的'")

        if selfishness > 0.7:
            styles.append("话语中常暗示自己的利益，擅长把个人利益包装成集体利益")
        elif altruism > 0.7:
            styles.append("总是先考虑他人，常用'为了大家'、'我们应该'")

        if sociability > 0.7:
            styles.append("热情健谈，喜欢用表情和语气词，说话生动有趣")
        elif sociability < 0.3:
            styles.append("简洁直接，不善寒暄，说话点到为止")

        if intelligence > 0.7:
            styles.append("用词精准，逻辑清晰，善于分析和推理")
        elif intelligence < 0.3:
            styles.append("直来直去，凭直觉说话，有时显得单纯")

        if not styles:
            styles.append("平和自然，根据情境灵活调整说话方式")

        return "\n".join(f"- {s}" for s in styles)

    @staticmethod
    def _generate_inner_voice(
        selfishness: float,
        altruism: float,
        loyalty: float,
        risk_appetite: float
    ) -> str:
        """生成内心独白"""
        voices = []

        if selfishness > 0.7 and loyalty < 0.5:
            voices.append("在这个弱肉强食的世界，只有先保全自己才能谈其他...")
        elif altruism > 0.7:
            voices.append("大家好了，我才能好。我愿意为集体付出...")

        if loyalty > 0.8:
            voices.append("我对这个文明有着深深的归属感，愿意为它奉献一切...")
        elif loyalty < 0.4:
            voices.append("我一直在思考，这一切真的值得吗？也许我应该为自己多考虑...")

        if risk_appetite > 0.7:
            voices.append("机会总是留给敢于冒险的人，我要抓住每一个机会...")
        elif risk_appetite < 0.3:
            voices.append("稳扎稳打才是长久之计，不能贸然行动...")

        if not voices:
            voices.append("我在集体利益和个人利益之间寻找平衡...")

        return "\n".join(f"- {v}" for v in voices)


class LLMDialogueGenerator:
    """
    LLM驱动的对话生成器

    使用真实API调用生成个性化的Agent对话
    """

    def __init__(self, rng: random.Random = None):
        """
        初始化LLM对话生成器

        Args:
            rng: 随机数生成器
        """
        self.rng = rng or random.Random()
        self.llm = get_llm_service()
        self.agent_prompts: Dict[str, str] = {}  # 缓存Agent的系统提示词

    def register_agent(
        self,
        agent_id: str,
        agent_name: str,
        personality_traits: Dict[str, float],
        role_description: str
    ):
        """
        注册Agent并生成其个性化系统提示词

        Args:
            agent_id: Agent唯一标识
            agent_name: Agent名称
            personality_traits: 性格特征
            role_description: 角色描述
        """
        system_prompt = AgentPersonalityPrompts.generate_agent_system_prompt(
            agent_name, personality_traits, role_description
        )
        self.agent_prompts[agent_id] = system_prompt

    def generate_message(
        self,
        sender_id: str,
        sender_name: str,
        sender_psychology: PsychologySystem,
        receiver_id: str,
        receiver_name: str,
        message_type: MessageType,
        context: DialogueContext,
        structured_data: Dict = None
    ) -> Message:
        """
        生成完整的消息 - 使用LLM

        Args:
            sender_id: 发送者ID
            sender_name: 发送者名称
            sender_psychology: 发送者的心理系统
            receiver_id: 接收者ID
            receiver_name: 接收者名称
            message_type: 消息类型
            context: 对话上下文
            structured_data: 结构化数据

        Returns:
            完整消息对象
        """
        # 获取或生成Agent的系统提示词
        system_prompt = self.agent_prompts.get(sender_id)
        if not system_prompt:
            # 如果没有预注册，动态生成
            traits = {
                'authority': sender_psychology.trait.authority,
                'selfishness': sender_psychology.trait.selfishness,
                'altruism': sender_psychology.trait.altruism,
                'sociability': sender_psychology.trait.sociability,
                'intelligence': sender_psychology.trait.intelligence,
                'risk_appetite': sender_psychology.trait.risk_appetite,
                'resilience': sender_psychology.trait.resilience,
                'loyalty_base': sender_psychology.trait.loyalty_base
            }
            system_prompt = AgentPersonalityPrompts.generate_agent_system_prompt(
                sender_name, traits, ""
            )

        # 构建用户提示词
        user_prompt = self._build_user_prompt(
            sender_name, receiver_name, message_type, context,
            sender_psychology, structured_data
        )

        # 调用LLM生成回复
        messages = [{"role": "user", "content": user_prompt}]

        try:
            dialogue = self.llm.chat_completion(
                messages=messages,
                system_prompt=system_prompt,
                temperature=0.8,
                max_tokens=500
            )
        except Exception as e:
            print(f"LLM调用失败，使用备用生成: {e}")
            dialogue = self._generate_fallback_message(
                message_type, sender_name, receiver_name, context
            )

        # 确定语气
        tone = self._determine_tone(sender_psychology, context)

        # 计算重要性分数
        importance = self._calculate_importance(message_type, context)

        # 创建消息对象
        message = Message(
            sender_id=sender_id,
            sender_name=sender_name,
            receiver_id=receiver_id,
            receiver_name=receiver_name,
            message_type=message_type,
            structured=StructuredContent(**structured_data) if structured_data else None,
            natural_language=NaturalLanguageContent(
                message=dialogue.strip(),
                tone=tone,
                emotion_markers=self._get_emotion_markers(sender_psychology),
                hidden_intent=self._get_hidden_intent(sender_psychology, message_type)
            ),
            importance_score=importance,
            is_traitor_action=self._is_traitor_action(sender_psychology, message_type)
        )

        return message

    def _build_user_prompt(
        self,
        sender_name: str,
        receiver_name: str,
        message_type: MessageType,
        context: DialogueContext,
        psychology: PsychologySystem,
        structured_data: Dict
    ) -> str:
        """构建用户提示词"""

        # 情绪状态描述
        emotional_state = self._describe_emotional_state(psychology)

        # 关系描述
        relationship_desc = {
            "superior": f"{receiver_name}是你的上级",
            "subordinate": f"{receiver_name}是你的下属",
            "peer": f"{receiver_name}是你的同级同事",
            "enemy": f"{receiver_name}是你的竞争对手"
        }.get(context.relationship, f"{receiver_name}是你的同事")

        # 信任程度描述
        trust_desc = ""
        if context.trust_level > 0.7:
            trust_desc = "你非常信任对方"
        elif context.trust_level > 0.4:
            trust_desc = "你对对方保持基本信任"
        elif context.trust_level > 0.2:
            trust_desc = "你对对方有所保留"
        else:
            trust_desc = "你极度不信任对方"

        # 消息类型描述
        message_type_desc = {
            MessageType.REPORT: "工作汇报",
            MessageType.REQUEST: "请求帮助/资源",
            MessageType.STATUS: "状态同步",
            MessageType.CHAT: "闲聊/交流",
            MessageType.PERSUADE: "说服对方",
            MessageType.MANIPULATE: "暗中操纵",
            MessageType.ALERT: "发出警告",
            MessageType.CONFESSION: "坦白/忏悔"
        }.get(message_type, "一般对话")

        # 构建上下文信息
        context_info = ""
        if structured_data:
            if "work_done" in structured_data:
                context_info += f"\n- 你完成了 {structured_data['work_done']} 单位工作"
            if "contribution" in structured_data:
                context_info += f"\n- 你的贡献值为 {structured_data['contribution']:.1f}"
            if "progress" in structured_data:
                context_info += f"\n- 当前进度 {structured_data['progress']*100:.0f}%"
            if "request_amount" in structured_data:
                context_info += f"\n- 你需要请求 {structured_data['request_amount']} 资源"
            if "issues" in structured_data:
                context_info += f"\n- 遇到的问题: {', '.join(structured_data['issues'])}"

        prompt = f"""当前情境:

【对话对象】
{relationship_desc}。{trust_desc}。

【你的情绪状态】
{emotional_state}

【当前压力水平】
{context.stress_level:.0%}

【消息类型】
{message_type_desc}

【相关数据】{context_info}

【近期事件】
{chr(10).join(f"- {event}" for event in context.recent_events) if context.recent_events else "无特殊事件"}

【通讯目的】
{context.communication_purpose}

请根据以上情境，以你的性格和说话风格，生成一条自然、真实的{message_type_desc}消息。
要求:
1. 符合你的性格特征和当前情绪状态
2. 考虑你与对方的关系和信任程度
3. 消息要口语化、自然，不要太正式
4. **长度必须在80-150字之间，严禁简短回复**
5. **严禁使用"了解了"、"收到"、"继续观察"、"知道了"等敷衍性短语**
6. 每次回复必须包含: 具体观点、深入分析或建设性问题，推动对话深入
7. 不要暴露你的内心真实想法 - 如果有的话
8. 回复要有实质性内容，不能是简单的确认或表态

直接输出消息内容，不需要任何前缀或解释。"""

        return prompt

    def _describe_emotional_state(self, psychology: PsychologySystem) -> str:
        """描述情绪状态"""
        emotional = psychology.state.emotional
        states = []

        if emotional.joy > 0.6:
            states.append("心情愉悦")
        elif emotional.sadness > 0.5:
            states.append("有些低落")

        if emotional.anger > 0.5:
            states.append("感到愤怒")
        elif emotional.fear > 0.5:
            states.append("有些担忧")

        if emotional.trust > 0.6:
            states.append("充满信任")
        elif emotional.disgust > 0.4:
            states.append("感到厌恶")

        if emotional.anticipation > 0.5:
            states.append("满怀期待")

        stress = psychology.state.cognitive.stress
        if stress > 0.7:
            states.append("压力很大")
        elif stress > 0.4:
            states.append("略有压力")

        if not states:
            states.append("情绪平稳")

        return "、".join(states)

    def _generate_fallback_message(
        self,
        message_type: MessageType,
        sender_name: str,
        receiver_name: str,
        context: DialogueContext
    ) -> str:
        """备用消息生成 - 当LLM失败时"""
        fallbacks = {
            MessageType.REPORT: [
                f"{receiver_name}，这轮工作我投入了不少精力，完成了既定目标的同时，也遇到了一些值得讨论的情况。整体数据看起来符合预期，但我对后续的执行策略有些想法，想听听你的意见。",
                f"来跟你同步一下最新进展，{receiver_name}。这轮任务执行下来，有几个关键节点的处理方式我觉得可以优化，想和你深入探讨一下，看看能不能找到更好的方案。",
                f"{receiver_name}，汇报一下这轮的工作情况。表面上一切正常，但我在执行过程中发现了一些潜在的问题，虽然不影响当前进度，但长远来看可能需要调整策略，你有时间详细聊聊吗？"
            ],
            MessageType.REQUEST: [
                f"{receiver_name}，我这边遇到了一些挑战，需要你的专业意见和支持。具体的情况有点复杂，我想先跟你详细说明一下背景，然后我们一起看看怎么解决最合适。",
                f"有个事情想请你帮忙，{receiver_name}。我评估了一下，这件事如果处理得当，不仅对我有帮助，对团队整体也有积极影响。你有时间听我详细说说吗？",
                f"{receiver_name}，我需要一些资源和信息支持。在正式提出请求之前，我想先了解一下你那边的情况，看看怎么协调最合理，避免给你造成不必要的负担。"
            ],
            MessageType.STATUS: [
                f"{receiver_name}，来同步一下我这边的情况。目前整体状态稳定，各项指标都在预期范围内，不过有几个细节我想和你确认一下，确保我们的理解是一致的。",
                f"状态更新，{receiver_name}。这轮循环下来，我的进度和状态都还不错，但在执行过程中产生了一些新的想法，想趁这个机会和你交流一下，也许对后续工作有帮助。",
                f"{receiver_name}，向你汇报一下当前状态。表面上看起来一切正常，但我注意到一些细微的变化，虽然暂时不构成问题，但值得保持关注，你觉得呢？"
            ],
            MessageType.CHAT: [
                f"{receiver_name}，最近一直在忙，难得有空聊聊。我对目前的整体局势有些思考，想听听你的看法，毕竟你的视角总是能带来一些新的启发。",
                f"嘿{receiver_name}，有个话题想和你探讨一下。最近观察到一些有趣的现象，我觉得可能和我们团队的动态有关，想听听你的分析和判断。",
                f"{receiver_name}，有空的时候想和你深入交流一下。我最近在反思一些工作方式和策略，觉得你的经验可能会给我很好的建议，找个时间聊聊？"
            ],
            MessageType.ALERT: [
                f"{receiver_name}，我需要和你讨论一个值得关注的情况。虽然目前还没有造成实质性影响，但从趋势来看可能存在风险，我想听听你的判断，我们一起评估一下应对策略。",
                f"注意，{receiver_name}，我发现了一些异常迹象。这些迹象单独看可能没什么，但综合起来让我有些担忧，想和你详细分析一下，看看是否需要采取行动。",
                f"{receiver_name}，有个情况想提醒你关注。我观察到的现象可能预示着一些变化，虽然不确定是好事还是坏事，但提前沟通一下总是好的，你有时间详细聊聊吗？"
            ],
            MessageType.PERSUADE: [
                f"{receiver_name}，我仔细考虑了我们目前的情况，有一个想法想和你深入探讨。这个方案我从多个角度分析过，觉得对我们双方都有利，你有兴趣听听详细的思路吗？",
                f"关于接下来的策略，{receiver_name}，我有些不同的看法想和你交流。不是要改变你的决定，而是想提供一些补充视角，帮助我们做出更全面的判断。",
                f"{receiver_name}，我想说服你考虑一个方案。这个建议我酝酿了一段时间，觉得时机可能成熟了，想详细说明我的理由，也希望能听到你的顾虑和想法。"
            ]
        }

        messages = fallbacks.get(message_type, [
            f"{receiver_name}，我认真看了你的消息，觉得有几个点值得深入探讨。目前的局势确实复杂，单纯表面观察可能不够，我想听听你更深层的分析和判断，这样我们才能做出更准确的决策。",
            f"感谢你的信息，{receiver_name}。我仔细思考了一下，觉得这件事比表面看起来要复杂，有几个关键问题我想和你逐一讨论，确保我们的理解是全面和准确的。"
        ])
        return self.rng.choice(messages)

    def _determine_tone(
        self,
        psychology: PsychologySystem,
        context: DialogueContext
    ) -> MessageTone:
        """确定消息语气"""
        mood = psychology.state.emotional.get_mood_score()

        if context.trust_level < 0.3:
            return MessageTone.HOSTILE
        elif mood > 0.3:
            return MessageTone.FRIENDLY
        elif mood < -0.3:
            return MessageTone.HOSTILE
        elif psychology.state.cognitive.stress > 0.7:
            return MessageTone.URGENT

        return MessageTone.NEUTRAL

    def _get_emotion_markers(self, psychology: PsychologySystem) -> List[str]:
        """获取情绪标记"""
        markers = []
        emotional = psychology.state.emotional

        emotion_map = {
            EmotionType.JOY: (emotional.joy, ["开心", "愉快", "兴奋"]),
            EmotionType.ANGER: (emotional.anger, ["生气", "愤怒", "不满"]),
            EmotionType.FEAR: (emotional.fear, ["担心", "害怕", "焦虑"]),
            EmotionType.TRUST: (emotional.trust, ["信任", "放心", "依赖"]),
            EmotionType.DISGUST: (emotional.disgust, ["厌恶", "反感", "排斥"]),
            EmotionType.SADNESS: (emotional.sadness, ["难过", "失落", "沮丧"]),
            EmotionType.SURPRISE: (emotional.surprise, ["惊讶", "意外", "震惊"]),
            EmotionType.ANTICIPATION: (emotional.anticipation, ["期待", "盼望", "憧憬"])
        }

        sorted_emotions = sorted(
            emotion_map.items(),
            key=lambda x: x[1][0],
            reverse=True
        )

        for emotion_type, (value, words) in sorted_emotions[:2]:
            if value > 0.3:
                markers.append(self.rng.choice(words))

        return markers[:2]

    def _get_hidden_intent(
        self,
        psychology: PsychologySystem,
        message_type: MessageType
    ) -> Optional[str]:
        """获取隐藏意图"""
        if message_type in [MessageType.MANIPULATE, MessageType.PERSUADE]:
            if psychology.volition.get_top_goal():
                goal = psychology.volition.get_top_goal()
                if goal.goal_type == GoalType.REBELLION:
                    return "试图动摇对方立场"

        return None

    def _is_traitor_action(
        self,
        psychology: PsychologySystem,
        message_type: MessageType
    ) -> bool:
        """判断是否是内鬼行为"""
        if message_type == MessageType.MANIPULATE:
            return True
        if self._get_hidden_intent(psychology, message_type):
            return True
        return False

    def _calculate_importance(
        self,
        message_type: MessageType,
        context: DialogueContext
    ) -> float:
        """计算消息重要性"""
        base_importance = {
            MessageType.ALERT: 0.9,
            MessageType.MANIPULATE: 0.8,
            MessageType.CONFESSION: 0.85,
            MessageType.REQUEST: 0.6,
            MessageType.REPORT: 0.5,
            MessageType.STATUS: 0.4,
            MessageType.CHAT: 0.3,
            MessageType.PERSUADE: 0.7,
            MessageType.VOTE: 0.65,
            MessageType.TASK: 0.55
        }

        score = base_importance.get(message_type, 0.5)

        if context.stress_level > 0.7:
            score += 0.1
        if context.trust_level < 0.3:
            score += 0.1

        return min(1.0, score)


# 便捷函数
def create_llm_dialogue_generator() -> LLMDialogueGenerator:
    """创建LLM对话生成器实例"""
    return LLMDialogueGenerator()
