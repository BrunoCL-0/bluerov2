#!/usr/bin/env python3
"""Gera worlds/coral_world_recife.sdf: aglomerados de corais 3D sobre o fundo de areia.

Os aglomerados ficam em trechos planos do fundo e cada colônia assenta na altura real do
terreno. A semente é fixa, então rodar de novo gera o mesmo mundo.
Pré-requisito para RODAR o mundo (não para gerar o SDF): scripts/setup_coral_recife.py.

Uso:  python3 scripts/make_world_recife.py [--seed 7]
Requer: pip install numpy
"""
import argparse, math, os, re
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DESC = os.path.join(HERE, '..', 'bluerov2_description')
FUNDO_Z = -10.0   # pose z do modelo sand_heightmap em coral_world_*.sdf

# maior lado (m) de cada malha no arquivo original, medido por setup_coral_recife.py
MAIOR_LADO = {
    'acropora_cervicornis': 0.01761, 'acropora_palmata': 0.32429, 'heliopora_coerulea': 0.44040,
    'leptoseris_gardineri': 0.16500, 'meandrina_meandrites': 0.40280, 'pocillopora_damicornis': 0.10620,
    'pseudodiploria_strigosa': 0.18770, 'seriatopora_hystrix': 181.141,
}
# tamanho-alvo (maior lado, m) de uma colônia. Estimativa: a fonte não informa o tamanho real.
ALVO = {
    'acropora_cervicornis': 0.35, 'acropora_palmata': 0.50, 'heliopora_coerulea': 0.45,
    'leptoseris_gardineri': 0.40, 'meandrina_meandrites': 0.55, 'pocillopora_damicornis': 0.35,
    'pseudodiploria_strigosa': 0.45, 'seriatopora_hystrix': 0.30,
}
TODAS = list(ALVO)

# nome, nº de colônias, espécies, {variante: peso}
AGLOMERADOS = [
    ('branco',            10, TODAS, {'branco': 1}),
    ('vermelho',           9, ['acropora_palmata', 'acropora_cervicornis', 'pocillopora_damicornis',
                               'seriatopora_hystrix', 'pseudodiploria_strigosa'], {'vermelho': 1}),
    ('verde',              9, TODAS, {'verde': 1}),
    ('marrom',            10, TODAS, {'marrom': 1}),
    ('azul_roxo',          8, ['heliopora_coerulea', 'meandrina_meandrites', 'leptoseris_gardineri',
                               'pseudodiploria_strigosa'], {'azul': 1, 'roxo': 1}),
    ('cores_misturadas',  12, TODAS, {'vermelho': 1, 'verde': 1, 'marrom': 1, 'roxo': 1, 'rosa': 1, 'amarelo': 1}),
    ('saudavel_com_branqueados', 12, TODAS, {'marrom': 4, 'verde': 3, 'vermelho': 2, 'branco': 3}),
    ('parcial_branqueando', 9, TODAS, {'verde_com_branco': 1, 'marrom_com_branco': 1, 'vermelho_com_branco': 1}),
    ('multicolor',         9, TODAS, {'multicolor': 2, 'marrom_com_verde': 1, 'roxo_com_rosa': 1, 'branco_com_rosa': 1}),
]
N_ISOLADOS = 8   # colônias soltas, bem separadas, cores variadas


class Terreno:
    def __init__(self, escala=None):
        dae = open(os.path.join(DESC, 'models', 'sand_heightmap', 'meshes', 'sandseabed.dae')).read()
        sdf = open(os.path.join(DESC, 'models', 'sand_heightmap', 'model.sdf')).read()
        no = float(re.search(r'<matrix sid="transform">\s*([\d.eE+-]+)', dae).group(1))
        esc = list(escala) if escala else [float(v) for v in re.search(r'<scale>([^<]+)</scale>', sdf).group(1).split()]
        arr = max(re.findall(r'<float_array[^>]*id="[^"]*positions[^"]*"[^>]*>([^<]+)</float_array>', dae), key=len)
        v = np.array(arr.split(), float).reshape(-1, 3)
        v = np.c_[v[:, 0] * no * esc[0], v[:, 1] * no * esc[1], v[:, 2] * no * esc[2] + FUNDO_Z]
        n = int(round(len(v) ** .5))
        v = v[np.lexsort((v[:, 1], v[:, 0]))]
        self.G, self.n = v[:, 2].reshape(n, n), n
        self.x0, self.y0 = v[0, 0], v[0, 1]
        self.passo = (v[-1, 0] - v[0, 0]) / (n - 1)
        self.metade = abs(self.x0)

    def h(self, x, y):
        fx, fy = (x - self.x0) / self.passo, (y - self.y0) / self.passo
        i, j = int(np.clip(np.floor(fx), 0, self.n - 2)), int(np.clip(np.floor(fy), 0, self.n - 2))
        u, w = fx - i, fy - j
        G = self.G
        return G[i, j]*(1-u)*(1-w) + G[i+1, j]*u*(1-w) + G[i, j+1]*(1-u)*w + G[i+1, j+1]*u*w

    def plano(self, cx, cy, L):
        """Inclinação (graus) e maior desvio (m) do plano ajustado numa janela LxL."""
        g = np.linspace(-L / 2, L / 2, 9)
        gx, gy = np.meshgrid(g, g)
        z = np.array([self.h(cx + a, cy + b) for a, b in zip(gx.ravel(), gy.ravel())])
        A = np.c_[gx.ravel(), gy.ravel(), np.ones(81)]
        (a, b, _), *_ = np.linalg.lstsq(A, z, rcond=None)
        return math.degrees(math.atan(math.hypot(a, b))), float(np.abs(z - A @ np.linalg.lstsq(A, z, rcond=None)[0]).max())


def escolhe_centros(t, n, dmin, L, evita=()):
    cand = []
    for cx in np.arange(4.0, t.metade - 3, 0.5):
        for cy in np.arange(-t.metade + 3, t.metade - 3, 0.5):
            inc, res = t.plano(cx, cy, L)
            if inc < 8 and res < 0.12:
                cand.append((math.hypot(cx - 1, cy) , cx, cy))
    cand.sort()
    out = []
    for _, cx, cy in cand:
        if all(math.hypot(cx - o[0], cy - o[1]) >= dmin for o in list(out) + list(evita)):
            out.append((cx, cy))
        if len(out) == n:
            break
    return out


def coloca(rng, t, cx, cy, raio, especies, variantes, n, ocupados):
    pesos = np.array(list(variantes.values()), float)
    nomes = list(variantes)
    colonias, tentativas = [], 0
    while len(colonias) < n and tentativas < 4000:
        tentativas += 1
        r, ang = raio * math.sqrt(rng.random()), rng.random() * 2 * math.pi
        x, y = cx + r * math.cos(ang), cy + r * math.sin(ang)
        sp = especies[rng.integers(len(especies))]
        tam = ALVO[sp] * rng.uniform(0.75, 1.3)
        rp = 0.58 * tam
        if any(math.hypot(x - ox, y - oy) < rp + orad + 0.05 for ox, oy, orad in ocupados):
            continue
        var = nomes[rng.choice(len(nomes), p=pesos / pesos.sum())]
        colonias.append(dict(sp=sp, var=var, x=x, y=y, z=t.h(x, y) - 0.02, yaw=rng.random() * 2 * math.pi,
                             s=tam / MAIOR_LADO[sp]))
        ocupados.append((x, y, rp))
    return colonias


def bloco(nome, c):
    return f'''    <model name="{nome}">
      <static>true</static>
      <pose>{c['x']:.3f} {c['y']:.3f} {c['z']:.3f} 0 0 {c['yaw']:.3f}</pose>
      <link name="link">
        <visual name="visual">
          <geometry>
            <mesh>
              <uri>model://bluerov2_description/models/coral_recife/{c['sp']}.glb</uri>
              <scale>{c['s']:.4f} {c['s']:.4f} {c['s']:.4f}</scale>
            </mesh>
          </geometry>
          <material>
            <ambient>1 1 1 1</ambient>
            <diffuse>1 1 1 1</diffuse>
            <pbr><metal>
              <albedo_map>model://bluerov2_description/models/coral_recife_tex/{c['var']}.jpg</albedo_map>
              <roughness>0.9</roughness>
              <metalness>0.0</metalness>
            </metal></pbr>
          </material>
        </visual>
      </link>
    </model>'''


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--seed', type=int, default=7)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    t = Terreno()
    raio = 1.55
    centros = escolhe_centros(t, len(AGLOMERADOS), 5.0, 2 * raio + 0.4)
    if len(centros) < len(AGLOMERADOS):
        raise SystemExit(f'só achei {len(centros)} trechos planos para {len(AGLOMERADOS)} aglomerados')
    ocupados, blocos, resumo = [], [], []
    for k, ((nome, n, esp, var), (cx, cy)) in enumerate(zip(AGLOMERADOS, centros), 1):
        cols = coloca(rng, t, cx, cy, raio, esp, var, n, ocupados)
        resumo.append((f'aglomerado{k:02d}_{nome}', cx, cy, len(cols)))
        for i, c in enumerate(cols, 1):
            blocos.append(bloco(f'recife_aglomerado{k:02d}_{nome}__{c["sp"]}__{c["var"]}__{i:02d}', c))
    soltos = escolhe_centros(t, N_ISOLADOS, 3.0, 0.9, evita=[(cx, cy) for cx, cy in centros for _ in (0,)] +
                             [(cx + dx, cy + dy) for cx, cy in centros for dx, dy in ((2.5, 0), (-2.5, 0), (0, 2.5), (0, -2.5))])
    variantes_soltos = ['branco', 'vermelho', 'verde', 'marrom', 'roxo', 'azul', 'rosa', 'amarelo', 'multicolor', 'verde_com_branco']
    for i, (cx, cy) in enumerate(soltos, 1):
        sp = TODAS[(i - 1) % len(TODAS)]
        c = dict(sp=sp, var=variantes_soltos[(i - 1) % len(variantes_soltos)], x=cx, y=cy, z=t.h(cx, cy) - 0.02,
                 yaw=rng.random() * 2 * math.pi, s=ALVO[sp] * rng.uniform(0.9, 1.2) / MAIOR_LADO[sp])
        blocos.append(bloco(f'recife_isolado__{sp}__{c["var"]}__{i:02d}', c))
    resumo.append(('isolados', 0, 0, len(soltos)))

    base = open(os.path.join(DESC, 'worlds', 'coral_world_textura.sdf')).read()
    cabeca = base[:base.index('    <!-- TESTE A (textura)')]
    txt = cabeca + f'''    <!-- MUNDO RECIFE: aglomerados de corais 3D (Smithsonian, CC0) sobre trechos planos do fundo.
         Gerado por scripts/make_world_recife.py (semente {a.seed}); não edite à mão, rode o script de novo.
         Objetos: recife_aglomerado<NN>_<tipo>__<especie>__<cor>__<n> e recife_isolado__<especie>__<cor>__<n>.
         Precisa dos arquivos locais (fora do git): scripts/setup_coral_recife.py (ver README).
         Sem eles o mundo carrega, mas sem corais. -->
''' + '\n'.join(blocos) + '\n\n  </world>\n</sdf>\n'
    destino = os.path.join(DESC, 'worlds', 'coral_world_recife.sdf')
    open(destino, 'w').write(txt)
    print(f'{len(blocos)} colônias -> {os.path.normpath(destino)}')
    for nome, cx, cy, n in resumo:
        print(f'  {nome:42s} centro=({cx:6.2f},{cy:6.2f})  colônias={n}')


if __name__ == '__main__':
    main()
