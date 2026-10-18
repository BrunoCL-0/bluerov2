#!/usr/bin/env python3
"""Copia para models/coral_textures_prova/ as fotos EXATAS listadas em worlds/prova_manifesto.csv.

O mundo coral_world_prova usa fotos de datasets do Kaggle (licença desconhecida), que por isso não estão
no repositório. Este script monta a pasta de fotos a partir dos datasets, sem sortear nada de novo:
cada linha `imagem` do manifesto diz qual arquivo vai para qual id (P001.png, P002.jpg, ...).

Uso:
  python3 scripts/setup_photos_prova.py --download --datasets <pasta>   # baixa os datasets (sem login) e copia
  python3 scripts/setup_photos_prova.py --datasets <pasta>              # datasets já baixados
Requer: pip install kagglehub (só com --download).
"""
import argparse, csv, glob, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DESC = os.path.join(HERE, '..', 'bluerov2_description')
DATASETS = {'A': 'vencerlanz09/healthy-and-bleached-corals-image-classification',
            'B': 'sonainjamil/bleached-corals-detection'}


def raiz(base, ds):
    v = sorted(glob.glob(os.path.join(base, 'datasets', *ds.split('/'), 'versions', '*')))
    return v[-1] if v else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--datasets', default=os.path.join(HERE, '..', 'datasets'), help='pasta dos datasets (layout do kagglehub)')
    ap.add_argument('--download', action='store_true', help='baixa os datasets com kagglehub antes de copiar')
    ap.add_argument('--out', default=os.path.join(DESC, 'models', 'coral_textures_prova'))
    a = ap.parse_args()
    base = os.path.abspath(os.path.expanduser(a.datasets))

    if a.download:
        try:
            import kagglehub
        except ImportError:
            sys.exit('Instale o kagglehub primeiro: pip install kagglehub')
        os.environ['KAGGLEHUB_CACHE'] = base
        for ds in DATASETS.values():
            print('baixando', ds)
            kagglehub.dataset_download(ds)

    manifesto = os.path.join(DESC, 'worlds', 'prova_manifesto.csv')
    linhas = [r for r in csv.DictReader(open(manifesto)) if r['tipo'] == 'imagem']
    raizes = {tag: raiz(base, ds) for tag, ds in DATASETS.items()}
    os.makedirs(a.out, exist_ok=True)
    faltando = []
    for r in linhas:
        tag, rel = r['fonte'].split(':', 1)
        if not raizes.get(tag):
            faltando.append(f"{r['id']}: dataset {DATASETS.get(tag, tag)} não encontrado em {base}")
            continue
        src = os.path.join(raizes[tag], rel)
        if not os.path.isfile(src):
            faltando.append(f"{r['id']}: {r['fonte']}")
            continue
        shutil.copyfile(src, os.path.join(a.out, r['id'] + os.path.splitext(src)[1].lower()))
    if faltando:
        sys.exit('Não encontrei:\n  ' + '\n  '.join(faltando) + f'\nProcurei em: {base} (use --download ou --datasets)')

    # confere se todas as fotos referenciadas no mundo existem
    sdf = open(os.path.join(DESC, 'worlds', 'coral_world_prova.sdf')).read()
    refs = set(re.findall(r'coral_textures_prova/([^<]+)<', sdf))
    ausentes = sorted(x for x in refs if not os.path.isfile(os.path.join(a.out, x)))
    if ausentes:
        sys.exit(f'O mundo referencia fotos que não foram criadas: {ausentes[:5]}')
    print(f'{len(linhas)} fotos em {os.path.normpath(a.out)} (o mundo coral_world_prova referencia {len(refs)})')


if __name__ == '__main__':
    main()
