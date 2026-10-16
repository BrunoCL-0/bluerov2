# BlueROV2 ROS 2

This repository contains the robot description and necessary launch files to describe and simulate the BlueROV2 (unmanned underwater vehicle) with [Gazebo](https://gazebosim.org/home) and its [hydrodynamics plugins](https://gazebosim.org/api/gazebo/6.1/underwater_vehicles.html) under ROS 2.


---

# Fork do projeto de corais: simulação em Docker (ROS 2 Jazzy + Gazebo Harmonic)

Esta branch (`feat/coral-world`) adiciona um Docker pronto para rodar o BlueROV2 no Gazebo
Harmonic, mais um mundo subaquático com fundo de areia (`coral_world`) para a gente colocar
os corais. Tudo abaixo foi escrito para quem **nunca rodou isso**: siga os passos na ordem.

> O Dockerfile original deste repositório (raiz, `build_docker.sh`/`run_docker.sh`) usa ROS 2
> Humble + Gazebo Fortress e foi mantido como está. **Use o da pasta [docker/](docker/)**.
> Motivo: o Fortress 6.16 não reconhece os plugins `gz::sim::systems::Hydrodynamics`,
> `Thruster` e `OdometryPublisher` usados no xacro atual (testado), então o robô ficaria sem
> propulsores, hidrodinâmica e odometria.

## O que você precisa (uma vez só)

- **Linux** com sessão gráfica (testado em Ubuntu 22.04, X11). O container usa `--net=host`,
  então não serve para Windows/macOS.
- **Docker Engine** instalado ([guia oficial](https://docs.docker.com/engine/install/), opção
  "Install using the apt repository") e seu usuário no grupo `docker`, para rodar sem `sudo`:
  ```bash
  sudo usermod -aG docker $USER   # depois faça logout/login
  docker run --rm hello-world     # teste: deve imprimir "Hello from Docker!"
  ```
- `xhost` (abre a janela do Gazebo na sua tela): `sudo apt install x11-xserver-utils`
- ~10 GB livres em disco e internet (a imagem final ocupa ~5 GB; o download de pacotes do ROS e do Gazebo é grande).
- GPU NVIDIA é **opcional**. Sem ela a renderização é feita pela CPU: funciona, mas é mais lenta.

## Passo 1: baixar o código

```bash
git clone -b feat/coral-world https://github.com/BrunoCL-0/bluerov2.git
cd bluerov2
```

## Passo 2: construir a imagem Docker (uma vez; 20 a 40 min dependendo da internet)

```bash
cd docker
./build.sh
```

Isso cria a imagem `bluerov2_harmonic` com ROS 2 Jazzy, Gazebo Harmonic, `ros_gz`,
`simple_launch`, `slider_publisher`, RViz e `thruster_manager`, `auv_control`, `pose_to_tf`
(estes três compilados a partir de commits fixos, para o build ser reproduzível).
Só repita este passo se mudar o `docker/Dockerfile`.

## Passo 3: abrir o container (Terminal 1)

```bash
cd bluerov2/docker      # (se ainda não estiver nela)
./run.sh
```

Você cai num prompt `root@...:/ws#`. **Todos os comandos dos passos seguintes são digitados
dentro do container**, a não ser que esteja escrito "no seu computador". O seu repositório
aparece dentro dele em `/ws/src/bluerov2`: você edita os arquivos no computador normalmente.

## Passo 4: compilar e subir a simulação (Terminal 1, dentro do container)

```bash
cd /ws
colcon build
source install/setup.bash
ros2 launch bluerov2_description coral_world_launch.py
```

Deve abrir a janela do Gazebo com o fundo de areia e o robô. Para parar: `Ctrl+C`.

- Sem janela (só o servidor): `ros2 launch bluerov2_description coral_world_launch.py gui:=false`
- Mudar a profundidade em que o robô nasce: `... coral_world_launch.py depth:=-8.`
- Mundo vazio original (só água): `ros2 launch bluerov2_description world_launch.py`

Depois de **editar** algum arquivo do pacote (mundo, xacro, launch), rode de novo
`colcon build` e `source install/setup.bash` dentro do container antes de relançar.

## Passo 5: conferir se está funcionando (Terminal 2)

Abra **outro terminal no seu computador** e entre no mesmo container:

```bash
docker exec -it bluerov2_harmonic bash
```

Dentro dele (já vem com o ROS carregado):

```bash
ros2 topic list                       # deve listar /bluerov2/image, /bluerov2/imu, /bluerov2/pose_gt ...
ros2 topic echo /bluerov2/pose_gt     # pose do robô (ground truth)
ros2 topic hz /bluerov2/image         # câmera, ~20 Hz
ros2 run rqt_image_view rqt_image_view   # escolha /bluerov2/image
```

### Mexer no robô com sliders (não testado)

Suba o mundo **sem** o robô e spawne o robô com sliders:

```bash
# Terminal 1
ros2 launch bluerov2_description coral_world_launch.py spawn:=false
# Terminal 2 (docker exec ...)
ros2 launch bluerov2_description upload_bluerov2_launch.py sliders:=true z:=-5.
```

Aparece uma janela com um slider por propulsor (±40 N) e outro para inclinar a câmera.

## O que existe no mundo `coral_world`

| Elemento | Posição (z, em metros) |
|---|---|
| Água (plano azul semitransparente) | 0 |
| Robô (ponto de partida) | −5 (`depth`) |
| Topo dos morros de areia | ≈ −7,5 |
| Base do fundo de areia | −10 |

O fundo tem 50 × 50 m e relevo de ~2,5 m. O robô tem flutuabilidade levemente positiva
(+1% por lado da caixa de empuxo, definido no xacro): sem propulsores ele **sobe devagar** até
a superfície. É esperado. Com o controlador PID ele mantém a profundidade.

## Problemas comuns

| Sintoma | Causa provável / o que fazer |
|---|---|
| Janela não abre, "cannot connect to display" ou "Authorization required" | Rode `xhost +local:docker` **no seu computador** e abra o container de novo. Confirme que `echo $DISPLAY` não está vazio (não testado em sessão Wayland pura). |
| `permission denied ... docker.sock` | Seu usuário não está no grupo `docker` (veja "O que você precisa"). |
| Log repete `Requesting list of world names` | O Gazebo não subiu. Procure o primeiro `[Err]` ou `died` mais acima no log (p. ex. arquivo de modelo não encontrado). |
| Muito lento | Renderização por CPU. Use `gui:=false` para testes ou instale o `nvidia-container-toolkit` e rode `./run.sh --gpu` (não testado). |
| Dois computadores/containers na mesma rede veem tópicos um do outro | O container usa a rede do host. Defina `export ROS_DOMAIN_ID=<número>` (e `export GZ_PARTITION=<nome>`) diferente em cada um. |
| Quero recomeçar do zero | No seu computador: `docker rm -f bluerov2_harmonic; docker volume rm bluerov2_build bluerov2_install bluerov2_log` |

## O que foi testado e o que não foi

Testado (Ubuntu 22.04, container Jazzy + Harmonic 8.15, renderização por CPU):
build da imagem; `colcon build` dos dois pacotes; mundo `coral_world` com a janela do Gazebo
mostrando a areia; tópicos `/bluerov2/image` (~19 Hz), `imu` (10 Hz), `pose_gt` e `odom`;
propulsores movendo o robô.

**Não testado:** `./run.sh --gpu`, os sliders, os controladores PID/sliding mode
(`bluerov2_control`) e o RViz dentro do Docker, Windows/macOS/WSL.

## O que este fork mudou em relação ao upstream (CentraleNantesROV/bluerov2)

- `docker/`: Dockerfile e scripts para Jazzy + Harmonic.
- `urdf/demo_world.sdf`: plugins renomeados para a sintaxe `gz-sim-*` (Harmonic).
- `launch/upload_bluerov2_launch.py`: o bridge de IMU agora usa o sensor `imu`
  (antes procurava `mpu` e `lsm`, que não existem mais no xacro).
- `worlds/coral_world.sdf`, `launch/coral_world_launch.py`, `models/sand_heightmap/`: mundo com
  fundo de areia. `CMakeLists.txt` passa a instalar `models` e `worlds`.

## Créditos e licenças do fundo de areia

`models/sand_heightmap/` foi copiado de https://github.com/clydemcqueen/bluerov2_gz (projeto
que declara MIT no `package.xml`), cujo `model.sdf` traz o cabeçalho do UUV Simulator
(Apache-2.0). A textura é de texturelib.com (uso livre, comercial ou não; não pode ser
redistribuída sozinha; pede crédito). Detalhes em `models/sand_heightmap/README.md` e
`models/sand_heightmap/materials/TEXTURE_LICENSE.txt`. Cite essas fontes no artigo.

---

# README original do upstream

## Requirements

### For the description

- [Xacro ](https://github.com/ros/xacro/tree/ros2), installable through `apt install ros-${ROS_DISTRO}-xacro`
- [simple_launch](https://github.com/oKermorgant/simple_launch), installable through `apt install ros-${ROS_DISTRO}-simple-launch`

### Gazebo

- ROS 2 with Gazebo Fortress or newer with `ros_gz_bridge`
    - Look out for your [ROS 2 / Gazebo versions combination](https://gazebosim.org/docs/garden/ros_installation)
- [pose_to_tf](https://github.com/oKermorgant/pose_to_tf), to get the ground truth from Gazebo if needed.

### For the control part

- [slider_publisher](https://github.com/oKermorgant/slider_publisher), installable through `apt install ros-${ROS_DISTRO}-slider-publisher`
- [auv_control](https://github.com/CentraleNantesROV/auv_control) for basic control laws, from source


## Installation 

Clone the package and its dependencies (if from source) in your ROS 2 workspace `src` and compile with `colcon`

## Running 

To run a demonstration with the vehicle, you can run a Gazebo scenario, such as an empty world with buoyancy and sensors setup:

```bash
ros2 launch bluerov2_description world_launch.py
```

and then spawn the robot with a GUI to control the thrusters:

```bash
ros2 launch bluerov2_description upload_bluerov2_launch.py sliders:=true
```

## Using with Docker

This repository provides a Docker setup to simplify installation and ensure a
reproducible ROS 2 + Gazebo environment.

---

### Requirements (Docker)

- Linux host
- Docker Engine ([How to Install](https://docs.docker.com/engine/install/), it is recommended to use the option "Install using the APT repository")
- Optional: NVIDIA GPU with NVIDIA Container Toolkit (for GPU acceleration)

---

### Build the Docker image

From the root of the repository, build the Docker image locally:

```bash
./build_docker.sh
```

This step needs to be executed once, or whenever the Dockerfile is modified.

---

### Run the container

Run without GPU support:

```bash
./run_docker.sh
```

Run with GPU support (recommended for Gazebo):

```bash
./run_docker.sh --gpu
```

The container provides access to:
- Gazebo GUI (X11)
- USB devices (e.g. joystick, serial interfaces)
- ROS 2 communication with nodes running outside the container


### ROS 2 communication outside Docker

The container uses host networking, allowing ROS 2 nodes running on the host
(or other machines on the same network) to communicate directly with the
simulation inside Docker.

## Input / output

Gazebo will:

- Subscribe to `/bluerov2/cmd_thruster[1..6]` and expect  `std_msgs/Float64` messages, being the thrust in Newton
- Publish sensor data to various topics (image, mpu+lsm for IMU, cloud for the sonar, odom)
- Publish the ground truth on `/bluerov2/pose_gt`. This pose is forwarded to `/tf` if `pose_to_tf` is used.


## High-level control

Basic control is available in the [auv_control](https://github.com/CentraleNantesROV/auv_control) package

In this case spawn the robot without manual sliders and run e.g. a cascaded PID controller:

```bash
ros2 launch bluerov2_description upload_bluerov2_launch.py
ros2 launch bluerov2_control cascaded_pids_launch.py sliders:=true
```


## License

BlueROV2 package is open-sourced under the Apache-2.0 license. See the
[LICENSE](LICENSE) file for details.
