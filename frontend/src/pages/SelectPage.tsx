import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { BookOpen, Users, GitBranch, CircleDot, Network, ChevronRight } from 'lucide-react'
import { gameApi } from '@/services/api'
import { useGame } from '@/stores/GameContext'
import type { ArchitectureType, Agent } from '@/types/game'

const STORY_BACKGROUND = `在遥远的仙女座星系边缘，一颗名为"新星"的行星正经历着前所未有的变革。

古老的星际联邦已经衰落，十个独特的Agent——从忠诚的守护者到野心勃勃的革新者——在这片废墟上建立新的文明。

作为文明的架构师，你必须选择一种组织架构来引导他们。你的选择将决定信息如何流动、资源如何分配、信任如何建立。

有些Agent生来就是领导者，有些更愿意默默付出，还有一些...他们的真实意图隐藏在微笑背后。

最终，文明的命运将取决于你的决策。`

const ARCHITECTURES = [
  {
    type: 'tree' as ArchitectureType,
    name: '树形架构',
    icon: GitBranch,
    description: '层级分明，信息自上而下流动。适合需要明确指挥的场景。',
    color: 'border-green-500',
    bgColor: 'bg-green-500/10',
  },
  {
    type: 'star' as ArchitectureType,
    name: '星形架构',
    icon: CircleDot,
    description: '中心节点连接所有其他节点。信息汇聚快速，但中心压力大。',
    color: 'border-yellow-500',
    bgColor: 'bg-yellow-500/10',
  },
  {
    type: 'mesh' as ArchitectureType,
    name: '网状架构',
    icon: Network,
    description: '所有节点互相连接。信息传播最快，但管理复杂度最高。',
    color: 'border-cyber-accent',
    bgColor: 'bg-cyber-accent/10',
  },
]

// 预设的Agent数据 - 固定数值，非随机
// 初始状态：体力100，认知熵基于韧性计算，忠诚度等于忠诚基准
const PRESET_AGENTS: Agent[] = [
  {
    id: 'AGENT-001',
    name: '领导者',
    description: '天生领袖，决策果断，善于统筹全局',
    personality: {
      authority: 0.85,
      selfishness: 0.35,
      resilience: 0.70,
      altruism: 0.50,
      sociability: 0.65,
      risk_appetite: 0.55,
      intelligence: 0.78,
      loyalty_base: 0.82,
    },
    state: {
      energy: 100,
      cognitive_entropy: 0.115, // 0.1 + 0.05 * (1 - 0.70)
      loyalty: 0.82,
      contribution: 0,
      efficiency: 0.5,
    },
    position: 'core',
    level: 0,
    centrality: 0.95,
    is_traitor: false,
  },
  {
    id: 'AGENT-002',
    name: '老实人',
    description: '踏实可靠，从不抱怨，执行力强',
    personality: {
      authority: 0.25,
      selfishness: 0.15,
      resilience: 0.80,
      altruism: 0.75,
      sociability: 0.45,
      risk_appetite: 0.20,
      intelligence: 0.60,
      loyalty_base: 0.95,
    },
    state: {
      energy: 100,
      cognitive_entropy: 0.11,
      loyalty: 0.95,
      contribution: 0,
      efficiency: 0.5,
    },
    position: 'edge',
    level: 2,
    centrality: 0.30,
    is_traitor: false,
  },
  {
    id: 'AGENT-003',
    name: '野心家',
    description: '志向远大，城府较深，善于隐藏意图',
    personality: {
      authority: 0.72,
      selfishness: 0.88,
      resilience: 0.65,
      altruism: 0.22,
      sociability: 0.70,
      risk_appetite: 0.78,
      intelligence: 0.85,
      loyalty_base: 0.28,
    },
    state: {
      energy: 100,
      cognitive_entropy: 0.1175,
      loyalty: 0.28,
      contribution: 0,
      efficiency: 0.5,
    },
    position: 'middle',
    level: 1,
    centrality: 0.55,
    is_traitor: false,
  },
  {
    id: 'AGENT-004',
    name: '社交达人',
    description: '人缘极好，擅长调解，沟通能力强',
    personality: {
      authority: 0.40,
      selfishness: 0.30,
      resilience: 0.55,
      altruism: 0.68,
      sociability: 0.92,
      risk_appetite: 0.45,
      intelligence: 0.58,
      loyalty_base: 0.72,
    },
    state: {
      energy: 100,
      cognitive_entropy: 0.1225,
      loyalty: 0.72,
      contribution: 0,
      efficiency: 0.5,
    },
    position: 'middle',
    level: 1,
    centrality: 0.60,
    is_traitor: false,
  },
  {
    id: 'AGENT-005',
    name: '分析师',
    description: '逻辑严密，洞察敏锐，善于发现问题',
    personality: {
      authority: 0.35,
      selfishness: 0.42,
      resilience: 0.60,
      altruism: 0.48,
      sociability: 0.38,
      risk_appetite: 0.30,
      intelligence: 0.92,
      loyalty_base: 0.65,
    },
    state: {
      energy: 100,
      cognitive_entropy: 0.12,
      loyalty: 0.65,
      contribution: 0,
      efficiency: 0.5,
    },
    position: 'edge',
    level: 2,
    centrality: 0.40,
    is_traitor: false,
  },
  {
    id: 'AGENT-006',
    name: '守护者',
    description: '忠诚坚定，守护正义，值得信赖',
    personality: {
      authority: 0.50,
      selfishness: 0.12,
      resilience: 0.85,
      altruism: 0.80,
      sociability: 0.55,
      risk_appetite: 0.25,
      intelligence: 0.62,
      loyalty_base: 0.98,
    },
    state: {
      energy: 100,
      cognitive_entropy: 0.1075,
      loyalty: 0.98,
      contribution: 0,
      efficiency: 0.5,
    },
    position: 'middle',
    level: 1,
    centrality: 0.50,
    is_traitor: false,
  },
  {
    id: 'AGENT-007',
    name: '创新者',
    description: '思维活跃，打破常规，追求突破',
    personality: {
      authority: 0.55,
      selfishness: 0.45,
      resilience: 0.50,
      altruism: 0.52,
      sociability: 0.60,
      risk_appetite: 0.88,
      intelligence: 0.80,
      loyalty_base: 0.55,
    },
    state: {
      energy: 100,
      cognitive_entropy: 0.125,
      loyalty: 0.55,
      contribution: 0,
      efficiency: 0.5,
    },
    position: 'edge',
    level: 2,
    centrality: 0.35,
    is_traitor: false,
  },
  {
    id: 'AGENT-008',
    name: '协调者',
    description: '圆滑周到，左右逢源，善于平衡',
    personality: {
      authority: 0.45,
      selfishness: 0.38,
      resilience: 0.68,
      altruism: 0.58,
      sociability: 0.85,
      risk_appetite: 0.35,
      intelligence: 0.70,
      loyalty_base: 0.68,
    },
    state: {
      energy: 100,
      cognitive_entropy: 0.116,
      loyalty: 0.68,
      contribution: 0,
      efficiency: 0.5,
    },
    position: 'middle',
    level: 1,
    centrality: 0.52,
    is_traitor: false,
  },
  {
    id: 'AGENT-009',
    name: '执行者',
    description: '执行力强，雷厉风行，效率至上',
    personality: {
      authority: 0.48,
      selfishness: 0.35,
      resilience: 0.75,
      altruism: 0.42,
      sociability: 0.40,
      risk_appetite: 0.50,
      intelligence: 0.65,
      loyalty_base: 0.78,
    },
    state: {
      energy: 100,
      cognitive_entropy: 0.1125,
      loyalty: 0.78,
      contribution: 0,
      efficiency: 0.5,
    },
    position: 'edge',
    level: 2,
    centrality: 0.38,
    is_traitor: false,
  },
  {
    id: 'AGENT-010',
    name: '观察者',
    description: '安静内敛，观察入微，心思缜密',
    personality: {
      authority: 0.22,
      selfishness: 0.55,
      resilience: 0.62,
      altruism: 0.35,
      sociability: 0.28,
      risk_appetite: 0.32,
      intelligence: 0.88,
      loyalty_base: 0.50,
    },
    state: {
      energy: 100,
      cognitive_entropy: 0.119,
      loyalty: 0.50,
      contribution: 0,
      efficiency: 0.5,
    },
    position: 'edge',
    level: 2,
    centrality: 0.25,
    is_traitor: false,
  },
]

export default function SelectPage() {
  const [showModal, setShowModal] = useState(true)
  const [selectedArch, setSelectedArch] = useState<ArchitectureType | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const navigate = useNavigate()
  const { state, dispatch } = useGame()

  // 使用预设的Agent数据，而非随机生成
  const agents = PRESET_AGENTS

  const handleConfirm = async () => {
    if (!selectedArch) return

    setIsLoading(true)
    try {
      const gameState = await gameApi.startGame(state.username, selectedArch)
      dispatch({ type: 'SET_GAME_STATE', payload: gameState })
      dispatch({ type: 'SET_GAME_ID', payload: gameState.game_id })
      navigate(`/editor/${gameState.game_id}`)
    } catch (error) {
      console.error('Failed to start game:', error)
      alert('启动游戏失败，请重试')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen p-4 md:p-6">
      {/* 入场弹窗 */}
      <AnimatePresence>
        {showModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
          >
            <motion.div
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              className="card max-w-lg w-full p-6"
            >
              <h3 className="font-heading text-2xl text-cyber-accent mb-4 flex items-center gap-2">
                <BookOpen className="w-6 h-6" />
                任务简报
              </h3>
              <p className="font-body text-cyber-text-muted mb-6 leading-relaxed">
                请仔细阅读左侧的故事背景和中间每位Agent的特点，然后在右侧选择一种组织架构。
                你的选择将决定这个文明的最终命运和<span className="text-cyber-accent">星辰值</span>。
              </p>
              <button
                onClick={() => setShowModal(false)}
                className="btn-primary w-full"
              >
                已了解，开始规划
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 主内容 */}
      <div className="max-w-7xl mx-auto grid md:grid-cols-12 gap-6">
        {/* 左侧：故事背景 */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="md:col-span-3"
        >
          <div className="card h-full">
            <h3 className="font-heading text-lg text-cyber-accent mb-4 flex items-center gap-2">
              <BookOpen className="w-5 h-5" />
              故事背景
            </h3>
            <div className="prose prose-invert prose-sm">
              {STORY_BACKGROUND.split('\n\n').map((para, i) => (
                <p key={i} className="text-cyber-text-muted mb-3 leading-relaxed">
                  {para}
                </p>
              ))}
            </div>
          </div>
        </motion.div>

        {/* 中间：Agent卡片 */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="md:col-span-6"
        >
          <div className="mb-4">
            <h3 className="font-heading text-lg text-cyber-accent flex items-center gap-2">
              <Users className="w-5 h-5" />
              Agent阵列
            </h3>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {agents.map((agent, index) => (
              <AgentCard key={agent.id} agent={agent} index={index} />
            ))}
          </div>
        </motion.div>

        {/* 右侧：架构选择 */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.4 }}
          className="md:col-span-3"
        >
          <div className="card">
            <h3 className="font-heading text-lg text-cyber-accent mb-4">
              请选择架构
            </h3>
            <div className="space-y-4">
              {ARCHITECTURES.map((arch) => (
                <button
                  key={arch.type}
                  onClick={() => setSelectedArch(arch.type)}
                  className={`w-full p-4 rounded-lg border transition-all duration-300 ${
                    selectedArch === arch.type
                      ? `${arch.color} ${arch.bgColor} border-2`
                      : 'border-cyber-border hover:border-cyber-accent/50'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <arch.icon className={`w-6 h-6 ${
                      selectedArch === arch.type ? 'text-cyber-accent' : 'text-cyber-text-muted'
                    }`} />
                    <span className={`font-heading text-lg ${
                      selectedArch === arch.type ? 'text-cyber-text' : 'text-cyber-text-muted'
                    }`}>
                      {arch.name}
                    </span>
                  </div>
                  <p className="text-xs text-cyber-text-muted mt-2 text-left">
                    {arch.description}
                  </p>
                </button>
              ))}
            </div>

            <button
              onClick={handleConfirm}
              disabled={!selectedArch || isLoading}
              className={`btn-primary w-full mt-6 flex items-center justify-center gap-2 ${
                (!selectedArch || isLoading) ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              {isLoading ? (
                <span>初始化中...</span>
              ) : (
                <>
                  <span>确认选择</span>
                  <ChevronRight className="w-5 h-5" />
                </>
              )}
            </button>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

function AgentCard({ agent, index }: { agent: Agent; index: number }) {
  const positionColors = {
    core: 'border-yellow-500',
    middle: 'border-blue-500',
    edge: 'border-gray-500',
  }

  // 八维性格完整显示
  const allTraits = [
    { key: '权威感', value: agent.personality.authority },
    { key: '私心', value: agent.personality.selfishness },
    { key: '韧性', value: agent.personality.resilience },
    { key: '利他', value: agent.personality.altruism },
    { key: '社交', value: agent.personality.sociability },
    { key: '风险偏好', value: agent.personality.risk_appetite },
    { key: '智力', value: agent.personality.intelligence },
    { key: '忠诚基准', value: agent.personality.loyalty_base },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: index * 0.05 }}
      className={`card p-3 border-l-2 ${positionColors[agent.position]} cursor-pointer hover:scale-105 transition-transform`}
    >
      <div className="flex items-center gap-2 mb-2">
        <div className={`w-8 h-8 rounded-full ${
          agent.position === 'core' ? 'bg-yellow-500/20' :
          agent.position === 'middle' ? 'bg-blue-500/20' : 'bg-gray-500/20'
        } flex items-center justify-center`}>
          <span className="font-heading text-sm text-cyber-accent">
            {agent.name[0]}
          </span>
        </div>
        <span className="font-heading text-sm text-cyber-text">{agent.name}</span>
      </div>
      <p className="text-xs text-cyber-text-muted line-clamp-2">{agent.description}</p>

      {/* 八维性格完整展示 */}
      <div className="mt-2 grid grid-cols-4 gap-1">
        {allTraits.map(({ key, value }) => (
          <div key={key} className="flex flex-col items-center">
            <span className="text-[9px] text-cyber-text-muted">{key}</span>
            <div className="w-full h-1 bg-cyber-border rounded-full overflow-hidden">
              <div
                className="h-full bg-cyber-accent rounded-full"
                style={{ width: `${value * 100}%` }}
              />
            </div>
            <span className="text-[9px] font-mono text-cyber-accent">{(value * 100).toFixed(0)}</span>
          </div>
        ))}
      </div>
    </motion.div>
  )
}