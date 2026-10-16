# ROS 2 Jazzy + Gazebo Harmonic
# O código do bluerov2 NÃO é copiado para a imagem: ele é montado como volume (ver run.sh).
FROM ros:jazzy-ros-base

ENV DEBIAN_FRONTEND=noninteractive
ENV DEPS_WS=/opt/deps_ws
ENV WS=/ws

RUN apt-get update && apt-get install -y --no-install-recommends \
    git build-essential cmake \
    python3-colcon-common-extensions python3-rosdep \
    mesa-utils libgl1 libegl1 libglx-mesa0 libgl1-mesa-dri x11-apps \
    ros-jazzy-ros-gz \
    ros-jazzy-xacro \
    ros-jazzy-simple-launch \
    ros-jazzy-slider-publisher \
    ros-jazzy-rviz2 \
    ros-jazzy-rqt-image-view \
    && rm -rf /var/lib/apt/lists/*

# Dependências que não estão no apt: compiladas uma vez, ficam na imagem.
# Fixadas nos commits testados (16/10/2026) para o build ser reproduzível.
# Para atualizar, troque o SHA (git ls-remote <url> HEAD).
ARG THRUSTER_MANAGER_SHA=bd7d7c9937dc70e0aab82dd29d9fa1f101a229db
ARG AUV_CONTROL_SHA=c8cae74ad51035142d9926466b0e069c21fc3596
ARG POSE_TO_TF_SHA=40c2b6defdb52ed1de73c817ff0b03c291f3e382

RUN mkdir -p ${DEPS_WS}/src && cd ${DEPS_WS}/src && \
    clone_at() { \
      git init -q "$1" && cd "$1" && \
      git remote add origin "$2" && \
      git fetch -q --depth 1 origin "$3" && \
      git checkout -q FETCH_HEAD && cd ..; \
    } && \
    clone_at thruster_manager https://github.com/CentraleNantesROV/thruster_manager.git ${THRUSTER_MANAGER_SHA} && \
    clone_at auv_control      https://github.com/CentraleNantesROV/auv_control.git      ${AUV_CONTROL_SHA} && \
    clone_at pose_to_tf       https://github.com/oKermorgant/pose_to_tf.git             ${POSE_TO_TF_SHA}

RUN . /opt/ros/jazzy/setup.sh && cd ${DEPS_WS} && \
    rosdep update && \
    rosdep install --from-paths src --ignore-src -r -y && \
    colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release && \
    rm -rf /var/lib/apt/lists/*

RUN echo "source /opt/ros/jazzy/setup.bash" >> /root/.bashrc && \
    echo "source ${DEPS_WS}/install/setup.bash" >> /root/.bashrc && \
    echo "[ -f ${WS}/install/setup.bash ] && source ${WS}/install/setup.bash" >> /root/.bashrc

WORKDIR ${WS}
CMD ["bash"]
