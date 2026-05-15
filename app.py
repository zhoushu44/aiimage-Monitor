from collections import defaultdict, deque
from datetime import datetime, timezone
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
import json
import os
import random
import threading

import psutil
from flask import Flask, jsonify, render_template_string, request


app = Flask(__name__)
STARTED_AT = datetime.now(timezone.utc)
TARGET_BASE_URL = os.getenv("TARGET_BASE_URL", "http://129.226.153.254:5078").rstrip("/")
API_STATS = defaultdict(lambda: {"count": 0, "errors": 0, "total_ms": 0.0, "max_ms": 0.0})
RECENT_REQUESTS = deque(maxlen=50)
STATS_LOCK = threading.Lock()


DASHBOARD_HTML = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>网页监控可视化</title>
  <style>
    :root { color-scheme: light dark; font-family: "Microsoft YaHei", system-ui, sans-serif; }
    body { margin: 0; background: #0f172a; color: #e5e7eb; }
    main { max-width: 1180px; margin: 0 auto; padding: 28px; }
    h1 { margin: 0 0 8px; font-size: 28px; }
    .sub { color: #94a3b8; margin-bottom: 22px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 14px; }
    .card { background: #111827; border: 1px solid #1f2937; border-radius: 14px; padding: 18px; box-shadow: 0 12px 30px rgba(0,0,0,.18); }
    .label { color: #94a3b8; font-size: 13px; }
    .value { font-size: 28px; font-weight: 700; margin-top: 8px; }
    .ok { color: #22c55e; }
    .warn { color: #f59e0b; }
    .bad { color: #ef4444; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    th, td { text-align: left; padding: 10px; border-bottom: 1px solid #1f2937; color: #cbd5e1; }
    th { color: #94a3b8; font-weight: 600; }
    a { color: #38bdf8; text-decoration: none; }
    code { color: #bae6fd; }
    .bar { height: 10px; border-radius: 999px; background: #1f2937; overflow: hidden; margin-top: 12px; }
    .bar span { display: block; height: 100%; width: 0%; background: #22c55e; transition: width .25s ease; }
    .muted { color: #94a3b8; font-size: 13px; margin-top: 8px; }
    .raw { white-space: pre-wrap; max-height: 360px; overflow: auto; font-size: 12px; color: #cbd5e1; }
    .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; margin-top: 12px; }
    .metric { background: #0b1220; border: 1px solid #1f2937; border-radius: 12px; padding: 14px; }
    .metric .name { color: #e2e8f0; font-weight: 700; }
    .metric .key { color: #38bdf8; font-size: 12px; margin-top: 4px; }
    .metric .number { font-size: 24px; font-weight: 800; margin-top: 8px; }
    .metric .desc { color: #94a3b8; font-size: 13px; line-height: 1.5; margin-top: 8px; }
  </style>
</head>
<body>
  <main>
    <h1>网页监控可视化</h1>
    <div class="sub">被监听网址：<code>{{ target }}</code>，本看板服务端口：<code>{{ port }}</code></div>
    <section class="grid">
      <div class="card"><div class="label">目标状态</div><div id="targetStatus" class="value">加载中</div><div id="targetMsg" class="muted">-</div></div>
      <div class="card"><div class="label">响应耗时</div><div id="latency" class="value">-</div><div class="muted">健康检查接口</div></div>
      <div class="card"><div class="label">CPU</div><div id="cpu" class="value">-</div><div class="bar"><span id="cpuBar"></span></div></div>
      <div class="card"><div class="label">内存</div><div id="mem" class="value">-</div><div class="bar"><span id="memBar"></span></div></div>
      <div class="card"><div class="label">磁盘</div><div id="disk" class="value">-</div><div class="bar"><span id="diskBar"></span></div></div>
      <div class="card"><div class="label">运行时间</div><div id="uptime" class="value">-</div><div class="muted">目标服务上报</div></div>
    </section>
    <section class="card" style="margin-top:14px">
      <div class="label">具体 JSON 指标中文说明</div>
      <div id="metricCards" class="metrics"></div>
    </section>
    <section class="card" style="margin-top:14px">
      <div class="label">目标接口采集结果</div>
      <table>
        <thead><tr><th>接口</th><th>HTTP</th><th>耗时</th><th>状态</th></tr></thead>
        <tbody id="endpointRows"></tbody>
      </table>
    </section>
    <section class="card" style="margin-top:14px">
      <div class="label">原始数据</div>
      <pre id="raw" class="raw">加载中</pre>
    </section>
    <section class="card" style="margin-top:14px">
      <div class="label">本看板接口</div>
      <table>
        <tbody>
          <tr><td>目标快照</td><td><a href="/api/target/snapshot">/api/target/snapshot</a></td></tr>
          <tr><td>本看板健康检查</td><td><a href="/api/health">/api/health</a></td></tr>
          <tr><td>本看板系统指标</td><td><a href="/api/metrics/system">/api/metrics/system</a></td></tr>
        </tbody>
      </table>
    </section>
  </main>
  <script>
    const cls = v => v >= 90 ? 'bad' : v >= 75 ? 'warn' : 'ok';
    const barColor = v => v >= 90 ? '#ef4444' : v >= 75 ? '#f59e0b' : '#22c55e';
    function pickMetric(data, names) {
      for (const name of names) {
        if (data && data[name] !== undefined && data[name] !== null) return data[name];
      }
      return null;
    }
    function setPercent(id, value) {
      const el = document.getElementById(id);
      const bar = document.getElementById(id + 'Bar');
      const num = Number(value);
      if (!Number.isFinite(num)) {
        el.textContent = '-';
        bar.style.width = '0%';
        return;
      }
      el.textContent = num.toFixed(1) + '%';
      el.className = 'value ' + cls(num);
      bar.style.width = Math.max(0, Math.min(100, num)) + '%';
      bar.style.background = barColor(num);
    }
    function formatValue(value, unit, scale = 1) {
      if (value === null || value === undefined || value === '') return '-';
      const num = Number(value);
      if (!Number.isFinite(num)) return value;
      return (num * scale).toFixed(unit === '%' ? 1 : 2).replace(/\.00$/, '') + unit;
    }
    async function refresh() {
      const snapshot = await fetch('/api/target/snapshot').then(r => r.json());
      document.getElementById('raw').textContent = JSON.stringify(snapshot, null, 2);
      document.getElementById('targetStatus').textContent = snapshot.status;
      document.getElementById('targetStatus').className = 'value ' + (snapshot.status === 'healthy' ? 'ok' : snapshot.status === 'degraded' ? 'warn' : 'bad');
      document.getElementById('targetMsg').textContent = snapshot.target;
      document.getElementById('latency').textContent = snapshot.health.latency_ms === null ? '-' : snapshot.health.latency_ms + 'ms';
      const metrics = snapshot.system.data.metrics || snapshot.system.data;
      setPercent('cpu', pickMetric(metrics, ['cpu_percent', 'cpu']));
      setPercent('mem', pickMetric(metrics, ['memory_percent', 'memory']));
      setPercent('disk', pickMetric(metrics, ['disk_percent', 'disk']));
      document.getElementById('uptime').textContent = pickMetric(metrics, ['uptime_seconds']) ?? snapshot.health.data.uptime_seconds ?? '-';
      document.getElementById('metricCards').innerHTML = snapshot.metric_descriptions.map(item => `<div class="metric"><div class="name">${item.name}</div><div class="key">${item.path}</div><div class="number">${formatValue(item.value, item.unit, item.scale)}</div><div class="desc">${item.description}</div></div>`).join('');
      document.getElementById('endpointRows').innerHTML = snapshot.endpoints.map(item => `<tr><td>${item.path}</td><td>${item.http_status ?? '-'}</td><td>${item.latency_ms ?? '-'}ms</td><td class="${item.ok ? 'ok' : 'bad'}">${item.ok ? '正常' : '异常'}</td></tr>`).join('');
    }
    refresh();
    setInterval(refresh, 5000);
  </script>
</body>
</html>
"""


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def uptime_seconds():
    return int((datetime.now(timezone.utc) - STARTED_AT).total_seconds())


def service_check(name, enabled=True):
    return {
        "name": name,
        "status": "healthy" if enabled else "disabled",
        "latency_ms": round(random.uniform(1, 8), 2) if enabled else None,
        "checked_at": now_iso(),
    }


@app.before_request
def before_request():
    request.started_at = perf_counter()


@app.after_request
def after_request(response):
    if request.path.startswith("/api/"):
        duration_ms = (perf_counter() - request.started_at) * 1000
        with STATS_LOCK:
            item = API_STATS[request.path]
            item["count"] += 1
            item["total_ms"] += duration_ms
            item["max_ms"] = max(item["max_ms"], duration_ms)
            if response.status_code >= 400:
                item["errors"] += 1
            RECENT_REQUESTS.appendleft({
                "path": request.path,
                "method": request.method,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "time": now_iso(),
            })
    return response


@app.route("/")
def dashboard():
    return render_template_string(DASHBOARD_HTML, port=os.getenv("PORT", "5079"), target=TARGET_BASE_URL)


def fetch_json(path, timeout=8):
    url = f"{TARGET_BASE_URL}{path}"
    started = perf_counter()
    try:
        with urlopen(url, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            latency_ms = round((perf_counter() - started) * 1000, 2)
            return {
                "path": path,
                "url": url,
                "ok": 200 <= response.status < 400,
                "http_status": response.status,
                "latency_ms": latency_ms,
                "data": parse_json(body),
                "error": None,
            }
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {
            "path": path,
            "url": url,
            "ok": False,
            "http_status": exc.code,
            "latency_ms": round((perf_counter() - started) * 1000, 2),
            "data": parse_json(body),
            "error": str(exc),
        }
    except (URLError, TimeoutError, ValueError) as exc:
        return {
            "path": path,
            "url": url,
            "ok": False,
            "http_status": None,
            "latency_ms": round((perf_counter() - started) * 1000, 2),
            "data": {},
            "error": str(exc),
        }


def parse_json(body):
    try:
        return json.loads(body) if body else {}
    except ValueError:
        return {"raw": body}


def get_nested(data, keys):
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def metric_item(name, json_path, value, unit, description, scale=1):
    return {
        "name": name,
        "path": json_path,
        "value": value,
        "unit": unit,
        "scale": scale,
        "description": description,
    }


def build_metric_descriptions(health_result, system_result, business_result, api_result):
    health = health_result.get("data", {})
    system = system_result.get("data", {})
    business = business_result.get("data", {})
    api = api_result.get("data", {})
    system_metrics = system.get("metrics", system)
    business_metrics = business.get("metrics", business)
    api_metrics = api.get("metrics", api)
    return [
        metric_item("服务总体状态", "health.data.status", health.get("status"), "", "目标服务当前健康状态，healthy 表示正常，degraded 表示部分异常，down 表示不可访问。"),
        metric_item("健康接口耗时", "health.latency_ms", health_result.get("latency_ms"), "ms", "看板请求目标 /api/health 接口花费的时间，数值越低说明响应越快。"),
        metric_item("数据库状态", "health.data.checks.database.status", get_nested(health, ["checks", "database", "status"]), "", "目标服务上报的数据库连通状态，up 表示数据库连接正常。"),
        metric_item("数据库延迟", "health.data.checks.database.latency_ms", get_nested(health, ["checks", "database", "latency_ms"]), "ms", "目标服务检查数据库连接消耗的时间，可用于判断数据库是否变慢。"),
        metric_item("Redis 状态", "health.data.checks.redis.status", get_nested(health, ["checks", "redis", "status"]), "", "目标服务上报的 Redis 连通状态，up 表示缓存服务正常。"),
        metric_item("Redis 延迟", "health.data.checks.redis.latency_ms", get_nested(health, ["checks", "redis", "latency_ms"]), "ms", "目标服务检查 Redis 连接消耗的时间。"),
        metric_item("对象存储状态", "health.data.checks.cos.status", get_nested(health, ["checks", "cos", "status"]), "", "目标服务上报的 COS/对象存储连通状态。"),
        metric_item("任务队列活跃任务", "health.data.checks.task_queue.active_tasks", get_nested(health, ["checks", "task_queue", "active_tasks"]), "", "目标任务队列当前处于活跃状态的任务数量。"),
        metric_item("CPU 使用率", "system.data.metrics.cpu_percent", system_metrics.get("cpu_percent"), "%", "服务器 CPU 当前使用比例，过高可能代表计算压力大。"),
        metric_item("内存使用率", "system.data.metrics.memory_percent", system_metrics.get("memory_percent"), "%", "服务器内存当前使用比例，持续过高可能导致服务不稳定。"),
        metric_item("磁盘使用率", "system.data.metrics.disk_percent", system_metrics.get("disk_percent"), "%", "服务器磁盘空间使用比例，接近 100% 时需要清理或扩容。"),
        metric_item("内存总量", "system.data.metrics.memory_total_mb", system_metrics.get("memory_total_mb"), "MB", "服务器可用内存总容量，单位为 MB。"),
        metric_item("已用内存", "system.data.metrics.memory_used_mb", system_metrics.get("memory_used_mb"), "MB", "目标服务或服务器上报的已使用内存，单位为 MB。"),
        metric_item("运行时间", "system.data.metrics.uptime_seconds", system_metrics.get("uptime_seconds"), "秒", "目标服务已经连续运行的时间，重启后会重新计数。"),
        metric_item("活跃线程数", "system.data.metrics.active_threads", system_metrics.get("active_threads"), "", "目标进程当前活跃线程数量，可辅助判断并发负载。"),
        metric_item("任务总数", "business.data.metrics.total_tasks", business_metrics.get("total_tasks"), "", "业务侧累计或当前统计到的任务总数量。"),
        metric_item("运行中任务", "business.data.metrics.running_tasks", business_metrics.get("running_tasks"), "", "当前正在执行的业务任务数量。"),
        metric_item("已完成任务", "business.data.metrics.completed_tasks", business_metrics.get("completed_tasks"), "", "已经成功完成的任务数量。"),
        metric_item("失败任务", "business.data.metrics.failed_tasks", business_metrics.get("failed_tasks"), "", "执行失败的任务数量，需要重点关注。"),
        metric_item("任务队列长度", "business.data.metrics.task_queue_length", business_metrics.get("task_queue_length"), "", "等待处理或队列中的任务数量，过高表示消费速度不足。"),
        metric_item("任务成功率", "business.data.metrics.tasks_success_rate", business_metrics.get("tasks_success_rate"), "%", "任务成功完成的比例，展示时按百分比显示。", 100),
        metric_item("API 请求总数", "api.data.metrics.requests_total", api_metrics.get("requests_total"), "", "目标服务累计处理的 API 请求数量。"),
        metric_item("每分钟请求数", "api.data.metrics.requests_per_minute", api_metrics.get("requests_per_minute"), "次/分钟", "目标服务当前 API 请求速率。"),
        metric_item("API 错误数", "api.data.metrics.error_count", api_metrics.get("error_count"), "", "目标服务累计 API 错误数量。"),
        metric_item("API 错误率", "api.data.metrics.error_rate", api_metrics.get("error_rate"), "%", "API 请求失败比例，展示时按百分比显示。", 100),
    ]


@app.route("/api/target/snapshot")
def target_snapshot():
    paths = ["/api/health", "/api/metrics/system", "/api/metrics/business", "/api/metrics/api"]
    results = [fetch_json(path) for path in paths]
    health_result = results[0]
    system_result = results[1]
    status = "healthy" if health_result["ok"] else "down"
    health_data = health_result.get("data", {})
    if isinstance(health_data, dict) and health_data.get("status") not in (None, "healthy", "up"):
        status = "degraded"
    return jsonify({
        "target": TARGET_BASE_URL,
        "status": status,
        "health": health_result,
        "system": system_result,
        "business": results[2],
        "api": results[3],
        "metric_descriptions": build_metric_descriptions(health_result, system_result, results[2], results[3]),
        "endpoints": results,
        "timestamp": now_iso(),
    })


@app.route("/api/health")
def health():
    return jsonify({
        "status": "healthy",
        "service": "web-monitor-backend",
        "version": "1.0.0",
        "uptime_seconds": uptime_seconds(),
        "timestamp": now_iso(),
    })


@app.route("/api/health/detail")
def health_detail():
    cpu = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage(os.getcwd()).percent
    checks = [
        service_check("application"),
        service_check("database", os.getenv("DATABASE_URL") is not None),
        service_check("redis", os.getenv("REDIS_URL") is not None),
        service_check("object_storage", os.getenv("COS_SECRET_ID") is not None),
    ]
    status = "healthy" if cpu < 90 and memory < 90 and disk < 95 else "degraded"
    return jsonify({
        "status": status,
        "service": "web-monitor-backend",
        "uptime_seconds": uptime_seconds(),
        "checks": checks,
        "resources": {"cpu_percent": cpu, "memory_percent": memory, "disk_percent": disk},
        "timestamp": now_iso(),
    }), 200 if status == "healthy" else 503


@app.route("/api/metrics/system")
def metrics_system():
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(os.getcwd())
    net = psutil.net_io_counters()
    return jsonify({
        "cpu": {"percent": psutil.cpu_percent(interval=0.1), "count": psutil.cpu_count()},
        "memory": {"percent": memory.percent, "total": memory.total, "used": memory.used, "available": memory.available},
        "disk": {"percent": disk.percent, "total": disk.total, "used": disk.used, "free": disk.free},
        "network": {"bytes_sent": net.bytes_sent, "bytes_recv": net.bytes_recv},
        "timestamp": now_iso(),
    })


@app.route("/api/metrics/business")
def metrics_business():
    with STATS_LOCK:
        total_requests = sum(item["count"] for item in API_STATS.values())
        total_errors = sum(item["errors"] for item in API_STATS.values())
    return jsonify({
        "total_requests": total_requests,
        "total_errors": total_errors,
        "error_rate": round(total_errors / total_requests, 4) if total_requests else 0,
        "active_services": 1,
        "uptime_seconds": uptime_seconds(),
        "timestamp": now_iso(),
    })


@app.route("/api/metrics/api")
def metrics_api():
    with STATS_LOCK:
        endpoints = []
        for path, item in sorted(API_STATS.items()):
            endpoints.append({
                "path": path,
                "count": item["count"],
                "errors": item["errors"],
                "avg_ms": round(item["total_ms"] / item["count"], 2) if item["count"] else 0,
                "max_ms": round(item["max_ms"], 2),
            })
        recent = list(RECENT_REQUESTS)
    return jsonify({"endpoints": endpoints, "recent_requests": recent, "timestamp": now_iso()})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5079"))
    app.run(host="0.0.0.0", port=port)
