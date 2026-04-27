---
name: "linux-continuous-cpu-profiler"
description: "开发和运维 Linux 持续 CPU Profiling 工具。在需要 7x24 采样、故障时间点回溯、或生成火焰图定位 CPU 瓶颈时使用此 Skill。"
---

# Linux Continuous CPU Profiler Skill

本 Skill 用于在 Linux（包括 WSL2）环境下构建和维护持续 CPU Profiling 工具。它解决了生产环境下“事后定位难”的问题，通过 7x24 小时分片采样，允许用户在出问题后通过时间点检索并生成火焰图。

## 核心能力

- **持续采样**：利用 `perf` 进行低开销分片采样（推荐 99Hz）。
- **时间回溯**：通过 JSON 元数据索引，支持按 ISO-8601 时间点精确匹配采样切片。
- **火焰图渲染**：自动化 `perf script` 到 SVG 火焰图的转换链路。
- **自动清理**：内置 Retention 机制，根据磁盘预算自动滚动清理旧数据。

## 使用场景

- **场景 1：线上偶发性 CPU 飙高**
  - *动作*：启动 `collect` 模式常驻运行。
  - *触发*：当监控报警时，记录时间点，使用 `query` 命令拉取火焰图。

- **场景 2：WSL2 开发环境验证**
  - *动作*：使用 `-f` 参数规避 `perf` 权限校验，使用国内镜像下载 FlameGraph。

## 最佳实践与避坑指南

### 1. 依赖安装 (针对不同环境)
- **标准 Linux**: `sudo apt install linux-tools-$(uname -r)`
- **WSL2 (内核版本匹配难)**: 
  - 使用 `sudo apt install linux-tools-virtual`。
  - 若 `perf` 报错，手动创建软链接：`sudo ln -s $(ls -d /usr/lib/linux-tools/*/perf | head -n 1) /usr/local/bin/perf`。

### 2. 权限调整
- 必须调整内核参数：
  ```bash
  sudo sysctl -w kernel.perf_event_paranoid=1
  sudo sysctl -w kernel.kptr_restrict=0
  ```
- 运行解析时若提示权限错误，务必在 `perf script` 中加入 `-f` 参数。

### 3. 网络加速 (FlameGraph)
- 在国内环境，优先使用 Gitee 镜像：`https://gitee.com/mirrors/FlameGraph.git`。

## 常用命令参考

| 功能 | 命令示例 |
| :--- | :--- |
| **单次验证** | `sudo python3 -m continuous_cpu_profiler.cli once --config config.json` |
| **后台常驻** | `sudo python3 -m continuous_cpu_profiler.cli collect --config config.json` |
| **时间点检索** | `sudo python3 -m continuous_cpu_profiler.cli query --at "2026-04-27T10:00:00+08:00" --output-dir ./out` |
| **查看切片** | `python3 -m continuous_cpu_profiler.cli list --config config.json` |

## 进阶建议
- **编译选项**：业务程序建议开启 `-fno-omit-frame-pointer` 以获得更准确的调用栈。
- **存储优化**：生产环境建议将 `data_dir` 指向高性能 SSD 挂载点，并根据磁盘大小设置合理的 `retention_hours`。
