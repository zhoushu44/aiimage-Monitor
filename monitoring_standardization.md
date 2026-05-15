# 监控系统标准化规则
![alt text](image.png)

## 1. 健康检查 API

### 1.1 基础健康检查
```
GET /api/health
```

响应格式：
```json
{
  "success": true,
  "status": "healthy",
  "timestamp": "2026-05-12T10:00:00Z",
  "checks": {
    "database": {"status": "up", "latency_ms": 5},
    "redis": {"status": "up", "latency_ms": 1},
    "cos": {"status": "up", "latency_ms": 0},
    "task_queue": {"status": "up", "active_tasks": 3}
  }
}
```

### 1.2 详细健康检查
```
GET /api/health/detail
```

响应格式：
```json
{
  "success": true,
  "status": "healthy",
  "timestamp": "2026-05-12T10:00:00Z",
  "checks": {
    "database": {"status": "up", "latency_ms": 5},
    "redis": {"status": "up", "latency_ms": 1},
    "cos": {"status": "up", "latency_ms": 0},
    "task_queue": {"status": "up", "active_tasks": 3}
  },
  "system": {
    "memory_used_mb": 512,
    "memory_total_mb": 2048,
    "memory_percent": 25,
    "cpu_percent": 15,
    "disk_percent": 10,
    "active_threads": 10
  }
}
```

---

## 2. 性能指标 API

### 2.1 系统指标
```
GET /api/metrics/system
```

响应格式：
```json
{
  "success": true,
  "metrics": {
    "uptime_seconds": 86400,
    "memory_used_mb": 512,
    "memory_total_mb": 2048,
    "memory_percent": 25,
    "cpu_percent": 15,
    "disk_used_gb": 10,
    "disk_total_gb": 100,
    "active_threads": 10,
    "active_connections": 50
  }
}
```

### 2.2 业务指标
```
GET /api/metrics/business
```

响应格式：
```json
{
  "success": true,
  "metrics": {
    "total_tasks": 100,
    "running_tasks": 3,
    "completed_tasks": 90,
    "failed_tasks": 7,
    "tasks_success_rate": 0.9,
    "task_queue_length": 3
  }
}
```

**说明：** 业务指标基于内存中的任务数据统计，不包含数据库查询。

### 2.3 API 指标
```
GET /api/metrics/api
```

响应格式：
```json
{
  "success": true,
  "metrics": {
    "requests_total": 10000,
    "requests_per_minute": 50.5,
    "error_count": 100,
    "error_rate": 0.01,
    "uptime_seconds": 86400
  }
}
```

**说明：** 使用 `@app.before_request` 和 `@app.after_request` 中间件统计请求数和错误数。

---

## 3. HertzBeat 集成配置

### 3.1 MCP 服务器概述

HertzBeat 启动时会自动在端口 `1157` 上启动 MCP（Model Context Protocol）服务器，提供 Streamable HTTP 协议的 MCP 服务，专为 AI Agent 集成和消费流式事件的客户端设计。

| 配置项 | 值 | 说明 |
|--------|-----|------|
| 协议 | Streamable HTTP (SSE) | MCP 传输协议 |
| 默认端口 | 1157 | MCP 服务端口 |
| 端点路径 | `/api/mcp` | MCP 连接 URL |
| 完整 URL | `http://{host}:1157/api/mcp` | 完整连接地址 |

### 3.2 MCP 身份验证

每次 MCP 请求必须使用以下方式之一进行身份验证：

#### 基本身份验证
```
Authorization: Basic <base64(username:password)>
```

### 3.3 Claude Code MCP 配置

方式一：使用 CLI 快速创建：
```bash
claude mcp add -s user -t http hertzbeat-mcp http://your-hertzbeat-server-host:1157/api/mcp --header "Authorization: Bearer your_jwt_key"
```

方式二：编辑 `~/.claude.json`，在 `mcpServers` 下添加：

JWT Bearer 认证：
```json
{
  "mcpServers": {
    "hertzbeat-mcp": {
      "type": "sse",
      "url": "http://your-hertzbeat-server-host:1157/api/mcp",
      "headers": {
        "Authorization": "Bearer <your-jwt-token>"
      }
    }
  }
}
```

Basic Auth 认证：
```json
{
  "mcpServers": {
    "hertzbeat-mcp": {
      "type": "sse",
      "url": "http://your-hertzbeat-server-host:1157/api/mcp",
      "headers": {
        "Authorization": "Basic <base64(username:password)>"
      }
    }
  }
}
```

保存后重启或重新加载 Claude Code 使配置生效。

### 3.4 Cursor MCP 配置

编辑 `.cursor/mcp.json`（用户目录或项目目录）：

JWT Bearer 认证：
```json
{
  "hertzbeat-mcp": {
    "url": "http://your-hertzbeat-server-host:1157/api/mcp",
    "headers": {
      "Authorization": "Bearer <your-jwt-token>"
    }
  }
}
```

Basic Auth 认证：
```json
{
  "hertzbeat-mcp": {
    "url": "http://your-hertzbeat-server-host:1157/api/mcp",
    "headers": {
      "Authorization": "Basic <base64(username:password)>"
    }
  }
}
```

保存后在 Cursor 中重新加载 MCP 或重启编辑器。

### 3.5 监控端点（HertzBeat HTTP 采集）

HertzBeat 通过 HTTP 协议定时采集以下端点，作为自定义监控器配置的数据源。

| 端点 | 用途 | 采集频率 | 状态 |
|------|------|---------|------|
| `/api/health` | 存活检查 | 10s | ✅ 已实现 |
| `/api/health/detail` | 详细健康检查 | 30s | ✅ 已实现 |
| `/api/metrics/system` | 系统指标 | 30s | ✅ 已实现 |
| `/api/metrics/business` | 业务指标 | 60s | ✅ 已实现 |
| `/api/metrics/api` | API 指标 | 60s | ✅ 已实现 |

### 3.6 MCP 可用工具映射

HertzBeat MCP 提供以下工具，可直接通过 AI Agent（Claude Code / Cursor）调用：

#### 监控管理工具

| MCP 工具 | 功能 | 对应场景 |
|----------|------|---------|
| `query_monitors` | 查询已配置的监控器，支持按 ID、类型、状态、主机、标签过滤排序 | 查看当前项目的监控目标状态 |
| `add_monitor` | 添加新的监控目标，支持全面配置 | 将本项目的健康检查端点注册为监控目标 |
| `list_monitor_types` | 列出所有可用的监控器类型 | 了解可监控的组件类型 |
| `get_monitor_additional_params` | 获取特定监控器类型所需的参数定义 | 查看添加监控器时需要的配置参数 |

#### 指标数据工具

| MCP 工具 | 功能 | 对应场景 |
|----------|------|---------|
| `query_realtime_metrics` | 获取指定监控器的实时指标数据（CPU、内存、磁盘等） | 实时查看系统指标 `/api/metrics/system` |
| `get_historical_metrics` | 获取指定时间范围的历史指标数据 | 分析业务指标趋势 `/api/metrics/business` |
| `get_warehouse_status` | 检查指标存储仓库状态 | 确认指标数据是否可操作和可访问 |

#### 告警管理工具

| MCP 工具 | 功能 | 对应场景 |
|----------|------|---------|
| `query_alerts` | 查询告警，支持按类型、状态、搜索词过滤排序 | 查看当前触发的告警 |
| `get_alerts_summary` | 获取告警摘要统计（总数、状态分布、优先级分解） | 快速了解整体告警状况 |

#### 告警规则定义工具

| MCP 工具 | 功能 | 对应场景 |
|----------|------|---------|
| `create_alert_rule` | 创建告警规则，支持阈值、字段条件 | 为本项目创建内存/CPU/任务成功率告警规则 |
| `list_alert_rules` | 列出现有告警规则，支持搜索和分页 | 查看已配置的告警规则列表 |
| `get_alert_rule_details` | 获取特定告警规则的详细信息 | 查看具体规则的阈值配置 |
| `toggle_alert_rule` | 启用或禁用告警规则 | 临时关闭/开启某个告警规则 |
| `get_apps_metrics_hierarchy` | 获取所有可用应用及其指标的层次结构 | 查看可用的监控指标树 |
| `bind_monitors_to_alert_rule` | 将监控器绑定到告警规则 | 将本项目监控器关联到告警规则 |

### 3.7 告警规则

#### 基础告警
| 指标 | 条件 | 级别 | 说明 |
|------|------|------|------|
| `status` | != healthy | 严重 | 服务异常 |
| `database.status` | != up | 严重 | 数据库断连 |
| `redis.status` | != up | 严重 | Redis 断连 |
| `cos.status` | != up | 警告 | COS 断连 |

#### 性能告警
| 指标 | 条件 | 级别 | 说明 |
|------|------|------|------|
| `memory_percent` | > 80% | 警告 | 内存使用过高 |
| `memory_percent` | > 90% | 严重 | 内存即将耗尽 |
| `cpu_percent` | > 80% | 警告 | CPU 使用过高 |
| `disk_used_gb/disk_total_gb` | > 90% | 警告 | 磁盘空间不足 |

#### 业务告警
| 指标 | 条件 | 级别 | 说明 |
|------|------|------|------|
| `tasks_success_rate` | < 0.9 | 警告 | 任务成功率过低 |
| `tasks_success_rate` | < 0.8 | 严重 | 任务成功率严重过低 |
| `task_queue_length` | > 50 | 警告 | 任务队列积压 |
| `task_queue_length` | > 100 | 严重 | 任务队列严重积压 |
| `error_rate` | > 0.05 | 警告 | API 错误率过高 |
| `error_rate` | > 0.1 | 严重 | API 错误率严重过高 |

### 3.8 MCP 集成操作流程

#### 通过 AI Agent 注册监控的流程
```
1. 确保 HertzBeat 服务已启动（MCP 自动在 1157 端口启动）
2. 在 HertzBeat Web UI 生成 JWT 令牌
3. 配置 Claude Code (~/.claude.json) 或 Cursor (.cursor/mcp.json)
4. 重启编辑器使 MCP 配置生效
5. 通过 AI Agent 调用 list_monitor_types 查看可用监控类型
6. 通过 AI Agent 调用 add_monitor 注册本项目的 /api/health 端点
7. 通过 AI Agent 调用 create_alert_rule 创建告警规则
8. 通过 AI Agent 调用 bind_monitors_to_alert_rule 绑定规则到监控器
```

#### 通过 AI Agent 日常运维的流程
```
1. 调用 query_monitors 查看所有监控目标状态
2. 调用 query_realtime_metrics 获取实时指标
3. 调用 get_alerts_summary 查看告警概况
4. 调用 query_alerts 查看具体告警详情
5. 需要时调用 toggle_alert_rule 调整告警规则
```

### 3.9 MCP 连接注意事项

- 如果连接断开，使用相同的请求头重新连接即可
- MCP 服务器与 HertzBeat 主服务同时启动，无需额外配置
- 如果使用非默认端口，需相应替换 URL 中的端口号
- JWT 令牌过期后需要在 Web UI 重新生成

---

## 4. 指标采集实现

### 4.1 连接检查
```python
def check_database():
    start = time.time()
    try:
        requests.get(f"{SUPABASE_URL}/rest/v1/", timeout=5)
        return {"status": "up", "latency_ms": int((time.time() - start) * 1000)}
    except:
        return {"status": "down", "latency_ms": 0}

def check_redis():
    start = time.time()
    try:
        from redis_client import is_redis_available
        if is_redis_available():
            return {"status": "up", "latency_ms": int((time.time() - start) * 1000)}
        return {"status": "down", "latency_ms": 0}
    except:
        return {"status": "down", "latency_ms": 0}

def check_cos():
    start = time.time()
    try:
        from cos_utils import is_cos_enabled
        if is_cos_enabled():
            return {"status": "up", "latency_ms": int((time.time() - start) * 1000)}
        return {"status": "disabled", "latency_ms": 0}
    except:
        return {"status": "down", "latency_ms": 0}
```

### 4.2 系统指标采集
```python
import psutil

def get_system_metrics():
    return {
        "memory_used_mb": psutil.Process().memory_info().rss // 1024 // 1024,
        "memory_percent": psutil.virtual_memory().percent,
        "cpu_percent": psutil.cpu_percent(interval=1),
        "disk_used_gb": psutil.disk_usage('/').used // 1024 // 1024 // 1024,
        "disk_total_gb": psutil.disk_usage('/').total // 1024 // 1024 // 1024,
        "active_threads": threading.active_count(),
    }
```

---

## 5. 认证与安全

### 5.1 监控端点认证
- 健康检查 `/api/health` 可公开访问
- 指标端点需要管理员权限或内部网络访问
- 建议通过 IP 白名单限制

### 5.2 敏感信息处理
- 不在指标中输出用户敏感信息
- 不输出 API 密钥
- 不输出具体错误堆栈

---

## 6. 日志格式规范

### 6.1 结构化日志
```python
logger.info('health_check', extra={
    'database': 'up',
    'redis': 'up',
    'cos': 'up',
    'latency_ms': 10
})
```

### 6.2 告警日志
```python
logger.warning('alert_triggered', extra={
    'metric': 'memory_percent',
    'value': 85,
    'threshold': 80,
    'level': 'warning'
})
```

---

## 7. 相关文件

- `app.py` - 监控 API 路由
- `redis_client.py` - Redis 连接检查
- `cos_utils.py` - COS 连接检查
- `supabase_client.py` - 数据库连接检查
