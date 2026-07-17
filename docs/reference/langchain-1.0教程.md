# Part 1.最新版LangChain 1.0快速入门介绍
这是一个非常重要的技术更新解读。LangChain 1.0 的发布标志着它从一个单纯的“工具箱”进化为了一个成熟的“Agent 生产平台”。

基于你**“先看具体例子，再理解抽象概念”**的偏好，我将这份关于 LangChain 1.0、LangGraph 以及整个生态的深度解读进行了重构。我们先从实际的应用场景切入，再上升到架构层面的变化。

---

### 一、 核心升级：从“胶水”到“智能引擎”

在 LangChain 1.0 之前，开发者常觉得它像一堆零散的积木（拼装库）。现在，它更像是一个底盘稳固的汽车平台（Agent Runtime）。

#### 1. 核心变化：LangGraph 成为底座
**【场景例子】**
想象你以前写一个 Agent，就像写一个无限 `while` 循环的 Python 脚本：你需要自己手动写代码去记录“在这个循环里，变量A变成了什么”、“如果报错了，怎么跳回上一步”。一旦程序崩溃，内存里的变量就丢了。
**【抽象概念】**
* **旧版：** `AgentExecutor` 是手动拼接的逻辑，难以处理复杂状态和持久化。
* **1.0 新版：** 所有的 Agent 逻辑（即使你在用 LangChain 的简单 API）现在**底层都运行在 LangGraph 上**。LangGraph 就像一个图数据库引擎，它自动帮你管理状态（State）、存档（Checkpoint）和并发。
* **结论：** LangChain = 快速构建的入口；LangGraph = 负责稳定运行的内核。

#### 2. 统一入口：`create_agent`
**【场景例子】**
以前你要创建一个 Agent，可能需要查阅 5 种不同的构造函数，还要纠结是用 `initialize_agent` 还是 `AgentExecutor`。
现在，你只需要一个指令：`create_agent`。
**【抽象概念】**
这是一个统一的 API 工厂。当你调用它时，它会在后台自动拉起一个基于 LangGraph 的运行时环境，默认配置好了循环调用、工具执行和停止条件。

---

### 二、 1.0 的王牌功能：中间件 (Middleware)

这是本次更新中最具工程价值的部分。**中间件**就像是安装在 Agent 思考过程中的“拦截器”或“过滤器”。

#### 场景 1：人在环 (Human-in-the-loop) -> 审批与修正
* **具体例子：** 你的 Agent 负责财务转账。当它决定调用“转账 API”转出 10,000 元时，中间件会**暂停**（Interrupt）程序，发一条消息给你：“是否批准？”。你在后台点击“批准”后，程序恢复执行；或者你修改金额为 5,000 元，Agent 接着按新金额执行。
* **抽象定义：** 利用 LangGraph 的**检查点 (Checkpointer)** 机制，在工具调用前/后挂载钩子。这让 Agent 具备了可中断、可修改、可恢复的能力。

#### 场景 2：消息治理 (Trimming/Summarization) -> 省钱与防遗忘
* **具体例子：** 用户和 Agent 聊了 100 轮，Token 即将通过 DeepSeek 的上下文上限，费用也在飙升。
    * **策略 A (修剪)：** 中间件自动切掉前 80 轮，只保留最近 20 轮。
    * **策略 B (汇总)：** 中间件自动把前 80 轮对话压缩成一段 200 字的摘要：“用户之前询问了关于 API key 的问题...”，并塞回上下文中。
* **抽象定义：** `SummarizationMiddleware` 或修剪逻辑。通过监控 Token 阈值，自动对 `State` 中的消息列表进行清洗，确保上下文既不超长又不丢失关键信息。

#### 场景 3：动态路由 (Model Routing) -> 聪明地分配任务
* **具体例子：** 用户问“你好”时，中间件分配便宜的 `deepseek-chat` 模型；用户问“请推导量子力学公式”时，中间件自动切换到昂贵的 `deepseek-reasoner` (R1) 模型。
* **抽象定义：** `wrap_model_call`。在模型调用发生前，根据输入复杂度、关键词或预算，动态替换执行的模型对象。

---

### 三、 LangChain vs. LangGraph：如何选择？

为了防止选择困难症，官方给出了明确的分工界限。我们可以用“装修”来类比：

| 维度 | LangChain 1.0 | LangGraph |
| :--- | :--- | :--- |
| **类比** | **精装房（拎包入住）** | **毛坯房（自由定制）** |
| **核心功能** | 提供标准化的积木：`create_agent`、标准消息块、通用中间件。 | 提供底层水电架构：图结构、状态管理、并发控制、复杂的条件分支。 |
| **适用人群** | **业务开发者**：需要快速把想法变成 MVP，或者构建标准流程。 | **平台架构师**：需要构建极其复杂的业务流（如多 Agent 协作、复杂的循环逻辑）。 |
| **关系** | 运行在 LangGraph 之上。 | 是 LangChain 的底层运行时。 |

**一句话总结：** 90% 的常规应用先用 LangChain 快速起步；剩下 10% 需要极高精细度控制的复杂逻辑，用 LangGraph 修改底层图结构。

---

### 四、 生态全景与现状

现在的 LangChain 已经不是一个单一的 Python 库，而是一个庞大的**生态系统 (LangChain.ai)**。

1.  **LangChain (核心库)：**
    * **定位：** 模型能力增强器。
    * **解决痛点：** 解决模型接口不统一（OpenAI, Anthropic, DeepSeek 接口各异）、输出不可控（帮你解析 JSON）、没有记忆等问题。
    * **现状：** 虽然曾被诟病代码臃肿，但在 1.0 版本通过标准化和瘦身，重新找准了定位。

2.  **LangGraph：**
    * **定位：** Multi-Agent 编排引擎。
    * **地位：** 目前生态内**最核心**的框架。Google、字节跳动（Deep Research 项目）等大厂的新项目都在使用它作为底层。

3.  **LangSmith：**
    * **定位：** 测试与监控平台。
    * **作用：** 这是一个可视化后台。你可以看到 Agent 每一步思考了什么、用了多少 Token、在哪里卡住了。这是企业级开发必不可少的 Debug 工具。

4.  **LangFlow：**
    * **定位：** 低代码/无代码平台。
    * **作用：** 类似 Dify 的拖拉拽界面，适合非程序员或快速原型搭建。它是目前 GitHub 上非常热门的可视化工具。

---

### 总结与建议

LangChain 1.0 的这次更新，实际上是在告诉开发者：**“不要再写过程式的脚本了，要用图（Graph）的思维去构建 Agent。”**

* **以前：** 你是写剧本的，规定 Agent 第一句说什么，第二句说什么。
* **现在：** 你是设计系统的，你定义状态、规则和工具，让 Agent 在 LangGraph 的“图”上自主运行，同时利用中间件进行必要的管控。

**这一转变对于企业级应用至关重要**，因为只有具备了状态持久化（断点续传）和中间件管控（人工审核），Agent 才能真正敢于在生产环境中处理敏感业务（如写数据库、转账）。

---

# Part 2.各类模型接入LangChain流程

你好，Severin！我是 Gemini。

收到你提供的《LangChain 1.0 入门实战：各类模型接入流程》课程资料。这份资料非常有价值，它涵盖了目前主流的大模型（DeepSeek、OpenAI、阿里通义千问）以及本地模型（Ollama）接入 LangChain 的标准范式。

记得你曾提过，你更喜欢\*\*“先看具体例子，再抽象出概念”\*\*的学习方式。这非常好，因为 LangChain 的设计哲学正是通过统一的代码结构（例子）来屏蔽底层复杂的 API 差异（概念）。

下面我将为你**整理并详细讲解**这份资料。我们将从具体的代码实现入手，最后总结出一套通用的“万能公式”。

-----

### 📚 核心主题：LangChain 的“适配器”模式

在进入代码前，你可以这样理解：

  * **大模型（LLM）** 就像不同品牌的**电源插座**（DeepSeek 是圆孔，OpenAI 是方孔，Ollama 是本地发电机）。
  * **LangChain** 就是一个**万能转接头**。
  * **你的代码** 只需要插在 LangChain 上，不需要关心后面接的是哪家电厂。

下面我们按厂商逐一拆解。

-----

### 🛠️ 第一部分：环境准备 (通用基础)

在连接任何模型之前，我们需要搭建地基。

**1. 安装 LangChain 核心包**

```bash
! pip install langchain
```

  * **注意版本**：课程要求 LangChain $\ge 1.0.0$。新版本（1.0+）对接口稳定性做了很大提升，这对于生产环境开发至关重要。

**2. 密钥管理 (安全第一)**
我们在代码中不应该直接写明文密码（API Key），而是使用 `.env` 文件。

  * **例子**：在项目根目录新建 `.env` 文件，写入 `DEEPSEEK_API_KEY=sk-xxxx`。
  * **代码加载**：
    ```python
    import os
    from dotenv import load_dotenv
    load_dotenv(override=True) # 加载 .env 文件中的变量到系统环境变量中
    ```
      * **详细解读**：`load_dotenv` 是 Python 开发中的标准操作，它能防止你把私有的 Key 不小心上传到 GitHub 上。

-----

### 🚀 第二部分：接入 DeepSeek (具体实战)

这是目前最热门的模型，资料中展示了两种接入方式，对比一下就能看出 LangChain 的优势。

#### 方式 A：不使用 LangChain（原生 SDK 调用）

这是“手搓”的方式，直接通过网络请求调用。

```python
# 初始化客户端
client = OpenAI(api_key=DeepSeek_API_KEY, base_url="https://api.deepseek.com")

# 发送请求（格式复杂，需要构建 messages 列表）
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "你好"}]
)
# 解析结果（层级很深）
print(response.choices[0].message.content)
```

  * **痛点**：你需要记住 `client.chat.completions.create` 这种复杂的写法，而且返回的 JSON 结构嵌套很深，提取内容麻烦。

#### 方式 B：使用 LangChain（推荐方式）

这是课程的核心。看代码有多简洁：

**1. 安装专用包**

```bash
! pip install langchain-deepseek
```

**2. 代码实现**

```python
from langchain_deepseek import ChatDeepSeek

# 实例化模型对象：在这里指定是 V3 (chat) 还是 R1 (reasoner)
model = ChatDeepSeek(model="deepseek-chat") 
# model = ChatDeepSeek(model="deepseek-reasoner") # 切换模型只需改这里

# 调用模型：这一步是通用的！
result = model.invoke("你好，请介绍你自己。")

# 获取结果
print(result.content)
```

**🔍 详细讲解：**

  * **`ChatDeepSeek`**：这是 LangChain 为 DeepSeek 定制的“连接器”。
  * **`invoke` (调用)**：这是 LangChain 的核心概念。无论后面是什么模型，你永远只需要调用 `invoke()` 方法。
  * **DeepSeek R1 (Reasoner)**：资料中展示了调用 `deepseek-reasoner`。你会发现返回结果中包含 `reasoning_content`（思维链），这是 R1 模型的特色，它会展示“思考过程”，适合处理复杂逻辑问题。

-----

### 🤖 第三部分：接入 OpenAI (举一反三)

既然你看懂了 DeepSeek 的 LangChain 接入方式，OpenAI 就非常容易理解了，因为逻辑完全一样。

**1. 安装专用包**

```bash
! pip install langchain-openai
```

**2. 代码实现**

```python
from langchain_openai import ChatOpenAI

# 实例化：这里可能有 base_url 是因为国内访问需要代理
model = ChatOpenAI(model="gpt-5-nano", base_url="代理地址...")

# 调用：完全一样的 invoke
result = model.invoke("你好")
print(result.content)
```

  * **详细解读**：这里唯一的区别仅仅是 `ChatDeepSeek` 变成了 `ChatOpenAI`。这就验证了我们开头说的“万能插座”理论。

-----

### ☁️ 第四部分：接入阿里百炼 Dashscope (Qwen)

这是国内最大的开源模型平台之一。

**1. 准备工作**

  * 需要去阿里云百炼控制台注册并获取 `DASHSCOPE_API_KEY`。

**2. 代码实现**

```python
# 注意：这里使用的是社区包 langchain_community
from langchain_community.chat_models.tongyi import ChatTongyi

model = ChatTongyi() # 默认使用 qwen-turbo 或 qwen-plus，也可以指定 model 参数

result = model.invoke("你好")
print(result.content)
```

  * **详细解读**：注意这里的导入路径 `langchain_community`。LangChain 把一些核心厂商（如 OpenAI）独立成了包，而像通义千问（Tongyi）目前主要在社区包里维护。但使用方法依然是标准的 `invoke`。

-----

### 🏠 第五部分：接入本地模型 Ollama

对于隐私要求高或离线环境，Ollama 是运行本地模型的神器（比如在本地跑 DeepSeek-R1）。

**1. 安装专用包**

```bash
! pip install langchain-ollama
```

**2. 代码实现**

```python
from langchain_ollama import ChatOllama

# 前提：你的电脑后台必须已经运行了 Ollama 且下载了 deepseek-r1 模型
model = ChatOllama(model="deepseek-r1")

result = model.invoke("你好")
print(result.content)
```

  * **详细解读**：Ollama 运行在本地（通常是 localhost:11434）。LangChain 自动处理了与本地服务器的通信。资料中展示的 `<think>` 标签，正是 DeepSeek-R1 模型特有的思维链输出，LangChain 能够完整保留这些原始输出。

-----

### 🎓 总结与抽象：LangChain 的核心逻辑

Severin，通过上面四个具体的例子，现在我们可以放心地**抽象出概念**了。你会发现所有代码都遵循同一个\*\*“三步走公式”\*\*：

1.  **Import（导入类）**：根据厂商选择不同的类。
      * DeepSeek $\rightarrow$ `ChatDeepSeek`
      * OpenAI $\rightarrow$ `ChatOpenAI`
      * 阿里 Qwen $\rightarrow$ `ChatTongyi`
      * 本地 Ollama $\rightarrow$ `ChatOllama`
2.  **Initialize（初始化）**：传入模型名称 (`model="xxx"`) 和密钥 (`api_key`)。
3.  **Invoke（调用）**：**这是最关键的抽象。** 无论步骤 1 和 2 怎么变，步骤 3 永远是 `model.invoke(prompt)`。

**这对开发的意义：**
如果你在开发一个 AI 应用，想从 GPT-4 切换到 DeepSeek V3，你只需要修改**配置代码**（步骤 1 和 2），而核心的**业务逻辑代码**（步骤 3 及之后的处理）完全不需要改动。这就是 LangChain 强大的兼容性。

-----

# Part 3.模型调用、记忆管理与工具调用流程

你好，叶博韬（Severin）。很高兴能协助你整理这份关于 **LangChain 1.0 核心基础**的课程内容。

这部分内容非常关键，它是从简单的“调用模型”转向构建“智能体（Agent）”的基石。根据你**偏好“先看具体例子，再抽象概念”的学习习惯**，我将课程内容重构为以下四个核心模块进行详细讲解。

-----

### 模块一：LangChain 1.0 的“原子”——消息（Message）

在 LangChain 1.0 中，一切交互的基础不再是简单的字符串，而是结构化的**Message（消息）**。

#### 1\. 具体例子

我们要让 AI 扮演一个角色并回答问题，代码是这样写的：

```python
from langchain.messages import HumanMessage, SystemMessage

# 定义消息列表
messages = [
    SystemMessage(content="你叫小智，是一名助人为乐的助手。"), # 设定 AI 人设
    HumanMessage(content="你好，请介绍下你自己。")           # 用户的输入
]

# 这里的 messages 变量，就是传给模型的核心数据
```

#### 2\. 概念抽象与详解

**为什么不直接传字符串？**
因为真实对话是复杂的。LangChain 通过标准化的 `Message` 对象，统一了所有大模型（OpenAI, DeepSeek, Claude等）的输入格式。

  * **Role（角色）**：
      * `SystemMessage`：系统的“上帝视角”指令（如：你是一个猫娘、你是一个严谨的律师）。
      * `HumanMessage`：用户说的话。
      * `AIMessage`：模型回复的话。
  * **Metadata（元数据）**：
    除了文本内容，消息还携带了额外信息（如 token 消耗、响应时间）。这在生产环境中对于计算成本和调试非常重要。

-----

### 模块二：模型的调用方式（Invoke, Stream, Batch）

有了消息，下一步就是发送给模型。LangChain 提供了三种主要方式，适应不同场景。

#### 1\. 标准调用 (Invoke)

**例子：** 就像发短信，发一条，回一条。

```python
response = model.invoke(messages)
print(response.content) 
# 输出：你好呀！我是小智...
```

**概念：** 最基础的同步调用。程序会“卡”在这里，直到模型把整句话想好并一次性返回。适合非实时性要求高的场景。

#### 2\. 流式调用 (Stream)

**例子：** 就像打字机，一个个字蹦出来。

```python
for chunk in model.stream("你好"):
    print(chunk.content, end="|", flush=True)
# 输出：你|好|！|很|高|兴|...
```

**概念：**

  * **原理**：模型每生成一个 token（字/词）就立即推送到前端，返回的是 `AIMessageChunk`（消息块）。
  * **优势**：极大地提升用户体验（User Experience），用户不需要面对几秒钟的空白屏幕等待。
  * **拼接**：LangChain 支持将这些碎片（Chunks）相加（`chunk + chunk`），最后拼成一个完整的回复。

#### 3\. 批处理 (Batch)

**例子：** 一次性问三个问题，并行处理。

```python
responses = model.batch([
    "请介绍下你自己。",
    "什么是机器学习？",
    "什么是深度学习？"
])
# model 会在后台同时处理这三个请求，处理完后统一返回一个列表
```

**概念：** \* **并发效率**：利用 `max_concurrency` 参数，可以让模型同时处理多个独立任务，而不是排队一个接一个做。

  * **应用场景**：比如你需要同时给 100 篇文档写摘要，用 Batch 比用循环（Loop）快得多。

[Image of synchronous vs asynchronous batch processing diagram]

-----

### 模块三：结构化输出 (Structured Output)

这是 Agent 开发中最强大的功能之一。默认情况下，模型吐出的是“自然语言”，但代码需要的是“JSON”或“对象”。

#### 1\. 具体例子

假设我们要从一段影评中提取电影信息，并存入数据库。

**定义结构 (Schema)：**

```python
from pydantic import BaseModel, Field

# 定义我们想要的数据格式（类似一张表格的表头）
class Movie(BaseModel):
    title: str = Field(..., description="电影标题")
    year: int = Field(..., description="上映年份")
    rating: float = Field(..., description="评分")

# 告诉模型：请严格按照这个格式输出
model_with_structure = model.with_structured_output(Movie)

# 调用模型
response = model_with_structure.invoke("讲讲诺兰的《盗梦空间》，2010年上映的，评分高达8.8呢")

# 模型直接返回对象，而不是废话
print(response) 
# 输出：Movie(title='Inception', year=2010, rating=8.8)
print(response.year) 
# 输出：2010 (这是真正的数字类型 int，不是字符串)
```

#### 2\. 概念抽象

  * **自然语言歧义**：人类语言是模糊的，程序是严谨的。
  * **Schema 约束**：通过 Pydantic，我们强制模型“填表”。模型不再随意发挥，而是精准提取关键信息。
  * **Agent 的基础**：这是工具调用（Tool Calling）的前提。Agent 需要精准地知道“搜索什么关键词”或“计算什么数字”，结构化输出保证了参数的准确性。

-----

### 模块四：实战——构建多轮对话机器人

最后，课程将上述概念整合成了一个具备“记忆”的聊天机器人。

#### 1\. 核心逻辑（Cli 命令行版）

我们来看代码是如何实现“记忆”的：

```python
# 1. 初始化一个列表，先把系统人设放进去
messages = [SystemMessage(content="你叫小智...")]

while True:
    user_input = input("你：")
    
    # 2. 【关键】把用户说的话，追加(append)到列表末尾
    messages.append(HumanMessage(content=user_input))
    
    # 3. 把整个列表传给模型（包括了之前的历史记录）
    # 使用 stream 实现打字机效果
    full_reply = ""
    for chunk in model.stream(messages):
        print(chunk.content, end="")
        full_reply += chunk.content
    
    # 4. 【关键】把 AI 回复的话，也追加到列表末尾，形成闭环
    messages.append(AIMessage(content=full_reply))
    
    # 5. 限制记忆长度（防止 token 溢出费钱），只记最后50句
    messages = messages[-50:] 
```

#### 2\. 概念抽象

  * **无状态模型**：大模型本身是“健忘”的（Stateless）。你问它第二句时，它已经忘了第一句。
  * **记忆管理**：这里的 `messages` 列表就是**短期记忆**。我们要做的就是不断地在这个列表里“堆叠”对话历史，每次请求都把“前因后果”一股脑发给模型。
  * **Gradio 可视化**：课程后半部分展示了如何用 Gradio 包装这个逻辑。原理完全一样，只是把 `print` 换成了网页上的气泡显示，把 `input` 换成了网页输入框。

-----

### 总结

这节课其实就讲了三件事，这也是开发 Agent 的基本功：

1.  **输入规范**：不要只传字符串，要传 `Message` 对象（包含角色和元数据）。
2.  **交互模式**：根据需求选择 `Stream`（即时快）、`Batch`（批量快）或 `Invoke`（简单）。
3.  **输出控制**：用 `Structured Output` 强迫模型说“机器能听懂的话”，而不是仅仅陪聊。


# Part 4.LangChain 1.0 Agent开发流程

你好，Severin (叶博韬)。这份课程笔记涵盖了 LangChain 1.0 版本中关于 Agent（智能体）开发的核心变革。

根据你偏好**先看具体例子，再抽象概念**的学习习惯，我将这份资料重新梳理。我们不先讲枯燥的定义，而是通过**代码实现的演进**和**实际运行的案例**，来一步步拆解 LangChain 1.0 的 Agent 架构。

-----

### 核心变革概览：从“工具箱”到“操作系统”

在深入代码之前，先建立一个直观的认知：

  * **过去 (0.x 版本)**：LangChain 像是一个**工具箱**。你想造个对话机器人，拿“对话钳子”；想造个搜索机器人，拿“搜索扳手”（即 `create_react_agent`, `create_json_agent` 等不同的 API）。你需要记住每个工具怎么用，很麻烦。
  * **现在 (1.0 版本)**：LangChain 变成了一个**通用操作系统**。无论你想造什么机器人，统一使用 **`create_agent`** 这一个入口。底层由 **LangGraph** 提供动力，就像操作系统的内核一样管理任务。

-----

### 第一部分：统一入口 `create_agent`

#### 1\. 它是如何工作的？（实例演示）

在 1.0 中，创建一个智能体变得极其简单，就像搭积木：**模型 (大脑) + 工具 (手脚) = 智能体**。

看看课程中的核心代码：

```python
# 1. 准备大模型 (大脑)
model = ChatDeepSeek(model="deepseek-chat")

# 2. 准备工具 (手脚，这里用了联网搜索)
web_search = TavilySearchResults(max_results=2)

# 3. 组装 Agent (使用统一入口 create_agent)
agent = create_agent(
    model=model,
    tools=[web_search],
    system_prompt="你是一名多才多艺的智能助手..."
)

# 4. 运行
result = agent.invoke({"messages": [{"role": "user", "content": "查询2024诺贝尔物理学奖得主"}]})
```

#### 2\. 从例子中抽象概念

  * **API 大一统**：你不再需要纠结是用 React 还是 JSON 架构，`create_agent` 会根据你传入的模型和工具自动处理。
  * **LangGraph 底层 (Runtime)**：
      * 虽然代码里没写，但 `create_agent` 在后台悄悄画了一张“图”（Graph）。
      * **节点 (Node)**：代表模型思考、工具执行。
      * **边 (Edge)**：代表流程流转（比如：思考完 -\> 决定调用工具 -\> 工具返回结果 -\> 再思考）。

-----

### 第二部分：工具调用与 ReAct 循环 (Agent 的核心)

Agent 之所以智能，是因为它能“自主决策”。课程中展示了两种工具接入方式，这体现了 Agent 如何通过**ReAct (Reasoning + Acting)** 循环来工作。

#### 1\. 接入内置工具 (以搜索为例)

当你问“2025年诺贝尔奖颁发了几个？”时，模型本身不知道答案（因为它有知识截止日期）。

**Agent 的执行流程（观察日志）：**

1.  **思考 (Reasoning)**：模型分析用户问题，决定调用 `tavily_search_results_json` 工具。
2.  **行动 (Acting)**：系统执行搜索，获得 JSON 格式的搜索结果（包含新闻标题、链接）。
3.  **再思考 (Reasoning)**：模型阅读搜索结果，总结成人类语言。
4.  **回答**：输出最终答案。

#### 2\. 接入自定义工具 (以查询天气和写文件为例)

这是最实用的部分。如果 LangChain 没有内置某个功能，你可以把任何 Python 函数变成工具。

**步骤：**

1.  **写函数**：写一个普通的 Python 函数（如 `get_weather`）。
2.  **加装饰器**：加上 `@tool`，让 Agent 能读懂这个函数是干嘛的（通过 docstring）。
3.  **给 Agent**：放入 `tools` 列表。

**高阶用法：多步与并发调用**
课程中的例子非常有意思，当你问：“查询天津、石家庄、上海天气，并写入本地文件”时，Agent 展现了强大的规划能力：

  * **并发调用**：它一次性发起了 3 个天气查询请求（天津、石家庄、上海），而不是查完一个再查下一个。这大大节省了时间。
  * **多步规划**：
      * 第一轮：调用 `get_weather` x 3。
      * 第二轮：拿到 3 个天气结果后，调用 `write_file` 把总结写入文件。
      * 第三轮：告诉用户“搞定了”。

-----

### 第三部分：记忆管理 (Memory)

Agent 如果没有记忆，就像只有 7 秒记忆的金鱼。LangChain 1.0 使用 `checkpointer` 来管理记忆。

#### 1\. 实例演示

```python
# 引入记忆保存器
from langgraph.checkpoint.memory import InMemorySaver
checkpointer = InMemorySaver()

# 创建带记忆的 Agent
agent = create_agent(..., checkpointer=checkpointer)

# 运行时指定 thread_id (线程ID)
config = {"configurable": {"thread_id": "1"}}

# 第一句话
agent.invoke(..., config) 
# 第二句话 (Agent 会去 thread_id="1" 的地方查找上文)
agent.invoke(..., config)
```

#### 2\. 概念解析

  * **Thread ID (线程 ID)**：这是区分不同对话的关键。你把 `thread_id` 设为 "1"，Agent 就记得 Severin 是谁；设为 "2"，它就是一张白纸。
  * **State Snapshot (状态快照)**：LangGraph 会在每一步操作后把当前的“状态”（包括聊天记录、工具结果）保存下来。这不仅用于记忆，还用于**断点续传**（比如程序崩溃了，可以从断开的地方继续跑）。

-----

### 总结与核心知识点梳理

| 维度 | LangChain 0.x (旧时代) | LangChain 1.0 (新时代) | 核心优势 |
| :--- | :--- | :--- | :--- |
| **创建方式** | 碎片化 (`create_react_agent` 等) | **统一入口 (`create_agent`)** | 降低心智负担，代码更简洁 |
| **底层架构** | 简单的链 (Chain) | **图结构 (LangGraph)** | 支持循环、分支、复杂的逻辑跳转 |
| **模型使用** | 主要是静态 | **静态 + 动态** | 可以在运行时根据任务难度换模型（如 gpt-4o vs mini） |
| **运行机制** | 简单的问答 | **ReAct 循环** | 思考 -\> 调工具 -\> 观察 -\> 再思考 |
| **状态管理** | 较弱 | **Checkpointer** | 像游戏存档一样，随时保存和恢复状态 |

### Severin，我能为你做的下一步

既然你已经掌握了 LangChain 1.0 的架构逻辑，下一步通常是动手实战。

**你想让我根据课程中的“自定义工具”部分，帮你写一个具体的 Python 代码框架吗？**
(例如：帮你写一个能“读取你电脑上的 PDF 文件并总结内容”的自定义工具 Agent demo)

Severin，没问题。我们遵循你喜欢的“从具体例子到抽象概念”的路径，深入拆解代码。

这两部分是 Agent 开发中最重要的“手脚”（工具）和“海马体”（记忆）。我们逐行代码来看它们是如何运作的。

-----

### 第一部分：接入自定义工具 (Custom Tools)

在 LangChain 1.0 中，接入工具的核心逻辑是将**Python 函数**转换为**大模型能读懂的 API 描述**。

#### 1\. 代码实现步骤

我们以课程中的“查询天气”为例，看代码是如何一步步构建的：

**Step 1: 定义普通的 Python 函数**
首先，这就是一个没有任何“AI 魔法”的普通函数。

```python
import os
import requests
import json
from langchain.tools import tool # 核心组件

# 这是一个标准的 Python 函数，还没有变成工具
def get_weather_logic(loc):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": loc,
        "appid": os.getenv("OPENWEATHER_API_KEY"),
        "units": "metric",
        "lang": "zh_cn"
    }
    response = requests.get(url, params=params)
    data = response.json()
    return json.dumps(data)
```

**Step 2: 使用 `@tool` 装饰器进行转化（关键步骤）**
这是最关键的一步。`@tool` 装饰器会利用 Python 的**类型提示 (Type Hints)** 和 **文档字符串 (Docstring)** 自动生成 JSON Schema。大模型就是通过读这个 Schema 来决定是否调用该工具。

```python
@tool
def get_weather(loc: str) -> str:
    """
    查询即时天气函数。
    
    :param loc: 必要参数，字符串类型。用于表示查询天气的具体城市名称（英文）。
                例如：查询北京天气，loc参数需要输入 'Beijing'。
    :return: 返回包含温度、湿度等天气信息的 JSON 字符串。
    """
    # ... (这里放入上面 Step 1 的具体逻辑) ...
    return get_weather_logic(loc) 
```

**🔍 深度解析：为什么这段代码有效？**
大模型是看不到函数内部代码的，它只能看到你写的文档字符串（Docstring）。

  * **函数名 (`get_weather`)**：告诉模型这个工具叫什么。
  * **Docstring (`"""..."""`)**：这是给模型的**操作说明书**。如果你写得模糊，模型就会乱调用。课程例子中明确指出了 `loc` 需要是英文（'Beijing'），这就是在通过 Prompt Engineering 引导模型正确传参。
  * **类型提示 (`loc: str`)**：告诉模型参数必须是字符串，防止模型传入数字或对象。

**Step 3: 将工具装配给 Agent**

```python
from langchain.agents import create_agent
from langchain_deepseek import ChatDeepSeek

# 1. 实例化模型
model = ChatDeepSeek(model="deepseek-chat")

# 2. 创建列表，把工具放进去（可以放多个）
tools = [get_weather] 

# 3. 组装
agent = create_agent(
    model=model,
    tools=tools,
    system_prompt="你是一个能调用工具的助手。"
)

# 4. 运行
result = agent.invoke({"messages": [{"role": "user", "content": "北京天气怎么样？"}]})
```

#### 2\. 底层运行流程 (ReAct 循环)

当你执行 `agent.invoke` 时，底层发生了什么？

1.  **Prompt 构建**：LangChain 会自动把 `get_weather` 的定义（名字、参数、说明）转换成一段系统提示词，告诉 DeepSeek：“我手里有一个叫 `get_weather` 的工具，如果你需要用，请按这个格式输出 JSON。”
2.  **模型推理**：DeepSeek 分析用户问题“北京天气”，发现这需要外部数据，于是输出一个特殊的 **Function Call** 指令（包含参数 `loc='Beijing'`）。
3.  **LangGraph 拦截**：Agent Runtime 捕获到这个指令，暂停思考，去执行 Python 函数 `get_weather('Beijing')`。
4.  **结果回填**：Python 函数运行完毕，返回天气 JSON。LangChain 把这个结果贴回对话历史中。
5.  **最终响应**：DeepSeek 看到有了天气数据，据此生成人类可读的回答。

-----

### 第二部分：记忆管理 (Memory Management)

在 LangChain 1.0 (基于 LangGraph) 中，记忆不再是简单的“把所有历史记录拼成字符串”，而是基于**状态快照 (State Checkpointing)**。

#### 1\. 代码实现步骤

**Step 1: 引入存储器 (Checkpointer)**
首先我们需要一个地方存记忆。开发测试用 `InMemorySaver`（存在内存里），生产环境通常用 Postgres 或 Redis。

```python
from langgraph.checkpoint.memory import InMemorySaver

# 初始化一个内存存储器
checkpointer = InMemorySaver()
```

**Step 2: 绑定存储器到 Agent**
在创建 Agent 时，显式地把这个“海马体”装进去。

```python
agent = create_agent(
    model=model,
    tools=tools,
    checkpointer=checkpointer  # <--- 关键参数：开启记忆功能
)
```

**Step 3: 使用 `thread_id` 进行对话**
这是记忆管理的核心。你需要通过 `config` 字典告诉 Agent：“这是谁的对话”。

```python
# 定义配置：这是 "线程1" (比如用户Severin的对话)
config_severin = {"configurable": {"thread_id": "user_severin_001"}}

# 第一轮对话
response1 = agent.invoke(
    {"messages": [{"role": "user", "content": "你好，我叫 Severin。"}]},
    config=config_severin  # <--- 带着身份证去访问
)
print(response1['messages'][-1].content)
# 输出: 你好 Severin！很高兴认识你...

# 第二轮对话 (模拟下一次请求)
response2 = agent.invoke(
    {"messages": [{"role": "user", "content": "你还记得我叫什么吗？"}]},
    config=config_severin  # <--- 再次出示同样的身份证
)
print(response2['messages'][-1].content)
# 输出: 当然记得，你是 Severin。
```

#### 2\. 多用户/多线程对比

为了让你更清楚 `thread_id` 的作用，我们看看如果换个 ID 会发生什么：

```python
# 定义配置：这是 "线程2" (比如另一个新用户的对话)
config_guest = {"configurable": {"thread_id": "guest_user_999"}}

# 尝试问同一个 Agent
response3 = agent.invoke(
    {"messages": [{"role": "user", "content": "你知道我是谁吗？"}]},
    config=config_guest  # <--- 换了身份证
)
print(response3['messages'][-1].content)
# 输出: 抱歉，我不认识你。请告诉我你的名字。
```

#### 3\. 深度解析：记忆是如何存储的？

在 LangChain 1.0 的底层（LangGraph）中，记忆不仅仅是“文本列表”，它是一个 **State Snapshot（状态快照）**。

当你传入 `thread_id="user_severin_001"` 时：

1.  **读取 (Read)**：Agent 去 `checkpointer` 里查找这个 ID 对应的最新状态（之前的聊天记录 `messages` 列表）。
2.  **执行 (Execute)**：Agent 把新的用户输入追加到列表中，调用模型。
3.  **写入 (Write)**：模型生成回答后，Agent 把更新后的整个状态列表再次**覆盖/追加**保存回 `checkpointer` 中。

这意味着，你甚至可以实现\*\*“时光倒流”\*\*——读取一个旧的状态点，修改它，然后从那里重新开始分支对话（这在复杂的 Agent 调试中非常有用）。

-----

### 总结：两者如何结合？

在实际开发中，你通常会同时使用这两者：

1.  **User**: "帮我查下北京天气，并在明天早上提醒我。"
2.  **Agent (Memory)**: 识别出这是 `thread_id="severin"`，检索到之前知道你在北京。
3.  **Agent (Tools)**: 调用 `get_weather("Beijing")`。
4.  **Agent (Tools)**: 可能会调用一个你写的 `schedule_reminder` 工具。
5.  **Agent (Memory)**: 将“已设置提醒”这个状态存入 Checkpointer，下次你问“我明天有啥安排”，它能从记忆里读出来。

# Part 5.LangChain Agent部署与上线流程

好的，叶博韬。为了让你更直观地理解这部分内容，我们将遵循你喜欢的\*\*“先看具体例子，再抽象出概念”\*\*的学习方式。

这部分课程的核心是从\*\*“写代码”**跨越到**“生产环境部署”\*\*。我们先通过一个具体的“厨房”类比来理解这些工具的角色，然后再深入技术细节。

-----

### 第一部分：核心工具套件（厨房类比法）

假设我们在经营一家**智能餐厅（Agent）**。为了让餐厅高效运转，我们需要以下几样东西：

1.  **LangSmith —— 餐厅的“监控摄像头与黑匣子”**

      * **具体例子**：如果顾客投诉菜咸了（Agent 回答错误），你需要回放录像，看厨师（LLM）是在哪一步放多了盐，还是调料（Prompt）本身就有问题。
      * **抽象概念**：**运行监控框架**。它用于调试（Trace）、评估性能（Evaluation）和监控流量。它记录 Agent 的每一次思考路径，帮助开发者优化 Token 消耗和回答质量。

2.  **LangGraph Studio —— 餐厅的“可视化中控台”**

      * **具体例子**：你设计了一套做菜流程（Graph），通过这个中控台，你可以像搭积木一样看到流程图。你可以试着输入“做一份牛排”，然后看着信号灯在流程图上亮起，实时观察每一步是否顺畅。
      * **抽象概念**：**图结构可视化与调试 IDE**。它允许你在浏览器中直观地看到 Agent 的节点跳转、分支逻辑，并进行实时交互测试。

3.  **LangGraph CLI —— 餐厅的“启动钥匙与管家”**

      * **具体例子**：餐厅装修好了，你需要一把钥匙（命令）来开门营业，让服务员（API）准备好接待顾客。
      * **抽象概念**：**服务部署命令行工具**。用于本地启动服务（`langgraph dev`）、初始化项目结构和未来的云端部署。

4.  **Agent Chat UI —— 餐厅的“前台点餐区”**

      * **具体例子**：顾客通过这个漂亮的界面点餐，而不是直接跑到后厨对着厨师喊。
      * **抽象概念**：**前端可视化交互界面**。官方提供的开源前端，适配了多模态、工具调用展示等功能，开箱即用。

-----

### 第二部分：从零构建智能体项目的标准流程

我们以\*\*“天气与新闻查询助手”\*\*为例，看看标准的工程化项目结构是怎样的。

#### 1\. 项目结构标准化

不再是随意的一个 `.py` 文件，而是像建房子一样打地基：

  * **`requirements.txt`**：装修清单（依赖库）。
  * **`.env`**：保险箱（存放 API Key，绝对不能硬编码在代码里）。
  * **`agent.py`**：核心大脑（定义 Graph、Tools 和 LLM）。
  * **`langgraph.json`**：**最重要的导航图**。它告诉 CLI 工具：“我的图在哪个文件的哪个变量里”。

#### 2\. 核心代码逻辑 (`agent.py`)

在这个例子中，Agent 有两个技能（Tools）：

  * `search_tool`：查新闻。
  * `get_weather`：查天气（调用 OpenWeather API）。

**逻辑流向：**
用户提问 -\> LLM 判断意图 -\> 选择工具 -\> 执行工具 -\> LLM 整理结果 -\> 返回给用户。

#### 3\. 启动与调试

  * **命令**：`langgraph dev`
  * **效果**：这行命令会同时启动后端 API 服务器和 LangGraph Studio。你可以在 Studio 中看到一个可视化的图，输入“北京天气”，就能看到绿色的线流向 `get_weather` 节点。

-----

### 第三部分：高阶实战 —— 智能数据分析助手 (Data Agent)

这是本课程的重头戏。我们要构建一个能**写 SQL 查库、写 Python 分析、画图**的超级助理。

#### 1\. 为什么这个 Agent 很强？（工具设计的艺术）

它没有使用通用的“全能工具”，而是将功能**原子化**拆解。这体现了 Agent 开发的一个重要原则：**工具定义得越具体，LLM 发挥越稳定。**

我们要解决的具体场景是：用户给出一个自然语言指令（如“画个图看看用户流失率”），Agent 自动操作数据库并画图。

#### 2\. 四大核心工具详解

| 工具名称 | 就像是... | 具体功能与代码细节 |
| :--- | :--- | :--- |
| **`sql_inter`** | **档案管理员** | **只负责查**。它执行 `SELECT` 语句，返回 JSON 数据。告诉 LLM：想看数据长什么样，用我。 |
| **`extract_data`** | **搬运工** | **只负责搬**。它执行 SQL，然后把结果读取为 **Pandas DataFrame** 并存入 Python 全局变量。告诉 LLM：想做后续分析，先用我把数据搬到内存里。 |
| **`python_inter`** | **计算器** | **只负责算**。执行非绘图的 Python 代码。比如计算平均值、方差。它会检查变量是否重复赋值。 |
| **`fig_inter`** | **画家** | **只负责画**。这是最关键的工具。它执行 `matplotlib/seaborn` 代码。\*\*注意点：\*\*为了让前端能看到图，它必须把图保存为物理文件（`.png`），并存放在前端项目的 `public` 目录下。 |

#### 3\. 关键代码解析：画家工具 (`fig_inter`)

这是最容易出错的地方，请看这段逻辑的精妙之处：

```python
# 1. 切换后端，防止在服务器端弹出窗口报错
matplotlib.use('Agg') 

# 2. 动态获取变量
# 这一步是为了让 LLM 生成的代码中定义的 fig 变量能被我们捕获
g = globals()
exec(py_code, g, local_vars) 
fig = local_vars.get(fname, None)

# 3. 路径映射
# 绝对路径：给 Python 保存文件用
# 相对路径：给前端 HTML 展示用
abs_path = os.path.join(images_dir, image_filename) 
rel_path = os.path.join("images", image_filename) 

# 4. 保存并返回路径
fig.savefig(abs_path)
return f"图片已保存，路径为: {rel_path}" 
```

**解释：** Agent 本身看不见图，它只需要知道“图画好了，放在了地址 X”。前端 UI 拿到地址 X 后，通过 Markdown 渲染把图展示给用户。

-----

### 第四部分：前后端联调（最后一块拼图）

现在后端（大脑）已经通过 `langgraph dev` 跑起来了，我们需要前端（脸面）。

1.  **Agent Chat UI**：这是官方提供的一个 Next.js 项目。
2.  **配置**：你需要把前端指向你的后端端口（通常是 `localhost:xxxx`）。
3.  **图像显示原理**：
      * Agent 后端把图片生成在前端项目的 `public/images` 文件夹下。
      * Agent 返回的消息里包含 `![图](images/fig.png)`。
      * 前端解析 Markdown，直接从自己的目录下读取图片显示。

-----

### 总结与核心知识点回顾

1.  **开发流程进化**：从单文件脚本 -\> 模块化项目（`agent.py` + `langgraph.json`）。
2.  **可视化调试**：**LangGraph Studio** 是开发复杂 Agent 的神器，它能让你看见思维链条的断裂处。
3.  **工具隔离原则**：在 Data Agent 中，我们将“查数据”、“存数据”、“算数据”、“画图”拆分为四个独立的工具。**各司其职**比**身兼数职**更稳定。
4.  **多模态交互技巧**：Agent 生成图片本质上是\*\*“代码生成 + 文件保存 + 路径返回”\*\*的过程。

通过这套流程，你就拥有了一个可以部署给真实用户使用的、具备企业级数据分析能力的 AI 智能体了。

这是一份非常详尽、含金量极高的企业级 Agent 开发课程。这份资料的核心价值在于它跨越了“写代码”到“工程化落地”的鸿沟。

为了让你能够透彻理解，我将这份杂乱的资料重构为一套**系统的学习路径**。我们将遵循\*\*“从具体场景（例子）出发，抽象出技术原理，最后落实到每一行核心代码”\*\*的逻辑进行讲解。

-----

# 课程核心：LangGraph 智能体开发与上线实战

本课程主要解决两个核心问题：

1.  **工程化套件**：如何使用专业的工具监控、调试和部署 Agent？（告别盲人摸象）
2.  **复杂业务落地**：如何构建一个能查库、能分析、能画图的“数据分析专家”？（Data Agent 实战）

-----

## 第一模块：Agent 军火库——核心开发套件详解

在开发复杂的 Agent 时，我们不仅需要 Python 库，还需要一套“IDE（集成开发环境）”。LangChain 1.0 提供了三个核心工具，我们可以用\*\*“现代厨房”\*\*来类比它们的关系。

### 1.1 LangSmith：全链路监控（厨房里的摄像头与黑匣子）

  * **具体场景**：你的 Agent 回答错了，用户很生气。以前你只能靠打印 `print` 日志去猜哪里错了。现在，你想看到：是用户问题没问对？还是检索没搜到数据？还是大模型推理逻辑断了？
  * **核心概念**：**LLM 工作流全生命周期平台**。
      * **Trace（追踪）**：记录每一次 Chain 的调用链路，像 X 光一样透视执行过程。
      * **Evaluation（评估）**：批量测试。比如上线前跑 100 个测试题，看准确率是否下降。
      * **Prompt Registry（Prompt 管理）**：版本控制你的提示词（v1.0, v1.1...）。

### 1.2 LangGraph Studio：可视化调试台（可视化中控大屏）

  * **具体场景**：Agent 的逻辑很复杂，像迷宫一样。单纯看代码很难想象它怎么跳跃。
  * **核心概念**：**图结构可视化 IDE**。
      * 它能根据你的代码自动生成流程图。
      * **实时交互**：你可以在图上输入“你好”，看着光标在节点间流动，哪一步卡住了，一目了然。

### 1.3 LangGraph CLI：工程化部署工具（启动钥匙）

  * **具体场景**：代码写好了，怎么变成一个 API 服务让前端调用？怎么在云端运行？
  * **核心概念**：**命令行接口**。
      * `langgraph init`：初始化标准项目结构（不再是乱糟糟的文件）。
      * `langgraph dev`：本地启动 API 服务器 + Studio 调试界面。
      * `langgraph deploy`：未来的一键上云。

-----

## 第二模块：构建标准化 Agent 项目（手把手代码解析）

传统的 `demo.py` 无法满足生产需求。LangGraph 定义了严格的**项目目录规范**。

### 2.1 标准目录结构

一个合规的 Agent 项目必须包含以下文件：

```text
my-agent-project/
├── agent.py            # 【大脑】核心逻辑：定义图(Graph)、工具(Tools)、状态(State)
├── langgraph.json      # 【地图】配置文件：告诉 CLI 去哪里找图，依赖什么配置
├── requirements.txt    # 【清单】依赖包列表
└── .env                # 【钥匙】环境变量：API Key，数据库密码（绝不硬编码！）
```

### 2.2 核心配置文件：langgraph.json

这是 CLI 能够运行项目的关键。

```json
{
  "dependencies": ["./"],          // 依赖查找路径
  "graphs": {
    "chatbot": "./agent.py:graph"  // 核心映射：服务名 -> 文件名:变量名
  },
  "env": ".env"                    // 环境变量文件路径
}
```

-----

## 第三模块：【重难点】打造智能数据分析助手 (Data Agent)

这是本课程最精华的代码实战。我们要构建一个 Agent，它不仅能聊天，还能连接 MySQL 数据库，读取数据，并用 Python 画图展示。

### 3.1 核心设计哲学：工具原子化 (Tool Atomization)

**具体例子**：如果你给 Agent 一个“全能工具”，它很容易晕头转向。
**抽象概念**：我们将复杂的任务拆解为四个**原子工具**，各司其职。

1.  **sql\_inter**：只负责**查**（SELECT）。
2.  **extract\_data**：只负责**搬**（把数据搬到内存）。
3.  **python\_inter**：只负责**算**（纯计算）。
4.  **fig\_inter**：只负责**画**（可视化）。

### 3.2 深度代码解析（逐行讲解）

#### 工具一：MySQL 查询工具 (`sql_inter`)

**作用**：让 Agent 知道数据库里有什么表，表结构是什么。

```python
# 使用 Pydantic 定义输入结构，这对 LLM 准确调用工具至关重要
class SQLQuerySchema(BaseModel):
    sql_query: str = Field(description="SQL查询语句...")

@tool(args_schema=SQLQuerySchema)
def sql_inter(sql_query: str) -> str:
    """
    负责执行 SQL 语句并返回结果字符串。
    注意：这里返回的是 JSON 字符串，因为 LLM 只能读文本。
    """
    # 1. 连接数据库（配置从环境变量读取，安全！）
    connection = pymysql.connect(...) 
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql_query)
            results = cursor.fetchall() # 获取所有结果
    finally:
        connection.close() # 必须关闭连接

    # 2. 序列化：把数据库里的行数据变成字符串给 LLM 看
    return json.dumps(results, ensure_ascii=False)
```

#### 工具二：数据提取工具 (`extract_data`)

**作用**：查询返回的只是文本，没法做数学分析。这个工具把数据加载为 Pandas DataFrame，存入 Python 的内存中。

```python
@tool(args_schema=ExtractQuerySchema)
def extract_data(sql_query: str, df_name: str) -> str:
    """
    将 SQL 结果保存为 Python 全局变量（DataFrame）。
    """
    # ... 连接数据库代码省略 ...
    
    # 1. Pandas 直接读取 SQL
    df = pd.read_sql(sql_query, connection)
    
    # 2. 【关键技巧】使用 globals()
    # 这一步将 DataFrame 挂载到了全局变量里。
    # 这样后续的 python_inter 工具就可以直接用 df_name 这个变量名来操作数据了。
    globals()[df_name] = df
    
    return f"✅ 成功创建 pandas 对象 `{df_name}`"
```

#### 工具三：可视化绘图工具 (`fig_inter`) —— **最复杂的部分**

**难点**：Agent 运行在后端（服务器），它没法弹出一个窗口显示图片。它必须把图片保存为文件，然后告诉前端图片在哪里。

```python
@tool(args_schema=FigCodeInput)
def fig_inter(py_code: str, fname: str) -> str:
    # 1. 【后端设置】切换 matplotlib 后端为 'Agg'
    # 这是一个非交互式后端，专门用于生成图片文件，防止服务器端报错。
    current_backend = matplotlib.get_backend()
    matplotlib.use('Agg') 

    # 2. 路径配置（这是前后端联调的痛点）
    # base_dir 必须指向前端项目的 public 目录，否则浏览器访问不到图片
    base_dir = r"C:\...\agent-chat-ui\public" 
    images_dir = os.path.join(base_dir, "images")

    try:
        # 3. 执行绘图代码
        g = globals()
        # 把 plt, sns 等库注入进去，让 LLM 生成的代码能用
        exec(py_code, g, {"plt": plt, "pd": pd, "sns": sns})
        
        # 4. 获取图像对象并保存
        fig = local_vars.get(fname, None)
        if fig:
            # 保存物理文件（绝对路径）
            fig.savefig(abs_path, bbox_inches='tight')
            # 返回相对路径（给前端 HTML 用）
            return f"✅ 图片已保存，路径为: {rel_path}"
            
    finally:
        plt.close('all') # 【重要】清理内存，防止图片画多了撑爆服务器
```

### 3.3 Agent 的大脑：System Prompt

代码写好了，如何让 LLM 听懂？Prompt 是关键。

```python
prompt = """
你是一名数据分析助手...
策略：
1. 先用 sql_inter 看看有什么数据。
2. 再用 extract_data 把数据提取为 DataFrame。
3. 最后用 fig_inter 画图。

重要要求：
- 如果生成了图片，必须在回答中用 Markdown 格式插入：![描述](图片路径)
- 不要只给路径，要让用户直接看到图。
"""
```

-----

## 第四模块：部署与前端交互

当后端通过 `langgraph dev` 启动后，你拥有了一个 API 服务。现在我们需要一个漂亮的界面。

### 4.1 Agent Chat UI

LangChain 官方提供的开源前端项目。

  * **原理**：它是一个 Next.js 网页应用，连接你的 LangGraph 后端。
  * **配置**：需要设置 `.env` 文件，指向后端的 URL（通常是 `localhost`）。
  * **核心流程**：
    1.  用户在 UI 提问。
    2.  UI 发送请求给 Backend。
    3.  Backend (Agent) 思考 -\> 查库 -\> 画图 -\> 保存图片到 `public/images`。
    4.  Backend 返回 Markdown `![图](/images/fig.png)`。
    5.  UI 解析 Markdown，去 `public/images` 加载图片展示给用户。

-----

## 总结：如何学习这套课程？

我建议你按照以下步骤消化这些内容：

1.  **先跑通环境**：不要急着写代码。先安装 `langgraph-cli`，把示例代码 `langgraph dev` 跑起来，确保能在 Studio 里看到图。
2.  **理解数据流**：在 Studio 里输入一个问题，观察数据是怎么在 Graph 节点之间流动的。
3.  **死磕 Data Agent**：重点研究 `fig_inter` 工具的实现。尝试修改图片保存路径，看看前端会发生什么（通常图就挂了），以此理解前后端资源映射的关系。
4.  **自定义扩展**：试着把 MySQL 换成 Excel 读取，或者增加一个“发送邮件报告”的工具。

这套体系学完，你就掌握了目前市面上最先进的 Agent 工程化开发能力。


# Part 6.LangChain Agent中间件入门介绍


你好！这份关于 **LangChain 1.0 Agent 中间件 (Middleware)** 的课程内容非常有价值，它展示了 Agent 开发从“简单调用”向“工程化控制”进阶的关键技术。

根据你的学习偏好（喜欢先看具体例子再抽象概念），我将这份资料整理为四个核心模块，结合代码实例详细讲解中间件如何通过“挂钩子”的方式，实现对 Agent 的**动态路由、记忆压缩**和**安全风控**。

-----

### 课程核心：LangChain 1.0 中间件 (Middleware)

#### 1\. 什么是中间件？(核心概念)

在 LangChain 1.0 之前，Agent 像一个黑盒，输入问题，输出结果。中间件的引入，就像在 Agent 的执行流水线上安装了多个“检查站”和“控制台”。

**它的核心逻辑是：** 在不修改 Agent 主逻辑代码的前提下，通过**钩子 (Hooks)** 介入执行流程。

  * **Before Model (调用前):** 检查输入、压缩历史、权限验证。
  * **Modify Model Request (请求修改):** 偷梁换柱，换模型、改参数。
  * **After Model (调用后):** 审查结果、格式修正、日志记录。
  * **Wrap Model/Tool Call (整体包裹):** 增加重试机制、熔断、人工审批。

**功能速查表：**

| 功能 | 常用钩子 | 典型应用场景 |
| :--- | :--- | :--- |
| **监控/日志** | `before_model`, `after_model` | 记录 Token 消耗、跟踪调用路径 |
| **动态路由** | `wrap_model_call` | 根据问题难度切换 DeepSeek-Chat / Reasoner |
| **上下文工程** | `before_model` | 消息裁剪、自动摘要、注入系统提示词 |
| **流程控制** | `wrap_model_call` | 自动重试、超时处理、降级方案 |
| **合规/风控** | `after_model`, `wrap_tool_call` | PII (敏感信息) 检测、人工审核 (HITL) |

-----

#### 2\. 实战应用一：模型动态选择 (Dynamic Routing)

**场景例子：**
用户问：“你好” -\> 用便宜快读的 `deepseek-chat`。
用户问：“推导这个微积分公式” -\> 用昂贵且慢的 `deepseek-reasoner`。

**代码实现逻辑：**
这里使用了 `wrap_model_call` 钩子，它把模型调用“包”了起来，在真正发送请求前，根据输入内容决定用哪个模型。

```python
@wrap_model_call
def dynamic_deepseek_routing(request: ModelRequest, handler) -> ModelResponse:
    # 1. 获取当前上下文信息
    messages = request.state.get("messages", [])
    last_user = _get_last_user_text(messages)
    
    # 2. 定义判断“复杂问题”的规则 (启发式 Heuristics)
    hard_keywords = ("证明", "推导", "规划", "chain of thought", "逻辑证明")
    is_hard = (
        len(messages) > 10 or           # 历史太长
        len(last_user) > 120 or         # 问题太长
        any(kw in last_user for kw in hard_keywords) # 命中关键词
    )

    # 3. 动态替换模型 (核心步骤)
    # 如果是难题，强行将 request.model 替换为 reasoner_model
    request.model = reasoner_model if is_hard else basic_model
    
    # 4. 放行，执行真正的调用
    return handler(request)
```

**效果：**

  * 当用户让其自我介绍时，命中简单规则，DeepSeek-Chat 秒回。
  * 当用户要求“推导速度与时间函数关系”时，命中 `hard_keywords`，DeepSeek-Reasoner 启动，输出了包含 `step-by-step` 的详细推理过程。

-----

#### 3\. 实战应用二：消息压缩 (Context Management)

随着对话进行，Token 会无限膨胀。中间件提供了三种不同维度的解决方案：

##### A. 修剪 (Trimming) - 简单粗暴

**逻辑：** 只保留最近的 N 条，之前的全扔掉。
**钩子：** `@before_model`
**代码解析：**

```python
@before_model
def trim_messages(state: AgentState, runtime: Runtime):
    messages = state["messages"]
    if len(messages) <= 4: return None
    
    # 保留第1条(System Prompt) + 最后3条
    # RemoveMessage(id=REMOVE_ALL_MESSAGES) 是 LangGraph 的特殊指令，用于清空旧状态
    return {
        "messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), messages[0]] + messages[-3:]
    }
```

  * **优点：** 极快，成本低。
  * **缺点：** 容易丢失早期的重要指令或信息。

##### B. 删除 (Deleting) - 精确手术

**逻辑：** 每次对话后，精准删除特定的旧消息（如由中间件自动清理最早的2条）。
**钩子：** `@after_model` (在模型回复后清理，为下一轮做准备)
**代码解析：**

```python
@after_model
def delete_old_messages(state: AgentState, runtime: Runtime):
    # 如果消息堆积超过4条，就删除最早的2条
    if len(messages) > 4:
        # 返回 RemoveMessage 对象列表，精准删除指定 ID 的消息
        return {"messages": [RemoveMessage(id=m.id) for m in messages[:2]]}
```

  * **优点：** 适合长周期运行的系统，防止上下文爆炸。

##### C. 汇总 (Summarization) - 智能压缩

**逻辑：** 不删除历史，而是把旧历史“浓缩”成一段摘要。
**实现：** 直接使用 `SummarizationMiddleware`。

```python
SummarizationMiddleware(
    model=summary_model,             # 用一个小模型来做总结
    max_tokens_before_summary=3000,  # 阈值：超过 3000 Token 就触发
    messages_to_keep=10              # 保留最近 10 条原话，之前的都变成 Summary
)
```

  * **优点：** 兼顾了上下文的连贯性和 Token 效率，是目前最推荐的长对话方案。

-----

#### 4\. 实战应用三：人在闭环 (Human-in-the-Loop)

**场景例子：** Agent 要执行 SQL 删除操作，或者要通过 Tavily 搜索联网。为了安全，必须让人类确认。

**代码实现逻辑：**
使用 `HumanInTheLoopMiddleware` 拦截工具调用。

```python
HumanInTheLoopMiddleware(
    interrupt_on={
        # 拦截名为 "tavily_search_results_json" 的工具
        "tavily_search_results_json": {
            "allowed_decisions": ["approve", "edit", "reject"], # 允许的操作
            "description": ... # 给审核员看的提示
        }
    }
)
```

**执行流程：**

1.  用户提问。
2.  模型决定调用搜索工具。
3.  **中间件拦截！** 程序暂停，返回 `__interrupt__` 状态。
4.  人类在 UI 上看到请求，点击 "Approve" (批准)。
5.  Agent 继续执行搜索并返回结果。

-----

### 总结

这份课程清晰地展示了 **LangChain 1.0 中间件** 的强大之处：它将 Agent 从“玩具”变成了“生产级应用”。

  * **解耦：** 业务逻辑（Prompt/Model）与 控制逻辑（重试/日志/风控）分离。
  * **灵活：** 像搭积木一样，可以随意组合“路由”、“压缩”、“审核”等模块。
  * **可观测与可控：** 你终于可以完全掌控 Agent 每一个步骤在做什么，而不是盲目信任大模型。

你好，Severin (叶博韬)。

这份关于 **LangChain 1.0 Agent 中间件 (Middleware)** 的课程资料非常硬核，它标志着 Agent 开发从“写 Prompt”进阶到了“系统工程化”的阶段。

根据你“先看例子，再抽象概念”的学习偏好，我将这份资料重新拆解。我们将从具体的业务场景出发，通过代码逐行解析，最后升华到架构层面的理解。

-----

### 第一部分：核心概念——什么是中间件？

想象一下，没有中间件的 Agent 就像一个\*\*“裸奔”的员工\*\*：你给他一个任务，他直接去干，干完给你结果。中间过程你无法插手，要么干得太慢（用了太贵的模型），要么干错了（说了不该说的话），要么记性太差（上下文爆炸）。

**中间件 (Middleware)** 就像是给这个员工配了一组\*\*“监工”和“秘书”\*\*：

1.  **秘书 (Before Model)**：在员工干活前，先把资料整理好（压缩上下文），把老板的叮嘱加上（注入 Prompt）。
2.  **调度员 (Wrap Model)**：看任务难易程度，简单的给实习生（小模型）干，难的给专家（大模型）干。
3.  **质检员 (After Model)**：员工干完活，检查一下有没有违规内容，或者把结果格式化一下再发出去。
4.  **安全员 (HITL)**：当员工要执行危险动作（如删库、发邮件）时，按住暂停键，等老板（你）签字确认。

#### 核心钩子 (Hooks) 机制

LangChain 1.0 通过在生命周期的特定位置“挂钩子”来实现这些功能：

  * `before_model`: **模型调用前**。用于修改输入（如上下文裁剪）。
  * `modify_model_request`: **请求构建时**。用于修改发给 API 的参数（如改 temperature，改 model\_name）。
  * `after_model`: **模型返回后**。用于检查或修改输出结果。
  * `wrap_model_call`: **包裹整个模型调用**。像一个壳子，可以决定是否真的调用模型，或者换个模型调用（动态路由）。
  * `wrap_tool_call`: **包裹工具调用**。用于工具层面的风控。

-----

### 第二部分：实战场景详解

#### 场景 1：模型动态选择 (智能路由)

**业务痛点：**
一直用 GPT-4o/DeepSeek-Reasoner 太贵且慢，一直用 DeepSeek-Chat 处理复杂逻辑又不够聪明。我们希望“杀鸡用鸡刀，宰牛用牛刀”。

**代码深度解析：**

```python
# 引入装饰器和类型定义
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse

# 定义两个模型实例
basic_model = ChatDeepSeek(model="deepseek-chat")        # "实习生"：快、省钱
reasoner_model = ChatDeepSeek(model="deepseek-reasoner") # "专家"：推理强、贵

# === 核心逻辑：定义中间件 ===
@wrap_model_call  # 使用 wrap 钩子，因为它要决定使用哪个模型实例
def dynamic_deepseek_routing(request: ModelRequest, handler) -> ModelResponse:
    """
    根据对话复杂度动态选择 DeepSeek 模型
    """
    # 1. 获取上下文状态
    messages = request.state.get("messages", [])
    msg_count = len(messages)
    
    # 2. 获取最近一条用户的输入（辅助函数 _get_last_user_text 用于提取文本）
    last_user = _get_last_user_text(messages)
    
    # 3. 定义“困难任务”的关键词库
    hard_keywords = ("证明", "推导", "严谨", "规划", "chain of thought", "数学")

    # 4. 启发式规则判断 (Heuristics)：满足任一条件即视为复杂任务
    is_hard = (
        msg_count > 10 or           # 历史对话太长，需要强记忆
        len(last_user) > 120 or     # 问题描述很长，通常细节多
        any(kw in last_user for kw in hard_keywords) # 命中关键词
    )

    # 5. 【关键动作】动态替换模型
    # 如果是困难模式，将 request 中的 model 属性强行替换为 reasoner_model
    request.model = reasoner_model if is_hard else basic_model
    
    # 打印日志方便调试
    print(f"当前任务难度判定: {'困难' if is_hard else '简单'} -> 使用模型: {request.model.model_name}")

    # 6. 放行：执行原本的调用流程（但此时模型可能已经变了）
    return handler(request)

# === 在 Agent 中启用 ===
agent = create_agent(
    model=basic_model, # 默认给一个模型
    tools=tools,  
    middleware=[dynamic_deepseek_routing] # 注入我们写的中间件
)
```

**原理解析：**
这个中间件截获了即将发出的请求，在毫秒级的时间内分析了你的意图，然后悄悄把“执行者”换掉了。用户无感，但效果和成本得到了双重优化。

-----

#### 场景 2：消息压缩 (记忆管理)

**业务痛点：**
大模型有上下文长度限制（Context Window），而且输入越长越贵。如果不管理历史记录，聊几十轮后就会报错或变笨。

课程介绍了三种策略，我们来详细对比：

| 策略 | 英文名 | 钩子类型 | 逻辑 | 适用场景 | 优点 | 缺点 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **修剪** | Trimming | `before_model` | 类似“滑动窗口”，只留最后 N 条 | 闲聊、即时问答 | 极快，不消耗 Token | 丢失早期记忆 |
| **删除** | Deleting | `after_model` | 主动清理垃圾，删除特定旧消息 | 任务型 Bot | 精准控制 | 实现较繁琐 |
| **汇总** | Summarization | 专用中间件 | 把旧消息压缩成一段摘要 | 长期陪伴、复杂项目 | 记忆保留最好 | 需额外调用模型(费钱) |

**1. 修剪 (Trimming) 代码详解：**

```python
@before_model
def trim_messages(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    messages = state["messages"]

    # 只有消息堆积到一定程度（>4条）才开始剪
    if len(messages) <= 4:
        return None

    # 策略：保留第1条(通常是System Prompt，不能删) + 最近3条
    first_msg = messages[0]
    new_messages = [first_msg] + messages[-3:]

    # 返回新的状态更新
    # RemoveMessage(id=REMOVE_ALL_MESSAGES) 是 LangGraph 的特殊指令
    # 它的作用是：先清空当前所有消息，然后用 new_messages 填充
    return {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES), 
            *new_messages
        ]
    }
```

**2. 汇总 (Summarization) 代码详解：**

```python
# 直接使用官方封装好的中间件
from langchain.agents.middleware import SummarizationMiddleware

agent = create_agent(
    model=main_model,
    tools=[],
    middleware=[
        SummarizationMiddleware(
            model=summary_model,             # 用一个小模型(如 deepseek-chat)来写摘要
            max_tokens_before_summary=3000,  # 阈值：Token 超过 3000 时触发
            messages_to_keep=10,             # 策略：保留最近 10 条原文，之前的全压缩
        )
    ],
    checkpointer=checkpointer, # 必须配合持久化存储，否则摘要没地方存
)
```

  * **抽象理解**：这就像写会议纪要。会议太长了（Token 太多），秘书（Summary Model）把前半截会议总结成“讨论了季度预算”，只保留现在的对话原文。

-----

#### 场景 3：人在闭环 (Human-in-the-Loop)

**业务痛点：**
Agent 如果能自动联网、删改数据库、发邮件，它可能会因为幻觉干出蠢事（比如把客户数据删了）。我们需要一个“确认按钮”。

**代码深度解析：**

```python
from langchain.agents.middleware import HumanInTheLoopMiddleware

# 配置 HITL 中间件
hitl_middleware = HumanInTheLoopMiddleware(
    interrupt_on={
        # 针对特定工具进行拦截
        "tavily_search_results_json": {
            # 允许人类做的操作：批准、修改参数、直接拒绝
            "allowed_decisions": ["approve", "edit", "reject"],
            
            # 动态生成描述，让人类知道 Agent 想干嘛
            "description": lambda tool_name, tool_input, state: (
                f"🔍 模型准备执行 Tavily 搜索：'{tool_input.get('query', '')}'"
            ),
        }
    },
    description_prefix="⚠️ 工具执行需要人工审批"
)

agent = create_agent(
    ...,
    middleware=[hitl_middleware]
)
```

**执行流程（抽象）：**

1.  **用户**：2024年诺贝尔奖是谁？
2.  **Agent**：我不知道，我要查 `tavily_search`。
3.  **中间件**：🛑 **暂停！** 触发 `interrupt`。系统挂起，返回状态给前端。
4.  **前端界面**：显示“Agent 想要搜索 '2024 诺贝尔'，是否批准？”
5.  **用户**：点击【批准】。
6.  **Agent**：收到信号，继续执行搜索，获取结果。

-----

### 第三部分：总结与抽象

通过这三个具体的实战例子，我们可以总结出 LangChain 1.0 中间件架构的精髓：

1.  **解耦 (Decoupling)**：Agent 的核心逻辑（思考、推理）与 辅助逻辑（日志、风控、记忆管理）完全分离。这让代码更干净。
2.  **可观测性 (Observability)**：你不再是盲目地跑模型，而是可以通过钩子清楚地看到每一步的状态、Token 消耗和工具调用。
3.  **控制力 (Control)**：从“完全自动驾驶”变成了“辅助驾驶”。你可以随时接管方向盘（HITL），或者根据路况切换驾驶模式（动态路由）。

