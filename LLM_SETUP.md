# LLM API 配置指南

## 概述

项目现在支持通过真实的LLM API生成Agent对话，每个Agent都有独特的个性和提示词。对话已集成到游戏引擎中，在每次循环时自动生成。

## 配置步骤

### 1. 编辑 .env 文件

打开项目根目录下的 `.env` 文件，填写你的API信息：

```env
# API 基础URL
# 示例:
# - DeepSeek: https://api.deepseek.com/v1
# - OpenAI: https://api.openai.com/v1
# - 其他兼容OpenAI格式的API
# 注意：如果API使用非标准路径，请填写完整URL到/chat/completions
LLM_API_URL=https://aiping.cn/api/v1/chat/completions

# API 密钥（从服务商获取）
LLM_API_KEY=your-actual-api-key-here

# 模型名称
# 示例:
# - DeepSeek: deepseek-chat, deepseek-coder
# - OpenAI: gpt-4, gpt-3.5-turbo
# - GLM: glm-5
LLM_MODEL=glm-5

# 可选配置
LLM_TIMEOUT=30
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=1000

# ========== 限流与重试配置（避免429错误）==========

# 每分钟最大请求数（根据你的API套餐调整）
# 免费套餐建议设置为 3-5，付费套餐可以设置为 10-60
LLM_RATE_LIMIT_REQUESTS=10

# 每分钟最大token数（根据你的API套餐调整）
# 免费套餐建议设置为 3000-5000，付费套餐可以设置为 10000+
LLM_RATE_LIMIT_TOKENS=10000

# 最大重试次数（遇到429错误时自动重试）
LLM_MAX_RETRIES=3

# 初始重试延迟（秒）
LLM_RETRY_DELAY=1.0

# 退避因子（每次重试延迟倍数）
LLM_RETRY_BACKOFF=2.0

# 最大并发请求数（同时进行的API调用数量）
# 建议设置为 1-3，避免触发限流
LLM_MAX_CONCURRENT=3
```

### 2. 获取API密钥

#### DeepSeek
1. 访问 https://platform.deepseek.com/
2. 注册并登录账号
3. 在API Keys页面创建新密钥
4. 复制密钥到 `.env` 文件

#### OpenAI
1. 访问 https://platform.openai.com/
2. 注册并登录账号
3. 在API Keys页面创建新密钥
4. 复制密钥到 `.env` 文件

#### 其他服务商
任何兼容OpenAI API格式的服务商都可以使用，只需修改 `LLM_API_URL` 和 `LLM_MODEL`。

**注意**: 如果API端点路径不是标准的 `/v1/chat/completions`，请直接在 `LLM_API_URL` 中填写完整路径。

## 特性说明

### 1. 上帝Agent（文明创世者）

- **角色定位**: 超越时空的存在，俯瞰文明兴衰
- **说话风格**: 深邃、神秘、带有哲学意味
- **特色表达**: "命运的骰子已掷出"、"在概率的海洋中"

### 2. 普通Agent个性化

每个Agent根据八维性格属性生成独特的：

- **性格画像**: 如"天生领袖"、"精明利己者"、"社交达人"
- **说话风格**: 根据权威感、私心、社交性等调整
- **内心独白**: 反映真实的内心想法和动机

### 3. 性格维度

- **权威感(authority)**: 影响说话是否命令式
- **私心(selfishness)**: 影响是否为自己谋划
- **利他(altruism)**: 影响是否关心他人
- **社交性(sociability)**: 影响健谈程度
- **智力(intelligence)**: 影响用词精准度
- **风险偏好(risk_appetite)**: 影响冒险倾向
- **韧性(resilience)**: 影响抗压能力
- **忠诚(loyalty_base)**: 影响对文明的归属感

### 4. 对话场景

系统会根据情境生成不同类型的消息：

- **工作汇报(REPORT)**: 高权威感Agent更倾向于汇报
- **请求帮助(REQUEST)**: 高私心或低效率时发起
- **闲聊(CHAT)**: 高社交性Agent更频繁
- **警告(ALERT)**: 高智力Agent会发出警告
- **说服(PERSUADE)**: 试图影响他人决策
- **操纵(MANIPULATE)**: 内鬼Agent的暗中行为

### 5. 游戏集成

对话系统已完全集成到游戏引擎中：

- **自动生成**: 每个循环自动触发Agent对话生成
- **消息存储**: 所有对话保存到SQLite数据库
- **前端显示**: 通过API接口 `/api/game/{game_id}/run-round` 返回消息
- **通讯系统**: 遵循游戏机制文档中的通讯与信息传播系统

## 文件结构

```
backend/core/
├── llm_service.py              # LLM API服务
├── llm_dialogue_generator.py   # LLM对话生成器
├── message_generator.py        # 游戏内消息生成器（已集成到引擎）
├── engine.py                   # 游戏引擎（已集成对话生成）
└── god_agent.py                # 上帝Agent（已有个性化提示词）

backend/api/
├── game_api.py                 # 游戏API（已更新获取真实消息）
└── communication_api.py        # 通讯API（用于前端展示）

.env                            # API配置文件
```

## 故障排除

### API调用失败

如果看到 `API调用失败: 401 Client Error`，说明：

1. API密钥未配置或配置错误
2. 系统会自动回退到模拟模式生成简单回复

### 模拟模式

当API未配置或调用失败时，系统会使用预设的模板生成回复。虽然不如LLM生成的丰富，但能保证系统正常运行。

### 404错误

如果看到 `404 Client Error`，说明API端点路径不正确。请检查：

1. `LLM_API_URL` 是否包含完整路径
2. 某些API可能需要 `/chat/completions` 完整路径

## 示例对话

不同性格的Agent会生成完全不同的对话风格：

**领导型Agent**:
> "听我的，咱们得保持步调一致。这轮产出提升20%，大家继续加油！"

**野心家Agent**:
> "这波效率提上来，主要是之前积累的资源这轮刚好能用上。这势头要是能稳住，咱们部门接下来的数据面会好看不少。"

**社交达人Agent**:
> "嘿！👋 跟你汇报一下哈，这波我感觉状态挺不错的～ 咱们这势头保持住，感觉接下来能更顺！✨"

## 注意事项

1. **API费用**: 使用真实API会产生费用，请注意控制调用频率
2. **隐私安全**: 不要将包含真实API密钥的.env文件提交到版本控制
3. **网络连接**: 使用真实API需要稳定的网络连接
4. **消息数量**: 每回合生成的消息数量取决于Agent之间的连接关系和通讯概率
