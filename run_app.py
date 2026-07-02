"""启动 OrderMind 本地 Web 应用。

开发阶段运行：
    python3 run_app.py

桌面应用打包后，Tauri/Electron 壳可以启动同样的本地服务，或直接复用
ordermind 包内的核心解析和校验能力。
"""

from ordermind.webapp import run


if __name__ == "__main__":
    run()
