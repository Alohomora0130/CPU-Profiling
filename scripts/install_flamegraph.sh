#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="${1:-/opt/FlameGraph}"

if [[ -d "${TARGET_DIR}/.git" ]]; then
  git -C "${TARGET_DIR}" pull --ff-only
else
  # 使用镜像地址（加速国内访问）
  MIRROR_URL="https://gitee.com/mirrors/FlameGraph.git"
  # 如果上面的还是不行，可以尝试这个镜像: https://gitee.com/mirrors/FlameGraph.git

  echo "Attempting to clone FlameGraph from $MIRROR_URL..."
  if git clone --depth 1 "$MIRROR_URL" "${TARGET_DIR}"; then
      echo "Successfully installed FlameGraph via git."
  else
      echo "Git clone failed. Trying to download ZIP as fallback..."
      rm -rf "${TARGET_DIR}"
      mkdir -p "${TARGET_DIR}"
      # 使用 FastGit 或其他加速下载 ZIP
      wget https://github.com/brendangregg/FlameGraph/archive/refs/heads/master.zip -O /tmp/fg.zip
      unzip /tmp/fg.zip -d /tmp/fg_extracted
      cp -r /tmp/fg_extracted/FlameGraph-master/* "${TARGET_DIR}/"
      echo "Successfully installed FlameGraph via ZIP fallback."
  fi
fi

echo "FlameGraph installed at ${TARGET_DIR}"
