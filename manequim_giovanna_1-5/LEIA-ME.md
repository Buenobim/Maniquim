# Manequim Giovanna – escala 1:5

Manequim de moulage no estilo "perna longa": perna inteira e braço removível do lado **direito** do corpo, perna esquerda cortada na coxa e presa na haste.
1 cm real = 2 mm no modelo.

## Peças (STL em mm)

| Arquivo | O que é | Tamanho aprox. (mm) |
|---|---|---|
| `manequim_tronco_perna.stl` | tronco + perna longa + coto | 80 × 58 × 288 |
| `manequim_braco.stl` | braço direito com a calota do ombro | 37 × 26 × 118 |
| `manequim_base.stl` | base 110 × 110 com encaixe da haste | 110 × 110 × 17 |
| `manequim_haste.stl` | haste Ø10 × 154 (ou use cavilha/tubo de 10 mm) | Ø10 × 154 |
| `manequim_montagem_conferencia.stl` | tudo montado, **só para conferência** | — |

Altura total montado: 306 mm (do chão ao topo do pescoço).

## Encaixes
- **Braço ↔ tronco:** face plana na cava e 2 furos Ø2,1 × 6,5 mm em cada lado. Use pedaços de filamento de 1,75 mm, ou pino de 2 mm, com cerca de 12 mm de comprimento. Cole os pinos no braço para ele continuar removível.
- **Haste:** furo Ø10,4 × 26 mm na base do coto e encaixe Ø10,4 × 14 mm na base (0,4 mm de folga).

## Medidas conferidas no modelo (cm reais)

| Medida | Tabela | Modelo |
|---|---|---|
| Busto | 90 | 90,0 |
| Cintura | 78 | 78,3 |
| Pequeno quadril | 86,5 | 86,5 |
| Quadril | 108 | 108,0 |
| Pescoço | 43 | 43,0 |
| Joelho | 37,5 | 37,5 |
| Braço (bíceps) | 31 | 31,0 |
| Cotovelo | 26 | 26,0 |
| Pulso | 15,5 | 15,5 |
| Gancho | 74,5 | **78,8** |

Medidas que não estavam na tabela e foram estimadas por proporção: coxa 61, meio da coxa 48, panturrilha 37, canela 22,5 e tornozelo 21,5.

## Alturas adotadas (cm reais, verticais)
- Gancho a 80,5 do chão (entrepernas). Cintura a 110,5 (gancho + cintura ao gancho de 30).
- A "cintura ao solo 118" da tabela não fecha com entrepernas + gancho (110,5). Prevaleceram as duas últimas.
- **Cava:** a tabela dá 26 cm acima da cintura, o que põe a axila na altura da jugular. Isso é anatomicamente impossível, então a axila foi colocada a cerca de 17 cm acima da cintura.
- Jugular a 137,5 (altura frente 27), 7ª cervical a cerca de 146,5 (altura costas 36,5), mamilos a 122 e afastados 21 cm.
- Braço: abertura de 15° em relação ao corpo, antebraço 12° à frente, 33 cm do ombro ao cotovelo e 57,5 cm até o pulso.

Não conferidas no modelo: transversais, entrecavas e ombro a ombro.

## Prancha para a cliente
`prancha_manequim_giovanna_1-5.pdf` (página 1: vistas e medidas principais; página 2: relatório completo) e `prancha_manequim_giovanna_1-5.png` (só a página 1). Para gerar de novo: `python gerar_prancha.py`.

## Regerar
`blender -b -P gerar_manequim.py -- <pasta>`. O corpo é um campo de distância com união suave entre tronco e pernas, e os seios e os glúteos são volumes próprios. Os parâmetros ficam no topo do script e a calibração dos contornos é automática.
