# Malhas de coral (coral_recife)

Oito modelos 3D da coleção de corais do Smithsonian Institution (Museu Nacional de História Natural),
publicados no Sketchfab em domínio público (**CC0 1.0**, http://creativecommons.org/publicdomain/zero/1.0/).
A licença também está gravada no próprio arquivo original (campo `asset.extras` do glTF).

| Arquivo | Espécie | Origem |
|---|---|---|
| `acropora_cervicornis.glb` | *Acropora cervicornis* | https://sketchfab.com/3d-models/acropora-cervicornis-detail-view-addc8ad93ace4e999085d6f8151cd694 |
| `acropora_palmata.glb` | *Acropora palmata* | https://sketchfab.com/3d-models/acropora-palmata-8cb986313c824ac38c373c0fabd0805f |
| `seriatopora_hystrix.glb` | *Seriatopora hystrix* | https://sketchfab.com/3d-models/seriatopora-hystrix-b6be88ce19e14e5bb038918d111430d5 |
| `pseudodiploria_strigosa.glb` | *Pseudodiploria strigosa* | https://sketchfab.com/3d-models/pseudodiploria-strigosa-8db353e299634cf1bfeca6f6d112582d |
| `leptoseris_gardineri.glb` | *Leptoseris gardineri* | https://sketchfab.com/3d-models/leptoseris-gardineri-fcb2217919ab47f7a57741e3ad2d60ba |
| `heliopora_coerulea.glb` | *Heliopora coerulea* | https://sketchfab.com/3d-models/heliopora-coerulea-52baa08bcffc41a8adefeb00aaf492ad |
| `meandrina_meandrites.glb` | *Meandrina meandrites* | https://sketchfab.com/3d-models/meandrina-meandrites-95884d3e683a4c51adddea41348f1f34 |
| `pocillopora_damicornis.glb` | *Pocillopora damicornis* | https://sketchfab.com/3d-models/pocillopora-damicornis-f1bdf3535d684e6e8788d76a11807ef9 |

Cada modelo é um espécime de museu seco (esqueleto), digitalizado por fotogrametria.

## Alterações em relação aos originais

Feitas por `scripts/setup_coral_recife.py`: texturas e materiais removidos (a cor vem do SDF, por imagem) e a origem da
malha movida para o centro da base. A geometria não foi alterada. O tamanho real de cada espécime não consta na fonte;
as escalas usadas nos mundos são estimativas. Os campos de autoria e licença do glTF original foram mantidos no arquivo.

`especies.json` guarda o maior lado de cada malha (usado por `scripts/make_world_recife.py`).
