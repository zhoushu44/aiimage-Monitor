# 网页监控可视化看板

这是一个基于 Flask 的网页监控可视化看板，用来监听 `http://129.226.153.254:5078`，采集目标服务的健康状态、系统资源、业务任务和 API 请求指标，并把 JSON 数据转换成带中文说明的可视化页面。

## 功能说明

- 监听目标服务：默认监听 `http://129.226.153.254:5078`
- 可视化展示：展示服务状态、响应耗时、CPU、内存、磁盘、运行时间等核心指标
- 中文指标说明：把 JSON 指标转换成中文名称、JSON 路径、当前值、单位和含义说明
- 原始数据查看：页面保留完整 JSON 快照，方便排查问题
- 自动刷新：页面每 5 秒自动重新采集目标数据

## 项目文件

```text
.
├── app.py                         # Flask 后端和可视化页面
├── requirements.txt               # Python 依赖
├── README.md                      # 项目说明
└── monitoring_standardization.md  # 监控规范文档
```

## 环境要求

- Python 3.10 或以上
- Windows PowerShell 或 PowerShell 7+
- 网络可以访问 `http://129.226.153.254:5078`

## 安装依赖

在项目目录执行：

```powershell
python -m pip install -r requirements.txt
```

依赖包括：

- Flask：提供后端接口和网页服务
- psutil：采集本地服务运行环境的系统指标

## 启动服务

在项目目录执行：

```powershell
$env:PORT="5078"
$env:TARGET_BASE_URL="http://129.226.153.254:5078"
python app.py
```

启动成功后会看到类似输出：

```text
* Running on http://127.0.0.1:5078
* Running on http://192.168.x.x:5078
```

## 访问地址

- 本地可视化看板：`http://127.0.0.1:5078/`
- 局域网可视化看板：`http://192.168.124.8:5078/`
- 目标快照接口：`http://127.0.0.1:5078/api/target/snapshot`
- 被监听目标服务：`http://129.226.153.254:5078`

## 被监听接口

看板会主动请求以下目标接口：

| 接口 | 用途 |
| --- | --- |
| `/api/health` | 获取服务健康状态、数据库、Redis、COS、任务队列状态 |
| `/api/metrics/system` | 获取 CPU、内存、磁盘、线程数、运行时间等系统指标 |
| `/api/metrics/business` | 获取任务总数、运行中任务、完成任务、失败任务、任务成功率等业务指标 |
| `/api/metrics/api` | 获取 API 请求总数、每分钟请求数、错误数、错误率等接口指标 |

## 看板接口

| 本地接口 | 说明 |
| --- | --- |
| `/` | 可视化页面 |
| `/api/target/snapshot` | 聚合目标服务的 JSON 快照，并附带中文指标说明 |
| `/api/health` | 看板自身健康检查 |
| `/api/health/detail` | 看板自身详细健康检查 |
| `/api/metrics/system` | 看板所在机器的系统指标 |
| `/api/metrics/business` | 看板自身请求统计 |
| `/api/metrics/api` | 看板自身 API 调用统计 |

## JSON 指标中文说明

`/api/target/snapshot` 返回的 `metric_descriptions` 字段会包含具体指标说明。每个指标结构如下：

```json
{
  "name": "CPU 使用率",
  "path": "system.data.metrics.cpu_percent",
  "value": 0.0,
  "unit": "%",
  "scale": 1,
  "description": "服务器 CPU 当前使用比例，过高可能代表计算压力大。"
}
```

字段含义：

| 字段 | 中文说明 |
| --- | --- |
| `name` | 指标中文名称 |
| `path` | 指标在聚合 JSON 中的位置 |
| `value` | 当前采集到的指标值 |
| `unit` | 指标单位 |
| `scale` | 展示倍率，例如错误率、成功率会乘以 100 后显示为百分比 |
| `description` | 指标中文解释 |

## 当前支持的指标

| 中文名称 | JSON 路径 | 说明 |
| --- | --- | --- |
| 服务总体状态 | `health.data.status` | 目标服务当前健康状态 |
| 健康接口耗时 | `health.latency_ms` | 请求目标健康接口的耗时 |
| 数据库状态 | `health.data.checks.database.status` | 数据库连接是否正常 |
| 数据库延迟 | `health.data.checks.database.latency_ms` | 数据库检查耗时 |
| Redis 状态 | `health.data.checks.redis.status` | Redis 连接是否正常 |
| Redis 延迟 | `health.data.checks.redis.latency_ms` | Redis 检查耗时 |
| 对象存储状态 | `health.data.checks.cos.status` | COS/对象存储是否正常 |
| 任务队列活跃任务 | `health.data.checks.task_queue.active_tasks` | 当前活跃任务数量 |
| CPU 使用率 | `system.data.metrics.cpu_percent` | 服务器 CPU 使用比例 |
| 内存使用率 | `system.data.metrics.memory_percent` | 服务器内存使用比例 |
| 磁盘使用率 | `system.data.metrics.disk_percent` | 服务器磁盘空间使用比例 |
| 内存总量 | `system.data.metrics.memory_total_mb` | 服务器内存总容量 |
| 已用内存 | `system.data.metrics.memory_used_mb` | 已使用内存容量 |
| 运行时间 | `system.data.metrics.uptime_seconds` | 目标服务连续运行时间 |
| 活跃线程数 | `system.data.metrics.active_threads` | 当前活跃线程数量 |
| 任务总数 | `business.data.metrics.total_tasks` | 业务任务总数量 |
| 运行中任务 | `business.data.metrics.running_tasks` | 当前正在执行的任务数量 |
| 已完成任务 | `business.data.metrics.completed_tasks` | 已完成任务数量 |
| 失败任务 | `business.data.metrics.failed_tasks` | 失败任务数量 |
| 任务队列长度 | `business.data.metrics.task_queue_length` | 队列中等待或正在处理的任务数量 |
| 任务成功率 | `business.data.metrics.tasks_success_rate` | 任务成功完成比例 |
| API 请求总数 | `api.data.metrics.requests_total` | API 累计请求数量 |
| 每分钟请求数 | `api.data.metrics.requests_per_minute` | 当前 API 请求速率 |
| API 错误数 | `api.data.metrics.error_count` | API 错误数量 |
| API 错误率 | `api.data.metrics.error_rate` | API 请求失败比例 |

## 修改监听目标

如果需要监听其他地址，启动前修改环境变量：

```powershell
$env:TARGET_BASE_URL="http://你的服务器IP:端口"
python app.py
```

也可以直接修改 [app.py](file:///e:/360MoveData/Users/Administrator/Desktop/%E6%96%B0%E9%A1%B9%E7%9B%AE/app.py) 中的默认值：

```python
TARGET_BASE_URL = os.getenv("TARGET_BASE_URL", "http://129.226.153.254:5078").rstrip("/")
```

## 验证命令

检查看板是否正常：

```powershell
Invoke-WebRequest http://127.0.0.1:5078/ -UseBasicParsing
```

查看目标快照：

```powershell
Invoke-RestMethod http://127.0.0.1:5078/api/target/snapshot | ConvertTo-Json -Depth 8
```

只查看中文指标说明：

```powershell
$snapshot = Invoke-RestMethod http://127.0.0.1:5078/api/target/snapshot
$snapshot.metric_descriptions | Select-Object name,path,value,unit,description
```

## 注意事项

- 当前 Flask 启动方式适合本地测试和内网使用；生产部署建议使用 Waitress、Gunicorn 或其他 WSGI 服务。
- 如果公网无法访问看板，需要确认防火墙、安全组和端口映射是否放行 `5078`。
- 如果目标服务接口结构变化，需要同步更新 [app.py](file:///e:/360MoveData/Users/Administrator/Desktop/%E6%96%B0%E9%A1%B9%E7%9B%AE/app.py) 中的 `build_metric_descriptions` 指标映射。
- 页面中的原始 JSON 区域用于排查接口返回内容，中文指标卡片来自 `metric_descriptions` 字段。
