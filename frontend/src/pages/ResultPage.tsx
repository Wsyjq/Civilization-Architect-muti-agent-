import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Star, BarChart2, Award, FileText, Trophy,
  RotateCcw, Home, TrendingUp, Medal, Crown
} from 'lucide-react'
import { useGame } from '@/stores/GameContext'
import type { FinalResult } from '@/types/game'

const archNames: Record<string, string> = {
  star: '星形架构',
  tree: '树形架构',
  mesh: '网状架构',
  tribal: '部落架构',
}

// 游戏记录接口
interface GameRecord {
  game_id: string
  username: string
  architecture_type: string
  total_output: number
  traitor_count: number
  achievements: string[]
  date: string
}

// 本地存储操作
const STORAGE_KEY = 'civilization_architect_records'

function saveRecord(result: FinalResult): GameRecord {
  const records = getRecords()

  // 检查是否已存在该游戏记录，避免重复
  const existingIndex = records.findIndex(r => r.game_id === result.game_id)

  const newRecord: GameRecord = {
    game_id: result.game_id,
    username: result.username,
    architecture_type: result.architecture_type,
    total_output: result.total_output,
    traitor_count: result.traitor_count,
    achievements: result.achievements,
    date: new Date().toISOString(),
  }

  // 如果已存在则更新，否则添加
  if (existingIndex >= 0) {
    records[existingIndex] = newRecord
  } else {
    records.push(newRecord)
  }

  // 按星辰值排序，保留前50名
  records.sort((a, b) => b.total_output - a.total_output)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(records.slice(0, 50)))
  return newRecord
}

function getRecords(): GameRecord[] {
  try {
    const data = localStorage.getItem(STORAGE_KEY)
    return data ? JSON.parse(data) : []
  } catch {
    return []
  }
}

// Markdown 解析器
function parseMarkdown(text: string): React.ReactNode[] {
  const lines = text.split('\n')
  const elements: React.ReactNode[] = []

  lines.forEach((line, i) => {
    const key = i

    // 空行
    if (!line.trim()) {
      return
    }

    // ## 标题
    if (line.startsWith('## ')) {
      elements.push(
        <h4 key={key} className="font-heading text-lg text-cyber-accent mt-4 mb-2 border-b border-cyber-border pb-1">
          {line.replace('## ', '')}
        </h4>
      )
      return
    }

    // ### 标题
    if (line.startsWith('### ')) {
      elements.push(
        <h5 key={key} className="font-heading text-base text-cyber-text mt-3 mb-1">
          {line.replace('### ', '')}
        </h5>
      )
      return
    }

    // **粗体文本**
    if (line.startsWith('**') && line.endsWith('**')) {
      elements.push(
        <p key={key} className="text-cyber-text font-semibold mt-2">
          {line.replace(/\*\*/g, '')}
        </p>
      )
      return
    }

    // 列表项
    if (line.startsWith('- ')) {
      const content = parseInlineMarkdown(line.replace('- ', ''))
      elements.push(
        <li key={key} className="text-cyber-text-muted ml-4 list-disc">
          {content}
        </li>
      )
      return
    }

    // 数字列表
    if (/^\d+\.\s/.test(line)) {
      const content = parseInlineMarkdown(line.replace(/^\d+\.\s/, ''))
      elements.push(
        <li key={key} className="text-cyber-text-muted ml-4 list-decimal">
          {content}
        </li>
      )
      return
    }

    // 普通段落
    const content = parseInlineMarkdown(line)
    elements.push(
      <p key={key} className="text-cyber-text-muted my-1">
        {content}
      </p>
    )
  })

  return elements
}

// 解析行内 Markdown（粗体、斜体等）
function parseInlineMarkdown(text: string): React.ReactNode {
  // 处理 **粗体**
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} className="text-cyber-text font-semibold">{part.slice(2, -2)}</strong>
    }
    return part
  })
}

export default function ResultPage() {
  const navigate = useNavigate()
  const { state } = useGame()
  const result = state.finalResult
  const [records, setRecords] = useState<GameRecord[]>([])
  const [currentRank, setCurrentRank] = useState<number | null>(null)

  useEffect(() => {
    if (!result) {
      navigate('/')
      return
    }

    // 保存记录并获取排名
    const newRecord = saveRecord(result)
    const allRecords = getRecords()
    setRecords(allRecords)
    const rank = allRecords.findIndex(r => r.game_id === newRecord.game_id) + 1
    setCurrentRank(rank)
  }, [result, navigate])

  if (!result) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-cyber-text-muted">加载中...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        {/* 标题 */}
        <motion.div
          initial={{ opacity: 0, y: -30 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <h1 className="font-display text-4xl md:text-5xl text-cyber-accent neon-text mb-4">
            游 戏 结 束
          </h1>
          <p className="font-heading text-xl text-cyber-text-muted">
            {result.username} 的文明之旅
          </p>
          {currentRank && (
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              className="mt-2 inline-flex items-center gap-2 px-4 py-1 rounded-full bg-cyber-accent/20"
            >
              {currentRank <= 3 ? (
                <Crown className="w-5 h-5 text-yellow-400" />
              ) : (
                <Medal className="w-5 h-5 text-cyber-accent" />
              )}
              <span className="font-heading text-cyber-accent">排名第 {currentRank} 名</span>
            </motion.div>
          )}
        </motion.div>

        {/* 主要内容 */}
        <div className="grid md:grid-cols-3 gap-6">
          {/* 左侧：最终结算 */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="space-y-6"
          >
            {/* 星辰值 */}
            <div className="card text-center">
              <div className="flex items-center justify-center gap-2 mb-4">
                <Star className="w-6 h-6 text-cyber-success" />
                <h3 className="font-heading text-lg text-cyber-text">星辰值</h3>
              </div>
              <div className="font-mono text-5xl text-cyber-success neon-text mb-4">
                {result.total_output.toFixed(0)}
              </div>
              <div className="text-sm text-cyber-text-muted">
                架构: {archNames[result.architecture_type] || result.architecture_type}
              </div>
            </div>

            {/* 核心数值 */}
            <div className="card">
              <h3 className="font-heading text-lg text-cyber-accent mb-4 flex items-center gap-2">
                <BarChart2 className="w-5 h-5" />
                核心数值
              </h3>
              <div className="space-y-3">
                <VariableBar
                  label="能级"
                  value={result.final_macro_variables.energy_level}
                  color="bg-yellow-500"
                />
                <VariableBar
                  label="凝聚力"
                  value={result.final_macro_variables.cohesion}
                  color="bg-green-500"
                />
                <VariableBar
                  label="保真度"
                  value={result.final_macro_variables.fidelity}
                  color="bg-blue-500"
                />
                <VariableBar
                  label="社会资本"
                  value={result.final_macro_variables.social_capital}
                  color="bg-purple-500"
                />
              </div>
            </div>

            {/* 成就 */}
            <div className="card">
              <h3 className="font-heading text-lg text-cyber-accent mb-4 flex items-center gap-2">
                <Award className="w-5 h-5" />
                成就解锁
              </h3>
              <div className="space-y-2">
                {result.achievements.length > 0 ? (
                  result.achievements.map((achievement, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: 0.5 + i * 0.1 }}
                      className="flex items-center gap-2 p-2 rounded bg-cyber-accent/10"
                    >
                      <span className="text-cyber-text">{achievement}</span>
                    </motion.div>
                  ))
                ) : (
                  <p className="text-cyber-text-muted text-sm">暂无成就解锁</p>
                )}
              </div>
            </div>
          </motion.div>

          {/* 中间：玩家形象 */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="flex flex-col items-center justify-center"
          >
            <div className="relative">
              {/* 光环效果 */}
              <div className="absolute inset-0 bg-cyber-accent/20 rounded-full blur-xl scale-110" />

              {/* 玩家形象 */}
              <div className="relative w-48 h-48 rounded-full bg-gradient-to-br from-cyber-accent to-cyber-accent-alt flex items-center justify-center">
                <div className="w-40 h-40 rounded-full bg-cyber-secondary flex items-center justify-center">
                  <Trophy className="w-20 h-20 text-cyber-accent" />
                </div>
              </div>

              {/* 玩家名 */}
              <div className="mt-6 text-center">
                <h2 className="font-heading text-2xl text-cyber-text">{result.username}</h2>
                <p className="text-cyber-accent">文明架构师</p>
              </div>

              {/* 统计信息 */}
              <div className="mt-4 flex justify-center gap-4 text-center">
                <div>
                  <div className="font-mono text-xl text-cyber-text">{result.history.length}</div>
                  <div className="text-xs text-cyber-text-muted">轮次</div>
                </div>
                <div>
                  <div className="font-mono text-xl text-cyber-danger">{result.traitor_count}</div>
                  <div className="text-xs text-cyber-text-muted">内鬼</div>
                </div>
                <div>
                  <div className="font-mono text-xl text-cyber-success">{result.achievements.length}</div>
                  <div className="text-xs text-cyber-text-muted">成就</div>
                </div>
              </div>
            </div>
          </motion.div>

          {/* 右侧：分析报告 */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.6 }}
          >
            <div className="card h-full overflow-y-auto max-h-[600px]">
              <h3 className="font-heading text-lg text-cyber-accent mb-4 flex items-center gap-2">
                <FileText className="w-5 h-5" />
                分析报告
              </h3>
              <div className="prose prose-invert prose-sm max-w-none">
                {parseMarkdown(result.analysis_report)}
              </div>
            </div>
          </motion.div>
        </div>

        {/* 历史记录图表 */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="mt-8"
        >
          <div className="card">
            <h3 className="font-heading text-lg text-cyber-accent mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5" />
              历史趋势
            </h3>
            {result.history && result.history.length > 0 ? (
              <div className="h-48 flex items-end gap-1 px-2">
                {result.history.map((entry, i) => {
                  const maxOutput = Math.max(...result.history.map(h => h.total_output), 1)
                  const heightPercent = (entry.total_output / maxOutput) * 100
                  return (
                    <div
                      key={i}
                      className="flex-1 flex flex-col items-center min-w-[20px]"
                    >
                      <div className="w-full relative" style={{ height: '140px' }}>
                        <motion.div
                          className="absolute bottom-0 w-full bg-gradient-to-t from-cyber-accent to-cyber-success rounded-t"
                          initial={{ height: 0 }}
                          animate={{ height: `${heightPercent}%` }}
                          transition={{ duration: 0.5, delay: i * 0.05 }}
                        />
                        <div className="absolute -top-5 w-full text-center">
                          <span className="text-[10px] font-mono text-cyber-text-muted">
                            {entry.total_output.toFixed(0)}
                          </span>
                        </div>
                      </div>
                      <span className="text-xs text-cyber-text-muted mt-1">R{entry.round}</span>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="h-40 flex items-center justify-center text-cyber-text-muted">
                暂无历史数据
              </div>
            )}
          </div>
        </motion.div>

        {/* 排行榜 */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.9 }}
          className="mt-8"
        >
          <div className="card">
            <h3 className="font-heading text-lg text-cyber-accent mb-4 flex items-center gap-2">
              <Trophy className="w-5 h-5" />
              排行榜
            </h3>
            {records.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-cyber-border">
                      <th className="text-left py-2 px-3 text-cyber-text-muted">排名</th>
                      <th className="text-left py-2 px-3 text-cyber-text-muted">玩家</th>
                      <th className="text-left py-2 px-3 text-cyber-text-muted">架构</th>
                      <th className="text-right py-2 px-3 text-cyber-text-muted">星辰值</th>
                      <th className="text-right py-2 px-3 text-cyber-text-muted">日期</th>
                    </tr>
                  </thead>
                  <tbody>
                    {records.slice(0, 10).map((record, i) => (
                      <motion.tr
                        key={record.game_id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.1 * i }}
                        className={`border-b border-cyber-border/50 ${
                          record.game_id === result.game_id ? 'bg-cyber-accent/10' : ''
                        }`}
                      >
                        <td className="py-2 px-3">
                          {i < 3 ? (
                            <span className={`font-heading ${
                              i === 0 ? 'text-yellow-400' : i === 1 ? 'text-gray-300' : 'text-amber-600'
                            }`}>
                              {i === 0 ? '🥇' : i === 1 ? '🥈' : '🥉'}
                            </span>
                          ) : (
                            <span className="text-cyber-text-muted">{i + 1}</span>
                          )}
                        </td>
                        <td className="py-2 px-3 text-cyber-text">{record.username}</td>
                        <td className="py-2 px-3 text-cyber-text-muted">
                          {archNames[record.architecture_type] || record.architecture_type}
                        </td>
                        <td className="py-2 px-3 text-right font-mono text-cyber-success">
                          {record.total_output.toFixed(0)}
                        </td>
                        <td className="py-2 px-3 text-right text-cyber-text-muted text-xs">
                          {new Date(record.date).toLocaleDateString()}
                        </td>
                      </motion.tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-cyber-text-muted text-center py-4">
                暂无记录
              </div>
            )}
          </div>
        </motion.div>

        {/* 底部操作 */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="mt-8 flex justify-center gap-4"
        >
          <button
            onClick={() => navigate('/')}
            className="btn-primary flex items-center gap-2"
          >
            <RotateCcw className="w-5 h-5" />
            再来一局
          </button>
          <button
            onClick={() => navigate('/')}
            className="btn-secondary flex items-center gap-2"
          >
            <Home className="w-5 h-5" />
            返回主页
          </button>
        </motion.div>
      </div>
    </div>
  )
}

function VariableBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-cyber-text-muted">{label}</span>
        <span className="font-mono text-cyber-text">{(value * 100).toFixed(0)}%</span>
      </div>
      <div className="h-2 bg-cyber-border rounded-full overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${color}`}
          initial={{ width: 0 }}
          animate={{ width: `${value * 100}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>
    </div>
  )
}