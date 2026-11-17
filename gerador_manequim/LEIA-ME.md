# Gerador de manequim de moulage

O gerador cria o manequim no formato "perna longa" (perna inteira, coto da outra perna e braço removível), na escala que você escolher, a partir da tabela de medidas. Ele usa as mesmas linhas da tabela da cliente.

## Plataforma (recomendado)

Dê dois cliques em **`Abrir gerador.bat`**. O navegador abre em `http://localhost:8770`. Se preferir o terminal:

```bash
python servidor.py
```

- **Montador (esquerda):** escolha feminino ou masculino, a escala, o lado e se tem braço. Depois preencha as medidas, nos mesmos grupos coloridos da planilha. Use as setas ↑ ↓ ou os botões − + para variar de 0,5 em 0,5 cm.
- **Manequim 3D (centro):** atualiza enquanto você digita. Ao passar o mouse ou clicar numa medida, a linha dela acende no corpo, com o valor em cm e em mm na escala, e a definição de como medir aparece embaixo. Dá para girar com o mouse e usar as vistas Frente, Lado, Costas e 3/4.
- **Ficha técnica (direita):** contornos (tabela × prévia × mm), conferência das medidas, alturas usadas no modelo e o botão **Gerar arquivos para impressão**. Ele roda o gerador completo, leva cerca de 1 minuto e deixa os STL e a prancha para baixar.
- **Planilha:** o seletor "Pessoa / tamanho" lê as colunas da `planilha_medidas.xlsx`, e **Salvar na planilha** grava a coluna (feche a planilha no Excel antes).
- **Bolinhas ao lado de cada medida:**

| Bolinha | Significado |
|---|---|
| verde | informada |
| tracejada | vazia, estimada por proporção |
| vazada vermelha | obrigatória faltando |
| laranja | ajustada no modelo |
| vermelha | fora da faixa usual de adultos |

- **Prévia × arquivo final:** a prévia é uma estimativa rápida feita no navegador, sem a união suave entre tronco e pernas. As medidas que valem são as do arquivo gerado, que aparecem na tabela "Final" e na prancha.

Funciona no seu computador. Numa reunião, compartilhe a tela. O 3D usa a biblioteca three.js, carregada da internet na primeira abertura.

## Pela linha de comando

1. Abra a `planilha_medidas.xlsx` e preencha uma coluna por pessoa ou tamanho (Giovanna, Rafael, P, M, G). Você pode renomear e acrescentar colunas.
2. Rode o comando abaixo para gerar todas as colunas preenchidas:

```bash
python gerar.py
```

Para gerar só uma coluna:

```bash
python gerar.py --pessoa Giovanna
```

Para só conferir a planilha e ver os avisos, sem modelar (é instantâneo):

```bash
python gerar.py --conferir
```

Também dá para usar outra planilha no mesmo formato: `python gerar.py outra_planilha.xlsx`.

Cada pessoa leva cerca de 1 minuto. O resultado fica em `saida/<Nome>/`:

| Arquivo | O que é |
|---|---|
| `manequim_tronco_perna.stl`, `manequim_braco.stl`, `manequim_base.stl`, `manequim_haste.stl` | peças para imprimir (mm) |
| `manequim_montagem_conferencia.stl` | tudo montado, só para olhar |
| `prancha_manequim_<Nome>.pdf` | página 1: vistas e contornos; página 2: relatório completo |
| `prancha_manequim_<Nome>.png` e `..._relatorio.png` | as duas páginas em imagem (fácil de mandar no Instagram ou WhatsApp) |
| `relatorio_medidas.json`, `projeto.json`, `log_blender.txt` | dados técnicos |

Precisa de Python com `openpyxl`, `numpy` e `matplotlib`, e do Blender 4.2 ou mais novo. O gerador acha o Blender sozinho; se não achar, defina a variável `BLENDER`.

## A planilha

- **Amarelo (contornos), azul (alturas) e branco:** iguais à tabela da cliente.
- **Obrigatórias:** busto, cintura, quadril, pescoço, ombro, braço, cotovelo, pulso, joelho, as alturas do corpo frente, costas e busto, cintura ao gancho, entrepernas, comprimento do braço, altura do cotovelo e abertura do busto. As outras, se vazias, são estimadas por proporção, e a prancha avisa.
- **Medidas extras (verde, opcionais):** altura total (só para conferir as proporções), coxa, panturrilha e tornozelo. Se ficarem vazias, são estimadas por regressão na base ANSUR II, a partir do quadril, braço, pulso e entrepernas (veja abaixo).
- **Opções (cinza):** sexo (F ou M), escala (5 = 1:5), lado da perna longa e do braço (D/E), com braço (Sim/Não) e abertura do braço em graus.

## O que o gerador confere sozinho

Esses avisos aparecem no terminal, na plataforma e na prancha, em "Para confirmar com você":

- Cintura ao solo × (entrepernas + cintura ao gancho). Prevalece a soma.
- Altura da cava: a axila precisa ficar, entre o gancho e a 7ª cervical, na faixa de 99% das pessoas da ANSUR II. Fora disso, é ajustada para a posição mediana.
- Pescoço coerente com busto, braço e pulso. Se ficar a mais de 2,5 desvios-padrão do esperado, aparece o aviso com o valor esperado.
- Gancho coerente com a cintura ao gancho e o quadril (mesmo critério).
- Cada medida dentro da faixa de 99% das pessoas da ANSUR II, do mesmo sexo.
- Altura corpo frente × costas incoerentes, altura do busto curta para a abertura dos mamilos, ombro a ombro × pescoço + ombro, altura total × alturas do tronco.
- Depois de modelar, qualquer contorno que ficou mais de 1 cm fora da tabela (normalmente o gancho).

## Base estatística: ANSUR II

[ANSUR II](https://www.openlab.psu.edu/ansur2/) é o levantamento antropométrico do Exército dos EUA feito em 2012, com 1.986 mulheres e 4.082 homens medidos e dados públicos. Os arquivos estão em `dados/ansur2/`. O `ansur.py` gera o `dados/ansur2_modelos.json`, com três coisas:

- **Faixas:** percentis de 0,5% e 99,5% de cada medida que existe nas duas tabelas (busto, quadril, pescoço, braço, pulso, coxa, panturrilha, tornozelo, entrepernas, altura total, ombro, cotovelo e comprimento do braço).
- **Regressões:**

| Medida | Precisão (fem.) | Calculada a partir de |
|---|---|---|
| coxa | R² 0,90, ± 1,8 cm | quadril, braço, entrepernas |
| panturrilha | R² 0,62, ± 1,7 cm | quadril, braço, pulso, entrepernas |
| tornozelo | R² 0,46, ± 1,1 cm | pulso, quadril, entrepernas |
| pescoço (conferência) | R² 0,54, ± 1,3 cm | busto, braço, pulso |
| gancho (conferência) | R² 0,69, ± 2,4 cm | altura cintura–gancho, quadril |

- **Proporções verticais:** posição da axila, do mamilo, da jugular e do ombro entre o gancho e a 7ª cervical, e 7ª cervical e gancho em relação à estatura.

Diferenças de definição em relação à tabela da cliente:
- A cintura da ANSUR é medida no umbigo, por isso a cintura não é conferida por ela.
- O gancho da ANSUR parte do umbigo, então é comparado por regressão e não direto.
- A base é de uma população militar norte-americana: serve como referência estatística, não como padrão de tamanhos brasileiro.

Para recalcular os modelos:

```bash
python ansur.py
```

## Como funciona

- Há dois **corpos-base**: o feminino (o manequim da Giovanna) e um masculino (tronco reto, ombros largos, peitoral e glúteos discretos, quadril estreito). Coloque `M` na linha "Sexo" para usar o masculino; nele, a linha "Busto" é o tórax.
- No corpo-base escolhido, cada altura (gancho, quadril, cintura, busto, cava, ombro, pescoço…) é levada para a altura da pessoa, e as larguras partem da proporção dos contornos.
- Depois, uma **calibração automática** ajusta o corpo até bater busto, cintura, pequeno quadril, quadril, pescoço, coxa, joelho, panturrilha, tornozelo, braço, cotovelo e pulso.
- O corpo é um campo de distância com **união suave** entre tronco e pernas, então não ficam degraus. Seios e glúteos são volumes próprios: o glúteo continua na parte de trás da coxa, e as nádegas têm o sulco no meio. As coxas mantêm uma folga entre si.
- Alturas medidas pela lateral (cintura ao quadril, ao joelho) são corrigidas pela diferença entre a cintura ao solo informada e a cintura vertical.

## Limitações

- **Formato:** a tabela só tem contornos e alturas. Postura, barriga e formato do bumbum seguem o corpo-base. Fotos de frente e de lado da pessoa ajudariam num ajuste manual.
- **Não conferidas no modelo:** transversais, entrecavas e ombro a ombro.
- **Gancho:** costuma sair 2 a 4 cm acima da tabela. A calibração não força esse valor para não achatar barriga e bumbum. A prancha mostra o valor esperado pela ANSUR II.
- **Alfinete:** o manequim é de plástico rígido e não aceita alfinete.

## Arquivos

| Arquivo | Função |
|---|---|
| `gerar.py` | comando principal |
| `medidas.py` | leitura da planilha, conferências e cálculo das alturas |
| `nucleo_blender.py` | modelagem no Blender: corpo-base, calibração, peças, furos, STL e imagens |
| `prancha.py` | prancha em PDF e PNG |
| `criar_planilha.py` | recria a planilha-modelo vazia, com a Giovanna de exemplo |
| `servidor.py` + `web/` | plataforma no navegador (prévia 3D ao vivo, planilha, geração) |
| `corpo.py` | corpos-base feminino e masculino e a deformação pelas medidas (usado pelo Blender e pela prévia) |
| `previa.py` | prévia rápida: mesmo campo de distância do arquivo final, com voxel maior, extraído por "surface nets", mais as linhas das cotas |
| `ansur.py` + `dados/` | base ANSUR II e os modelos estatísticos (faixas, regressões, proporções) |
