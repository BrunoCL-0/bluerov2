Fundo de areia copiado do projeto bluerov2_gz (https://github.com/clydemcqueen/bluerov2_gz, MIT),
que por sua vez vem do UUV Simulator (Apache-2.0, ver cabeçalho de model.sdf).
Textura: texturelib.com (ver materials/TEXTURE_LICENSE.txt).

Alteração: escala do mesh de 0.5 0.5 0.25 para 0.1 0.1 0.1.
O .dae tem uma matriz interna de escala 50, então o tamanho real é:
  lado  = 10 (vértices) * 50 * escala_xy  -> 50 m x 50 m com escala 0.1
  altura do relevo = 0.5 * 50 * escala_z  -> ~2.5 m com escala 0.1
