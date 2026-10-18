# BlueROV2 ROS 2

This repository contains the robot description and necessary launch files to describe and simulate the BlueROV2 (unmanned underwater vehicle) with [Gazebo](https://gazebosim.org/home) and its [hydrodynamics plugins](https://gazebosim.org/api/gazebo/6.1/underwater_vehicles.html) under ROS 2.


---

# Fork do projeto de corais: simulação em Docker (ROS 2 Jazzy + Gazebo Harmonic)

Esta branch (`feat/coral-world`) adiciona um Docker pronto para rodar o BlueROV2 no Gazebo
Harmonic, mais um mundo subaquático com fundo de areia (`coral_world_textura`) para a gente colocar
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
- `python3` e `python3-venv` (para o passo das fotos): `sudo apt install python3 python3-venv`
- ~10 GB livres em disco e internet (a imagem final ocupa ~5 GB; o download de pacotes do ROS e do Gazebo é grande).
- GPU NVIDIA é **opcional**. Sem ela a renderização é feita pela CPU: funciona, mas é mais lenta.

## Passo 1: baixar o código

```bash
git clone -b feat/coral-world https://github.com/BrunoCL-0/bluerov2.git
cd bluerov2
```

Os corais 3D (`.glb`, CC0) já vêm no repositório. As **fotos** de coral usadas por alguns mundos vêm de datasets do Kaggle
sem licença clara e por isso **não** estão no repositório: um script as baixa (sem login, ~60 MB) e monta as pastas.
Rode **uma vez**, no seu computador (fora do container), na raiz do repositório:

```bash
./scripts/setup_assets.sh
```

Ele cria um ambiente virtual em `.venv-assets/` (não mexe no Python do sistema) e as pastas
`bluerov2_description/models/coral_textures/` e `models/coral_textures_prova/`, ambas ignoradas pelo git. Sem esse
passo os mundos carregam normalmente, mas os planos de foto ficam sem imagem.

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
ros2 launch bluerov2_description coral_world_textura_launch.py
```

Deve abrir a janela do Gazebo com o fundo de areia e o robô. Para parar: `Ctrl+C`.

- Sem janela (só o servidor): `ros2 launch bluerov2_description coral_world_textura_launch.py gui:=false`
- Mudar a profundidade em que o robô nasce: `... coral_world_textura_launch.py depth:=-8.`
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
ros2 launch bluerov2_description coral_world_textura_launch.py spawn:=false
# Terminal 2 (docker exec ...)
ros2 launch bluerov2_description upload_bluerov2_launch.py sliders:=true z:=-5.
```

Aparece uma janela com um slider por propulsor (±40 N) e outro para inclinar a câmera.

## Controlar o robô pelo teclado e ver a câmera

Cada comando vai num terminal **separado**, dentro do container. Para abrir outro terminal no mesmo container,
rode no seu computador: `docker exec -it bluerov2_harmonic bash`. O mundo precisa estar rodando (Terminal 1).
Sem o controlador (Terminal 2) o robô **sobe sozinho** até a superfície, porque tem flutuabilidade levemente positiva.

**Terminal 2: controlador PID** (transforma velocidade em comando dos propulsores e segura a profundidade):
```bash
ros2 launch bluerov2_control cascaded_pids_launch.py sliders:=false rviz:=false
```

**Terminal 3: teclado** (o repo não traz teleop; o pacote vem do apt e **precisa ser reinstalado toda vez que o
container é recriado pelo `./run.sh`**):
```bash
apt-get update && apt-get install -y ros-jazzy-teleop-twist-keyboard
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=/bluerov2/cmd_vel \
  -p stamped:=true -p frame_id:=bluerov2/base_link -p speed:=0.3 -p turn:=0.5
```
Teclas, com esse terminal em foco: `i` frente, `,` ré, `j`/`l` gira esquerda/direita, `u`/`o` frente girando,
`J`/`L` (shift) andam de lado, `t` sobe, `b` desce, `k` para, `q`/`z` aumentam/diminuem a velocidade em 10%.

**Terminal 4: inclinar a câmera para baixo** (positivo olha para baixo; limite ±1,05 rad):
```bash
ros2 topic pub -r 10 /bluerov2/cmd_tilt std_msgs/msg/Float64 "{data: 0.9}"
```

**Terminal 5: ver a imagem da câmera:**
```bash
ros2 run rqt_image_view rqt_image_view /bluerov2/image
```

Testado: com o PID ligado, publicar velocidade em `/bluerov2/cmd_vel` move o robô (0,3 m/s andou ~2,3 m em 8 s), e o
tópico `/bluerov2/image` publica a ~17 a 20 Hz. **Não testado:** o teleop com teclado de verdade, o sentido de cada
tecla e a janela do `rqt_image_view`.

## O que existe no mundo `coral_world_textura`

| Elemento | Posição (z, em metros) |
|---|---|
| Água (plano azul semitransparente) | 0 |
| Robô (ponto de partida) | −5 (`depth`) |
| Topo dos morros de areia | ≈ −7,5 |
| Base do fundo de areia | −10 |

O fundo tem 50 × 50 m e relevo de ~2,5 m. O robô tem flutuabilidade levemente positiva
(+1% por lado da caixa de empuxo, definido no xacro): sem propulsores ele **sobe devagar** até
a superfície. É esperado. Com o controlador PID ele mantém a profundidade.

## Texturas de coral (Teste A)

O mundo `coral_world_textura` tem 8 planos de ~0,6 m sobre trechos planos do fundo, cada um com uma
foto de coral (4 saudáveis, 2 vermelhos e 2 verdes, e 4 branqueados). As fotos são criadas por
`./scripts/setup_assets.sh` (veja o Passo 1) em `bluerov2_description/models/coral_textures/`. Depois, no container,
rode `colcon build` e `source install/setup.bash` de novo para as fotos serem instaladas.
Para criar só estas fotos, à mão: `python3 scripts/setup_coral_textures.py --download` (requer `pillow` e `kagglehub`).

Os planos ficam em x = 3 a 7,3 m e y = −6 a 4,5 m (o robô nasce em x = 1, y = 0, olhando para +x).
Para ver um plano com a câmera, aproxime o robô do fundo e incline a câmera para baixo
(`ros2 topic pub -r 10 /bluerov2/cmd_tilt std_msgs/msg/Float64 "{data: 0.9}"`).

Limitações: as fotos têm 227 a 300 px (ficam borradas se ampliadas), a cena não tem atenuação de cor
da água, e uma foto em plano não é um coral em 3D. Serve para validar o pipeline, não a acurácia.
Os datasets são de classificação, sem caixas delimitadoras, e há imagens repetidas e algumas que
não são coral.

## Mundo recife (aglomerados de corais 3D)

`coral_world_recife` tem **96 colônias** de 8 espécies de coral 3D do Smithsonian (CC0) espalhadas
em **9 aglomerados** sobre trechos planos do fundo, mais **8 colônias isoladas**. As cores são
aplicadas por imagem no SDF, em cima de uma malha única por espécie. Aglomerados:

| Aglomerado | O que tem |
|---|---|
| 01 `branco` | só colônias brancas (branqueadas) |
| 02 `vermelho`, 03 `verde`, 04 `marrom` | uma cor por aglomerado, várias espécies |
| 05 `azul_roxo` | azul e roxo |
| 06 `cores_misturadas` | vermelho, verde, marrom, roxo, rosa e amarelo juntos |
| 07 `saudavel_com_branqueados` | maioria colorida com ~25% branqueadas |
| 08 `parcial_branqueando` | colônias verdes, marrons e vermelhas com **manchas brancas** |
| 09 `multicolor` | colônias com **manchas de várias cores** |
| `isolados` | 8 colônias soltas, bem separadas |

Objetos no SDF: `recife_aglomerado<NN>_<tipo>__<especie>__<cor>__<n>` e `recife_isolado__...`.
Espécies: *Acropora cervicornis*, *A. palmata*, *Seriatopora hystrix*, *Pseudodiploria strigosa*,
*Leptoseris gardineri*, *Heliopora coerulea*, *Meandrina meandrites* e *Pocillopora damicornis*
([links no topo de `scripts/setup_coral_recife.py`](scripts/setup_coral_recife.py)).

As malhas (`bluerov2_description/models/coral_recife/*.glb`, ~44 MB) e as 15 texturas de cor (`models/coral_recife_tex/`,
geradas por ruído, sem material de terceiros) **já estão no repositório**; não há nada para baixar. Origem e licença das
malhas em [models/coral_recife/README.md](bluerov2_description/models/coral_recife/README.md).

Para rodar, no container: `colcon build`, `source install/setup.bash` e
`ros2 launch bluerov2_description coral_world_recife_launch.py depth:=-8.`

Para **recriar as malhas do zero** (só manutenção): baixe os 8 modelos no Sketchfab em `.glb` (exige login), salve como
`acropora_palmata.glb`, `seriatopora_hystrix.glb` etc. numa pasta e rode
`pip install pillow numpy && python3 scripts/setup_coral_recife.py --input <essa pasta>`.

`python3 scripts/make_world_recife.py` regenera o SDF (semente fixa; `--seed N` muda a disposição).
Os aglomerados ficam entre x = 4 e 22 m e |y| até ~21 m; o robô nasce em x = 1, y = 0.

Limitações: as cores "saudáveis" são sintéticas (os originais são esqueletos de museu), as texturas
são ruído colorido (sem o detalhe de superfície do original, então os corais parecem recortes
lisos), os tamanhos são estimativas (a fonte não informa) e a orientação "natural" de cada
espécie não foi verificada. Em teste sem janela, com 96 colônias, a câmera ficou a ~12 Hz.

## Mundo de prova (fotos e corais 3D no mesmo mundo, com morros)

Pensado para avaliar um detector treinado com as fotos reais dos datasets, **sem depender de como o YOLO
será feito** (detecção ou classificação, versão, resolução). `coral_world_prova` tem o fundo **com morros** e dois
conjuntos de espécimes, cada um com as 5 situações abaixo (**32 espécimes por conjunto, 64 no total**; a versão completa, com 70
por conjunto, é mais pesada e sai com `--completo`):

| Conjunto | Onde | O que é |
|---|---|---|
| `imagem_P001...P032` | zona y < 0 (à direita do robô) | planos de 0,6 m com **foto real** dos datasets |
| `cad_P001...P032` | zona y > 0 (à esquerda) | **corais 3D**, cores medidas nas fotos do dataset |

O mesmo `id` tem a mesma situação e a mesma classe nos dois conjuntos (o `P007` de foto e o `P007` 3D), mas **não a
mesma posição**: cada conjunto fica numa zona do fundo. Cada situação é uma faixa de voo ao longo de x:

| Situação | O que é | Classe de verdade |
|---|---|---|
| `s1_controle` | 6 isolados, espaçamento regular de 2 m | 3 saudáveis + 3 branqueados |
| `s2_intercalados` | 6 isolados, espaçamento e posição lateral aleatórios | 3 + 3 |
| `s3a_aglom_puro` | 2 aglomerados de 4, cada um de uma classe só | 1 de saudáveis + 1 de branqueados |
| `s3b_aglom_misto` | 2 aglomerados de 4 com as duas classes juntas | 3+1 e 1+3 |
| `s4_dificil` | 4 isolados com branqueamento parcial | `ambiguo` (reportar à parte) |

**Como ficam sobre os morros.** Um plano de foto só pode ficar em chão plano, então cada foto vai para o trecho plano mais
próximo da posição ideal (o gerador também procura onde pôr a zona das fotos para esse deslocamento ser pequeno). Os
corais 3D ficam exatamente na posição ideal, assentados pelo ponto mais baixo sob a base. Por isso as faixas das fotos
são **aproximadas**: deslocamento médio de 0,8 m e máximo de 1,9 m, registrado em `desloc_m`. Em chão inclinado, parte do
coral 3D pode ficar enterrada.

**Verdade de terreno** em `bluerov2_description/worlds/`: `prova_manifesto.csv` (uma linha por espécime, com `tipo`
imagem/cad, posição real e ideal, `desloc_m`, foto de origem, rótulo do dataset, espécie e textura) e
`prova_manifesto_misto.json` (contagens, zonas e **caminho de voo sugerido acompanhando o relevo**, 1,5 m acima do
ponto mais alto de cada trecho; o caminho não foi testado com o robô).

**Altura sugerida: 1,5 m acima do fundo.** Com a câmera do robô (640 px, campo de 60°), um plano de 0,6 m ocupa ~220 px,
quase o tamanho nativo das fotos (227 a 300 px). Os morros sobem até ~2,5 m, então voar a altura fixa bate neles.

Para criar as fotos: `./scripts/setup_assets.sh` (Passo 1). Ele copia **exatamente** as fotos listadas em
`prova_manifesto.csv`, sem sortear nada de novo. As malhas dos corais 3D já vêm no repositório (veja "Mundo recife").

No container: `colcon build`, `source install/setup.bash` e
`ros2 launch bluerov2_description coral_world_prova_launch.py`. Para manter o robô na profundidade, use o
controlador PID e o teleop de teclado.

**Evitar vazamento de dados.** Quando a divisão treino/validação/teste for definida, salve os nomes das imagens
de treino num `treino.txt` (uma por linha) e, **para quem mantém o mundo**, regenere-o (muda as fotos sorteadas, o SDF e o
manifesto) com `pip install pillow numpy` e `python3 scripts/make_world_prova.py --datasets datasets --excluir treino.txt`.
Hoje a divisão é desconhecida. `--pool A` ou `--pool B` usa só um dataset (útil para o teste entre datasets).
Mudar `--seed` muda o sorteio.

**Como as fotos foram escolhidas.** Sorteio com semente fixa, sem duplicatas (hash perceptual). Depois, curadoria
**visual, imagem por imagem**: foram rejeitadas as com marca d'água ("WILD Singapore" e outras), mergulhador, desenho digital
e o que não é coral (estrela-do-mar, anêmona com peixe-palhaço, couve ornamental). As 30 fotos de branqueado e as 10 de
branqueamento parcial foram **escolhidas à mão** (listas no topo de `scripts/make_world_prova.py`).

**Limitações (leia antes de interpretar resultados):**
- Os rótulos "saudável/branqueado" são os dos datasets, que têm ruído. Algumas fotos "saudáveis" são cenas de recife
  inteiras, com peixes, e não colônias isoladas. A classe `ambiguo` não foi validada por especialista.
- A paleta dos corais 3D sai de um agrupamento de cores das fotos saudáveis; como as fotos incluem rocha, sombra e
  água, ela é **apagada e escura** (marrons, oliva, verde-mar), de pouco contraste com a areia, enquanto os
  branqueados são brancos. Isso pode misturar "visibilidade" com "classe" no resultado.
- A cena é escura (hipótese não verificada: o plano de água projeta sombra) e não tem a tinta azul-esverdeada
  da água das fotos reais. A diferença de aparência entre foto e 3D é parte do que a prova mede, mas não é controlada.
- Fotos em planos são cenas planas, não corais em 3D; os corais 3D são esqueletos recoloridos.
- Com morros, a altura e a oclusão variam ao longo da faixa, o que dificulta comparar foto e 3D posição a posição.

## Problemas comuns

| Sintoma | Causa provável / o que fazer |
|---|---|
| Janela não abre, "cannot connect to display" ou "Authorization required" | Rode `xhost +local:docker` **no seu computador** e abra o container de novo. Confirme que `echo $DISPLAY` não está vazio (não testado em sessão Wayland pura). |
| Gazebo não abre a renderização: `Failed to create dummy render window`, `OpenGL 3.3 is not supported` ou `eglInitialize failed` | Costuma ser notebook com Intel + NVIDIA: o container não traz o driver da NVIDIA. O `./run.sh` já expõe só as placas que não são NVIDIA (Intel/AMD). Se ainda falhar, confira com `ls /dev/dri` e `ls /sys/class/drm`. `./run.sh --gpu` expõe todas e exige o `nvidia-container-toolkit` (não testado). |
| `permission denied ... docker.sock` | Seu usuário não está no grupo `docker` (veja "O que você precisa"). |
| Log repete `Requesting list of world names` | O Gazebo não subiu. Procure o primeiro `[Err]` ou `died` mais acima no log (p. ex. arquivo de modelo não encontrado). |
| Muito lento | A janela do Gazebo desenha todos os objetos. Use `gui:=false` para testes, diminua o mundo (`make_world_prova.py` gera a versão leve por padrão) ou use a GPU com `./run.sh --gpu` (não testado). |
| Dois computadores/containers na mesma rede veem tópicos um do outro | O container usa a rede do host. Defina `export ROS_DOMAIN_ID=<número>` (e `export GZ_PARTITION=<nome>`) diferente em cada um. |
| Quero recomeçar do zero | No seu computador: `docker rm -f bluerov2_harmonic; docker volume rm bluerov2_build bluerov2_install bluerov2_log` |

## O que foi testado e o que não foi

Testado (Ubuntu 22.04, container Jazzy + Harmonic 8.15, sem janela, `gui:=false`):
- **Fluxo completo a partir de um clone limpo**: `git clone` → `./scripts/setup_assets.sh` (21 s) → `./docker/run.sh` →
  `colcon build` → `coral_world_prova_launch.py`. Sem erros no log, câmera a ~18 Hz, tempo real 1,0, e fotos e corais 3D
  visíveis na imagem da câmera.
- Build da imagem; `colcon build` dos dois pacotes; tópicos `/bluerov2/image`, `imu` (10 Hz), `pose_gt` e `odom`;
  propulsores movendo o robô; com o controlador PID, publicar velocidade em `/bluerov2/cmd_vel` move o robô.
- A janela do Gazebo foi usada pelo autor em `coral_world_textura` e `coral_world_prova` (a versão antiga do mundo de
  prova, com 140 objetos, ficou lenta; a atual tem 64).

**Não testado:** `./run.sh --gpu`, os sliders, o sliding mode, o RViz dentro do Docker, o teleop com teclado de verdade,
o caminho de voo sugerido no manifesto e Windows/macOS/WSL.

## O que este fork mudou em relação ao upstream (CentraleNantesROV/bluerov2)

- `docker/`: Dockerfile e scripts para Jazzy + Harmonic.
- `urdf/demo_world.sdf`: plugins renomeados para a sintaxe `gz-sim-*` (Harmonic).
- `launch/upload_bluerov2_launch.py`: o bridge de IMU agora usa o sensor `imu`
  (antes procurava `mpu` e `lsm`, que não existem mais no xacro).
- `worlds/coral_world_textura.sdf`, `launch/coral_world_textura_launch.py`, `models/sand_heightmap/`: mundo com
  fundo de areia. `CMakeLists.txt` passa a instalar `models` e `worlds`.
- `scripts/setup_assets.sh`, `scripts/setup_coral_textures.py`, `scripts/setup_photos_prova.py`: baixam os datasets de fotos
  e montam as pastas de fotos dos mundos (as fotos ficam fora do git).
- `worlds/coral_world_recife.sdf`, `launch/coral_world_recife_launch.py`, `scripts/setup_coral_recife.py`,
  `scripts/make_world_recife.py`: aglomerados de 96 corais 3D (8 espécies) em várias cores.
- `worlds/coral_world_prova.sdf`, `launch/coral_world_prova_launch.py`,
  `worlds/prova_manifesto*`, `scripts/make_world_prova.py`: corpos de prova (foto e 3D) com verdade de terreno.
- `models/coral_recife/` (malhas 3D CC0) e `models/coral_recife_tex/` (texturas de cor procedurais).

## Créditos e licenças

**Corais 3D:** os 8 modelos de `models/coral_recife/` são do Smithsonian Institution (Museu Nacional de História
Natural), em domínio público (CC0 1.0). Lista, links e alterações feitas em `models/coral_recife/README.md`. Cite a fonte no artigo.

**Fotos de coral:** vêm dos datasets do Kaggle `vencerlanz09/healthy-and-bleached-corals-image-classification` e
`sonainjamil/bleached-corals-detection` (artigo associado: Jamil et al., 2021, *Big Data and Cognitive Computing* 5(4):53).
Não estão no repositório e a licença de cada foto não foi verificada; confira os termos antes de redistribuí-las.

**Fundo de areia:**

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
