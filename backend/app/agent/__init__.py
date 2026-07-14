"""
智能体模块

Day 8:
- 单 Agent
- 检测 Tool 绑定
- SSE 流式输出

当前版本：
- 使用轻量规则路由选择 detect_single / detect_batch / detect_zip
- 不依赖外部 LLM API Key
- 后续可升级为 LangChain ReAct Agent
"""