#!/usr/bin/env bash
# Abre um shell no container (ROS 2 Jazzy + Gazebo Harmonic).
#   ./run.sh          -> sem GPU NVIDIA dedicada (padrão, renderização por CPU/Mesa)
#   ./run.sh --gpu    -> usa a GPU NVIDIA (exige nvidia-container-toolkit; não testado)
#
# O repo é montado em /ws/src/bluerov2. Os resultados do colcon (build/install/log)
# ficam em volumes do Docker, então não sujam o repo e não se misturam com um
# workspace ROS instalado no host.
set -e

IMAGE=bluerov2_harmonic
NAME=bluerov2_harmonic
REPO_HOST="$(cd "$(dirname "$0")/.." && pwd)"

GPU_ARGS=""
if [ "$1" = "--gpu" ]; then
  GPU_ARGS="--gpus all -e NVIDIA_VISIBLE_DEVICES=all -e NVIDIA_DRIVER_CAPABILITIES=all"
  shift
fi

DRI_ARGS=""
[ -d /dev/dri ] && DRI_ARGS="--device /dev/dri"

# libera a janela do container no seu X11 (precisa do pacote x11-xserver-utils)
if command -v xhost >/dev/null 2>&1; then
  xhost +local:docker >/dev/null || echo "[aviso] xhost falhou: a janela do Gazebo pode não abrir"
else
  echo "[aviso] xhost não encontrado (sudo apt install x11-xserver-utils): a janela do Gazebo pode não abrir"
fi

docker rm -f "$NAME" >/dev/null 2>&1 || true
exec docker run -it --name "$NAME" \
  --net=host --ipc=host \
  -e DISPLAY="$DISPLAY" -e QT_X11_NO_MITSHM=1 \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  $DRI_ARGS \
  -v "$REPO_HOST":/ws/src/bluerov2 \
  -v bluerov2_build:/ws/build -v bluerov2_install:/ws/install -v bluerov2_log:/ws/log \
  $GPU_ARGS \
  "$IMAGE" "$@"
