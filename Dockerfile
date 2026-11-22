# 1. 基础镜像：以官方轻量级 Python 3.12 镜像作为地基
FROM python:3.12-slim

# 2. 设置容器内的工作目录为 /app
WORKDIR /app

# 3. 复制依赖文件并安装依赖包（使用国内镜像源加速）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 4. 复制后端代码和初始化 SQL 脚本
COPY backend/ ./backend/
COPY sql/ ./sql/

# 5. 声明容器内部服务监听 5000 端口
EXPOSE 5000

# 6. 容器启动时默认运行的命令
CMD ["python", "backend/app.py"]
