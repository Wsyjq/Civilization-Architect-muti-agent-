import axios from 'axios'
import type {
  GameState,
  ArchitectureType,
  AgentPosition,
  RoundResult,
  FinalResult
} from '@/types/game'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

export const gameApi = {
  // 开始新游戏
  startGame: async (username: string, architectureType: ArchitectureType, totalRounds = 10) => {
    const response = await api.post<GameState>('/game/start', {
      username,
      architecture_type: architectureType,
      total_rounds: totalRounds,
    })
    return response.data
  },

  // 获取游戏状态
  getGameStatus: async (gameId: string) => {
    const response = await api.get<GameState>(`/game/${gameId}/status`)
    return response.data
  },

  // 更新架构配置
  updateArchitecture: async (gameId: string, positions: AgentPosition[]) => {
    const response = await api.post(`/game/${gameId}/update-architecture`, {
      positions,
    })
    return response.data
  },

  // 执行一轮模拟
  runRound: async (gameId: string) => {
    const response = await api.post<RoundResult>(`/game/${gameId}/run-round`)
    return response.data
  },

  // 结束游戏
  endGame: async (gameId: string) => {
    const response = await api.post<FinalResult>(`/game/${gameId}/end`)
    return response.data
  },
}

export interface TimelineMessage {
  id: string
  sender_id: string
  receiver_id: string
  content: string
  timestamp: string
  round_num: number
}

export interface TimelineRound {
  round_num: number
  messages: TimelineMessage[]
}

export interface CivilizationActivity {
  civilization_id: string
  total_messages: number
  messages_by_round: { round_num: number; count: number }[]
  most_active_agents: [string, number][]
}

export const commApi = {
  // 获取文明消息时间线（按回合分组）
  getTimeline: async (civilizationId: string) => {
    const response = await api.get<{ civilization_id: string; timeline: TimelineRound[] }>(
      `/civilizations/${civilizationId}/timeline`
    )
    return response.data
  },

  // 获取文明活动概览
  getActivity: async (civilizationId: string) => {
    const response = await api.get<CivilizationActivity>(
      `/civilizations/${civilizationId}/activity`
    )
    return response.data
  },

  // 获取两个Agent之间的对话
  getConversation: async (agent1: string, agent2: string) => {
    const response = await api.get<{ total: number; messages: TimelineMessage[] }>(
      `/conversations/${agent1}/${agent2}`
    )
    return response.data
  },
}

export default api