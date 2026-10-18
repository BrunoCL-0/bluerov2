#!/usr/bin/env python3
"""Gera o mundo de PROVA com morros: fotos reais e corais 3D no mesmo mundo.

  worlds/coral_world_prova.sdf          espécimes de FOTO (planos, objetos imagem_<id>_...) na zona y<0 e
                                        espécimes 3D (objetos cad_<id>_...) na zona y>0
  worlds/prova_manifesto.csv            verdade de terreno: posição e classe de cada espécime
  worlds/prova_manifesto_misto.json     contagens, zonas e caminho de voo sugerido (acompanha o relevo)

O mesmo id (P001...) tem a mesma situação e a mesma classe nos dois conjuntos, mas posições diferentes
(cada conjunto fica numa zona). Planos de foto só ficam em chão plano, então cada foto vai ao trecho plano
mais próximo da posição ideal (o deslocamento fica no manifesto); os corais 3D ficam na posição ideal.

Situações (uma faixa de voo cada, a faixa vai ao longo de x; y relativo à zona = -6, -3, 0, 3, 6):
  s1_controle      10 isolados, espaçamento regular, 5 saudáveis + 5 branqueados
  s2_intercalados  10 isolados, espaçamento e posição lateral aleatórios, 5 + 5
  s3a_aglom_puro   4 aglomerados de 5, cada um de uma classe só (2 saudáveis, 2 branqueados)
  s3b_aglom_misto  4 aglomerados de 5, com as duas classes juntas
  s4_dificil       10 isolados AMBÍGUOS (branqueamento parcial / várias cores): classe "ambiguo"

Classes de verdade de terreno: saudavel, branqueado, ambiguo. Nada aqui depende de como o YOLO
será feito (detecção ou classificação, versão, resolução).

As fotos vêm de datasets do Kaggle (sem licença clara): ficam em models/coral_textures_prova/,
fora do git. A divisão treino/validação/teste ainda não é conhecida: use --excluir com a lista de
arquivos usados no treino para NÃO usá-los como corpo de prova (evita vazamento de dados).

Uso:
  python3 scripts/make_world_prova.py --datasets <pasta dos datasets> [--excluir treino.txt]
                                      [--pool ambos|A|B] [--seed 11] [--folhas <pasta>]
Requer: pip install pillow numpy. Os corais 3D pedem antes scripts/setup_coral_recife.py.
"""
import argparse, csv, glob, json, math, os, shutil, sys
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_world_recife as mw          # noqa: E402  (Terreno, ALVO, MAIOR_LADO, TODAS)
import setup_coral_recife as sr         # noqa: E402  (textura procedural)

DESC = os.path.join(HERE, '..', 'bluerov2_description')
MODELS = os.path.join(DESC, 'models')
WORLDS = os.path.join(DESC, 'worlds')
FUNDO_Z = -10.0
FAIXAS_Y = {'s1_controle': -6.0, 's2_intercalados': -3.0, 's3a_aglom_puro': 0.0,
            's3b_aglom_misto': 3.0, 's4_dificil': 6.0}
LADO_FOTO = 0.6                         # maior lado do plano com foto, em m
ALTURA_VOO = 1.5                        # altura sugerida acima do fundo, em m

VENCER = 'vencerlanz09/healthy-and-bleached-corals-image-classification'
SONAIN = 'sonainjamil/bleached-corals-detection'
DATASETS = (('A', VENCER, {'healthy_corals': 'saudavel', 'bleached_corals': 'branqueado'}),
            ('B', SONAIN, {'Train/Unbleached': 'saudavel', 'Train/Bleached': 'branqueado'}))

# Imagens revisadas e rejeitadas na curadoria visual de 16/10/2026: marca d'água ("WILD Singapore" etc.), mergulhador,
# desenho digital, animal que não é coral. São trocadas pela próxima da fila, sem mexer nas demais.
REJEITADAS = {
    'A:bleached_corals/10033870215_3664757d59_o.jpg',
    'A:bleached_corals/14157532279_3e38313638_o.jpg',
    'A:bleached_corals/14343383014_c661e512ee_o.jpg',
    'A:bleached_corals/20818206781_fcee27a762_o.jpg',
    'A:bleached_corals/27957509801_f1a062f256_o.jpg',
    'A:bleached_corals/28687860430_e8f3f57eba_o.jpg',
    'A:bleached_corals/29376275703_fc3ea71718_o.jpg',
    'A:bleached_corals/4695377101_03d3573df4_o.jpg',
    'A:bleached_corals/4959196019_4f4b0ccd45_o.jpg',
    'A:bleached_corals/4963809687_dd5d81d6b6_o.jpg',
    'A:bleached_corals/5029269095_a326041de2_o.jpg',
    'A:bleached_corals/5160419996_ff4ba8452c_o.jpg',
    'A:bleached_corals/5398026994_8e1486aa13_o.jpg',
    'A:bleached_corals/9399125405_a3672a192f_o.jpg',
    'A:bleached_corals/9670495054_392fa34907_o.jpg',
    'A:healthy_corals/10493583423_65c6ddfc38_o.jpg',
    'A:healthy_corals/47812522351_2fba5f0178_o.jpg',
    'A:healthy_corals/5737445273_47eb32094f_o.jpg',
    'A:healthy_corals/6099267701_f67dd74f07_b.jpg',
    'B:Train/Bleached/1.png',
    'B:Train/Unbleached/129.png',
    'B:Train/Bleached/11.png',
    'A:bleached_corals/14548646926_661e9ea246_o.jpg',
    'B:Train/Bleached/119.png',
    'A:bleached_corals/30022664915_53a5dd62cd_o.jpg',
    'B:Train/Unbleached/180.png',
    'A:bleached_corals/7326685866_a069c89210_o.jpg',
    'B:Train/Bleached/114.png',
    'A:bleached_corals/40157597050_bfa01019b5_o.jpg',
    'A:healthy_corals/6349794433_7656b74bac_b.jpg',
    'A:healthy_corals/27255427184_bd1c03fbd8_b.jpg',
    'B:Train/Bleached/120.png',
    'B:Train/Unbleached/168.png',
    'A:healthy_corals/12678987553_66ddc5afd9_b.jpg',
    'A:healthy_corals/9359755544_a953c819c0_o.jpg',
    'A:bleached_corals/8199768672_5540db83f4_o.jpg',
    'A:bleached_corals/9406240021_a65af0d829_o.jpg',
    'A:bleached_corals/4819583169_106ff643c9_o.jpg',
    'A:healthy_corals/8358200706_9d8b0034d7_b.jpg',
    'A:healthy_corals/6152696118_8ff1861877_b.jpg',
    'A:healthy_corals/7465120086_e31e1c3a1e_o.jpg',
    'A:healthy_corals/4143552479_ea84d31442_o.jpg',
    'A:healthy_corals/24056773005_70743784b6_o.jpg',
}

# Fotos de branqueamento PARCIAL escolhidas à mão (curadoria de 16/10/2026) para a situação s4_dificil.
# A heurística automática (fração de branco) erra nesse grupo (pegou couve ornamental e coral todo branco).
AMBIGUAS_ESCOLHIDAS = [
    'A:bleached_corals/18179620866_b2d98c8421_o.jpg',
    'A:bleached_corals/11023816893_9994f554e2_o.jpg',
    'A:bleached_corals/8677946826_be2f953cb0_o.jpg',
    'A:bleached_corals/10415679866_6eea4769f6_o.jpg',
    'A:bleached_corals/14633767870_660d182ff5_o.jpg',
    'B:Train/Bleached/154.png',
    'B:Train/Bleached/91.png',
    'B:Train/Bleached/194.png',
    'A:bleached_corals/13938277197_44b23a6021_b.jpg',
    'A:bleached_corals/4117345237_96cd1dc700_o.jpg',
]

# 30 fotos de BRANQUEADO escolhidas à mão entre as 76 candidatas (curadoria de 16/10/2026): sem logo, sem
# mergulhador, sem anêmona com peixe-palhaço; formas variadas. O dataset A tem muita marca d'água nas brancas.
BRANQUEADAS_ESCOLHIDAS = [
    'A:bleached_corals/14913058584_146660dcf6_b.jpg',
    'A:bleached_corals/15605895000_8981814747_o.png',
    'A:bleached_corals/16051547956_12d5b6c365_o.jpg',
    'A:bleached_corals/18018559720_f2f0944cf4_o.jpg',
    'A:bleached_corals/18206069405_acac2f12e6_o.jpg',
    'A:bleached_corals/27119208655_78d1206562_b.jpg',
    'A:bleached_corals/27304994093_ea6064e76e_o.jpg',
    'A:bleached_corals/392871468_82f033b05d_o.jpg',
    'A:bleached_corals/5318916908_9b56002abb_o.jpg',
    'A:bleached_corals/5529485045_0e83ba0976_b.jpg',
    'A:bleached_corals/5815918114_9a94837b24_o.jpg',
    'A:bleached_corals/6157774144_25d6386699_o.jpg',
    'A:bleached_corals/6832379570_3fd4e2757e_o.jpg',
    'A:bleached_corals/7173611516_66280e1fda_o.jpg',
    'A:bleached_corals/8514121744_567b5db215_o.jpg',
    'A:bleached_corals/8677958894_932fcb0d30_o.jpg',
    'B:Train/Bleached/101.png',
    'B:Train/Bleached/105.png',
    'B:Train/Bleached/111.png',
    'B:Train/Bleached/112.png',
    'B:Train/Bleached/118.png',
    'B:Train/Bleached/121.png',
    'B:Train/Bleached/132.png',
    'B:Train/Bleached/137.png',
    'B:Train/Bleached/143.png',
    'B:Train/Bleached/160.png',
    'B:Train/Bleached/161.png',
    'B:Train/Bleached/200.png',
    'B:Train/Bleached/59.png',
    'B:Train/Bleached/93.png',
]


# ----------------------------------------------------------------------------- fotos
def raiz(base, ds):
    v = sorted(glob.glob(os.path.join(base, 'datasets', *ds.split('/'), 'versions', '*')))
    return v[-1] if v else None


def dhash(im):
    a = np.asarray(im.convert('L').resize((9, 8), Image.LANCZOS)).astype(int)
    return int(''.join('1' if b else '0' for b in (a[:, 1:] > a[:, :-1]).ravel()), 2)


def metricas(caminho):
    im = Image.open(caminho).convert('RGB')
    w, h = im.size
    c = im.crop((int(w * .2), int(h * .2), int(w * .8), int(h * .8)))
    hsv = np.asarray(c.convert('HSV')).astype(float)
    H, S, V = hsv[..., 0] * 360 / 255, hsv[..., 1] / 255, hsv[..., 2] / 255
    branco = float(((S < .18) & (V > .72)).mean())
    colorido = (S >= .18) & (V > .15)
    sat = float(S[colorido].mean()) if colorido.any() else 0.0
    return dict(branco=branco, sat=sat, hash=dhash(im), tam=im.size)


def listar(base, pool, excluir):
    itens = []
    for tag, ds, subs in DATASETS:
        if pool not in ('ambos', tag):
            continue
        r = raiz(base, ds)
        if not r:
            sys.exit(f'dataset {ds} não encontrado em {base} (rode setup_coral_textures.py --download)')
        for sub, rot in subs.items():
            for f in sorted(glob.glob(os.path.join(r, sub, '*'))):
                nome = os.path.basename(f)
                if nome in excluir:
                    continue
                itens.append(dict(caminho=f, arquivo=nome, dataset=tag, rotulo=rot, chave=f'{tag}:{sub}/{nome}'))
    return itens


def candidatos(itens):
    """Calcula métricas, tira duplicatas e separa em saudavel / branqueado / ambiguo."""
    vistos, out = [], {'saudavel': [], 'branqueado': [], 'ambiguo': []}
    for it in itens:
        try:
            m = metricas(it['caminho'])
        except Exception:
            continue
        if any(bin(m['hash'] ^ h).count('1') <= 6 for h in vistos):
            continue                                   # duplicata ou quase
        vistos.append(m['hash'])
        it.update(m)
        if 0.14 <= m['branco'] <= 0.30:
            out['ambiguo'].append(it)
        elif it['rotulo'] == 'saudavel' and m['branco'] <= 0.08 and m['sat'] >= 0.28:
            out['saudavel'].append(it)
        elif it['rotulo'] == 'branqueado' and m['branco'] >= 0.30:
            out['branqueado'].append(it)
    return out


def paleta_saudavel(itens, rng, k=5):
    """Cores dominantes dos corais saudáveis do dataset (k-means em RGB, sem água, areia e escuro)."""
    px = []
    for it in rng.permutation([i for i in itens if i['rotulo'] == 'saudavel'])[:250]:
        im = Image.open(it['caminho']).convert('RGB')
        w, h = im.size
        c = im.crop((int(w * .2), int(h * .2), int(w * .8), int(h * .8)))
        rgb = np.asarray(c).reshape(-1, 3).astype(float)
        hsv = np.asarray(c.convert('HSV')).reshape(-1, 3).astype(float)
        Hh, S, V = hsv[:, 0] * 360 / 255, hsv[:, 1] / 255, hsv[:, 2] / 255
        agua = (Hh > 165) & (Hh < 265)
        ok = (S > .30) & (V > .25) & (V < .95) & ~agua
        if ok.sum() > 50:
            px.append(rgb[ok][rng.choice(ok.sum(), size=min(300, ok.sum()), replace=False)])
    X = np.vstack(px)
    cent = X[rng.choice(len(X), k, replace=False)]
    for _ in range(30):
        lab = np.argmin(((X[:, None, :] - cent[None]) ** 2).sum(-1), axis=1)
        cent = np.array([X[lab == j].mean(0) if (lab == j).any() else cent[j] for j in range(k)])
    peso = np.bincount(lab, minlength=k) / len(lab)
    ordem = np.argsort(-peso)
    return [tuple(int(v) for v in cent[j]) for j in ordem], [float(peso[j]) for j in ordem]


def cor_branqueado(itens):
    acc = []
    for it in itens:
        if it['rotulo'] != 'branqueado':
            continue
        a = np.asarray(Image.open(it['caminho']).convert('RGB')).reshape(-1, 3).astype(float)
        mx, mn = a.max(1), a.min(1)
        ok = (mx > 150) & ((mx - mn) / np.maximum(mx, 1) < .2)
        if ok.sum() > 100:
            acc.append(a[ok].mean(0))
    return tuple(int(v) for v in np.mean(acc, 0))


# ----------------------------------------------------------------------------- layout
def sorteia_classes(rng, n_h, n_b):
    v = ['saudavel'] * n_h + ['branqueado'] * n_b
    return list(rng.permutation(v))


def cluster_pos(rng, cx, cy, n, raio=1.0, dmin=0.7):
    pts, tent = [], 0
    while len(pts) < n and tent < 5000:
        tent += 1
        r, a = raio * math.sqrt(rng.random()), rng.random() * 2 * math.pi
        p = (cx + r * math.cos(a), cy + r * math.sin(a))
        if all(math.hypot(p[0] - q[0], p[1] - q[1]) >= dmin for q in pts):
            pts.append(p)
    if len(pts) < n:
        raise SystemExit('não coube o aglomerado: aumente o raio')
    return pts


def monta_layout(rng, leve=True):
    """Layout ideal (coordenadas relativas à zona). leve=True: 32 espécimes; False: 70."""
    n_iso, n_cl, tam_cl, n_dif = (6, 2, 4, 4) if leve else (10, 4, 5, 10)
    centros = (6, 12) if leve else (6, 11.5, 17, 22.5)
    sp = []

    def add(sit, grupo, classe, x, y):
        sp.append(dict(situacao=sit, grupo=grupo, classe=classe, x=float(x), y=float(y), yaw=float(rng.random() * 2 * math.pi)))
    # s1: regular
    cl = sorteia_classes(rng, n_iso // 2, n_iso // 2)
    for i in range(n_iso):
        add('s1_controle', '', cl[i], 5.0 + 2.0 * i, FAIXAS_Y['s1_controle'])
    # s2: espaçamento e posição lateral aleatórios
    cl, x = sorteia_classes(rng, n_iso // 2, n_iso // 2), 5.0
    for i in range(n_iso):
        add('s2_intercalados', '', cl[i], x, FAIXAS_Y['s2_intercalados'] + rng.uniform(-.5, .5))
        x += rng.uniform(1.5, 2.5)
    # s3a: aglomerados de uma classe só (metade de cada classe)
    metade = n_cl // 2
    cls = list(rng.permutation(['saudavel'] * metade + ['branqueado'] * metade))
    for g, (cx, c) in enumerate(zip(centros, cls), 1):
        for (px, py) in cluster_pos(rng, cx, FAIXAS_Y['s3a_aglom_puro'], tam_cl):
            add('s3a_aglom_puro', f'g{g}', c, px, py)
    # s3b: aglomerados mistos (maioria saudável ou maioria branqueada)
    base = [(3, 1), (1, 3)] if leve else [(3, 2), (2, 3), (3, 2), (2, 3)]
    comp = list(rng.permutation(base))
    for g, (cx, (nh, nb)) in enumerate(zip(centros, comp), 1):
        classes = sorteia_classes(rng, int(nh), int(nb))
        for (px, py), c in zip(cluster_pos(rng, cx, FAIXAS_Y['s3b_aglom_misto'], tam_cl), classes):
            add('s3b_aglom_misto', f'g{g}', c, px, py)
    # s4: ambíguos
    for i in range(n_dif):
        add('s4_dificil', '', 'ambiguo', 5.0 + 2.0 * i, FAIXAS_Y['s4_dificil'])
    for i, e in enumerate(sp, 1):
        e['id'] = f'P{i:03d}'
    return sp


# ----------------------------------------------------------------------------- SDF
def cabeca_sdf():
    s = open(os.path.join(WORLDS, 'coral_world_textura.sdf')).read()
    return s[:s.index('    <!-- fundo de areia')]




def bloco_foto(nome, e):
    return f'''    <model name="{nome}">
      <static>true</static>
      <pose>{e['x']:.3f} {e['y']:.3f} {e['z_foto']:.3f} 0 0 {e['yaw']:.3f}</pose>
      <link name="link">
        <visual name="visual">
          <geometry><plane><normal>0 0 1</normal><size>{e['plano'][0]} {e['plano'][1]}</size></plane></geometry>
          <material>
            <ambient>1 1 1 1</ambient><diffuse>1 1 1 1</diffuse>
            <pbr><metal>
              <albedo_map>model://bluerov2_description/models/coral_textures_prova/{e['foto']}</albedo_map>
              <roughness>0.9</roughness><metalness>0.0</metalness>
            </metal></pbr>
          </material>
        </visual>
      </link>
    </model>'''


def bloco_cad(nome, e):
    s = e['escala_cad']
    return f'''    <model name="{nome}">
      <static>true</static>
      <pose>{e['x']:.3f} {e['y']:.3f} {e['z_cad']:.3f} 0 0 {e['yaw']:.3f}</pose>
      <link name="link">
        <visual name="visual">
          <geometry><mesh>
            <uri>model://bluerov2_description/models/coral_recife/{e['especie']}.glb</uri>
            <scale>{s:.4f} {s:.4f} {s:.4f}</scale>
          </mesh></geometry>
          <material>
            <ambient>1 1 1 1</ambient><diffuse>1 1 1 1</diffuse>
            <pbr><metal>
              <albedo_map>model://bluerov2_description/models/coral_prova_tex/{e['textura']}.jpg</albedo_map>
              <roughness>0.9</roughness><metalness>0.0</metalness>
            </metal></pbr>
          </material>
        </visual>
      </link>
    </model>'''



# ----------------------------------------------------------------------------- modo misto (com morros)
Y_FOTOS, Y_CAD = -9.0, 9.0       # centro da zona de cada conjunto (as faixas ficam em y = centro + FAIXAS_Y)


class MascaraPlana:
    """Quais pontos do fundo são planos o bastante para um plano de foto (calculado uma vez)."""

    def __init__(self, t, passo=0.25):
        self.t, self.passo = t, passo
        self.n = int((2 * (t.metade - 1)) / passo) + 1
        self.o = -(t.metade - 1)
        m = np.zeros((self.n, self.n), bool)
        for i in range(self.n):
            for j in range(self.n):
                inc, res = t.plano(self.o + i * passo, self.o + j * passo, 0.7)
                m[i, j] = inc < 3.0 and res < 0.03
        self.m = m

    def mais_perto(self, ix, iy, usados, dmin=0.8, rmax=6.0):
        ci, cj = int(round((ix - self.o) / self.passo)), int(round((iy - self.o) / self.passo))
        R = int(rmax / self.passo)
        melhor = None
        for i in range(max(0, ci - R), min(self.n, ci + R + 1)):
            for j in range(max(0, cj - R), min(self.n, cj + R + 1)):
                if not self.m[i, j]:
                    continue
                x, y = self.o + i * self.passo, self.o + j * self.passo
                d = math.hypot(x - ix, y - iy)
                if d > rmax or (melhor and d >= melhor[0]):
                    continue
                if any(math.hypot(x - ux, y - uy) < dmin for ux, uy in usados):
                    continue
                melhor = (d, x, y)
        return melhor


def lugares_fotos(sp, masc, y0, dx):
    usados, out = [], []
    for e in sp:
        r = masc.mais_perto(e['x'] + dx, e['y'] + y0, usados)
        if r is None:
            return None
        d, x, y = r
        usados.append((x, y))
        out.append((x, y, d))
    return out


def posiciona_misto(sp, t):
    """Duas listas (foto e cad) com posições reais sobre o relevo.

    Planos de foto só ficam em chão plano; por isso procuro onde pôr a zona das fotos (y0 e um
    pequeno deslocamento em x) para a foto ficar o mais perto possível da posição ideal."""
    masc = MascaraPlana(t)
    melhor = None
    for y0 in np.arange(-21.0, -5.9, 0.5):
        for dx in (-1.0, 0.0, 1.0, 2.0):
            r = lugares_fotos(sp, masc, y0, dx)
            if r is None:
                continue
            ds = [d for _, _, d in r]
            chave = (float(np.mean(ds)) + 0.5 * float(max(ds)))
            if melhor is None or chave < melhor[0]:
                melhor = (chave, y0, dx, r)
    if melhor is None:
        raise SystemExit('não achei onde pôr a zona das fotos')
    _, y0, dx, lugares = melhor
    fotos, cads = [], []
    for e, (x, y, d) in zip(sp, lugares):
        f, c = dict(e), dict(e)
        gx, gy = np.meshgrid(np.linspace(-.3, .3, 5), np.linspace(-.3, .3, 5))
        f.update(x=x, y=y, x_ideal=e['x'] + dx, y_ideal=e['y'] + y0, desloc=d,
                 z_foto=max(t.h(x + p, y + q) for p, q in zip(gx.ravel(), gy.ravel())) + 0.012)
        c['x'], c['y'] = e['x'], e['y'] + Y_CAD
        c.update(x_ideal=c['x'], y_ideal=c['y'], desloc=0.0)
        r = 0.2   # assenta pelo ponto mais baixo sob a base (enterra um pouco em vez de flutuar)
        gx, gy = np.meshgrid(np.linspace(-r, r, 5), np.linspace(-r, r, 5))
        c['z_cad'] = min(t.h(c['x'] + p, c['y'] + q) for p, q in zip(gx.ravel(), gy.ravel())) - 0.01
        fotos.append(f)
        cads.append(c)
    return fotos, cads, float(y0), float(dx)


def escreve_misto(fotos, cads, y_fotos):
    corpo = '\n'.join(bloco_foto(f"imagem_{e['id']}_{e['situacao']}_{e['classe']}", e) for e in fotos)
    corpo += '\n\n' + '\n'.join(bloco_cad(f"cad_{e['id']}_{e['situacao']}_{e['classe']}", e) for e in cads)
    txt = cabeca_sdf() + f'''    <!-- MUNDO DE PROVA MISTO, com morros. Gerado por scripts/make_world_prova.py; não edite à mão.
         Fotos (objetos imagem_<id>_...) na zona y<0 (faixas em y = {y_fotos + min(FAIXAS_Y.values())} a {y_fotos + max(FAIXAS_Y.values())});
         corais 3D (objetos cad_<id>_...) na zona y>0 (faixas em y = {Y_CAD + min(FAIXAS_Y.values())} a {Y_CAD + max(FAIXAS_Y.values())}).
         O mesmo id (P001...) tem a mesma situação e a mesma classe nas duas zonas.
         Verdade de terreno em worlds/prova_manifesto.csv. Precisa de arquivos locais fora do git (ver README). -->
    <include>
      <uri>model://bluerov2_description/models/sand_heightmap</uri>
      <name>seabed</name>
      <pose>0 0 {FUNDO_Z} 0 0 0</pose>
    </include>

''' + corpo + '\n\n  </world>\n</sdf>\n'
    open(os.path.join(WORLDS, 'coral_world_prova.sdf'), 'w').write(txt)


# ----------------------------------------------------------------------------- principal
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--datasets', required=True, help='pasta onde estão os datasets (layout do kagglehub)')
    ap.add_argument('--excluir', help='arquivo de texto com nomes de imagens do TREINO, uma por linha')
    ap.add_argument('--pool', default='ambos', choices=['ambos', 'A', 'B'], help='A=vencerlanz09, B=sonainjamil')
    ap.add_argument('--seed', type=int, default=11)
    ap.add_argument('--completo', action='store_true',
                    help='mundo completo (70 espécimes por conjunto, pesado); o padrão é o leve (32 por conjunto)')
    ap.add_argument('--folhas', help='pasta para salvar folhas de contato das fotos escolhidas (curadoria)')
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    base = os.path.abspath(os.path.expanduser(a.datasets))
    excluir = set(open(a.excluir).read().split()) if a.excluir else set()

    sp = monta_layout(rng, leve=not a.completo)
    pedidos = {c: sum(1 for e in sp if e['classe'] == c) for c in ('saudavel', 'branqueado', 'ambiguo')}
    cand = candidatos(listar(base, a.pool, excluir))
    for c, n in pedidos.items():
        if len(cand[c]) < n:
            sys.exit(f'só há {len(cand[c])} fotos candidatas de "{c}", são necessárias {n}')
    perm = {c: list(rng.permutation(cand[c])) for c in pedidos}
    fb = {i['chave']: i for i in cand['branqueado']}
    if all(k in fb for k in BRANQUEADAS_ESCOLHIDAS) and len(BRANQUEADAS_ESCOLHIDAS) >= pedidos['branqueado']:
        escolhidas = [fb[k] for k in BRANQUEADAS_ESCOLHIDAS]
        ordem = np.random.default_rng(a.seed + 3).permutation(len(escolhidas))
        perm['branqueado'] = [escolhidas[i] for i in ordem] + [i for i in perm['branqueado'] if i['chave'] not in BRANQUEADAS_ESCOLHIDAS]
    fixas = {i['chave']: i for i in cand['ambiguo']}
    if all(k in fixas for k in AMBIGUAS_ESCOLHIDAS) and len(AMBIGUAS_ESCOLHIDAS) >= pedidos['ambiguo']:
        perm['ambiguo'] = [fixas[k] for k in AMBIGUAS_ESCOLHIDAS] + [i for i in perm['ambiguo'] if i['chave'] not in AMBIGUAS_ESCOLHIDAS]
    # Cada posição j tem a sua sequência de reposição perm[j], perm[j+n], perm[j+2n]...: rejeitar uma
    # foto só troca aquela posição e não desloca as outras.
    # Reserva final para 'branqueado' (o grupo mais escasso): fotos que o dataset rotula como branqueadas mas
    # com menos branco na métrica (caíram no balde 'ambiguo'), fora das escolhidas à mão. Sorteio separado,
    # para não alterar o resto da seleção.
    r2 = np.random.default_rng(a.seed + 2)
    extra = list(r2.permutation([i for i in cand['ambiguo']
                                 if i['rotulo'] == 'branqueado' and i['chave'] not in AMBIGUAS_ESCOLHIDAS]))

    def posicao(c, j):
        n = pedidos[c]
        cadeia = [perm[c][k] for k in range(j, len(perm[c]), n)]
        if c == 'branqueado':
            cadeia += [extra[k] for k in range(j, len(extra), n)]
        for it in cadeia:
            if it['chave'] not in REJEITADAS:
                return it
        raise SystemExit(f'sem fotos de reposição para "{c}"')
    escolha = {c: [posicao(c, j) for j in range(n)] for c, n in pedidos.items()}
    print('candidatas (sem duplicatas):', {c: len(v) for c, v in cand.items()}, '| usadas:', pedidos)

    # cores dos corais 3D a partir das fotos do próprio dataset
    paleta, pesos = paleta_saudavel(cand['saudavel'], rng)
    bq = cor_branqueado(cand['branqueado'])
    print('paleta saudável (RGB, peso):', [(c, round(p, 2)) for c, p in zip(paleta, pesos)], '| branqueado:', bq)

    fotos_dir = os.path.join(MODELS, 'coral_textures_prova')
    shutil.rmtree(fotos_dir, ignore_errors=True)
    os.makedirs(fotos_dir)
    for e in sp:
        it = escolha[e['classe']].pop()
        ext = os.path.splitext(it['arquivo'])[1].lower()
        e['foto'] = f"{e['id']}{ext}"
        shutil.copyfile(it['caminho'], os.path.join(fotos_dir, e['foto']))
        w, h = it['tam']
        e['plano'] = (LADO_FOTO, round(LADO_FOTO * h / w, 3)) if w >= h else (round(LADO_FOTO * w / h, 3), LADO_FOTO)
        e['fonte'] = it['chave']
        e['rotulo_dataset'] = it['rotulo']
        e['branco_foto'] = round(it['branco'], 3)
        # versão cad: mesma classe, espécie sorteada
        e['especie'] = mw.TODAS[rng.integers(len(mw.TODAS))]
        e['escala_cad'] = mw.ALVO[e['especie']] * rng.uniform(.9, 1.15) / mw.MAIOR_LADO[e['especie']]

    # texturas procedurais dos corais 3D (cores medidas nas fotos)
    tex_dir = os.path.join(MODELS, 'coral_prova_tex')
    os.makedirs(tex_dir, exist_ok=True)
    sr.CORES['branqueado_medido'] = bq
    for k, c in enumerate(paleta, 1):
        sr.CORES[f'saudavel_c{k}'] = c
    trng = np.random.default_rng(a.seed + 1)
    sr.textura('b', 'branqueado_medido', [], 0, trng).save(os.path.join(tex_dir, 'branqueado.jpg'), quality=88)
    nomes_saud = []
    for k in range(1, len(paleta) + 1):
        sr.textura('s', f'saudavel_c{k}', [], 0, trng).save(os.path.join(tex_dir, f'saudavel_c{k}.jpg'), quality=88)
        sr.textura('p', f'saudavel_c{k}', ['branqueado_medido'], 0.38, trng).save(os.path.join(tex_dir, f'parcial_c{k}.jpg'), quality=88)
        nomes_saud.append(f'saudavel_c{k}')
    sr.CORES['x1'], sr.CORES['x2'] = paleta[1], paleta[2]
    sr.textura('m', f'saudavel_c1', ['x1', 'x2', 'branqueado_medido'], 0.55, trng).save(os.path.join(tex_dir, 'multicolor.jpg'), quality=88)
    p = np.array(pesos) / sum(pesos)
    for e in sp:
        if e['classe'] == 'saudavel':
            e['textura'] = nomes_saud[rng.choice(len(nomes_saud), p=p)]
        elif e['classe'] == 'branqueado':
            e['textura'] = 'branqueado'
        else:
            e['textura'] = 'multicolor' if rng.random() < .4 else f'parcial_c{rng.choice(len(paleta), p=p) + 1}'

    th = mw.Terreno()                      # fundo com morros (modelo sand_heightmap)
    fotos, cads, y_fotos, dx_fotos = posiciona_misto(sp, th)
    escreve_misto(fotos, cads, y_fotos)
    with open(os.path.join(WORLDS, 'prova_manifesto.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['id', 'tipo', 'situacao', 'grupo', 'classe_gt', 'x', 'y', 'z', 'yaw_rad', 'x_ideal', 'y_ideal',
                    'desloc_m', 'tamanho_m', 'fonte', 'rotulo_dataset', 'branco_na_foto', 'especie', 'textura'])
        for tipo, lst in (('imagem', fotos), ('cad', cads)):
            for e in lst:
                base_row = [e['id'], tipo, e['situacao'], e['grupo'], e['classe'], f"{e['x']:.3f}", f"{e['y']:.3f}"]
                if tipo == 'imagem':
                    w.writerow(base_row[:7] + [f"{e['z_foto']:.3f}", f"{e['yaw']:.3f}", f"{e['x_ideal']:.3f}", f"{e['y_ideal']:.3f}",
                                               f"{e['desloc']:.2f}", max(e['plano']), e['fonte'], e['rotulo_dataset'], e['branco_foto'], '', ''])
                else:
                    w.writerow(base_row[:7] + [f"{e['z_cad']:.3f}", f"{e['yaw']:.3f}", f"{e['x_ideal']:.3f}", f"{e['y_ideal']:.3f}",
                                               '0.00', round(mw.ALVO[e['especie']], 3), '', '', '', e['especie'], e['textura']])
    # caminho sugerido acompanhando o relevo: 1,5 m acima do ponto mais alto numa janela ao redor
    caminho = {}
    for zona, y0 in (('fotos', y_fotos), ('cad', Y_CAD)):
        lista, ida = [], True
        for dy in FAIXAS_Y.values():
            y = y0 + dy
            xs = np.arange(3.0, 26.0 + 1e-9, 1.0)
            xs = xs if ida else xs[::-1]
            for x in xs:
                zmax = max(th.h(x + i, y + j) for i in (-1.5, 0, 1.5) for j in (-0.8, 0, 0.8))
                lista.append([round(float(x), 2), round(float(y), 2), round(float(zmax + ALTURA_VOO), 2)])
            ida = not ida
        caminho[zona] = lista
    json.dump({'modo': 'misto', 'semente': a.seed, 'zonas_y': {'fotos': y_fotos, 'cad': Y_CAD}, 'deslocamento_x_fotos': dx_fotos, 'faixas_dy': FAIXAS_Y,
               'altura_sobre_o_morro_m': ALTURA_VOO, 'caminho_sugerido_xyz': caminho,
               'situacoes': {k: sum(1 for e in sp if e['situacao'] == k) for k in FAIXAS_Y}, 'classes': pedidos,
               'deslocamento_medio_fotos_m': round(float(np.mean([e['desloc'] for e in fotos])), 2),
               'deslocamento_max_fotos_m': round(float(max(e['desloc'] for e in fotos)), 2),
               'paleta_saudavel_rgb': paleta, 'branqueado_rgb': bq},
              open(os.path.join(WORLDS, 'prova_manifesto_misto.json'), 'w'), indent=1)
    print(f"{len(sp)} espécimes de cada tipo no mesmo mundo -> worlds/coral_world_prova.sdf + prova_manifesto.csv")
    print(f"foto: deslocamento até o trecho plano  média {np.mean([e['desloc'] for e in fotos]):.2f} m, máx {max(e['desloc'] for e in fotos):.2f} m")

    if a.folhas:
        os.makedirs(a.folhas, exist_ok=True)
        for k in range(0, len(sp), 20):
            sheet = Image.new('RGB', (5 * 240, 4 * 240), (30, 30, 30))
            d = ImageDraw.Draw(sheet)
            for j, e in enumerate(sp[k:k + 20]):
                im = Image.open(os.path.join(fotos_dir, e['foto'])).convert('RGB')
                im.thumbnail((240, 240))
                x, y = (j % 5) * 240, (j // 5) * 240
                sheet.paste(im, (x, y))
                d.rectangle((x, y, x + 150, y + 14), fill=(0, 0, 0))
                d.text((x + 3, y + 2), f"{e['id']} {e['classe']} {e['fonte'].split('/')[-1][:12]}", fill=(255, 255, 0))
            sheet.save(os.path.join(a.folhas, f'folha_{k // 20 + 1}.png'))


if __name__ == '__main__':
    main()
