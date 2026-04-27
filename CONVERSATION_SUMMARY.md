# Linux 持续 CPU Profiling 工具开发对话记录

本文件记录了从零开发一个 Linux 持续 CPU Profiling 工具的全过程，包括遇到的技术挑战及其解决方案。

## 1. 任务目标
开发一个 7x24 小时持续 CPU Profiling 采集工具，支持：
- 后台常驻采样（基于 `perf`）。
- 按时间点回溯采样数据。
- 自动生成火焰图定位根因。
- 形成可复用的 Trae Skill。

## 2. 技术方案
- **采集引擎**：Linux 原生 `perf` (record/script)。
- **逻辑编排**：Python 3.11+ (负责分片、索引、清理)。
- **可视化**：FlameGraph (Brendan Gregg)。
- **部署方式**：`systemd` 守护进程。

## 3. 对话关键里程碑与实战解决的问题

### 阶段一：架构设计与基础代码实现
- 建立了项目骨架：`src/`（源码）, `deploy/`（配置）, `scripts/`（安装）, `tests/`（测试）。
- 实现了 `collector.py` 负责 `perf` 任务调度。
- 实现了 `query.py` 负责 ISO 时间点到分片文件的索引匹配。

### 阶段二：WSL2 环境下的实战攻坚
由于用户在 Windows + WSL2 环境下运行，遇到了多个典型环境问题：

#### 问题 1：FlameGraph 下载失败 (TLS 握手错误)
- **现象**：`git clone` 访问 GitHub 失败。
- **对策**：修改脚本支持 Gitee 镜像加速及 ZIP Fallback 下载机制。

#### 问题 2：`/var/lib` 目录权限拒绝
- **现象**：普通用户无权在系统目录写数据。
- **对策**：创建 `wsl-test-config.json`，将数据目录指向项目内的 `./data`。

#### 问题 3：`perf` 命令找不到 (WSL2 特有)
- **现象**：`linux-tools-$(uname -r)` 在 WSL2 中无法直接 locate。
- **对策**：
    - 安装 `linux-tools-virtual`。
    - 手动建立软链接：`sudo ln -s $(ls -d /usr/lib/linux-tools/*/perf | head -n 1) /usr/local/bin/perf`。

#### 问题 4：`perf script` 权限校验报错
- **现象**：在 `/mnt/d/` (Windows 挂载盘) 下解析数据时，`perf` 认为文件所有者不安全。
- **对策**：在 `render.py` 的解析逻辑中强制加入 `-f` 参数规避校验。

### 阶段三：功能验证
- **单次采样成功**：输出了包含元数据和路径的 JSON。
- **火焰图生成成功**：通过 `query` 命令成功在 `output/` 生成了可交互的 `flamegraph.svg`。

## 4. 交付产物清单
- **核心代码**：`src/continuous_cpu_profiler/`
- **Skill 文档**：`.trae/skills/linux-continuous-cpu-profiler/SKILL.md`
- **测试配置**：`examples/wsl-test-config.json`
- **运行脚本**：`scripts/install_flamegraph.sh`

## 5. 后续扩展建议
1. **多机汇聚**：可将本地分片上传至 S3，配合中心化索引。
2. **eBPF 演进**：对于高版本内核，可引入 eBPF 采集器以进一步降低开销。
3. **前端展示**：可以为生成的 SVG 列表做一个简单的 Web 索引页面。

---
*记录生成日期：2026-04-27*
