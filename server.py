"""
FastAPI 服务入口

提供游戏API和静态文件服务
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os

from backend.api.game_api import router as game_router
from backend.api.communication_api_v2 import router as comm_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print("[*] 文明架构师游戏服务启动中...")
    yield
    # 关闭时
    print("[*] 游戏服务已关闭")


app = FastAPI(
    title="文明架构师 API",
    description="Agent文明模拟策略游戏API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "message": "文明架构师服务运行正常"}


# 注册路由 - 先注册API路由
app.include_router(game_router, prefix="/api/v1/game", tags=["游戏控制"])
app.include_router(comm_router, prefix="/api/v1", tags=["通讯系统"])

# 静态文件服务（前端构建后的文件）- 最后注册，避免覆盖API路由
frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
print(f"[*] 前端静态文件路径: {frontend_dist}")
print(f"[*] 路径是否存在: {os.path.exists(frontend_dist)}")
if os.path.exists(frontend_dist):
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # 如果请求的是API路径，让API路由处理
        if full_path.startswith("api/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not Found")
        # 否则返回前端index.html
        index_file = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"detail": "Frontend not built"}
    
    print("[*] SPA 路由服务已启用")
else:
    print("[*] 警告: 前端静态文件目录不存在")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
