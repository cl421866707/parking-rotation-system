# 停车轮换抽签系统

部门停车位轮换抽签：默认 **5 人 / 3 车位**（园区 2 + 公园 1），半年一轮。支持必中池、轮空池、候选池抽签，历史记录与撤销，配置与数据以本地 JSON 持久化。

技术栈：Python 3.11 + Flask，前端为原生 HTML / CSS / JS。

---

## 环境要求

- Python **3.8+**（推荐 **3.11**）
- 依赖见 [`requirements.txt`](requirements.txt)（当前为 Flask）
- 可选：Docker / Docker Buildx（用于镜像构建，含 amd64 / arm64）

---

## 本地运行（不使用 Docker）

### 1. 安装依赖

**Windows PowerShell**

```powershell
cd D:\Project\Local\PycharmProjects\parking-rotation-system
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Linux / macOS（Shell）**

```bash
cd /path/to/parking-rotation-system
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

国内网络可改用清华源：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
```

### 2. 启动服务

```bash
python app.py
```

默认监听 `0.0.0.0:5000`。浏览器打开：

http://127.0.0.1:5000

可用环境变量覆盖：

| 变量 | 默认 | 说明 |
|------|------|------|
| `HOST` | `0.0.0.0` | 监听地址 |
| `PORT` | `5000` | 端口 |

**PowerShell 示例**

```powershell
$env:HOST = "127.0.0.1"; $env:PORT = "5000"; python app.py
```

**Shell 示例**

```bash
HOST=127.0.0.1 PORT=5000 python app.py
```

### 3. 数据与配置

| 文件 | 作用 |
|------|------|
| [`settings.json`](settings.json) | 指定数据目录，默认 `"data_dir": "data"` |
| `data/app_config.json` | 参与人姓名、车位显示名、规则文案 |
| `data/state.json` | 当前连胜 / 轮空状态与本轮结果 |
| `data/history.json` | 抽签历史（可撤销最近一次） |

页面分为三个 Tab：**抽签**、**历史记录**（可按日期筛选）、**系统设置**。

---

## Docker 使用

镜像基于 Python 3.11-slim（DaoCloud 代理拉取），pip 使用清华源，适合中国大陆构建。

镜像名示例：`parking-rotation:3.11`

### 当前平台单架构构建

在项目根目录执行。

**Windows PowerShell**

```powershell
cd D:\Project\Local\PycharmProjects\parking-rotation-system
docker build -t parking-rotation:3.11 .
```

**Linux / macOS（Shell）**

```bash
cd /path/to/parking-rotation-system
docker build -t parking-rotation:3.11 .
```

### 指定架构构建（amd64 / arm64）

需启用 Buildx：

```bash
docker buildx version
docker buildx create --name multiarch --use
```

若已有 builder，可直接：

```bash
docker buildx use multiarch
```

#### 仅构建 amd64

**PowerShell**

```powershell
docker buildx build --platform linux/amd64 -t parking-rotation:3.11-amd64 --load .
```

**Shell**

```bash
docker buildx build --platform linux/amd64 -t parking-rotation:3.11-amd64 --load .
```

#### 仅构建 arm64

**PowerShell**

```powershell
docker buildx build --platform linux/arm64 -t parking-rotation:3.11-arm64 --load .
```

**Shell**

```bash
docker buildx build --platform linux/arm64 -t parking-rotation:3.11-arm64 --load .
```

#### 一次构建多架构（推送到仓库）

`--load` 通常只能加载单一平台到本地；多架构需 `--push` 到镜像仓库。

**PowerShell**

```powershell
# 将 YOUR_REGISTRY 换成实际仓库前缀，例如 registry.cn-hangzhou.aliyuncs.com/yourns
$REG = "YOUR_REGISTRY/parking-rotation"
docker buildx build `
  --platform linux/amd64,linux/arm64 `
  -t "${REG}:3.11" `
  -t "${REG}:latest" `
  --push .
```

**Shell**

```bash
REG="YOUR_REGISTRY/parking-rotation"
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t "${REG}:3.11" \
  -t "${REG}:latest" \
  --push .
```

本地分别导出两个单架构镜像时，用上面的「仅构建 amd64 / arm64」各执行一次即可。

### 运行容器

将宿主机 `data` 目录挂载进容器，保证配置与历史持久化。

**Windows PowerShell**

```powershell
docker run -d `
  -p 5000:5000 `
  -v "${PWD}/data:/app/data" `
  --name parking `
  parking-rotation:3.11
```

**Linux / macOS（Shell）**

```bash
docker run -d \
  -p 5000:5000 \
  -v "$(pwd)/data:/app/data" \
  --name parking \
  parking-rotation:3.11
```

访问：http://127.0.0.1:5000

常用管理命令：

```bash
docker logs -f parking
docker stop parking
docker rm parking
```

在 Apple Silicon 上若要强制跑 amd64 镜像：

```bash
docker run -d --platform linux/amd64 -p 5000:5000 -v "$(pwd)/data:/app/data" --name parking parking-rotation:3.11-amd64
```

---

## 功能概要

- **抽签**：首轮全体随机抽 3 人；之后必中池（上轮未中）全进，候选池抽 1 人保留；连中两次下轮轮空
- **车位**：2 园区 + 1 公园（中签者中再随机分配）
- **录牌**：只展示姓名；园区可进 4 人 = 全体减去公园位中签者
- **历史**：记录分配前后三池与结果；支持按日期筛选、撤销最近一次
- **设置**：可改姓名、车位显示名、规则文案；人数与车位数量锁定为 5 / 3

---

## 目录结构

```text
parking-rotation-system/
  app.py                 # Flask 入口
  settings.json          # data_dir 配置
  requirements.txt
  Dockerfile
  .dockerignore
  lottery/               # 抽签引擎与 JSON 读写
  static/                # 前端
  data/                  # 业务 JSON（建议 Docker 挂载）
```

---

## 许可证

内部使用；按部门约定分发。
