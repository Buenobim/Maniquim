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
- **Medidas extras (verde, opcionais):** altura total (só para conferir as proporções), coxa, panturrilha e tornozelo. Se ficarem vazias, são estimadas a partir do quadril e do joelho.
- **Opções (cinza):** sexo (F ou M), escala (5 = 1:5), lado da perna longa e do braço (D/E), com braço (Sim/Não) e abertura do braço em graus.

## O que o gerador confere sozinho

Esses avisos aparecem no terminal e na prancha, em "Para confirmar com você":

- Cintura ao solo × (entrepernas + cintura ao gancho). Prevalece a soma.
- Altura da cava fora do lugar possível (acima do pescoço ou abaixo do busto). É ajustada.
- Altura corpo frente × costas incoerentes, altura do busto curta para a abertura dos mamilos.
- Ombro a ombro × pescoço + ombro, pescoço acima da média, altura total × alturas do tronco.
- Depois de modelar, qualquer contorno que ficou mais de 1 cm fora da tabela (normalmente o gancho).

## Como funciona

- Há dois **corpos-base**: o feminino (o manequim da Giovanna) e um masculino (tronco reto, ombros largos, peitoral e glúteos discretos, quadril estreito). Coloque `M` na linha "Sexo" para usar o masculino; nele, a linha "Busto" é o tórax.
- O corpo-base escolhido Cada altura dele (gancho, quadril, cintura, busto, cava, ombro, pescoço…) é levada para a altura da pessoa, e as larguras partem da proporção dos contornos.
- Depois, uma **calibração automática** ajusta o corpo até bater busto, cintura, pequeno quadril, quadril, pescoço, coxa, joelho, panturrilha, tornozelo, braço, cotovelo e pulso.
- O corpo é um campo de distância com **união suave** entre tronco e pernas, então não ficam degraus. Seios e glúteos são volumes próprios.
- Alturas medidas pela lateral (cintura ao quadril, ao joelho) são corrigidas pela diferença entre a cintura ao solo informada e a cintura vertical.

## Limitações

- **Formato:** a tabela só tem contornos e alturas. Postura, barriga e formato do bumbum seguem o corpo-base. Fotos de frente e de lado da pessoa ajudariam num ajuste manual.
- **Não conferidas no modelo:** transversais, entrecavas e ombro a ombro.
- **Gancho:** costuma sair 3 a 5 cm acima da tabela. A calibração não força esse valor para não deformar barriga e bumbum.
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
| `previa.py` | prévia rápida (seções + calibração 2D + linhas das cotas) |
