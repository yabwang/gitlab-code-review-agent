#!/usr/bin/env python3
"""
Agent 启动脚本

支持启动单个 Agent 或全部 Agent

Usage:
    # 启动所有 Agent
    python scripts/start_agents.py --all

    # 启动单个 Agent
    python scripts/start_agents.py --agent coordinator --port 8080
    python scripts/start_agents.py --agent llm --port 8082
    python scripts/start_agents.py --agent security --port 8081
"""
import argparse
import asyncio
import logging
import multiprocessing
import os
import sys
import uvicorn

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Agent 配置
AGENTS = {
    "coordinator": {
        "class": "CoordinatorAgent",
        "module": "app.agents.coordinator",
        "default_port": 8080
    },
    "security": {
        "class": "SecurityAgent",
        "module": "app.agents.security_agent",
        "default_port": 8081
    },
    "llm": {
        "class": "LLMAgent",
        "module": "app.agents.llm_agent",
        "default_port": 8082
    }
}


def import_agent(agent_name: str):
    """动态导入 Agent 类"""
    config = AGENTS.get(agent_name)
    if not config:
        raise ValueError(f"Unknown agent: {agent_name}")

    module = __import__(config["module"], fromlist=[config["class"]])
    return getattr(module, config["class"])


async def start_agent(agent_name: str, port: int = None):
    """启动单个 Agent"""
    config = AGENTS.get(agent_name)
    if not config:
        raise ValueError(f"Unknown agent: {agent_name}")

    port = port or config["default_port"]

    # 动态导入并实例化 Agent
    AgentClass = import_agent(agent_name)
    agent = AgentClass()
    agent.port = port

    # 初始化 Agent
    settings = get_settings()
    await agent.initialize({
        "llm_provider": settings.LLM_PROVIDER,
        "llm_api_key": settings.LLM_API_KEY,
        "llm_api_url": settings.LLM_API_URL,
        "llm_model": settings.LLM_MODEL,
    })

    logger.info(f"启动 {agent.name} 在端口 {port}")

    # 启动 uvicorn
    uvicorn.run(
        agent.get_app(),
        host="0.0.0.0",
        port=port,
        log_level="info"
    )


def run_agent_process(agent_name: str, port: int = None):
    """在独立进程中运行 Agent"""
    config = AGENTS.get(agent_name)
    if not config:
        raise ValueError(f"Unknown agent: {agent_name}")

    port = port or config["default_port"]

    # 动态导入 Agent 类
    AgentClass = import_agent(agent_name)
    agent = AgentClass()
    agent.port = port

    # 获取配置（同步）
    settings = get_settings()
    agent_config = {
        "llm_provider": settings.LLM_PROVIDER,
        "llm_api_key": settings.LLM_API_KEY,
        "llm_api_url": settings.LLM_API_URL,
        "llm_model": settings.LLM_MODEL,
    }

    # 初始化 Agent（同步方式）
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(agent.initialize(agent_config))

    logger.info(f"启动 {agent.name} 在端口 {port}")

    # 启动 uvicorn（阻塞调用）
    uvicorn.run(
        agent.get_app(),
        host="0.0.0.0",
        port=port,
        log_level="info"
    )


def start_all_agents():
    """启动所有 Agent"""
    processes = []

    for agent_name, config in AGENTS.items():
        port = config["default_port"]
        p = multiprocessing.Process(
            target=run_agent_process,
            args=(agent_name, port),
            name=f"{agent_name}-agent"
        )
        p.start()
        processes.append((agent_name, p))
        logger.info(f"启动 {agent_name} Agent (PID: {p.pid}, 端口: {port})")

    # 等待所有进程
    try:
        for agent_name, p in processes:
            p.join()
    except KeyboardInterrupt:
        logger.info("收到终止信号，停止所有 Agent...")
        for agent_name, p in processes:
            p.terminate()
            logger.info(f"已停止 {agent_name} Agent")


def main():
    parser = argparse.ArgumentParser(description="启动 Agent 服务")
    parser.add_argument(
        "--all",
        action="store_true",
        help="启动所有 Agent"
    )
    parser.add_argument(
        "--agent",
        choices=list(AGENTS.keys()),
        help="启动指定的 Agent"
    )
    parser.add_argument(
        "--port",
        type=int,
        help="指定端口（仅在启动单个 Agent 时有效）"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出所有可用的 Agent"
    )

    args = parser.parse_args()

    if args.list:
        print("可用的 Agent:")
        for name, config in AGENTS.items():
            print(f"  - {name}: 端口 {config['default_port']}")
        return

    if args.all:
        start_all_agents()
    elif args.agent:
        port = args.port or AGENTS[args.agent]["default_port"]
        run_agent_process(args.agent, port)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()