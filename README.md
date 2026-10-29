# DLG-Mini 950 3DP — Projeto Completo para Bambu Lab P2S (Nervuras Geodésicas CAD 0% Infill)

Projeto de aeromodelo RC **DLG (Discus Launch Glider)** de $950\text{ mm}$ de envergadura e $640\text{ mm}$ de comprimento, baseado na geometria oficial do **RCRCM DLG-Mini X-Tail**, otimizado para impressão 3D em **LW-PLA (com $0\%$ de Infill de fatiador)** e **PETG / PLA-CF** no volume de $256 \times 256 \times 256\text{ mm}$ da **Bambu Lab P2S**.

---

## 1. Blueprints Técnicos de Engenharia (`blueprints/`)

- [`blueprints/DLG_Mini_950_Blueprint_Orthographic.jpg`](file:///Users/pia/lab/antigravity/dlg/blueprints/DLG_Mini_950_Blueprint_Orthographic.jpg) — Prancha técnica ortográfica completa (4 vistas + corte transversal mostrando as câmaras ocas e nervuras geodésicas internas de $0\%$ Infill).
- [`blueprints/DLG_Mini_950_Blueprint_Full.svg`](file:///Users/pia/lab/antigravity/dlg/blueprints/DLG_Mini_950_Blueprint_Full.svg) — Blueprint vetorial de alta precisão com traçado exato das nervuras geodésicas a $45^\circ$, tubos de carbono e corte transversal ampliado da asa.
- [`blueprints/DLG_Mini_950_CAD_1to1.dxf`](file:///Users/pia/lab/antigravity/dlg/blueprints/DLG_Mini_950_CAD_1to1.dxf) — Desenho CAD 2D em escala 1:1 (em milímetros) dividido em *layers* para abrir diretamente no Fusion 360, AutoCAD, SolidWorks ou QCAD.

---

## 2. Como Funciona a Estrutura Interna das Asas e Cauda ($0\%$ Infill no Bambu Studio)

Todos os arquivos `.stl` das asas (`W1`, `W2`, `Flaperons`) e da cauda (`X-Tail`) em [`stl/`](file:///Users/pia/lab/antigravity/dlg/stl) já possuem **nervuras diagonais geodésicas a $45^\circ$ (treliça Warren de $0,85\text{ mm}$)** e **câmaras ocas de alívio (*Hollow Lightening Bays*)** modeladas diretamente dentro da malha 3D:
- **Casca externa de $0,45\text{ mm}$:** Imprime com apenas **1 perímetro (`Wall Loops = 1`)** no bico de $0,4\text{ mm}$.
- **Mangas cilíndricas internas contínuas:** Abraçam o tubo principal de carbono $\varnothing 6 \times 4\text{ mm}$ ($X = 49\text{ mm}$), a vareta auxiliar $\varnothing 2\text{ mm}$ ($X = 98\text{ mm}$) e a vareta antitorção do flaperon $\varnothing 2\text{ mm}$ ($X = 116\text{ mm}$).
- **Configuração obrigatória no Bambu Studio para Plate 1 e Plate 2 (LW-PLA):**
  - `Wall Loops` = **`1`**
  - `Sparse Infill Density` = **`0%`** (Zero Infill!)
  - `Enable Support` = **`Off`** (as nervuras internas têm inclinação $\le 45^\circ$ e são 100% autoportantes).

---

## 3. Modelos 3D Prontos para o Bambu Studio (`stl/`)

### Plate 1 — Asas Bipartidas e Flaperons (Filamento: **LW-PLA Ativo**, **`0% Infill`**)
- [`W1_Left_Inner_Wing_245mm.stl`](file:///Users/pia/lab/antigravity/dlg/stl/Plate1_LW-PLA_Wings/W1_Left_Inner_Wing_245mm.stl) e [`W1_Right_Inner_Wing_245mm.stl`](file:///Users/pia/lab/antigravity/dlg/stl/Plate1_LW-PLA_Wings/W1_Right_Inner_Wing_245mm.stl)
- [`W2_Left_Outer_Wing_Peg_230mm.stl`](file:///Users/pia/lab/antigravity/dlg/stl/Plate1_LW-PLA_Wings/W2_Left_Outer_Wing_Peg_230mm.stl) e [`W2_Right_Outer_Wing_230mm.stl`](file:///Users/pia/lab/antigravity/dlg/stl/Plate1_LW-PLA_Wings/W2_Right_Outer_Wing_230mm.stl)
- [`Flaperon_Left_Inner_225mm.stl`](file:///Users/pia/lab/antigravity/dlg/stl/Plate1_LW-PLA_Wings/Flaperon_Left_Inner_225mm.stl), [`Flaperon_Left_Outer_210mm.stl`](file:///Users/pia/lab/antigravity/dlg/stl/Plate1_LW-PLA_Wings/Flaperon_Left_Outer_210mm.stl), [`Flaperon_Right_Inner_225mm.stl`](file:///Users/pia/lab/antigravity/dlg/stl/Plate1_LW-PLA_Wings/Flaperon_Right_Inner_225mm.stl) e [`Flaperon_Right_Outer_210mm.stl`](file:///Users/pia/lab/antigravity/dlg/stl/Plate1_LW-PLA_Wings/Flaperon_Right_Outer_210mm.stl)

### Plate 2 — Empenagem X-Tail em Peça Única (Filamento: **LW-PLA Ativo**, **`0% Infill`**)
- [`XTail_Horizontal_Stabilizer_240mm.stl`](file:///Users/pia/lab/antigravity/dlg/stl/Plate2_LW-PLA_XTail/XTail_Horizontal_Stabilizer_240mm.stl) e [`XTail_Elevator_240mm.stl`](file:///Users/pia/lab/antigravity/dlg/stl/Plate2_LW-PLA_XTail/XTail_Elevator_240mm.stl)
- [`XTail_Vertical_Fin_175mm.stl`](file:///Users/pia/lab/antigravity/dlg/stl/Plate2_LW-PLA_XTail/XTail_Vertical_Fin_175mm.stl) e [`XTail_Rudder_175mm.stl`](file:///Users/pia/lab/antigravity/dlg/stl/Plate2_LW-PLA_XTail/XTail_Rudder_175mm.stl)

### Plate 3 — Pod da Fuselagem, Bandeja de 4 Servos e Junções M3 (Filamento: **PETG / PLA-CF**, **`25% Infill`**)
- [`Fuselage_Nose_Pod_245mm.stl`](file:///Users/pia/lab/antigravity/dlg/stl/Plate3_PETG_Structural_Pod/Fuselage_Nose_Pod_245mm.stl) e [`Fuselage_Canopy_Hatch.stl`](file:///Users/pia/lab/antigravity/dlg/stl/Plate3_PETG_Structural_Pod/Fuselage_Canopy_Hatch.stl)
- [`Servo_Tray_4x_SubMicro.stl`](file:///Users/pia/lab/antigravity/dlg/stl/Plate3_PETG_Structural_Pod/Servo_Tray_4x_SubMicro.stl)
- [`Root_Rib_Joiner_Left_M3.stl`](file:///Users/pia/lab/antigravity/dlg/stl/Plate3_PETG_Structural_Pod/Root_Rib_Joiner_Left_M3.stl) e [`Root_Rib_Joiner_Right_M3.stl`](file:///Users/pia/lab/antigravity/dlg/stl/Plate3_PETG_Structural_Pod/Root_Rib_Joiner_Right_M3.stl) — Costelas de raiz com túneis angulados a $-5,0^\circ$ para travar o diedro de $5,0^\circ$ por semi-asa ($10,0^\circ$ total = $+41,4\text{ mm}$ na ponta) usando vareta reta de carbono $\varnothing 4\text{ mm}$.
- [`Dihedral_V_Joiner_10deg_PETG.stl`](file:///Users/pia/lab/antigravity/dlg/stl/Plate3_PETG_Structural_Pod/Dihedral_V_Joiner_10deg_PETG.stl) — Luva central em "V" com $10,0^\circ$ ($5,0^\circ$ de cada lado) e alma interna de $\varnothing 4\text{ mm}$ para conectar os dois tubos principais $\varnothing 6 \times 4\text{ mm}$.
- [`XTail_Center_Clamp_8mm_Boom.stl`](file:///Users/pia/lab/antigravity/dlg/stl/Plate3_PETG_Structural_Pod/XTail_Center_Clamp_8mm_Boom.stl)
- [`Flaperon_Root_Horns_BallLink_Pair.stl`](file:///Users/pia/lab/antigravity/dlg/stl/Plate3_PETG_Structural_Pod/Flaperon_Root_Horns_BallLink_Pair.stl)

---

## 4. Script Gerador Paramétrico (`cad/`)
- [`cad/generate_dlg_stl.py`](file:///Users/pia/lab/antigravity/dlg/cad/generate_dlg_stl.py) — Gera todas as malhas 3D com as nervuras geodésicas internas, além dos arquivos `.svg`, `.dxf` e `.dat`.
