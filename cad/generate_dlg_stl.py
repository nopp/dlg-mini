#!/usr/bin/env python3
"""
Gerador Parametrico 3D (STL c/ Nervuras Geodesicas Internas 0% Infill + Diedro Fisico 5.0°/lado
+ Blueprints SVG/DXF) para o DLG-Mini 950 3DP (Baseado no RCRCM DLG-Mini X-Tail)
Otimizado para Bambu Lab P2S (256 x 256 x 256 mm)

SISTEMA DE DIEDRO FÍSICO DE 5.0° POR SEMI-ASA (10.0° TOTAL = 41.4mm NA PONTA):
Para permitir o uso de varetas e tubos de carbono cilíndricos retos comerciais mantendo o diedro
ótimo de planeio (5.0° de cada lado / 10.0° total):
1. O túnel da Baioneta Retilínea de Carbono Ø4mm x 110mm (em X=39mm) nos primeiros 55mm da
   raiz de W1 e das Costelas de Raiz possui inclinação de -5.0° no plano YZ (entra em Y=+2.5mm
   na raiz Z=0 e termina em Y=-2.3mm em Z=55mm). Assim, ao inserir a vareta reta horizontal de
   Ø4mm, as duas semi-asas ficam fisicamente travadas com +5.0° de diedro de cada lado!
2. Adicionalmente, é gerada a peça `Dihedral_V_Joiner_10deg_PETG.stl` (luva central em V com
   5.0° de cada lado para unir os 2 tubos principais Ø6x4mm com 2 pinos de carbono Ø4mm), e o
   berço do Pod + Costelas de Raiz M3 possuem assentamento angulado em V de 5.0°/lado.
"""

import math
import os
import struct
from typing import List, Tuple

Vec3 = Tuple[float, float, float]
Triangle = Tuple[Vec3, Vec3, Vec3]

DIHEDRAL_DEG = 5.0  # 5.0 graus por semi-asa = 10.0 graus total (41.4mm de elevação na ponta)
DIHEDRAL_RAD = math.radians(DIHEDRAL_DEG)
DIHEDRAL_TAN = math.tan(DIHEDRAL_RAD)


# ==============================================================================
# 1. UTILITÁRIOS GEOMÉTRICOS E EXPORTADOR STL BINÁRIO MANIFOLD
# ==============================================================================

def sub3(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross3(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def norm3(v: Vec3) -> Vec3:
    length = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if length < 1e-12:
        return (0.0, 0.0, 1.0)
    return (v[0] / length, v[1] / length, v[2] / length)


def write_binary_stl(filepath: str, triangles: List[Triangle], header_text: str = "DLG-Mini 950 3DP") -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    header = header_text.encode("ascii", errors="ignore")[:80].ljust(80, b" ")
    with open(filepath, "wb") as f:
        f.write(header)
        f.write(struct.pack("<I", len(triangles)))
        for p1, p2, p3 in triangles:
            normal = norm3(cross3(sub3(p2, p1), sub3(p3, p1)))
            f.write(struct.pack("<12fH", *normal, *p1, *p2, *p3, 0))


def quad_to_tris(p0: Vec3, p1: Vec3, p2: Vec3, p3: Vec3, flip: bool = False) -> List[Triangle]:
    if not flip:
        return [(p0, p1, p2), (p0, p2, p3)]
    return [(p0, p2, p1), (p0, p3, p2)]


# ==============================================================================
# 2. PERFIS AERODINÂMICOS E CAVIDADES DE NERVURAS GEODÉSICAS (0% INFILL)
# ==============================================================================

def airfoil_synerj_dlg(
    x: float,
    t_ratio: float = 0.074,
    m: float = 0.018,
    p: float = 0.32,
    te_thick_ratio: float = 0.0055,
) -> Tuple[float, float]:
    x = max(0.0, min(1.0, x))
    yt = 5.0 * t_ratio * (
        0.2969 * math.sqrt(x)
        - 0.1260 * x
        - 0.3516 * (x ** 2)
        + 0.2843 * (x ** 3)
        - 0.1036 * (x ** 4)
    ) + x * (te_thick_ratio * 0.5)

    if x < p and p > 0:
        yc = (m / (p ** 2)) * (2.0 * p * x - x ** 2)
    elif p > 0:
        yc = (m / ((1.0 - p) ** 2)) * ((1.0 - 2.0 * p) + 2.0 * p * x - x ** 2)
    else:
        yc = 0.0

    return (yc + yt, yc - yt)


def get_airfoil_loop(
    chord: float,
    x_offset: float,
    y_offset: float,
    t_ratio: float = 0.074,
    camber: float = 0.018,
    x_start_frac: float = 0.0,
    x_end_frac: float = 1.0,
    n_pts: int = 48,
    te_min_mm: float = 0.85,
) -> List[Tuple[float, float]]:
    """
    Gera um contorno fechado de 2 * (n_pts + 1) pontos no sentido anti-horário (CCW):
    - Índices 0 .. n_pts: Curva superior (+Y) indo da direita (x_end_frac) para a esquerda (x_start_frac)
    - Índices n_pts+1 .. 2*n_pts+1: Curva inferior (-Y) indo da esquerda (x_start_frac) para a direita (x_end_frac)
    """
    te_ratio = te_min_mm / max(chord, 30.0)
    xs = []
    for i in range(n_pts + 1):
        beta = (math.pi * i) / n_pts
        frac = 0.5 * (1.0 - math.cos(beta))
        x_val = x_start_frac + frac * (x_end_frac - x_start_frac)
        xs.append(x_val)

    upper_pts = []
    lower_pts = []
    for xf in xs:
        yu, yl = airfoil_synerj_dlg(xf, t_ratio=t_ratio, m=camber, te_thick_ratio=te_ratio)
        px = x_offset + xf * chord
        upper_pts.append((px, y_offset + yu * chord))
        lower_pts.append((px, y_offset + yl * chord))

    return list(reversed(upper_pts)) + lower_pts


def get_circle_loop(cx: float, cy: float, radius: float, n_pts: int = 36) -> List[Tuple[float, float]]:
    """
    Gera um círculo fechado de 2 * m pontos no sentido anti-horário (CCW):
    - Primeira metade (0 .. m-1): Semicírculo superior (+Y) da direita (ang=0) para a esquerda (ang=pi)
    - Segunda metade (m .. 2*m-1): Semicírculo inferior (-Y) da esquerda (ang=pi) para a direita (ang=2*pi)
    """
    m = max(8, n_pts // 2)
    upper_half = []
    lower_half = []
    for i in range(m):
        ang_u = math.pi * i / (m - 1)
        upper_half.append((cx + radius * math.cos(ang_u), cy + radius * math.sin(ang_u)))
        ang_l = math.pi + math.pi * i / (m - 1)
        lower_half.append((cx + radius * math.cos(ang_l), cy + radius * math.sin(ang_l)))
    return upper_half + lower_half


def get_airfoil_hollow_bay_loop(
    x0_mm: float,
    x1_mm: float,
    chord: float,
    le_x: float,
    t_ratio: float,
    camber: float,
    skin_wall_mm: float,
    is_right_wing: bool,
    n_seg: int = 10,
) -> List[Tuple[float, float]]:
    """
    Gera uma câmara oca de 2 * (n_seg + 1) pontos SEMPRE no sentido anti-horário (CCW):
    - Índices 0 .. n_seg: Teto (+Y) indo da direita (x1_mm) para a esquerda (x0_mm)
    - Índices n_seg+1 .. 2*n_seg+1: Piso (-Y) indo da esquerda (x0_mm) para a direita (x1_mm)
    """
    if x1_mm - x0_mm < 1.8:
        x_mid = 0.5 * (x0_mm + x1_mm)
        x0_mm = x_mid - 0.9
        x1_mm = x_mid + 0.9

    top_plus_y = []
    bot_minus_y = []
    for i in range(n_seg + 1):
        u = i / n_seg
        px = x0_mm + u * (x1_mm - x0_mm)
        xf = max(0.015, min(0.985, (px - le_x) / chord))
        yu, yl = airfoil_synerj_dlg(xf, t_ratio=t_ratio, m=camber, te_thick_ratio=0.008)
        y_extrados = yu * chord - skin_wall_mm
        y_intrados = yl * chord + skin_wall_mm
        if y_extrados - y_intrados < 0.5:
            y_mid = 0.5 * (yu + yl) * chord
            y_extrados = y_mid + 0.25
            y_intrados = y_mid - 0.25
        if is_right_wing:
            # Extradorso está em +Y, Intradorso está em -Y
            top_plus_y.append((px, y_extrados))
            bot_minus_y.append((px, y_intrados))
        else:
            # Semi-asa esquerda espelhada em Y: lado +Y é (-y_intrados) e lado -Y é (-y_extrados)
            top_plus_y.append((px, -y_intrados))
            bot_minus_y.append((px, -y_extrados))

    return list(reversed(top_plus_y)) + bot_minus_y


def triangle_wave(t: float) -> float:
    p = (t / (2.0 * math.pi)) % 1.0
    if p < 0.25:
        return 4.0 * p
    elif p < 0.75:
        return 2.0 - 4.0 * p
    else:
        return -4.0 + 4.0 * p


# ==============================================================================
# 3. CONSTRUTOR DE SÓLIDOS LOFT COM CAVIDADES E NERVURAS INTERNAS (MANIFOLD)
# ==============================================================================

def loft_with_holes(
    outer_loops: List[List[Tuple[float, float]]],
    hole_loops_per_slice: List[List[List[Tuple[float, float]]]],
    z_slices: List[float],
) -> List[Triangle]:
    tris: List[Triangle] = []
    num_slices = len(z_slices)
    n_outer = len(outer_loops[0])
    num_holes = len(hole_loops_per_slice[0]) if hole_loops_per_slice else 0

    for s in range(num_slices - 1):
        z0, z1 = z_slices[s], z_slices[s + 1]
        L0, L1 = outer_loops[s], outer_loops[s + 1]
        for i in range(n_outer):
            inext = (i + 1) % n_outer
            p00 = (L0[i][0], L0[i][1], z0)
            p10 = (L0[inext][0], L0[inext][1], z0)
            p11 = (L1[inext][0], L1[inext][1], z1)
            p01 = (L1[i][0], L1[i][1], z1)
            tris.extend(quad_to_tris(p00, p10, p11, p01, flip=False))

    for h in range(num_holes):
        n_hole = len(hole_loops_per_slice[0][h])
        for s in range(num_slices - 1):
            z0, z1 = z_slices[s], z_slices[s + 1]
            H0, H1 = hole_loops_per_slice[s][h], hole_loops_per_slice[s + 1][h]
            for i in range(n_hole):
                inext = (i + 1) % n_hole
                p00 = (H0[i][0], H0[i][1], z0)
                p10 = (H0[inext][0], H0[inext][1], z0)
                p11 = (H1[inext][0], H1[inext][1], z1)
                p01 = (H1[i][0], H1[i][1], z1)
                tris.extend(quad_to_tris(p00, p10, p11, p01, flip=True))

    for cap_idx, is_top in [(0, False), (num_slices - 1, True)]:
        z_val = z_slices[cap_idx]
        outer = outer_loops[cap_idx]
        holes = hole_loops_per_slice[cap_idx] if num_holes > 0 else []
        tris.extend(triangulate_cap_with_holes(outer, holes, z_val, is_top))

    return tris


def stitch_two_open_chains(
    outer_chain: List[Tuple[float, float]],
    inner_chain: List[Tuple[float, float]],
    z_val: float,
    is_top: bool,
) -> List[Triangle]:
    tris: List[Triangle] = []
    i = 0
    j = 0
    no = len(outer_chain)
    ni = len(inner_chain)
    while i < no - 1 or j < ni - 1:
        p_o = (outer_chain[i][0], outer_chain[i][1], z_val)
        p_i = (inner_chain[j][0], inner_chain[j][1], z_val)
        if i == no - 1:
            advance_outer = False
        elif j == ni - 1:
            advance_outer = True
        else:
            d_next_o = math.hypot(outer_chain[i + 1][0] - inner_chain[j][0], outer_chain[i + 1][1] - inner_chain[j][1])
            d_next_i = math.hypot(outer_chain[i][0] - inner_chain[j + 1][0], outer_chain[i][1] - inner_chain[j + 1][1])
            advance_outer = d_next_o <= d_next_i

        if advance_outer:
            p_o_next = (outer_chain[i + 1][0], outer_chain[i + 1][1], z_val)
            tris.append((p_o, p_o_next, p_i) if is_top else (p_o, p_i, p_o_next))
            i += 1
        else:
            p_i_next = (inner_chain[j + 1][0], inner_chain[j + 1][1], z_val)
            tris.append((p_o, p_i_next, p_i) if is_top else (p_o, p_i, p_i_next))
            j += 1

    return tris


def triangulate_cap_with_holes(
    outer: List[Tuple[float, float]],
    holes: List[List[Tuple[float, float]]],
    z_val: float,
    is_top: bool,
) -> List[Triangle]:
    """
    Triangulação exata de 5 regiões para tampas de perfil aerodinâmico com múltiplos furos/câmaras:
    Cada contorno L (outer e cada hole) possui 2*M pontos:
      - L[0 .. M-1]: curva superior (+Y) indo da direita (X_max) para a esquerda (X_min)
      - L[M .. 2*M-1]: curva inferior (-Y) indo da esquerda (X_min) para a direita (X_max)
    """
    tris: List[Triangle] = []
    if not holes:
        cx = sum(p[0] for p in outer) / len(outer)
        cy = sum(p[1] for p in outer) / len(outer)
        c3 = (cx, cy, z_val)
        n = len(outer)
        for i in range(n):
            p0 = (outer[i][0], outer[i][1], z_val)
            p1 = (outer[(i + 1) % n][0], outer[(i + 1) % n][1], z_val)
            tris.append((c3, p0, p1) if is_top else (c3, p1, p0))
        return tris

    m_out = len(outer) // 2
    outer_upper = outer[:m_out]      # Direita (X_max) -> Esquerda (X_min) pelo lado +Y
    outer_lower = outer[m_out:]      # Esquerda (X_min) -> Direita (X_max) pelo lado -Y

    # Ordena os furos da Direita (X_max) para a Esquerda (X_min)
    holes_rtl = sorted(holes, key=lambda h: sum(p[0] for p in h) / len(h), reverse=True)

    # 1. Cadeia superior composta (+Y, da direita p/ esquerda) e cadeia inferior (-Y, da esquerda p/ direita)
    inner_upper: List[Tuple[float, float]] = [outer[0]]
    for h in holes_rtl:
        mh = len(h) // 2
        inner_upper.extend(h[:mh])
    inner_upper.append(outer[m_out - 1])

    inner_lower: List[Tuple[float, float]] = [outer[m_out]]
    for h in reversed(holes_rtl):
        mh = len(h) // 2
        inner_lower.extend(h[mh:])
    inner_lower.append(outer[-1])

    # Costura a casca superior (+Y) e a casca inferior (-Y)
    tris.extend(stitch_two_open_chains(outer_upper, inner_upper, z_val, is_top))
    tris.extend(stitch_two_open_chains(inner_lower, outer_lower, z_val, is_top))

    # 2. Fecha os Quads verticais das nervuras (Rib Webs) entre furos vizinhos e nas extremidades LE / TE!
    # Parede traseira (entre outer[-1]->outer[0] e o furo mais à direita holes_rtl[0])
    h_first = holes_rtl[0]
    tris.extend(
        quad_to_tris(
            (outer[-1][0], outer[-1][1], z_val),
            (outer[0][0], outer[0][1], z_val),
            (h_first[0][0], h_first[0][1], z_val),
            (h_first[-1][0], h_first[-1][1], z_val),
            flip=not is_top,
        )
    )

    # Nervuras internas entre cada par de furos consecutivos (h_right e h_left)
    for k in range(len(holes_rtl) - 1):
        h_right = holes_rtl[k]
        h_left = holes_rtl[k + 1]
        mr = len(h_right) // 2
        tris.extend(
            quad_to_tris(
                (h_right[mr][0], h_right[mr][1], z_val),
                (h_right[mr - 1][0], h_right[mr - 1][1], z_val),
                (h_left[0][0], h_left[0][1], z_val),
                (h_left[-1][0], h_left[-1][1], z_val),
                flip=not is_top,
            )
        )

    # Parede frontal do Bordo de Ataque (entre o furo mais à esquerda holes_rtl[-1] e outer[m_out-1]->outer[m_out])
    h_last = holes_rtl[-1]
    ml = len(h_last) // 2
    tris.extend(
        quad_to_tris(
            (h_last[ml][0], h_last[ml][1], z_val),
            (h_last[ml - 1][0], h_last[ml - 1][1], z_val),
            (outer[m_out - 1][0], outer[m_out - 1][1], z_val),
            (outer[m_out][0], outer[m_out][1], z_val),
            flip=not is_top,
        )
    )

    return tris


# ==============================================================================
# 4. ASA BIPARTIDA COM NERVURAS GEODÉSICAS 0% INFILL + TÚNEL DE DIEDRO 5.0°/LADO
# ==============================================================================

def wing_chord_and_le_at_span(y_span: float) -> Tuple[float, float]:
    """
    Geometria trapezoidal limpa alinhada pela Longarina Principal (32.67% da corda = X = 49.0mm fixo):
    - Na raiz (y = 0mm): corda = 150.0mm, LE = 0.0mm, Longarina = 49.0mm (32.67%), Dobradiça = 112.5mm (75%)
    - No meio (y = 245mm): corda = 126.8mm
    - Na ponta (y = 475mm): corda = 105.0mm (área alar total exata = 2 * 475 * (150+105)/2 = 121.125 mm² + flaperon = 12.6 dm²)
    Como a variação é linear de y=0 a y=475mm e a linha de 32.67% da corda é fixa em X = 49.0mm:
    1. O tubo principal de carbono Ø6x4mm (em X = 49.0mm) fica SEMPRE no ponto de espessura máxima
       do perfil (32.67% da corda) da raiz até a ponta, NUNCA cruzando o bordo de ataque!
    2. A linha da dobradiça do flaperon (75% da corda), a vareta auxiliar (64% da corda) e a vareta
       antitorção do flaperon (78.5% da corda) são TODAS linhas 100% retas de y=0 até y=475mm!
    """
    u = max(0.0, min(1.0, y_span / 475.0))
    chord = 150.0 - 45.0 * u  # 150.0mm na raiz -> 126.8mm em y=245mm -> 105.0mm na ponta (y=475mm)
    spar_frac = 49.0 / 150.0  # 0.326667 (ponto de espessura máxima do perfil)
    le_x = 49.0 - spar_frac * chord
    return chord, le_x


def wing_thickness_ratio_at_span(y_span: float) -> float:
    """
    Progressão aerodinâmica de perfil tipo AG455ct (7.4% na raiz) -> AG47ct (8.2% na ponta)
    para garantir que na ponta da asa (corda 105mm) a espessura na longarina seja 8.6mm,
    mantendo parede sólida generosa acima e abaixo do tubo de carbono Ø6mm!
    """
    u = max(0.0, min(1.0, y_span / 475.0))
    return 0.074 + 0.008 * u


def generate_wing_segment(
    y_start: float,
    y_end: float,
    is_right_wing: bool,
    has_peg_socket: bool = False,
    n_slices: int = 70,
) -> List[Triangle]:
    """
    Gera o segmento da asa (W1 245mm ou W2 230mm) com coordenadas internas 100% proporcionais
    à corda local c(y), garantindo que NENHUMA câmara oca ou furo jamais cruze a casca externa:
    1. Casca externa de 0.45mm (1 perímetro de bico 0.4mm)
    2. Túnel da Longarina Principal Ø6x4mm (furo Ø6.25mm sempre em X = 49.0mm = 32.67% da corda!)
    3. Túnel de Baioneta Retilínea Angulada em -5.0° (nos primeiros 55mm de W1)
    4. Túnel da Longarina Auxiliar Ø2mm (sempre em 64.5% da corda local — linha 100% reta!)
    5. 5 Câmaras Ocas separadas por Nervuras Diagonais Geodésicas a 45° no CAD (0% Infill)
    """
    z_slices = []
    outer_loops = []
    hole_loops = []
    rib_thick = 0.86
    skin_wall = 0.48
    sign_y = 1.0 if is_right_wing else -1.0

    for s in range(n_slices):
        v = s / (n_slices - 1)
        y_span = y_start + v * (y_end - y_start)
        z_local = y_span - y_start
        chord, le_x = wing_chord_and_le_at_span(y_span)
        t_ratio = wing_thickness_ratio_at_span(y_span)
        hinge_wall_x = le_x + 0.745 * chord

        loop = get_airfoil_loop(
            chord=chord,
            x_offset=le_x,
            y_offset=0.0,
            t_ratio=t_ratio,
            camber=0.018,
            x_start_frac=0.0,
            x_end_frac=0.745,
            n_pts=52,
            te_min_mm=1.2,
        )
        if not is_right_wing:
            loop = [(px, -py) for (px, py) in reversed(loop)]

        # 1. Furo do Tubo de Carbono Principal Ø6.0mm (sempre em X = 49.0mm = 32.67% da corda!)
        spar_x = 49.0
        yu_spar, yl_spar = airfoil_synerj_dlg((spar_x - le_x) / chord, t_ratio=t_ratio, m=0.018)
        spar_cy = 0.5 * (yu_spar + yl_spar) * chord * sign_y
        # O tubo de carbono de 450mm vai até y=450mm; nos últimos 25mm (y=450..475) reduz p/ Ø3.6mm
        spar_r = 3.125 if y_span <= 452.0 else 1.80
        hole_main = get_circle_loop(spar_x, spar_cy, spar_r, n_pts=36)

        # 2. Furo da Vareta Auxiliar Ø2.0mm (linha reta em 64.5% da corda: X=96.75mm na raiz -> X=72.9mm na ponta)
        aux_x = le_x + 0.645 * chord
        yu_aux, yl_aux = airfoil_synerj_dlg(0.645, t_ratio=t_ratio, m=0.018)
        aux_cy = 0.5 * (yu_aux + yl_aux) * chord * sign_y
        hole_aux = get_circle_loop(aux_x, aux_cy, 1.125, n_pts=36)

        # 3. Nervuras Diagonais Geodésicas Internas (Warren Truss a 45°), 100% proporcionais à corda local!
        diag_wave = triangle_wave(2.0 * math.pi * y_span / 36.0)

        if y_start < 10.0:
            # Painel W1: inclui o Túnel Angulado de Diedro (-5.0°) em 25.5% da corda
            dih_x = le_x + 0.255 * chord
            z_clamped = min(y_span, 55.0)
            dihedral_tunnel_cy = (2.40 - z_clamped * DIHEDRAL_TAN) * sign_y
            dihedral_r = 2.08 if y_span <= 56.0 else 1.15
            hole_dihedral = get_circle_loop(dih_x, dihedral_tunnel_cy, dihedral_r, n_pts=32)

            dbox_start = le_x + 0.035 * chord
            dbox_end = dih_x - dihedral_r - 1.1
            dbox_mid_base = 0.5 * (dbox_start + dbox_end)
            dbox_amp = 0.25 * (dbox_end - dbox_start)
            rib_dbox_x = dbox_mid_base + dbox_amp * diag_wave
            bay_dbox_1 = get_airfoil_hollow_bay_loop(
                dbox_start, rib_dbox_x - 0.5 * rib_thick, chord, le_x, t_ratio, 0.018, skin_wall, is_right_wing
            )
            bay_dbox_2 = get_airfoil_hollow_bay_loop(
                rib_dbox_x + 0.5 * rib_thick, dbox_end, chord, le_x, t_ratio, 0.018, skin_wall, is_right_wing
            )
            front_holes = [bay_dbox_1, bay_dbox_2, hole_dihedral]
        else:
            # Painel W2: D-Box limpo proporcional entre 4% da corda e (spar_x - spar_r - 1.2mm)
            dbox_start = le_x + 0.040 * chord
            dbox_end = spar_x - spar_r - 1.2
            dbox_mid_base = 0.5 * (dbox_start + dbox_end)
            dbox_amp = 0.28 * (dbox_end - dbox_start)
            rib_dbox_x = dbox_mid_base + dbox_amp * diag_wave
            bay_dbox_1 = get_airfoil_hollow_bay_loop(
                dbox_start, rib_dbox_x - 0.5 * rib_thick, chord, le_x, t_ratio, 0.018, skin_wall, is_right_wing
            )
            bay_dbox_2 = get_airfoil_hollow_bay_loop(
                rib_dbox_x + 0.5 * rib_thick, dbox_end, chord, le_x, t_ratio, 0.018, skin_wall, is_right_wing
            )
            front_holes = [bay_dbox_1, bay_dbox_2]

        # Caixa Central de Torção proporcional entre (spar_x + spar_r + 1.2mm) e (aux_x - 2.2mm)
        # Se for a região do Launch Peg na asa esquerda (442mm <= y_span <= 458mm), engrossa a parede
        # ao redor da longarina principal (bloco sólido interno p/ furar o pino de carbono Ø4mm rente à casca!)
        peg_extra_wall = 4.5 if (has_peg_socket and 440.0 <= y_span <= 460.0) else 0.0
        mid_start = spar_x + spar_r + 1.2 + peg_extra_wall
        mid_end = aux_x - 2.2
        mid_span_w = mid_end - mid_start
        rib_m1_x = mid_start + 0.33 * mid_span_w + 0.11 * mid_span_w * diag_wave
        rib_m2_x = mid_start + 0.67 * mid_span_w - 0.11 * mid_span_w * diag_wave

        bay_mid_1 = get_airfoil_hollow_bay_loop(
            mid_start, rib_m1_x - 0.5 * rib_thick, chord, le_x, t_ratio, 0.018, skin_wall, is_right_wing
        )
        bay_mid_2 = get_airfoil_hollow_bay_loop(
            rib_m1_x + 0.5 * rib_thick, rib_m2_x - 0.5 * rib_thick, chord, le_x, t_ratio, 0.018, skin_wall, is_right_wing
        )
        bay_mid_3 = get_airfoil_hollow_bay_loop(
            rib_m2_x + 0.5 * rib_thick, mid_end, chord, le_x, t_ratio, 0.018, skin_wall, is_right_wing
        )

        # Câmara Traseira Pré-Dobradiça proporcional entre (aux_x + 2.2mm) e (hinge_wall_x - 1.5mm)
        bay_rear = get_airfoil_hollow_bay_loop(
            aux_x + 2.2, hinge_wall_x - 1.5, chord, le_x, t_ratio, 0.018, skin_wall, is_right_wing
        )

        z_slices.append(z_local)
        outer_loops.append(loop)
        hole_loops.append(
            front_holes + [
                hole_main,
                bay_mid_1,
                bay_mid_2,
                bay_mid_3,
                hole_aux,
                bay_rear,
            ]
        )

    tris = loft_with_holes(outer_loops, hole_loops, z_slices)
    return tris


def generate_flaperon_segment(
    y_start: float,
    y_end: float,
    is_right_wing: bool,
    n_slices: int = 50,
) -> List[Triangle]:
    z_slices = []
    outer_loops = []
    hole_loops = []
    skin_wall = 0.45
    rib_thick = 0.85

    for s in range(n_slices):
        v = s / (n_slices - 1)
        y_span = y_start + v * (y_end - y_start)
        z_local = y_span - y_start
        chord, le_x = wing_chord_and_le_at_span(y_span)
        t_ratio = wing_thickness_ratio_at_span(y_span)
        te_x = le_x + chord

        loop = get_airfoil_loop(
            chord=chord,
            x_offset=le_x,
            y_offset=0.0,
            t_ratio=t_ratio,
            camber=0.018,
            x_start_frac=0.755,
            x_end_frac=1.0,
            n_pts=44,
            te_min_mm=0.85,
        )
        if not is_right_wing:
            loop = [(px, -py) for (px, py) in reversed(loop)]

        # Posição da vareta antitorção Ø2mm proporcional (78.5% da corda = linha 100% reta!)
        torsion_x = le_x + 0.785 * chord
        yu_f, yl_f = airfoil_synerj_dlg(0.785, t_ratio=t_ratio, m=0.018)
        f_cy = 0.5 * (yu_f + yl_f) * chord * (1.0 if is_right_wing else -1.0)
        hole_torsion = get_circle_loop(torsion_x, f_cy, 1.05, n_pts=32)

        f_start = torsion_x + 2.0
        f_end = max(f_start + 4.5, te_x - 3.2)
        diag_wave = triangle_wave(2.0 * math.pi * y_span / 28.0)
        f_rib_x = 0.5 * (f_start + f_end) + 0.24 * (f_end - f_start) * diag_wave

        bay_f1 = get_airfoil_hollow_bay_loop(
            f_start, f_rib_x - 0.5 * rib_thick, chord, le_x, t_ratio, 0.018, skin_wall, is_right_wing, n_seg=8
        )
        bay_f2 = get_airfoil_hollow_bay_loop(
            f_rib_x + 0.5 * rib_thick, f_end, chord, le_x, t_ratio, 0.018, skin_wall, is_right_wing, n_seg=8
        )

        z_slices.append(z_local)
        outer_loops.append(loop)
        hole_loops.append([hole_torsion, bay_f1, bay_f2])

    return loft_with_holes(outer_loops, hole_loops, z_slices)


# ==============================================================================
# 5. CAUDA X-TAIL COM NERVURAS GEODÉSICAS INTERNAS NO CAD (0% INFILL)
# ==============================================================================

def tail_chord_and_le(z_pos: float, span: float, root_chord: float, tip_chord: float, spar_x_mm: float) -> Tuple[float, float]:
    """
    Geometria trapezoidal da empenagem X-Tail alinhada pelo eixo da vareta reta de carbono Ø2mm:
    - Na base Z=0 (raiz na mesa de impressão): corda = root_chord (75mm), LE = 0.0mm
    - No topo Z=span (ponta do estabilizador): corda = tip_chord (50mm horiz / 42mm vert)
    - O eixo da vareta de carbono (spar_x_mm = 22.0mm = 29.33% da corda) fica SEMPRE no ponto de
      maior espessura do perfil HT12/HT14 da base até a ponta, eliminando overhangs e rasgos no BA!
    """
    u = max(0.0, min(1.0, z_pos / max(1.0, span)))
    chord = root_chord - (root_chord - tip_chord) * u
    spar_frac = spar_x_mm / root_chord
    le_x = spar_x_mm - spar_frac * chord
    return chord, le_x


def generate_xtail_half_surface(
    span: float,
    root_chord: float,
    tip_chord: float,
    t_ratio_root: float,
    t_ratio_tip: float,
    x_start_frac: float,
    x_end_frac: float,
    is_control_surface: bool = False,
    n_slices: int = 44,
) -> List[Triangle]:
    """
    Gera uma semi-superfície da empenagem X-Tail (impressa em pé na Bambu Lab P2S com a raiz
    larga de 75mm na mesa Z=0 afilando até a ponta em Z=span, ZERO overhang!):
    - Possui túnel contínuo p/ vareta reta de carbono Ø2.0mm (na parte fixa) ou Ø1.0mm (no profundor/leme)
    - Possui câmaras ocas com nervura geodésica diagonal a 45° modelada no CAD (0% Infill)
    """
    z_slices = []
    outer_loops = []
    hole_loops = []
    skin_wall = 0.44
    rib_thick = 0.82
    main_spar_x = 22.0  # 29.33% da corda de 75mm (ponto de espessura máxima do perfil HT12/HT14)

    for s in range(n_slices):
        v = s / (n_slices - 1)
        z_pos = v * span
        chord, le_x = tail_chord_and_le(z_pos, span, root_chord, tip_chord, main_spar_x)
        t_ratio = t_ratio_root + (t_ratio_tip - t_ratio_root) * v

        loop = get_airfoil_loop(
            chord=chord,
            x_offset=le_x,
            y_offset=0.0,
            t_ratio=t_ratio,
            camber=0.0,
            x_start_frac=x_start_frac,
            x_end_frac=x_end_frac,
            n_pts=40,
            te_min_mm=0.80,
        )

        diag_wave = triangle_wave(2.0 * math.pi * z_pos / 26.0)

        if not is_control_surface:
            # Parte fixa (0% a 63% da corda):
            # - Vareta reta de carbono Ø2.0mm sempre em X = 22.0mm (29.33% da corda local!)
            spar_r = 1.08
            hole_spar = get_circle_loop(main_spar_x, 0.0, spar_r, n_pts=32)

            # Câmara oca frontal (D-Box do estabilizador, entre 4.5% da corda e a vareta Ø2mm)
            f_start = le_x + 0.045 * chord
            f_end = main_spar_x - spar_r - 0.9
            bay_front = get_airfoil_hollow_bay_loop(
                f_start, f_end, chord, le_x, t_ratio, 0.0, skin_wall, True, n_seg=8
            )

            # 2 Câmaras ocas traseiras separadas por nervura diagonal geodésica a 45°
            r_start = main_spar_x + spar_r + 0.9
            r_end = le_x + (x_end_frac - 0.025) * chord
            r_span = r_end - r_start
            r_rib = r_start + 0.50 * r_span + 0.22 * r_span * diag_wave
            bay_rear1 = get_airfoil_hollow_bay_loop(
                r_start, r_rib - 0.5 * rib_thick, chord, le_x, t_ratio, 0.0, skin_wall, True, n_seg=8
            )
            bay_rear2 = get_airfoil_hollow_bay_loop(
                r_rib + 0.5 * rib_thick, r_end, chord, le_x, t_ratio, 0.0, skin_wall, True, n_seg=8
            )
            holes_this_slice = [bay_front, hole_spar, bay_rear1, bay_rear2]
        else:
            # Parte móvel (Profundor / Leme: 64% a 100% da corda):
            # - Furo p/ vareta de reforço de carbono Ø1.0mm em 68.5% da corda + câmara oca traseira
            ctrl_spar_x = le_x + 0.685 * chord
            hole_spar = get_circle_loop(ctrl_spar_x, 0.0, 0.62, n_pts=28)
            c_start = ctrl_spar_x + 1.4
            c_end = le_x + 0.94 * chord
            bay_ctrl = get_airfoil_hollow_bay_loop(
                c_start, c_end, chord, le_x, t_ratio, 0.0, skin_wall, True, n_seg=8
            )
            holes_this_slice = [hole_spar, bay_ctrl]

        z_slices.append(z_pos)
        outer_loops.append(loop)
        hole_loops.append(holes_this_slice)

    return loft_with_holes(outer_loops, hole_loops, z_slices)


def offset_triangles(tris: List[Triangle], dx: float, dy: float, dz: float) -> List[Triangle]:
    return [
        (
            (p1[0] + dx, p1[1] + dy, p1[2] + dz),
            (p2[0] + dx, p2[1] + dy, p2[2] + dz),
            (p3[0] + dx, p3[1] + dy, p3[2] + dz),
        )
        for (p1, p2, p3) in tris
    ]


def generate_xtail_pair_stl(
    span_a: float,
    span_b: float,
    root_chord: float,
    tip_chord_a: float,
    tip_chord_b: float,
    t_ratio_root: float,
    t_ratio_tip: float,
    x_start_frac: float,
    x_end_frac: float,
    is_control_surface: bool,
) -> List[Triangle]:
    """
    Gera o par completo do Estabilizador (ex: Esquerdo 120mm + Direito 120mm = 240mm,
    ou Vertical Superior 105mm + Inferior 70mm = 175mm) posicionados lado a lado na mesa (Z=0)
    pela base larga de 75mm (zero overhang e 100% de aderência na Bambu Lab P2S!).
    """
    half_a = generate_xtail_half_surface(
        span_a, root_chord, tip_chord_a, t_ratio_root, t_ratio_tip, x_start_frac, x_end_frac, is_control_surface
    )
    half_b = generate_xtail_half_surface(
        span_b, root_chord, tip_chord_b, t_ratio_root, t_ratio_tip, x_start_frac, x_end_frac, is_control_surface
    )
    return offset_triangles(half_a, 0.0, -10.0, 0.0) + offset_triangles(half_b, 0.0, 10.0, 0.0)

def generate_cylinder_z(
    cx: float,
    cy: float,
    r_outer: float,
    r_inner: float,
    z0: float,
    z1: float,
    orient_along_y: bool = False,
    y_len: float = 20.0,
) -> List[Triangle]:
    outer0 = get_circle_loop(cx, cy, r_outer, n_pts=48)
    outer1 = get_circle_loop(cx, cy, r_outer, n_pts=48)
    holes = [[get_circle_loop(cx, cy, r_inner, n_pts=48)], [get_circle_loop(cx, cy, r_inner, n_pts=48)]] if r_inner > 0 else []
    tris = loft_with_holes([outer0, outer1], holes, [z0, z1])
    if orient_along_y:
        z_mid = 0.5 * (z0 + z1)
        rotated: List[Triangle] = []
        for p1, p2, p3 in tris:
            rp1 = (p1[0], (p1[2] - z_mid) * (y_len / (z1 - z0)), z_mid + p1[1])
            rp2 = (p2[0], (p2[2] - z_mid) * (y_len / (z1 - z0)), z_mid + p2[1])
            rp3 = (p3[0], (p3[2] - z_mid) * (y_len / (z1 - z0)), z_mid + p3[1])
            rotated.append((rp1, rp2, rp3))
        return rotated
    return tris


def pod_cross_section_dims(z_from_tail: float) -> Tuple[float, float, float, float]:
    """
    Perfil longitudinal aerodinâmico (ogiva Haack / RCRCM DLG-Mini) do Pod de 245mm:
    - Z = 0.0mm (na mesa): Colar cilíndrico traseiro Ø13.6mm ext / Ø8.16mm int p/ tubo de carbono Ø8x6mm
    - Z = 0 a 55mm: Cone traseiro de transição suave do tubo Ø8mm para o corpo do pod
    - Z = 35 a 148mm: Berço da Asa Bipartida com assento em V (5.0° por lado = 10° total)
    - Z = 148 a 220mm: Cabine aberta em gota (Cockpit com arcos a 45° nas extremidades, zero suporte!)
    - Z = 170 a 245mm: Ogiva parabólica contínua fechando suavemente até r=0.8mm na ponta Z=245mm!
    """
    if z_from_tail <= 55.0:
        u = z_from_tail / 55.0
        s = u * u * (3.0 - 2.0 * u)
        rx = 6.8 + 6.7 * s
        y_top = 6.8 + 4.2 * s
        y_bot = -6.8 - 10.2 * s
        wall = 2.0
    elif z_from_tail <= 165.0:
        rx = 13.5
        y_top = 11.0
        y_bot = -17.0
        wall = 1.9
    else:
        # Ogiva contínua de Z=165mm até Z=245mm (sem degrau na ponta!)
        u = (z_from_tail - 165.0) / (245.0 - 165.0)
        taper = max(0.06, (1.0 - (u ** 1.65)) ** 0.58)
        rx = 13.5 * taper
        droop = -2.2 * (u ** 1.4)
        y_top = droop + 11.0 * taper
        y_bot = droop - 17.0 * taper
        wall = min(2.1, max(1.2, rx * 0.48))

    return rx, y_top, y_bot, wall


def generate_fuselage_pod_245mm() -> List[Triangle]:
    """
    Gera o Pod da Fuselagem de 245mm contínuo, aerodinâmico e 100% imprimível em pé na Bambu Lab P2S:
    - Bloco 1 (Z = 0 a 146mm): Seção fechada com soquete Ø8.16mm na base (Z=0..55mm) e Berço da Asa
      em "V" (diedro de 5.0°/lado) com transição contínua sem degraus.
    - Bloco 2 (Z = 146 a 218mm): Cabine aberta em "U" com transição em arco de 45° no início (146..162mm)
      e no fim (202..218mm), eliminando degraus horizontais e permitindo imprimir sem suportes!
    - Bloco 3 (Z = 218 a 236mm): Proa oca para a ponta da bateria LiPo 1S 350mAh.
    - Bloco 4 (Z = 236 a 245mm): Ponta do bico maciça e arredondada sem degrau.
    """
    tris: List[Triangle] = []
    m_pts = 32

    def make_closed_ring(z: float) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
        rx, y_top, y_bot, wall = pod_cross_section_dims(z)
        y_mid = 0.5 * (y_top + y_bot)
        ry = 0.5 * (y_top - y_bot)
        outer_u, outer_l, inner_u, inner_l = [], [], [], []
        saddle_blend = math.sin(math.pi * (z - 35.0) / 111.0) ** 0.75 if 35.0 <= z <= 146.0 else 0.0

        for i in range(m_pts):
            ang_u = math.pi * i / (m_pts - 1)
            ox_u = rx * math.cos(ang_u)
            oy_ellipse = y_mid + ry * math.sin(ang_u)
            if saddle_blend > 0.0:
                v_saddle = (y_top - 2.2) + abs(ox_u) * DIHEDRAL_TAN
                oy_u = (1.0 - saddle_blend) * oy_ellipse + saddle_blend * min(oy_ellipse, v_saddle)
            else:
                oy_u = oy_ellipse

            ang_l = math.pi + math.pi * i / (m_pts - 1)
            ox_l = rx * math.cos(ang_l)
            oy_l = y_mid + ry * math.sin(ang_l)

            if z <= 55.0:
                u_b = max(0.0, (z - 35.0) / 20.0) if z > 35.0 else 0.0
                irx = 4.08 * (1.0 - u_b) + max(4.08, rx - wall) * u_b
                iry = 4.08 * (1.0 - u_b) + max(4.08, ry - wall) * u_b
                iy_mid = y_mid * u_b
            else:
                irx = max(1.8, rx - wall)
                iry = max(1.8, ry - wall)
                iy_mid = y_mid

            ix_u = irx * math.cos(ang_u)
            iy_u = min(oy_u - 1.5, iy_mid + iry * math.sin(ang_u))
            ix_l = irx * math.cos(ang_l)
            iy_l = iy_mid + iry * math.sin(ang_l)

            outer_u.append((ox_u, oy_u))
            outer_l.append((ox_l, oy_l))
            inner_u.append((ix_u, iy_u))
            inner_l.append((ix_l, iy_l))

        return (outer_u + outer_l, inner_u + inner_l)

    def make_u_cockpit_arcs(z: float) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
        rx, y_top, y_bot, wall = pod_cross_section_dims(z)
        y_mid = 0.5 * (y_top + y_bot)
        ry = 0.5 * (y_top - y_bot)
        irx = max(2.5, rx - wall)
        iry = max(2.5, ry - wall)

        # Transição em arco suave (formato de gota / canopy) nas pontas da cabine (146..160mm e 204..218mm)
        if z < 160.0:
            open_frac = (z - 146.0) / 14.0
        elif z > 204.0:
            open_frac = (218.0 - z) / 14.0
        else:
            open_frac = 1.0
        open_frac = max(0.15, min(1.0, open_frac))
        half_gap_deg = 82.0 * open_frac  # Abre até 82° para cada lado do topo para amplo acesso aos 4 servos e LiPo

        ang_start = math.radians(90.0 - half_gap_deg)
        ang_end = math.radians(90.0 + half_gap_deg - 360.0)
        n_arc = 44
        outer_arc = []
        inner_arc = []
        for i in range(n_arc):
            u = i / (n_arc - 1)
            ang = ang_start + u * (ang_end - ang_start)
            outer_arc.append((rx * math.cos(ang), y_mid + ry * math.sin(ang)))
            inner_arc.append((irx * math.cos(ang), y_mid + iry * math.sin(ang)))
        return outer_arc, inner_arc

    # 1. Bloco Traseiro e Berço da Asa (Z = 0.0 a 146.0mm)
    z_b1 = [146.0 * (i / 38.0) for i in range(39)]
    out_b1, hol_b1 = [], []
    for z in z_b1:
        o, h = make_closed_ring(z)
        out_b1.append(o)
        hol_b1.append([h])
    tris.extend(loft_with_holes(out_b1, hol_b1, z_b1))

    # 2. Bloco do Cockpit Aberto em Gota (Z = 146.0 a 218.0mm)
    z_b2 = [146.0 + 72.0 * (i / 28.0) for i in range(29)]
    arcs_b2 = [make_u_cockpit_arcs(z) for z in z_b2]
    n_arc = len(arcs_b2[0][0])
    for s in range(len(z_b2) - 1):
        z0, z1 = z_b2[s], z_b2[s + 1]
        o0, i0 = arcs_b2[s]
        o1, i1 = arcs_b2[s + 1]
        for k in range(n_arc - 1):
            tris.extend(quad_to_tris((o0[k][0], o0[k][1], z0), (o0[k + 1][0], o0[k + 1][1], z0), (o1[k + 1][0], o1[k + 1][1], z1), (o1[k][0], o1[k][1], z1), flip=True))
            tris.extend(quad_to_tris((i0[k][0], i0[k][1], z0), (i0[k + 1][0], i0[k + 1][1], z0), (i1[k + 1][0], i1[k + 1][1], z1), (i1[k][0], i1[k][1], z1), flip=False))
        tris.extend(quad_to_tris((o0[0][0], o0[0][1], z0), (i0[0][0], i0[0][1], z0), (i1[0][0], i1[0][1], z1), (o1[0][0], o1[0][1], z1), flip=True))
        tris.extend(quad_to_tris((i0[-1][0], i0[-1][1], z0), (o0[-1][0], o0[-1][1], z0), (o1[-1][0], o1[-1][1], z1), (i1[-1][0], i1[-1][1], z1), flip=True))
    for cap_idx, flip_cap in [(0, False), (len(z_b2) - 1, True)]:
        zc = z_b2[cap_idx]
        oc, ic = arcs_b2[cap_idx]
        for k in range(n_arc - 1):
            tris.extend(quad_to_tris((oc[k][0], oc[k][1], zc), (oc[k + 1][0], oc[k + 1][1], zc), (ic[k + 1][0], ic[k + 1][1], zc), (ic[k][0], ic[k][1], zc), flip=flip_cap))

    # 3. Bloco da Proa Oca p/ Bateria 1S (Z = 218.0 a 236.0mm)
    z_b3 = [218.0 + 18.0 * (i / 10.0) for i in range(11)]
    out_b3, hol_b3 = [], []
    for z in z_b3:
        o, h = make_closed_ring(z)
        out_b3.append(o)
        hol_b3.append([h])
    tris.extend(loft_with_holes(out_b3, hol_b3, z_b3))

    # 4. Ponta Maciça Arredondada do Bico (Z = 236.0 a 245.0mm)
    z_b4 = [236.0 + 9.0 * (i / 10.0) for i in range(11)]
    out_b4 = []
    for z in z_b4:
        o, _ = make_closed_ring(z)
        out_b4.append(o)
    tris.extend(loft_with_holes(out_b4, [], z_b4))

    return tris


def generate_canopy_hatch() -> List[Triangle]:
    """
    Tampa superior aerodinâmica do Canopy (comprimento 72mm, cobrindo Z = 146mm a Z = 218mm do Pod)
    impressa em pé com o arco superior exato da ogiva do Pod para fechamento contínuo da fuselagem.
    """
    z_slices = []
    outer_loops = []
    m_pts = 28
    for s in range(29):
        v = s / 28.0
        z_local = v * 72.0
        z_pod = 146.0 + z_local
        rx, y_top, y_bot, wall = pod_cross_section_dims(z_pod)
        y_mid = 0.5 * (y_top + y_bot)
        ry = 0.5 * (y_top - y_bot)
        irx = max(2.5, rx - 1.5)
        iry = max(2.5, ry - 1.5)

        if z_pod < 160.0:
            open_frac = (z_pod - 146.0) / 14.0
        elif z_pod > 204.0:
            open_frac = (218.0 - z_pod) / 14.0
        else:
            open_frac = 1.0
        open_frac = max(0.15, min(1.0, open_frac))
        half_gap_deg = 80.0 * open_frac

        ang_r = math.radians(90.0 - half_gap_deg)
        ang_l = math.radians(90.0 + half_gap_deg)
        upper_curve = []
        lower_curve = []
        for i in range(m_pts):
            u = i / (m_pts - 1)
            ang = ang_r + u * (ang_l - ang_r)
            upper_curve.append((rx * math.cos(ang), y_mid + ry * math.sin(ang)))
        for i in range(m_pts):
            u = i / (m_pts - 1)
            ang_b = ang_l - u * (ang_l - ang_r)
            lower_curve.append((irx * math.cos(ang_b), y_mid + iry * math.sin(ang_b)))
        z_slices.append(z_local)
        outer_loops.append(upper_curve + lower_curve)
    return loft_with_holes(outer_loops, [], z_slices)


def generate_box_with_holes(
    width_x: float,
    length_y: float,
    height_z: float,
    holes_xy: List[Tuple[float, float, float]],
) -> List[Triangle]:
    n_per_hole = 36
    total_pts = max(64, n_per_hole * max(1, len(holes_xy)))
    outer: List[Tuple[float, float]] = []
    hx = width_x * 0.5
    hy = length_y * 0.5
    for i in range(total_pts):
        ang = 2.0 * math.pi * i / total_pts
        c, s = math.cos(ang), math.sin(ang)
        px = hx * math.copysign(abs(c) ** 0.15, c)
        py = hy * math.copysign(abs(s) ** 0.15, s)
        outer.append((px, py))

    holes_loops = [get_circle_loop(cx, cy, r, n_pts=n_per_hole) for (cx, cy, r) in holes_xy]
    return loft_with_holes(
        [outer, outer],
        [holes_loops, holes_loops] if holes_loops else [],
        [0.0, height_z],
    )


def generate_servo_tray_4x() -> List[Triangle]:
    holes = [
        (-5.2, -22.0, 4.2),
        (5.2, -10.0, 4.2),
        (-5.5, 18.0, 4.2),
        (5.5, 18.0, 4.2),
    ]
    return generate_box_with_holes(23.0, 82.0, 3.2, holes)


def generate_root_rib_joiner(is_right: bool) -> List[Triangle]:
    """
    Costela de Raiz Híbrida em PETG (15mm) com:
    - Túnel angulado de -5.0° para a baioneta reta de carbono Ø4mm (em X=38.5mm)
    - Furo para o tubo principal Ø6x4mm / Luva em V (em X=49.0mm)
    - Furo angulado de -5.0° para o pino traseiro anti-rotação Ø4mm (em X=98.0mm)
    - Aba escalonada com 2 furos passantes M3 (X=25mm e X=90mm)
    """
    z_slices = [0.0, 15.0]
    sign_y = 1.0 if is_right else -1.0
    loop = get_airfoil_loop(
        chord=150.0,
        x_offset=0.0,
        y_offset=0.0,
        t_ratio=0.074,
        camber=0.018,
        x_start_frac=0.0,
        x_end_frac=0.745,
        n_pts=48,
        te_min_mm=1.2,
    )
    if not is_right:
        loop = [(px, -py) for (px, py) in reversed(loop)]

    holes_per_z = []
    for z_val in z_slices:
        # O túnel da baioneta reta Ø4mm (X=38.5mm) e do pino traseiro (X=98.0mm) inclinam -5.0° ao longo dos 15mm!
        dy_dihedral = z_val * DIHEDRAL_TAN
        h_dihedral_rod = get_circle_loop(38.5, (2.60 - dy_dihedral) * sign_y, 2.08, n_pts=36)
        h_main_spar = get_circle_loop(49.0, 1.25 * sign_y, 3.12, n_pts=36)
        h_rear_pin = get_circle_loop(98.0, (1.40 - dy_dihedral) * sign_y, 2.08, n_pts=36)
        holes_per_z.append([h_dihedral_rod, h_main_spar, h_rear_pin])

    rib_tris = loft_with_holes([loop, loop], holes_per_z, z_slices)

    tab_tris = generate_box_with_holes(
        width_x=90.0,
        length_y=12.0,
        height_z=4.5,
        holes_xy=[(-32.5, 0.0, 1.65), (32.5, 0.0, 1.65)],
    )
    z_tab_offset = 0.0 if not is_right else 4.5
    for p1, p2, p3 in tab_tris:
        tp1 = (p1[0] + 57.5, p1[1], p1[2] + z_tab_offset)
        tp2 = (p2[0] + 57.5, p2[1], p2[2] + z_tab_offset)
        tp3 = (p3[0] + 57.5, p3[1], p3[2] + z_tab_offset)
        rib_tris.append((tp1, tp2, tp3))

    return rib_tris


def generate_dihedral_v_joiner_10deg() -> List[Triangle]:
    """
    Gera a Baioneta/Luva Central em "V" com 10.0° de diedro total (5.0° de cada lado):
    - Recebe 2 segmentos retos de vareta de carbono Ø4.0mm x 65mm (um de cada lado, no ângulo exato de 5.0°)
    - Possui os 2 furos passantes M3 (X=25mm e X=90mm) para ser parafusada junto com as abas da asa no Pod!
    """
    z_slices = []
    outer_loops = []
    hole_loops = []
    # Varre de Z = -45mm (asa esquerda) até Z = +45mm (asa direita), dobrando em V com 5.0° no centro (Z=0)
    for s in range(21):
        v = (s / 20.0) * 2.0 - 1.0  # -1.0 a +1.0
        z = v * 45.0
        y_v_shift = abs(z) * DIHEDRAL_TAN  # Sobe exatamente 5.0° para cada lado!
        outer = get_circle_loop(49.0, y_v_shift, 3.05, n_pts=40)  # Entra justa no tubo Ø6.25mm ou berço
        inner = get_circle_loop(49.0, y_v_shift, 2.06, n_pts=40)  # Alma interna p/ vareta de carbono Ø4.0mm
        z_slices.append(z)
        outer_loops.append(outer)
        hole_loops.append([inner])

    return loft_with_holes(outer_loops, hole_loops, z_slices)


def generate_xtail_center_clamp_8mm() -> List[Triangle]:
    sleeve = generate_cylinder_z(cx=0.0, cy=0.0, r_outer=6.0, r_inner=4.08, z0=0.0, z1=32.0)
    saddle = generate_box_with_holes(
        width_x=14.0,
        length_y=32.0,
        height_z=5.0,
        holes_xy=[(0.0, -8.0, 1.05), (0.0, 8.0, 1.05)],
    )
    for p1, p2, p3 in saddle:
        sp1 = (p1[0], p1[2] + 5.0, p1[1] + 16.0)
        sp2 = (p2[0], p2[2] + 5.0, p2[1] + 16.0)
        sp3 = (p3[0], p3[2] + 5.0, p3[1] + 16.0)
        sleeve.append((sp1, sp2, sp3))
    return sleeve


def generate_flaperon_root_horns() -> List[Triangle]:
    tris: List[Triangle] = []
    for offset_x in (-12.0, 12.0):
        horn = generate_box_with_holes(
            width_x=16.0,
            length_y=12.0,
            height_z=3.0,
            holes_xy=[(-4.5, 0.0, 1.05), (5.0, 3.5, 0.85)],
        )
        for p1, p2, p3 in horn:
            tris.append(((p1[0] + offset_x, p1[1], p1[2]), (p2[0] + offset_x, p2[1], p2[2]), (p3[0] + offset_x, p3[1], p3[2])))
    return tris


# ==============================================================================
# 7. GERADOR DE BLUEPRINTS TÉCNICOS VETORIAIS (SVG + DXF EM ESCALA 1:1)
# ==============================================================================

def export_engineering_blueprints_svg_dxf(base_dir: str) -> None:
    bp_dir = os.path.join(base_dir, "blueprints")
    os.makedirs(bp_dir, exist_ok=True)
    svg_path = os.path.join(bp_dir, "DLG_Mini_950_Blueprint_Full.svg")
    dxf_path = os.path.join(bp_dir, "DLG_Mini_950_CAD_1to1.dxf")

    span_samples = [i * 5.0 for i in range(96)]
    le_pts_right = []
    te_pts_right = []
    hinge_pts_right = []
    for y in span_samples:
        c, lex = wing_chord_and_le_at_span(y)
        le_pts_right.append((lex, y))
        hinge_pts_right.append((lex + 0.75 * c, y))
        te_pts_right.append((lex + c, y))

    geodesic_lines = []
    for y in range(0, 470, 2):
        y0 = float(y)
        y1 = float(y + 2)
        c0, lex0 = wing_chord_and_le_at_span(y0)
        c1, lex1 = wing_chord_and_le_at_span(y1)
        w0 = triangle_wave(2.0 * math.pi * y0 / 36.0)
        w1 = triangle_wave(2.0 * math.pi * y1 / 36.0)
        # Nervura D-box proporcional
        db0_s, db0_e = lex0 + 0.04 * c0, 49.0 - 4.3
        db1_s, db1_e = lex1 + 0.04 * c1, 49.0 - 4.3
        db0 = 0.5 * (db0_s + db0_e) + 0.28 * (db0_e - db0_s) * w0
        db1 = 0.5 * (db1_s + db1_e) + 0.28 * (db1_e - db1_s) * w1
        geodesic_lines.append(((db0, y0), (db1, y1)))
        # Nervuras caixa central proporcionais (entre X=53.3mm e 64.5% da corda)
        m0_s, m0_e = 53.3, lex0 + 0.645 * c0 - 2.2
        m1_s, m1_e = 53.3, lex1 + 0.645 * c1 - 2.2
        mw0 = m0_e - m0_s
        mw1 = m1_e - m1_s
        geodesic_lines.append(((m0_s + 0.33 * mw0 + 0.11 * mw0 * w0, y0), (m1_s + 0.33 * mw1 + 0.11 * mw1 * w1, y1)))
        geodesic_lines.append(((m0_s + 0.67 * mw0 - 0.11 * mw0 * w0, y0), (m1_s + 0.67 * mw1 - 0.11 * mw1 * w1, y1)))
        if 20 <= y <= 453:
            fw0 = triangle_wave(2.0 * math.pi * y0 / 28.0)
            fw1 = triangle_wave(2.0 * math.pi * y1 / 28.0)
            f0_s, f0_e = lex0 + 0.785 * c0 + 2.0, lex0 + c0 - 3.2
            f1_s, f1_e = lex1 + 0.785 * c1 + 2.0, lex1 + c1 - 3.2
            f0 = 0.5 * (f0_s + f0_e) + 0.24 * (f0_e - f0_s) * fw0
            f1 = 0.5 * (f1_s + f1_e) + 0.24 * (f1_e - f1_s) * fw1
            geodesic_lines.append(((f0, y0), (f1, y1)))

    svg_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1800 1250" width="1800" height="1250">',
        '<rect width="1800" height="1250" fill="#0b2242"/>',
    ]

    def svg_line_poly(x1: float, y1: float, x2: float, y2: float, width: float, color: str) -> str:
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length < 1e-6:
            return ""
        nx = -dy / length * (width * 0.5)
        ny = dx / length * (width * 0.5)
        pts = f"{x1 + nx:.2f},{y1 + ny:.2f} {x2 + nx:.2f},{y2 + ny:.2f} {x2 - nx:.2f},{y2 - ny:.2f} {x1 - nx:.2f},{y1 - ny:.2f}"
        return f'<polygon points="{pts}" fill="{color}"/>'

    # Desenha a malha de engenharia (grid) com retângulos preenchidos para compatibilidade 100% com SVG e JPG/PNG
    for gx in range(25, 1776, 25):
        col_g = "#1d4982" if (gx - 25) % 100 == 0 else "#12325c"
        w_g = 1.4 if (gx - 25) % 100 == 0 else 0.8
        svg_lines.append(f'<rect x="{gx:.1f}" y="90" width="{w_g}" height="1135" fill="{col_g}"/>')
    for gy in range(90, 1226, 25):
        col_g = "#1d4982" if (gy - 90) % 100 == 0 else "#12325c"
        w_g = 1.4 if (gy - 90) % 100 == 0 else 0.8
        svg_lines.append(f'<rect x="25" y="{gy:.1f}" width="1750" height="{w_g}" fill="{col_g}"/>')

    svg_lines.extend([
        '<rect x="25" y="25" width="1750" height="65" fill="#07172e" stroke="#7ec8ff" stroke-width="2"/>',
        '<text x="45" y="65" fill="#ffffff" font-family="Monaco, monospace" font-size="21" font-weight="bold">BLUEPRINT TÉCNICO CAD: DLG-MINI 950 3DP (DIEDRO 5.0°/LADO + NERVURAS GEODÉSICAS 0% INFILL)</text>',
        '<text x="1320" y="63" fill="#7ec8ff" font-family="Monaco, monospace" font-size="14">DIEDRO: 10° TOTAL (+41.4mm PONTA) | ENV: 950mm</text>',
    ])

    cx_top, cy_top = 555.0, 275.0
    scale_top = 0.96

    def map_top(x_long: float, y_span: float) -> Tuple[float, float]:
        return (cx_top + y_span * scale_top, cy_top + x_long * scale_top)

    svg_lines.append('<text x="55" y="122" fill="#ffd166" font-family="Monaco, monospace" font-size="16" font-weight="bold">1. VISTA EM PLANTA (ASA ESQ: NERVURAS GEODÉSICAS 45° INTERNAS | ASA DIR: PAINÉIS W1/W2)</text>')

    # Tubo de Carbono da Cauda Ø8x6mm (de X=0mm a X=+505mm)
    p_boom0 = map_top(0.0, -4.0)
    p_boom1 = map_top(505.0, 4.0)
    svg_lines.append(
        f'<rect x="{p_boom0[0]:.1f}" y="{p_boom0[1]:.1f}" width="{p_boom1[0] - p_boom0[0]:.1f}" height="{p_boom1[1] - p_boom0[1]:.1f}" fill="#ffd166" stroke="#ffffff" stroke-width="1.2"/>'
    )

    # Pod da Fuselagem (245mm: X=-135mm até X=+110mm)
    pod_center = map_top(-12.5, 0.0)
    svg_lines.append(f'<ellipse cx="{pod_center[0]:.1f}" cy="{pod_center[1]:.1f}" rx="{14.0 * scale_top:.1f}" ry="{122.5 * scale_top:.1f}" fill="#1d4e89" stroke="#ffffff" stroke-width="2"/>')

    # Polígono da Asa Completa (950mm) + Borda branca
    wing_poly_pts = []
    for lex, y in reversed(le_pts_right):
        wing_poly_pts.append(map_top(lex, -y))
    for lex, y in le_pts_right[1:]:
        wing_poly_pts.append(map_top(lex, y))
    for tex, y in reversed(te_pts_right):
        wing_poly_pts.append(map_top(tex, y))
    for tex, y in te_pts_right[1:]:
        wing_poly_pts.append(map_top(tex, -y))

    pts_str = " ".join(f"{px:.1f},{py:.1f}" for px, py in wing_poly_pts)
    svg_lines.append(f'<polygon points="{pts_str}" fill="#143d6b" fill-opacity="0.82"/>')
    for i in range(len(wing_poly_pts)):
        p0 = wing_poly_pts[i]
        p1 = wing_poly_pts[(i + 1) % len(wing_poly_pts)]
        svg_lines.append(svg_line_poly(p0[0], p0[1], p1[0], p1[1], 2.4, "#ffffff"))

    # Nervuras Geodésicas Internas
    for (x0, y0), (x1, y1) in geodesic_lines:
        p0_l = map_top(x0, -y0)
        p1_l = map_top(x1, -y1)
        svg_lines.append(svg_line_poly(p0_l[0], p0_l[1], p1_l[0], p1_l[1], 1.6, "#5ce1e6"))
        p0_r = map_top(x0, y0)
        p1_r = map_top(x1, y1)
        svg_lines.append(svg_line_poly(p0_r[0], p0_r[1], p1_r[0], p1_r[1], 1.1, "#2c6cb0"))

    # Longarinas e Baionetas de Carbono na Asa
    for x_spar, span_lim, col, w_stroke in [
        (38.5, 55.0, "#ff6b6b", 4.2),   # Baioneta Reta de Diedro Ø4mm x 110mm (-5.0° no plano YZ)
        (49.0, 455.0, "#ffd166", 4.6),  # Longarina Principal Tubo Ø6x4mm
        (98.0, 350.0, "#06d6a0", 2.6),  # Longarina Auxiliar Vareta Ø2mm
        (116.0, 450.0, "#ff9f1c", 2.4), # Vareta Antitorção do Flaperon Ø2mm
    ]:
        pL = map_top(x_spar, -span_lim)
        pR = map_top(x_spar, span_lim)
        svg_lines.append(svg_line_poly(pL[0], pL[1], pR[0], pR[1], w_stroke, col))

    # Linha de Dobradiça dos Flaperons (X = 112.5mm)
    hL = map_top(112.5, -455.0)
    hR = map_top(112.5, 455.0)
    svg_lines.append(svg_line_poly(hL[0], hL[1], hR[0], hR[1], 1.6, "#ffffff"))

    # Linha de divisão W1 (245mm) / W2 (230mm) para a Bambu Lab P2S
    for side in (-1.0, 1.0):
        p_div0 = map_top(8.0, side * 245.0)
        p_div1 = map_top(152.0, side * 245.0)
        svg_lines.append(svg_line_poly(p_div0[0], p_div0[1], p_div1[0], p_div1[1], 2.8, "#ff6b6b"))

    # Pino de Lançamento (Launch Peg Ø4mm na ponta esquerda)
    peg0 = map_top(49.0, -445.0)
    peg1 = map_top(49.0, -483.0)
    svg_lines.append(svg_line_poly(peg0[0], peg0[1], peg1[0], peg1[1], 6.5, "#ff6b6b"))

    # Estabilizador Horizontal X-Tail (Envergadura 240mm = ±120mm)
    ht_pts = [
        map_top(445.0, -120.0),
        map_top(435.0, 0.0),
        map_top(445.0, 120.0),
        map_top(495.0, 120.0),
        map_top(510.0, 0.0),
        map_top(495.0, -120.0),
    ]
    ht_str = " ".join(f"{px:.1f},{py:.1f}" for px, py in ht_pts)
    svg_lines.append(f'<polygon points="{ht_str}" fill="#143d6b"/>')
    for i in range(len(ht_pts)):
        p0 = ht_pts[i]
        p1 = ht_pts[(i + 1) % len(ht_pts)]
        svg_lines.append(svg_line_poly(p0[0], p0[1], p1[0], p1[1], 2.2, "#ffffff"))
    ht_spar_L = map_top(458.0, -118.0)
    ht_spar_R = map_top(458.0, 118.0)
    svg_lines.append(svg_line_poly(ht_spar_L[0], ht_spar_L[1], ht_spar_R[0], ht_spar_R[1], 2.4, "#06d6a0"))

    svg_lines.append(f'<text x="{cx_top - 455:.1f}" y="{cy_top - 22:.1f}" fill="#ff6b6b" font-family="Monaco, monospace" font-size="13">LAUNCH PEG Ø4mm</text>')
    svg_lines.append(f'<text x="{cx_top - 420:.1f}" y="{cy_top + 178:.1f}" fill="#5ce1e6" font-family="Monaco, monospace" font-size="13">NERVURAS GEODÉSICAS 45° (0.85mm NO CAD - 0% INFILL)</text>')
    svg_lines.append(f'<text x="{cx_top + 55:.1f}" y="{cy_top - 22:.1f}" fill="#ffd166" font-family="Monaco, monospace" font-size="13">TUBO Ø6x4mm (X=49mm) + BAIONETA DIEDRO 5° (X=38.5mm)</text>')
    svg_lines.append(f'<text x="{cx_top + 55:.1f}" y="{cy_top + 178:.1f}" fill="#ff9f1c" font-family="Monaco, monospace" font-size="13">VARETA ANTITORÇÃO Ø2mm NO FLAPERON (X=116mm)</text>')
    svg_lines.append(f'<text x="{cx_top + 165:.1f}" y="{cy_top + 410:.1f}" fill="#ffd166" font-family="Monaco, monospace" font-size="13">ESTABILIZADOR X-TAIL (240mm x 75mm)</text>')

    # ==================== 2. VISTA LATERAL COMPLETA (640mm) COM POD 4 SERVOS + X-TAIL ====================
    svg_lines.append('<rect x="55" y="770" width="995" height="190" fill="#07172e" stroke="#7ec8ff" stroke-width="1.8"/>')
    svg_lines.append('<text x="75" y="795" fill="#ffd166" font-family="Monaco, monospace" font-size="15" font-weight="bold">2. VISTA LATERAL (640mm) — POD 245mm + 4 SERVOS + BOOM CARBONO Ø8x6mm + LEME X-TAIL 175mm</text>')

    side_ox, side_oy = 230.0, 875.0
    side_s = 1.15
    svg_lines.append(f'<rect x="{side_ox + 55 * side_s:.1f}" y="{side_oy - 4.0 * side_s:.1f}" width="{450 * side_s:.1f}" height="{8.0 * side_s:.1f}" fill="#ffd166" stroke="#ffffff" stroke-width="1.2"/>')
    pod_side_pts = [
        (side_ox - 135 * side_s, side_oy + 2),
        (side_ox - 115 * side_s, side_oy - 12 * side_s),
        (side_ox - 40 * side_s, side_oy - 16 * side_s),
        (side_ox + 15 * side_s, side_oy - 12 * side_s),
        (side_ox + 110 * side_s, side_oy - 4 * side_s),
        (side_ox + 110 * side_s, side_oy + 5 * side_s),
        (side_ox + 20 * side_s, side_oy + 17 * side_s),
        (side_ox - 75 * side_s, side_oy + 16 * side_s),
        (side_ox - 125 * side_s, side_oy + 8 * side_s),
    ]
    pod_side_str = " ".join(f"{px:.1f},{py:.1f}" for px, py in pod_side_pts)
    svg_lines.append(f'<polygon points="{pod_side_str}" fill="#143d6b" stroke="#ffffff" stroke-width="2.0"/>')
    svg_lines.append(f'<rect x="{side_ox - 118 * side_s:.1f}" y="{side_oy - 5 * side_s:.1f}" width="{38 * side_s:.1f}" height="{12 * side_s:.1f}" fill="#06d6a0" stroke="#ffffff" stroke-width="1"/>')
    svg_lines.append(f'<rect x="{side_ox - 55 * side_s:.1f}" y="{side_oy - 4 * side_s:.1f}" width="{18 * side_s:.1f}" height="{14 * side_s:.1f}" fill="#ff9f1c" stroke="#ffffff" stroke-width="1"/>')
    svg_lines.append(f'<rect x="{side_ox - 30 * side_s:.1f}" y="{side_oy - 4 * side_s:.1f}" width="{18 * side_s:.1f}" height="{14 * side_s:.1f}" fill="#ff9f1c" stroke="#ffffff" stroke-width="1"/>')
    svg_lines.append(f'<rect x="{side_ox + 5 * side_s:.1f}" y="{side_oy - 5 * side_s:.1f}" width="{18 * side_s:.1f}" height="{14 * side_s:.1f}" fill="#ff6b6b" stroke="#ffffff" stroke-width="1"/>')
    svg_lines.append(svg_line_poly(side_ox + 23 * side_s, side_oy - 6 * side_s, side_ox + 116 * side_s, side_oy - 13 * side_s, 2.8, "#ff6b6b"))
    wing_side_pts = [
        (side_ox + px * side_s, side_oy - 13 * side_s - py * side_s)
        for px, py in get_airfoil_loop(150.0, 0.0, 0.0, 0.074, 0.018, 0.0, 1.0, n_pts=30)
    ]
    svg_lines.append(f'<polygon points="{" ".join(f"{px:.1f},{py:.1f}" for px, py in wing_side_pts)}" fill="#7ec8ff" fill-opacity="0.45" stroke="#ffffff" stroke-width="1.8"/>')
    vt_side_pts = [
        (side_ox + 435 * side_s, side_oy),
        (side_ox + 465 * side_s, side_oy - 68 * side_s),
        (side_ox + 503 * side_s, side_oy - 68 * side_s),
        (side_ox + 510 * side_s, side_oy),
        (side_ox + 500 * side_s, side_oy + 45 * side_s),
        (side_ox + 460 * side_s, side_oy + 45 * side_s),
    ]
    svg_lines.append(f'<polygon points="{" ".join(f"{px:.1f},{py:.1f}" for px, py in vt_side_pts)}" fill="#143d6b" stroke="#ffffff" stroke-width="2.0"/>')
    svg_lines.append(f'<text x="{side_ox - 130 * side_s:.1f}" y="{side_oy + 38:.1f}" fill="#06d6a0" font-family="Monaco, monospace" font-size="12">LiPo 1S + RX</text>')
    svg_lines.append(f'<text x="{side_ox - 40 * side_s:.1f}" y="{side_oy + 38:.1f}" fill="#ff9f1c" font-family="Monaco, monospace" font-size="12">4x Servos + Pushrod Curto</text>')
    svg_lines.append(f'<text x="{side_ox + 185 * side_s:.1f}" y="{side_oy + 28:.1f}" fill="#ffd166" font-family="Monaco, monospace" font-size="12">Tubo Carbono Ø8x6mm (450mm)</text>')

    # ==================== 3. CORTE TRANSVERSAL DA RAIZ DA ASA (0% INFILL + TÚNEL DIEDRO 5°) ====================
    svg_lines.append('<rect x="55" y="975" width="995" height="230" fill="#07172e" stroke="#7ec8ff" stroke-width="1.8"/>')
    svg_lines.append('<text x="75" y="1002" fill="#ffd166" font-family="Monaco, monospace" font-size="15" font-weight="bold">3. CORTE DA RAIZ DA ASA (c = 150mm) — CÂMARAS OCAS (0% INFILL) + TÚNEL DE DIEDRO 5.0°</text>')

    sec_ox, sec_oy = 115.0, 1105.0
    sec_scale = 5.4
    outer_sec = get_airfoil_loop(150.0, 0.0, 0.0, 0.074, 0.018, 0.0, 0.745, n_pts=60, te_min_mm=1.2)
    flap_sec = get_airfoil_loop(150.0, 0.0, 0.0, 0.074, 0.018, 0.755, 1.0, n_pts=40, te_min_mm=0.85)

    outer_sec_str = " ".join(f"{sec_ox + px * sec_scale:.1f},{sec_oy - py * sec_scale:.1f}" for px, py in outer_sec)
    flap_sec_str = " ".join(f"{sec_ox + px * sec_scale:.1f},{sec_oy - py * sec_scale:.1f}" for px, py in flap_sec)
    svg_lines.append(f'<polygon points="{outer_sec_str}" fill="#1b467a" stroke="#ffffff" stroke-width="2.5"/>')
    svg_lines.append(f'<polygon points="{flap_sec_str}" fill="#1b467a" stroke="#ffffff" stroke-width="2.5"/>')

    bays_x = [(2.5, 17.5), (18.8, 34.8), (53.2, 67.0), (68.2, 81.2), (82.4, 95.8), (100.2, 110.5), (118.2, 132.0), (133.2, 146.5)]
    for bx0, bx1 in bays_x:
        bay_loop = get_airfoil_hollow_bay_loop(bx0, bx1, 150.0, 0.0, 0.074, 0.018, 0.45, True, n_seg=12)
        bay_str = " ".join(f"{sec_ox + px * sec_scale:.1f},{sec_oy - py * sec_scale:.1f}" for px, py in bay_loop)
        svg_lines.append(f'<polygon points="{bay_str}" fill="#051020" stroke="#5ce1e6" stroke-width="1.5"/>')

    for cx_mm, cy_override, r_mm, col in [
        (38.5, 2.6, 2.0, "#ff6b6b"),
        (49.0, None, 3.0, "#ffd166"),
        (98.0, None, 1.0, "#06d6a0"),
        (116.0, None, 1.0, "#ff9f1c"),
    ]:
        yu, yl = airfoil_synerj_dlg(cx_mm / 150.0, 0.074, 0.018)
        cy_mm = cy_override if cy_override is not None else 0.5 * (yu + yl) * 150.0
        scx = sec_ox + cx_mm * sec_scale
        scy = sec_oy - cy_mm * sec_scale
        svg_lines.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{r_mm * sec_scale:.1f}" fill="{col}" stroke="#ffffff" stroke-width="1.5"/>')

    svg_lines.append('<text x="75" y="1188" fill="#ffffff" font-family="Monaco, monospace" font-size="12">VERMELHO (X=38.5): Baioneta Diedro -5° Ø4mm | AMARELO (X=49): Tubo Ø6x4mm | ESCURO: Câmaras Ocas 0% Infill</text>')

    # ==================== 4. PAINEL DIREITO: VISTA FRONTAL DO DIEDRO E TABELA TÉCNICA ====================
    svg_lines.append('<rect x="1075" y="110" width="675" height="1095" fill="#07172e" stroke="#7ec8ff" stroke-width="1.8"/>')
    svg_lines.append('<text x="1095" y="145" fill="#ffd166" font-family="Monaco, monospace" font-size="16" font-weight="bold">4. VISTA FRONTAL DO DIEDRO (5.0°/LADO) &amp; TABELA DE ENGENHARIA</text>')

    fcx, fcy = 1412.0, 275.0
    f_scale = 0.62
    tip_dx = 475.0 * f_scale
    tip_dy = 475.0 * math.sin(DIHEDRAL_RAD) * f_scale
    svg_lines.append(svg_line_poly(fcx - tip_dx, fcy, fcx + tip_dx, fcy, 1.5, "#3b82f6"))
    svg_lines.append(svg_line_poly(fcx, fcy, fcx - tip_dx, fcy - tip_dy, 5.2, "#ffffff"))
    svg_lines.append(svg_line_poly(fcx, fcy, fcx + tip_dx, fcy - tip_dy, 5.2, "#ffffff"))
    svg_lines.append(svg_line_poly(fcx - 120 * f_scale, fcy - 6, fcx + 120 * f_scale, fcy - 6, 3.4, "#ffd166"))
    svg_lines.append(svg_line_poly(fcx, fcy - 105 * f_scale, fcx, fcy + 70 * f_scale, 3.4, "#ffd166"))
    svg_lines.append(f'<circle cx="{fcx:.1f}" cy="{fcy + 6:.1f}" r="11" fill="#1d4e89" stroke="#7ec8ff" stroke-width="2"/>')
    svg_lines.append(f'<text x="{fcx - 270:.1f}" y="{fcy + 70:.1f}" fill="#ffd166" font-family="Monaco, monospace" font-size="13.5" font-weight="bold">DIEDRO ÓTIMO DE PLANEIO: 5.0° POR LADO (10.0° TOTAL = +41.4mm PONTA)</text>')

    specs_text = [
        ("MODELO BASE DE REFERÊNCIA:", "RCRCM DLG-Mini X-Tail"),
        ("IMPRESSORA 3D CONFIGURADA:", "Bambu Lab P2S (256 x 256 x 256 mm)"),
        ("ENVERGADURA TOTAL (b):", "950 mm (2x 475 mm Bipartida)"),
        ("COMPRIMENTO TOTAL (L):", "640 mm (Pod 245mm + Boom exposto 395mm)"),
        ("DIEDRO ÓTIMO DE PLANEIO:", "5.0° por semi-asa (10.0° Total)"),
        ("ELEVAÇÃO VERTICAL DA PONTA:", "+41.4 mm acima da raiz (475 * sin 5°)"),
        ("GERAÇÃO FÍSICA DO DIEDRO:", "Túnel -5° (X=38.5mm) + Luva V 10° (X=49mm)"),
        ("DIVISÃO POR SEMI-ASA (P2S):", "Seção W1 = 245 mm | Seção W2 = 230 mm"),
        ("ÁREA ALAR / ALONGAMENTO:", "12.6 dm² (126.000 mm²) | AR = 7.16"),
        ("CORDA RAIZ / MEIO / PONTA:", "150 mm / 140 mm (Y=245) / 95 mm (Y=450)"),
        ("CORDA MÉDIA AERODINÂMICA:", "CMA = 133.1 mm (em Y = 219 mm)"),
        ("CENTRO DE GRAVIDADE (CG):", "45 mm do Bordo de Ataque (33.9% CMA)"),
        ("PERFIL AERODINÂMICO ASA:", "SynerJ / AG455ct-02r (Bordo Fuga 0.8mm)"),
        ("PERFIS DA CAUDA X-TAIL:", "Drela HT12 (6% Horiz) / HT14 (7% Vert)"),
        ("TUBO DA CAUDA (TAIL BOOM):", "1x Tubo Cilíndrico Carbono Ø8x6 x 450 mm"),
        ("LONGARINA PRINCIPAL ASA:", "2x Tubo Cilíndrico Carbono Ø6x4 x 450 mm"),
        ("BAIONETA RETA DE DIEDRO:", "1x Vareta Maciça Carbono Ø4 mm x 110 mm"),
        ("PINOS DA LUVA EM V (10°):", "2x Vareta Maciça Carbono Ø4 mm x 65 mm"),
        ("LONGARINAS AUX. E FLAPERON:", "Varetas Maciças Carbono Ø2.0 mm"),
        ("UNIÃO CENTRAL DA ASA:", "Abas Sobrepostas + 2x Parafusos M3"),
        ("LAYOUT DOS 4 SERVOS:", "Todos no Pod + Pushrods Curtos (Flaperon)"),
        ("FATIAMENTO BAMBU STUDIO:", "1 Parede | 0% Infill | Sem Suportes"),
    ]
    ty = 395
    for k, v in specs_text:
        svg_lines.append(f'<text x="1095" y="{ty}" fill="#7ec8ff" font-family="Monaco, monospace" font-size="13" font-weight="bold">{k}</text>')
        svg_lines.append(f'<text x="1360" y="{ty}" fill="#ffffff" font-family="Monaco, monospace" font-size="13">{v}</text>')
        ty += 35

    svg_lines.append("</svg>")
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg_lines))

    # 2. Atualiza DXF 1:1 incluindo vista frontal do diedro de 5.0° por lado (10.0° total)
    dxf_lines = ["0", "SECTION", "2", "ENTITIES"]

    def add_dxf_line(x1: float, y1: float, x2: float, y2: float, layer: str = "0") -> None:
        dxf_lines.extend([
            "0", "LINE", "8", layer,
            "10", f"{x1:.4f}", "20", f"{y1:.4f}", "30", "0.0",
            "11", f"{x2:.4f}", "21", f"{y2:.4f}", "31", "0.0",
        ])

    for i in range(len(le_pts_right) - 1):
        add_dxf_line(le_pts_right[i][0], le_pts_right[i][1], le_pts_right[i + 1][0], le_pts_right[i + 1][1], "WING_OUTLINE")
        add_dxf_line(te_pts_right[i][0], te_pts_right[i][1], te_pts_right[i + 1][0], te_pts_right[i + 1][1], "WING_OUTLINE")
        add_dxf_line(le_pts_right[i][0], -le_pts_right[i][1], le_pts_right[i + 1][0], -le_pts_right[i + 1][1], "WING_OUTLINE")
        add_dxf_line(te_pts_right[i][0], -te_pts_right[i][1], te_pts_right[i + 1][0], -te_pts_right[i + 1][1], "WING_OUTLINE")

    for (x0, y0), (x1, y1) in geodesic_lines:
        add_dxf_line(x0, y0, x1, y1, "GEODESIC_RIBS_45DEG")
        add_dxf_line(x0, -y0, x1, -y1, "GEODESIC_RIBS_45DEG")

    # Linha de elevação frontal do diedro de 5.0° por lado (41.4mm na ponta de 475mm)
    add_dxf_line(-300.0, 0.0, -300.0 + 41.4, 475.0, "DIHEDRAL_5DEG_PER_SIDE")
    add_dxf_line(-300.0, 0.0, -300.0 + 41.4, -475.0, "DIHEDRAL_5DEG_PER_SIDE")

    dxf_lines.extend(["0", "ENDSEC", "0", "EOF"])
    with open(dxf_path, "w", encoding="utf-8") as f:
        f.write("\n".join(dxf_lines))


def export_airfoil_dat_files(base_dir: str) -> None:
    airfoil_dir = os.path.join(base_dir, "airfoils")
    os.makedirs(airfoil_dir, exist_ok=True)
    profiles = [
        ("synerj_dlg_ag455ct_3dp.dat", "SYNERJ / AG455ct-02r 3DP Modified (0.8mm TE)", 0.074, 0.018, 0.0055),
        ("ht12_horizontal_tail_3dp.dat", "Drela HT12 6% Symmetric 3DP", 0.060, 0.000, 0.0080),
        ("ht14_vertical_fin_3dp.dat", "Drela HT14 7% Symmetric 3DP", 0.070, 0.000, 0.0080),
    ]
    for filename, title, t_ratio, camber, te_ratio in profiles:
        path = os.path.join(airfoil_dir, filename)
        n = 60
        xs = [0.5 * (1.0 - math.cos(math.pi * i / n)) for i in range(n + 1)]
        upper = []
        lower = []
        for x in xs:
            yu, yl = airfoil_synerj_dlg(x, t_ratio=t_ratio, m=camber, te_thick_ratio=te_ratio)
            upper.append((x, yu))
            lower.append((x, yl))
        coords = list(reversed(upper)) + lower[1:]
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"{title}\n")
            for x, y in coords:
                f.write(f"  {x:.6f}  {y:.6f}\n")


def main() -> None:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    p1_dir = os.path.join(base_dir, "stl", "Plate1_LW-PLA_Wings")
    p2_dir = os.path.join(base_dir, "stl", "Plate2_LW-PLA_XTail")
    p3_dir = os.path.join(base_dir, "stl", "Plate3_PETG_Structural_Pod")

    print("1. Exportando Perfis (.dat) e Blueprints Técnicos Vetoriais (.svg e .dxf 1:1) com Diedro 5.0°/lado...")
    export_airfoil_dat_files(base_dir)
    export_engineering_blueprints_svg_dxf(base_dir)

    print("2. Gerando Plate 1 — Asas c/ Nervuras Geodésicas 0% Infill + Túnel Angulado de Diedro 5.0°/lado...")
    tasks_p1 = [
        ("W1_Right_Inner_Wing_245mm.stl", generate_wing_segment(0.0, 245.0, is_right_wing=True, has_peg_socket=False)),
        ("W1_Left_Inner_Wing_245mm.stl", generate_wing_segment(0.0, 245.0, is_right_wing=False, has_peg_socket=False)),
        ("W2_Right_Outer_Wing_230mm.stl", generate_wing_segment(245.0, 475.0, is_right_wing=True, has_peg_socket=False)),
        ("W2_Left_Outer_Wing_Peg_230mm.stl", generate_wing_segment(245.0, 475.0, is_right_wing=False, has_peg_socket=True)),
        ("Flaperon_Right_Inner_225mm.stl", generate_flaperon_segment(20.0, 245.0, is_right_wing=True)),
        ("Flaperon_Right_Outer_210mm.stl", generate_flaperon_segment(245.0, 455.0, is_right_wing=True)),
        ("Flaperon_Left_Inner_225mm.stl", generate_flaperon_segment(20.0, 245.0, is_right_wing=False)),
        ("Flaperon_Left_Outer_210mm.stl", generate_flaperon_segment(245.0, 455.0, is_right_wing=False)),
    ]
    for fname, tris in tasks_p1:
        out_path = os.path.join(p1_dir, fname)
        write_binary_stl(out_path, tris, f"DLG950 5degDihedral {fname}")
        print(f"   -> {fname}: {len(tris)} triangulos")

    print("3. Gerando Plate 2 — Empenagem X-Tail COM NERVURAS INTERNAS NO CAD (0% Infill, Base Plana Sem Overhang)...")
    tasks_p2 = [
        (
            "XTail_Horizontal_Stabilizer_240mm.stl",
            generate_xtail_pair_stl(120.0, 120.0, 75.0, 48.0, 48.0, 0.068, 0.080, 0.0, 0.64, is_control_surface=False),
        ),
        (
            "XTail_Elevator_240mm.stl",
            generate_xtail_pair_stl(120.0, 120.0, 75.0, 48.0, 48.0, 0.068, 0.080, 0.65, 1.0, is_control_surface=True),
        ),
        (
            "XTail_Vertical_Fin_175mm.stl",
            generate_xtail_pair_stl(105.0, 70.0, 75.0, 42.0, 45.0, 0.075, 0.085, 0.0, 0.60, is_control_surface=False),
        ),
        (
            "XTail_Rudder_175mm.stl",
            generate_xtail_pair_stl(105.0, 70.0, 75.0, 42.0, 45.0, 0.075, 0.085, 0.61, 1.0, is_control_surface=True),
        ),
        (
            "XTail_Horizontal_Half_120mm.stl",
            generate_xtail_half_surface(120.0, 75.0, 48.0, 0.068, 0.080, 0.0, 0.64, is_control_surface=False),
        ),
        (
            "XTail_Vertical_Upper_Fin_105mm.stl",
            generate_xtail_half_surface(105.0, 75.0, 42.0, 0.075, 0.085, 0.0, 0.60, is_control_surface=False),
        ),
        (
            "XTail_Vertical_Lower_SubFin_70mm.stl",
            generate_xtail_half_surface(70.0, 75.0, 45.0, 0.075, 0.085, 0.0, 0.60, is_control_surface=False),
        ),
    ]
    for fname, tris in tasks_p2:
        out_path = os.path.join(p2_dir, fname)
        write_binary_stl(out_path, tris, f"DLG950 0%Infill {fname}")
        print(f"   -> {fname}: {len(tris)} triangulos")

    print("4. Gerando Plate 3 — Pod c/ Berço em V 10°, Luva de Diedro V 10°, Raízes M3 e Bandeja 4 Servos...")
    tasks_p3 = [
        ("Fuselage_Nose_Pod_245mm.stl", generate_fuselage_pod_245mm()),
        ("Fuselage_Canopy_Hatch.stl", generate_canopy_hatch()),
        ("Servo_Tray_4x_SubMicro.stl", generate_servo_tray_4x()),
        ("Root_Rib_Joiner_Right_M3.stl", generate_root_rib_joiner(is_right=True)),
        ("Root_Rib_Joiner_Left_M3.stl", generate_root_rib_joiner(is_right=False)),
        ("Dihedral_V_Joiner_10deg_PETG.stl", generate_dihedral_v_joiner_10deg()),
        ("XTail_Center_Clamp_8mm_Boom.stl", generate_xtail_center_clamp_8mm()),
        ("Flaperon_Root_Horns_BallLink_Pair.stl", generate_flaperon_root_horns()),
    ]
    for fname, tris in tasks_p3:
        out_path = os.path.join(p3_dir, fname)
        write_binary_stl(out_path, tris, f"DLG950 {fname}")
        print(f"   -> {fname}: {len(tris)} triangulos")

    print("\nConcluído! Diedro físico de 5.0° por semi-asa (10.0° total) implementado em todas as peças.")


if __name__ == "__main__":
    main()
