#!/bin/bash
set -e

echo "========================================="
echo "  Literature Review Agent - 部署脚本"
echo "========================================="

# -------------------- 检查环境 --------------------
echo ""
echo "[1/4] 检查环境..."

if ! command -v docker &>/dev/null; then
    echo "Docker 未安装，正在安装..."
    curl -fsSL https://get.docker.com | sh
    systemctl start docker
    systemctl enable docker
else
    echo "Docker 已安装: $(docker --version)"
fi

if ! docker compose version &>/dev/null; then
    echo "Docker Compose 未安装，请安装后重试"
    exit 1
fi
echo "Docker Compose 已安装"

# -------------------- 配置环境变量 --------------------
echo ""
echo "[2/4] 配置环境变量..."

if [ ! -f .env ]; then
    cp .env.docker .env
    echo "已从 .env.docker 创建 .env 文件"
else
    echo ".env 文件已存在，跳过"
fi

# 强制用户检查 API Key
DEEPSEEK_KEY=$(grep DEEPSEEK_API_KEY .env | cut -d= -f2)
if [ -z "$DEEPSEEK_KEY" ] || [ "$DEEPSEEK_KEY" = "sk-your-api-key-here" ]; then
    echo ""
    echo "!! 警告：DEEPSEEK_API_KEY 未填写或仍为默认值"
    echo "!! 请编辑 .env 文件中的 DEEPSEEK_API_KEY"
    read -p "!! 是否现在编辑？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ${EDITOR:-vim} .env
    else
        echo "跳过编辑，后续需要手动修改 .env"
    fi
fi

# -------------------- 拉取/构建镜像 --------------------
echo ""
echo "[3/4] 拉取并构建镜像..."

# 尝试拉取基础镜像（如果网络不通会走构建缓存）
docker pull mysql:8.0 2>/dev/null || echo "MySQL 镜像拉取超时，将使用已缓存镜像"
docker compose build

# -------------------- 启动服务 --------------------
echo ""
echo "[4/4] 启动服务..."

docker compose down 2>/dev/null
docker compose up -d

# -------------------- 等待就绪 --------------------
echo ""
echo "等待服务就绪..."
sleep 10

# 健康检查
echo ""
echo "========================================="
echo "  健康检查"
echo "========================================="

# MySQL
if docker compose exec mysql mysqladmin ping -h localhost -u root -p"${MYSQL_ROOT_PASSWORD:-root_password_123}" &>/dev/null; then
    echo "[✓] MySQL     - 运行正常"
else
    echo "[✗] MySQL     - 异常，请检查日志"
fi

# 后端
if curl -sf http://localhost:8000/health &>/dev/null; then
    echo "[✓] Backend   - 运行正常"
else
    echo "[✗] Backend   - 异常，请检查日志"
fi

# 前端
if curl -sf http://localhost:3000/ &>/dev/null; then
    echo "[✓] Frontend  - 运行正常"
else
    echo "[✗] Frontend  - 异常，请检查日志"
fi

# -------------------- 输出访问地址 --------------------
echo ""
echo "========================================="
echo "  部署完成！"
echo "========================================="
echo ""
echo "  访问地址: http://$(curl -s ip.sb 2>/dev/null || echo 'YOUR_IP'):3000"
echo "  API 文档: http://localhost:8000/docs"
echo ""
echo "  管理命令:"
echo "    docker compose ps          查看服务状态"
echo "    docker compose logs -f     查看实时日志"
echo "    docker compose restart     重启所有服务"
echo "    docker compose down        停止所有服务"
echo ""
