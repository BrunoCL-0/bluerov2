#!/usr/bin/env python3
"""Copia para o repo as fotos de coral usadas como textura no mundo coral_world_textura.

As fotos vêm de datasets do Kaggle sem licença clara e por isso NÃO ficam no git
(a pasta de destino está no .gitignore). Cada pessoa roda este script uma vez.

Uso:
  python3 scripts/setup_coral_textures.py --download            # baixa os datasets com kagglehub
  python3 scripts/setup_coral_textures.py --datasets <pasta>    # usa datasets já baixados
                                                                #  (cache do kagglehub: <pasta>/datasets/<dono>/<nome>/versions/N)
"""
import argparse, glob, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DEFAULT = os.path.join(HERE, '..', 'bluerov2_description', 'models', 'coral_textures')

VENCER = 'vencerlanz09/healthy-and-bleached-corals-image-classification'
SONAIN = 'sonainjamil/bleached-corals-detection'

# nome no mundo  ->  (dataset, caminho relativo dentro da versão)
SELECAO = {
    'saudavel_vermelho_1.png': (SONAIN, 'Train/Unbleached/109.png'),
    'saudavel_vermelho_2.png': (SONAIN, 'Train/Unbleached/123.png'),
    'saudavel_verde_1.jpg':    (VENCER, 'healthy_corals/3283358041_57a98063bb_o.jpg'),
    'saudavel_verde_2.png':    (SONAIN, 'Train/Unbleached/113.png'),
    'branqueado_1.png':        (SONAIN, 'Train/Bleached/161.png'),
    'branqueado_2.png':        (SONAIN, 'Train/Bleached/118.png'),
    'branqueado_3.jpg':        (VENCER, 'bleached_corals/392871468_82f033b05d_o.jpg'),
    'branqueado_4.png':        (SONAIN, 'Train/Bleached/105.png'),
}


def raiz_dataset(base, dataset):
    versoes = sorted(glob.glob(os.path.join(base, 'datasets', *dataset.split('/'), 'versions', '*')))
    return versoes[-1] if versoes else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--datasets', help='pasta onde estão (ou serão baixados) os datasets')
    ap.add_argument('--download', action='store_true', help='baixa os datasets com kagglehub (pip install kagglehub)')
    ap.add_argument('--out', default=OUT_DEFAULT, help='pasta de destino (padrão: models/coral_textures)')
    a = ap.parse_args()

    base = os.path.abspath(os.path.expanduser(a.datasets or os.path.join(HERE, '..', 'datasets')))
    if a.download:
        try:
            import kagglehub
        except ImportError:
            sys.exit('Instale o kagglehub primeiro: pip install kagglehub')
        os.environ['KAGGLEHUB_CACHE'] = base
        for d in (VENCER, SONAIN):
            print('baixando', d)
            kagglehub.dataset_download(d)

    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    raizes, faltando = {}, []
    for nome, (dataset, rel) in SELECAO.items():
        raiz = raizes.setdefault(dataset, raiz_dataset(base, dataset))
        src = os.path.join(raiz, rel) if raiz else None
        if not src or not os.path.isfile(src):
            faltando.append(f'{nome}  <-  {dataset}/{rel}')
            continue
        shutil.copyfile(src, os.path.join(out, nome))
        print('ok ', nome)
    if faltando:
        print('\nNão encontrei:', *faltando, sep='\n  ')
        print(f'\nProcurei em: {base}\nBaixe os datasets (veja --download) ou aponte --datasets para a pasta certa.')
        sys.exit(1)
    print(f'\n{len(SELECAO)} texturas em {out}')


if __name__ == '__main__':
    main()
