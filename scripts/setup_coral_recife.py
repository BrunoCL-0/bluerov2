#!/usr/bin/env python3
"""Prepara os corais 3D do mundo coral_world_recife.

Entrada: modelos CC0 do Smithsonian baixados do Sketchfab em glTF (.glb), todos numa pasta
(o download exige login, por isso é manual). Espécies usadas e links:
  Acropora cervicornis    https://sketchfab.com/3d-models/acropora-cervicornis-detail-view-addc8ad93ace4e999085d6f8151cd694
  Acropora palmata        https://sketchfab.com/3d-models/acropora-palmata-8cb986313c824ac38c373c0fabd0805f
  Seriatopora hystrix     https://sketchfab.com/3d-models/seriatopora-hystrix-b6be88ce19e14e5bb038918d111430d5
  Pseudodiploria strigosa https://sketchfab.com/3d-models/pseudodiploria-strigosa-8db353e299634cf1bfeca6f6d112582d
  Leptoseris gardineri    https://sketchfab.com/3d-models/leptoseris-gardineri-fcb2217919ab47f7a57741e3ad2d60ba
  Heliopora coerulea      https://sketchfab.com/3d-models/heliopora-coerulea-52baa08bcffc41a8adefeb00aaf492ad
  Meandrina meandrites    https://sketchfab.com/3d-models/meandrina-meandrites-95884d3e683a4c51adddea41348f1f34
  Pocillopora damicornis  https://sketchfab.com/3d-models/pocillopora-damicornis-f1bdf3535d684e6e8788d76a11807ef9
Nomes dos arquivos esperados: <especie>.glb (ex.: acropora_palmata.glb; "_detail_view" é ignorado).

Saídas:
  models/coral_recife/<especie>.glb   malha limpa (sem texturas), origem no centro da base.
                                      Fica fora do git (.gitignore).
  models/coral_recife_tex/<cor>.jpg   texturas de cor PROCEDURAIS (ruído colorido, sem terceiros),
                                      inclusive variantes com manchas de outras cores.
  models/coral_recife/especies.json   tamanho de cada malha (usado por make_world_recife.py).

A cor é aplicada no SDF (<albedo_map>) por cima da malha, então não existe um .glb por cor.
Os corais originais são esqueletos de museu: todas as cores "saudáveis" são sintéticas.

Uso:  python3 scripts/setup_coral_recife.py --input <pasta com os .glb>
Requer: pip install pillow numpy
"""
import argparse, glob, itertools, json, os, struct, sys
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(HERE, '..', 'bluerov2_description', 'models')

# cores base (RGB 0-255)
CORES = {
    'branco': (236, 233, 226), 'vermelho': (200, 32, 28), 'verde': (62, 148, 46),
    'marrom': (138, 94, 42), 'roxo': (116, 52, 158), 'azul': (44, 100, 190),
    'rosa': (232, 108, 156), 'amarelo': (222, 184, 48),
}
# variantes com manchas: nome -> (cor de fundo, [cores das manchas], fração coberta por manchas)
MANCHADAS = {
    'verde_com_branco': ('verde', ['branco'], 0.38),
    'vermelho_com_branco': ('vermelho', ['branco'], 0.38),
    'marrom_com_branco': ('marrom', ['branco'], 0.38),
    'marrom_com_verde': ('marrom', ['verde'], 0.40),
    'roxo_com_rosa': ('roxo', ['rosa'], 0.40),
    'branco_com_rosa': ('branco', ['rosa'], 0.30),
    'multicolor': ('marrom', ['verde', 'rosa', 'branco', 'amarelo'], 0.55),
}


def mat(n):
    if 'matrix' in n:
        return np.array(n['matrix']).reshape(4, 4).T
    T, S, R = np.eye(4), np.eye(4), np.eye(4)
    if 'translation' in n: T[:3, 3] = n['translation']
    if 'scale' in n: S = np.diag(list(n['scale']) + [1])
    if 'rotation' in n:
        x, y, z, w = n['rotation']
        R[:3, :3] = [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                     [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                     [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]]
    return T @ R @ S


def ler_glb(caminho):
    b = open(caminho, 'rb').read()
    if b[:4] != b'glTF':
        sys.exit(f'{caminho} não é um .glb')
    jlen, _ = struct.unpack('<I4s', b[12:20])
    j = json.loads(b[20:20 + jlen])
    bo = 20 + jlen + 8
    return j, b[bo:bo + struct.unpack('<I', b[20 + jlen:24 + jlen])[0]]


def escrever_glb(caminho, j, blob):
    jb = json.dumps(j, separators=(',', ':')).encode()
    jb += b' ' * (-len(jb) % 4)
    blob += b'\0' * (-len(blob) % 4)
    with open(caminho, 'wb') as f:
        f.write(struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(jb) + 8 + len(blob)))
        f.write(struct.pack('<I4s', len(jb), b'JSON') + jb)
        f.write(struct.pack('<I4s', len(blob), b'BIN\0') + blob)


def caixa(j):
    """Caixa envolvente no referencial final (com as transformações dos nós aplicadas)."""
    lo, hi = np.full(3, 1e30), np.full(3, -1e30)

    def anda(i, M):
        nonlocal lo, hi
        n = j['nodes'][i]
        M = M @ mat(n)
        if 'mesh' in n:
            for p in j['meshes'][n['mesh']]['primitives']:
                a = j['accessors'][p['attributes']['POSITION']]
                for c in itertools.product(*zip(a['min'], a['max'])):
                    q = (M @ np.array(list(c) + [1]))[:3]
                    lo, hi = np.minimum(lo, q), np.maximum(hi, q)
        for c in n.get('children', []):
            anda(c, M)
    for r in j['scenes'][j.get('scene', 0)]['nodes']:
        anda(r, np.eye(4))
    return lo, hi


def limpar(j, blob):
    """Remove texturas/materiais e põe a origem no centro da base (menor z). Eixo vertical = z."""
    lo, hi = caixa(j)
    centro = (lo + hi) / 2
    tx = [-centro[0], -centro[1], -lo[2]]
    img_views = {im['bufferView'] for im in j.get('images', []) if 'bufferView' in im}
    usados = {a['bufferView'] for a in j['accessors'] if 'bufferView' in a}
    if img_views & usados or (img_views and min(img_views) < max(usados)):
        sys.exit('layout inesperado: imagens misturadas com a geometria')
    fim = 0
    for i, v in enumerate(j['bufferViews']):
        if i not in img_views:
            fim = max(fim, v.get('byteOffset', 0) + v['byteLength'])
    j['bufferViews'] = [v for i, v in enumerate(j['bufferViews']) if i not in img_views]
    for k in ('images', 'textures', 'samplers'):
        j.pop(k, None)
    j['materials'] = [{'name': 'coral', 'pbrMetallicRoughness': {'metallicFactor': 0.0, 'roughnessFactor': 0.9}}]
    for m in j['meshes']:
        for p in m['primitives']:
            p['material'] = 0
    cena = j['scenes'][j.get('scene', 0)]
    j['nodes'].append({'name': 'pivo', 'translation': tx, 'children': list(cena['nodes'])})
    cena['nodes'] = [len(j['nodes']) - 1]
    j['buffers'][0]['byteLength'] = fim
    j.setdefault('asset', {}).setdefault('extras', {})['modification'] = \
        'texturas removidas e origem movida para o centro da base por scripts/setup_coral_recife.py'
    return blob[:fim], (hi - lo)


def textura(nome, base, manchas, fracao, rng, tam=1024):
    """Ruído colorido (grão fino + variação suave); com manchas de outras cores se pedido."""
    fino = rng.normal(0, 0.09, (tam, tam, 1))
    suave = np.asarray(Image.fromarray((rng.random((64, 64)) * 255).astype(np.uint8))
                       .resize((tam, tam), Image.BICUBIC).filter(ImageFilter.GaussianBlur(8))).astype(float)[..., None] / 255
    var = 1 + fino + (suave - 0.5) * 0.35
    img = np.array(CORES[base], float)[None, None, :] * np.ones((tam, tam, 1))
    if manchas:
        campo = np.asarray(Image.fromarray((rng.random((24, 24)) * 255).astype(np.uint8))
                           .resize((tam, tam), Image.BICUBIC).filter(ImageFilter.GaussianBlur(10))).astype(float)
        corte = np.quantile(campo, 1 - fracao)
        mascara = campo >= corte
        qual = np.asarray(Image.fromarray((rng.random((8, 8)) * 255).astype(np.uint8))
                          .resize((tam, tam), Image.BICUBIC).filter(ImageFilter.GaussianBlur(20))).astype(float)
        bins = np.quantile(qual, np.linspace(0, 1, len(manchas) + 1)[1:-1]) if len(manchas) > 1 else []
        idx = np.digitize(qual, bins)
        for k, cm in enumerate(manchas):
            sel = mascara & (idx == k)
            img[sel] = np.array(CORES[cm], float)
    return Image.fromarray(np.clip(img * var, 0, 255).astype(np.uint8))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--input', required=True, help='pasta com os .glb baixados')
    a = ap.parse_args()
    arquivos = sorted(glob.glob(os.path.join(os.path.expanduser(a.input), '*.glb')))
    if not arquivos:
        sys.exit(f'Nenhum .glb em {a.input}. Veja os links no topo deste script.')
    saida = os.path.join(MODELS, 'coral_recife'); os.makedirs(saida, exist_ok=True)
    tex = os.path.join(MODELS, 'coral_recife_tex'); os.makedirs(tex, exist_ok=True)

    esp = {}
    for f in arquivos:
        nome = os.path.basename(f)[:-4].replace('_detail_view', '')
        j, blob = ler_glb(f)
        novo, tam = limpar(j, blob)
        destino = os.path.join(saida, nome + '.glb')
        escrever_glb(destino, j, novo)
        esp[nome] = {'tamanho_m': [round(float(v), 5) for v in tam], 'maior_lado_m': round(float(tam.max()), 5)}
        print(f'ok  {nome}.glb  {os.path.getsize(destino) / 1e6:.1f} MB  maior lado {tam.max():.4f}')
    json.dump(esp, open(os.path.join(saida, 'especies.json'), 'w'), indent=1)

    rng = np.random.default_rng(12345)
    for c in CORES:
        textura(c, c, [], 0, rng).save(os.path.join(tex, c + '.jpg'), quality=88)
    for n, (base, man, fr) in MANCHADAS.items():
        textura(n, base, man, fr, rng).save(os.path.join(tex, n + '.jpg'), quality=88)
    print(f'{len(CORES) + len(MANCHADAS)} texturas em {tex}')


if __name__ == '__main__':
    main()
