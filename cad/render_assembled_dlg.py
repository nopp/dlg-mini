#!/usr/bin/env python3
"""
Montador 3D e Renderizador Studio Multi-Vista do DLG-Mini 950 3DP Completo.
- Posiciona todas as peças geradas (.stl) + tubos/varetas de carbono no espaço 3D real da aeronave
  (incluindo a rotação física do diedro de 5.0° por semi-asa = 10.0° total).
- Exporta o arquivo STL completo montado: `stl/DLG_Mini_950_Full_Assembly.stl`
- Renderiza em alta resolução (com supersampling 2x e iluminação Studio Phong) 4 vistas 3D coloridas
  em `blueprints/DLG_Mini_950_3D_Assembly_Render.jpg` e `.png`.
"""

import math
import os
import sys
from typing import List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_dlg_stl as cad
from PIL import Image, ImageDraw, ImageFont

Point3D = Tuple[float, float, float]
Triangle = Tuple[Point3D, Point3D, Point3D]
ColorRGB = Tuple[int, int, int]


def make_cylinder_along_axis(
    p0: Point3D, p1: Point3D, radius: float, n_seg: int = 28, n_axial: int = 28
) -> List[Triangle]:
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    dz = p1[2] - p0[2]
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    if length < 1e-6:
        return []
    ux, uy, uz = dx / length, dy / length, dz / length
    if abs(ux) < 0.8:
        vx, vy, vz = 0.0, -uz, uy
    else:
        vx, vy, vz = -uz, 0.0, ux
    vlen = math.sqrt(vx * vx + vy * vy + vz * vz)
    vx, vy, vz = vx / vlen, vy / vlen, vz / vlen
    wx = uy * vz - uz * vy
    wy = uz * vx - ux * vz
    wz = ux * vy - uy * vx

    rings: List[List[Point3D]] = []
    for k in range(n_axial + 1):
        frac = k / n_axial
        cx = p0[0] + dx * frac
        cy = p0[1] + dy * frac
        cz = p0[2] + dz * frac
        ring: List[Point3D] = []
        for i in range(n_seg):
            ang = 2.0 * math.pi * i / n_seg
            ca, sa = math.cos(ang), math.sin(ang)
            rx = radius * (ca * vx + sa * wx)
            ry = radius * (ca * vy + sa * wy)
            rz = radius * (ca * vz + sa * wz)
            ring.append((cx + rx, cy + ry, cz + rz))
        rings.append(ring)

    tris: List[Triangle] = []
    for k in range(n_axial):
        r0 = rings[k]
        r1 = rings[k + 1]
        for i in range(n_seg):
            ni = (i + 1) % n_seg
            tris.append((r0[i], r0[ni], r1[ni]))
            tris.append((r0[i], r1[ni], r1[i]))
    for i in range(n_seg):
        ni = (i + 1) % n_seg
        tris.append((p0, rings[0][ni], rings[0][i]))
        tris.append((p1, rings[-1][i], rings[-1][ni]))
    return tris


def transform_wing_to_aircraft(
    tris: List[Triangle], span_offset: float, is_right_wing: bool, z_saddle: float = 9.2
) -> List[Triangle]:
    """
    Transforma um segmento de asa/flaperon da orientação vertical na mesa (x_b, y_b, z_b)
    para as coordenadas 3D da aeronave (X_long, Y_span, Z_vert) com diedro de 5.0° por lado.
    """
    dih = math.radians(cad.DIHEDRAL_DEG)
    cd, sd = math.cos(dih), math.sin(dih)
    out: List[Triangle] = []
    for p1, p2, p3 in tris:
        pts_ac = []
        for xb, yb, zb in (p1, p2, p3):
            s = span_offset + zb
            t = yb if is_right_wing else -yb
            x_ac = xb
            if is_right_wing:
                y_ac = s * cd - t * sd
            else:
                y_ac = -(s * cd - t * sd)
            z_ac = z_saddle + s * sd + t * cd
            pts_ac.append((x_ac, y_ac, z_ac))
        out.append((pts_ac[0], pts_ac[1], pts_ac[2]))
    return out


def transform_pod_to_aircraft(tris: List[Triangle], z_offset_pod: float = 0.0, z_lift: float = 0.0) -> List[Triangle]:
    """
    No Pod:
    - z_b = 0 é o colar traseiro do boom (X_ac = +145mm, logo abaixo do bordo de fuga da asa)
    - z_b = 35..146mm é o berço da asa em V (X_ac = +110mm até -1mm, exatamente sob a raiz da asa!)
    - z_b = 146..218mm é a cabine/canopy (X_ac = -1mm até -73mm, à frente do bordo de ataque da asa!)
    - z_b = 245mm é a ponta do bico (X_ac = -100mm).
    """
    out: List[Triangle] = []
    for p1, p2, p3 in tris:
        pts = []
        for xb, yb, zb in (p1, p2, p3):
            z_pod = zb + z_offset_pod
            x_ac = 145.0 - z_pod
            y_ac = xb
            z_ac = yb + z_lift
            pts.append((x_ac, y_ac, z_ac))
        out.append((pts[0], pts[2], pts[1]))
    return out


def transform_htail_half_to_aircraft(
    tris: List[Triangle], is_right: bool, x_root_le: float = 443.0, z_mount: float = 4.2
) -> List[Triangle]:
    out: List[Triangle] = []
    for p1, p2, p3 in tris:
        pts = []
        for xb, yb, zb in (p1, p2, p3):
            x_ac = x_root_le + xb
            y_ac = zb if is_right else -zb
            z_ac = z_mount + yb
            pts.append((x_ac, y_ac, z_ac))
        if is_right:
            out.append((pts[0], pts[2], pts[1]))
        else:
            out.append((pts[0], pts[1], pts[2]))
    return out


def transform_vtail_half_to_aircraft(
    tris: List[Triangle], is_upper: bool, x_root_le: float = 465.0
) -> List[Triangle]:
    out: List[Triangle] = []
    for p1, p2, p3 in tris:
        pts = []
        for xb, yb, zb in (p1, p2, p3):
            x_ac = x_root_le + xb
            y_ac = yb
            z_ac = zb if is_upper else -zb
            pts.append((x_ac, y_ac, z_ac))
        if is_upper:
            out.append((pts[0], pts[1], pts[2]))
        else:
            out.append((pts[0], pts[2], pts[1]))
    return out


def make_solid_wingtip_cap(is_right_wing: bool) -> List[Triangle]:
    """Gera a ponteira aerodinâmica fechada em Y = ±475mm para o modelo montado."""
    chord, le_x = cad.wing_chord_and_le_at_span(475.0)
    y_sign = 1.0 if is_right_wing else -1.0
    loop0 = cad.get_airfoil_loop(
        chord, le_x, 0.0, t_ratio=0.062, camber=0.014, x_start_frac=0.0, x_end_frac=0.74, n_pts=40
    )
    loop1 = cad.get_airfoil_loop(
        chord * 0.94, le_x + 2.0, 0.0, t_ratio=0.055, camber=0.012, x_start_frac=0.0, x_end_frac=0.74, n_pts=40
    )
    if y_sign < 0:
        loop0 = [(px, -py) for (px, py) in loop0]
        loop1 = [(px, -py) for (px, py) in loop1]
    raw = cad.loft_with_holes([loop0, loop1], [], [0.0, 2.5])
    return transform_wing_to_aircraft(raw, 475.0, is_right_wing)


def build_assembled_dlg_components(peg_side: str = "left") -> List[Tuple[str, List[Triangle], ColorRGB]]:
    """
    Constrói todos os componentes 3D posicionados no espaço da aeronave com suas cores de renderização.
    - `peg_side`: "left" (Pino na Asa Esquerda p/ Destros), "right" (Pino na Asa Direita p/ Canhotos), ou "both".
    Comprimento total: X = -100mm (Ponta do Bico) até X = +540mm (Bordo de fuga do Leme) = 640mm exatos!
    """
    components: List[Tuple[str, List[Triangle], ColorRGB]] = []

    # 1. Tubo de Carbono da Cauda Ø8x6mm (X = 100mm até X = 535mm)
    boom_tris = make_cylinder_along_axis((100.0, 0.0, 0.0), (535.0, 0.0, 0.0), radius=4.0, n_seg=32)
    components.append(("Carbon_Tail_Boom_8mm", boom_tris, (48, 54, 64)))

    # 2. Pod da Fuselagem de 245mm (X = -100mm a +145mm) em PETG Branco/Cinza Claro Aeroespacial
    pod_raw = cad.generate_fuselage_pod_245mm()
    pod_tris = transform_pod_to_aircraft(pod_raw, z_offset_pod=0.0, z_lift=0.0)
    components.append(("Fuselage_Nose_Pod_245mm", pod_tris, (232, 238, 246)))

    # 3. Bandeja de 4 Servos Sub-Micro alojada dentro do Cockpit (X = -52mm a +30mm)
    tray_raw = cad.generate_servo_tray_4x()
    tray_tris: List[Triangle] = []
    for p1, p2, p3 in tray_raw:
        pts = [(-12.0 + yb, xb * 0.82, -4.5 + zb) for (xb, yb, zb) in (p1, p2, p3)]
        tray_tris.append((pts[0], pts[1], pts[2]))
    components.append(("Servo_Tray_4x", tray_tris, (245, 166, 35)))

    # 4. Tampa do Canopy (posicionada à frente da asa, X = -73mm a -1mm, em Azul Cobalto Metálico)
    hatch_raw = cad.generate_canopy_hatch()
    hatch_tris = transform_pod_to_aircraft(hatch_raw, z_offset_pod=146.0, z_lift=0.3)
    components.append(("Fuselage_Canopy_Hatch", hatch_tris, (42, 128, 220)))

    # 5. Painéis Internos da Asa Bipartida W1 (0 a 245mm, Diedro 5.0°/lado) - LW-PLA Branco Gelo
    w1_r_raw = cad.generate_wing_segment(0.0, 245.0, is_right_wing=True, has_peg_socket=False)
    w1_l_raw = cad.generate_wing_segment(0.0, 245.0, is_right_wing=False, has_peg_socket=False)
    components.append(("W1_Right_Inner", transform_wing_to_aircraft(w1_r_raw, 0.0, True), (225, 234, 246)))
    components.append(("W1_Left_Inner", transform_wing_to_aircraft(w1_l_raw, 0.0, False), (225, 234, 246)))

    # 6. Painéis Externos da Asa W2 (245 a 475mm, Diedro 5.0°/lado, com Ponta Elíptica Arredondada e opção ambidestra de Pino)
    has_right_peg = peg_side in ("right", "both")
    has_left_peg = peg_side in ("left", "both")
    w2_r_raw = cad.generate_wing_segment(245.0, 475.0, is_right_wing=True, has_peg_socket=has_right_peg)
    w2_l_raw = cad.generate_wing_segment(245.0, 475.0, is_right_wing=False, has_peg_socket=has_left_peg)
    components.append(("W2_Right_Outer", transform_wing_to_aircraft(w2_r_raw, 245.0, True), (190, 214, 244)))
    components.append(("W2_Left_Outer", transform_wing_to_aircraft(w2_l_raw, 245.0, False), (190, 214, 244)))

    # 7. Flaperons (Internos 20..245mm e Externos 245..429mm, casando sem entalhe com a ponteira integral de W2)
    flap_ri = cad.generate_flaperon_segment(20.0, 245.0, is_right_wing=True)
    flap_ro = cad.generate_flaperon_segment(245.0, 429.0, is_right_wing=True)
    flap_li = cad.generate_flaperon_segment(20.0, 245.0, is_right_wing=False)
    flap_lo = cad.generate_flaperon_segment(245.0, 429.0, is_right_wing=False)
    components.append(("Flaperon_Right_Inner", transform_wing_to_aircraft(flap_ri, 20.0, True), (235, 94, 64)))
    components.append(("Flaperon_Right_Outer", transform_wing_to_aircraft(flap_ro, 245.0, True), (235, 94, 64)))
    components.append(("Flaperon_Left_Inner", transform_wing_to_aircraft(flap_li, 20.0, False), (235, 94, 64)))
    components.append(("Flaperon_Left_Outer", transform_wing_to_aircraft(flap_lo, 245.0, False), (235, 94, 64)))

    # 8. Pino de Lançamento (Launch Peg) Ambidestro de Carbono Ø4mm x 50mm (Esquerda p/ Destros OU Direita p/ Canhotos!)
    dih = math.radians(cad.DIHEDRAL_DEG)
    s_peg = 450.0
    if has_left_peg:
        y_peg_l = -s_peg * math.cos(dih)
        z_peg_l = 9.2 + s_peg * math.sin(dih)
        peg_l0 = (75.0, y_peg_l - 22.0 * math.sin(dih), z_peg_l - 22.0 * math.cos(dih))
        peg_l1 = (75.0, y_peg_l + 28.0 * math.sin(dih), z_peg_l + 28.0 * math.cos(dih))
        peg_l_tris = make_cylinder_along_axis(peg_l0, peg_l1, radius=2.1, n_seg=24)
        components.append(("Carbon_Launch_Peg_4mm", peg_l_tris, (255, 205, 56)))

    if has_right_peg:
        y_peg_r = s_peg * math.cos(dih)
        z_peg_r = 9.2 + s_peg * math.sin(dih)
        peg_r0 = (75.0, y_peg_r + 22.0 * math.sin(dih), z_peg_r - 22.0 * math.cos(dih))
        peg_r1 = (75.0, y_peg_r - 28.0 * math.sin(dih), z_peg_r + 28.0 * math.cos(dih))
        peg_r_tris = make_cylinder_along_axis(peg_r0, peg_r1, radius=2.1, n_seg=24)
        components.append(("Carbon_Launch_Peg_Right_4mm", peg_r_tris, (16, 232, 168)))

    # 9. Empenagem Horizontal X-Tail (Estabilizador Fixo 240mm + Profundor 240mm)
    ht_half = cad.generate_xtail_half_surface(120.0, 75.0, 48.0, 0.068, 0.080, 0.0, 0.64, is_control_surface=False)
    el_half = cad.generate_xtail_half_surface(120.0, 75.0, 48.0, 0.068, 0.080, 0.65, 1.0, is_control_surface=True)
    components.append(("XTail_Horiz_Stab_R", transform_htail_half_to_aircraft(ht_half, True), (218, 228, 242)))
    components.append(("XTail_Horiz_Stab_L", transform_htail_half_to_aircraft(ht_half, False), (218, 228, 242)))
    components.append(("XTail_Elevator_R", transform_htail_half_to_aircraft(el_half, True), (235, 94, 64)))
    components.append(("XTail_Elevator_L", transform_htail_half_to_aircraft(el_half, False), (235, 94, 64)))

    # 10. Empenagem Vertical X-Tail (Deriva Superior 105mm + Sub-Fin Inferior 70mm = 175mm + Leme)
    vt_up = cad.generate_xtail_half_surface(105.0, 75.0, 42.0, 0.075, 0.085, 0.0, 0.60, is_control_surface=False)
    vt_lo = cad.generate_xtail_half_surface(70.0, 75.0, 45.0, 0.075, 0.085, 0.0, 0.60, is_control_surface=False)
    rd_up = cad.generate_xtail_half_surface(105.0, 75.0, 42.0, 0.075, 0.085, 0.61, 1.0, is_control_surface=True)
    rd_lo = cad.generate_xtail_half_surface(70.0, 75.0, 45.0, 0.075, 0.085, 0.61, 1.0, is_control_surface=True)
    components.append(("XTail_Vert_Fin_Upper", transform_vtail_half_to_aircraft(vt_up, True), (210, 224, 242)))
    components.append(("XTail_Vert_SubFin_Lower", transform_vtail_half_to_aircraft(vt_lo, False), (210, 224, 242)))
    components.append(("XTail_Rudder_Upper", transform_vtail_half_to_aircraft(rd_up, True), (235, 94, 64)))
    components.append(("XTail_Rudder_Lower", transform_vtail_half_to_aircraft(rd_lo, False), (235, 94, 64)))

    return components


def render_view_panel(
    components: List[Tuple[str, List[Triangle], ColorRGB]],
    width: int,
    height: int,
    yaw_deg: float,
    pitch_deg: float,
    roll_deg: float = 0.0,
    zoom_scale: float = 1.0,
    pan_x: float = 0.0,
    pan_y: float = 0.0,
    bg_color: Tuple[int, int, int] = (15, 28, 48),
    center_pt: Point3D = (165.0, 0.0, 15.0),
) -> Image.Image:
    """
    Renderiza os componentes 3D com supersampling 2x, algoritmo do pintor (Z-sort) e iluminação Studio Phong.
    """
    ss = 2
    W, H = width * ss, height * ss
    img = Image.new("RGB", (W, H), bg_color)
    draw = ImageDraw.Draw(img)

    # Grade sutil de fundo no painel
    grid_step = 40 * ss
    for gx in range(0, W, grid_step):
        draw.line([(gx, 0), (gx, H)], fill=(22, 40, 68), width=1)
    for gy in range(0, H, grid_step):
        draw.line([(0, gy), (W, gy)], fill=(22, 40, 68), width=1)

    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    roll = math.radians(roll_deg)
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cr, sr = math.cos(roll), math.sin(roll)

    xc, yc, zc = center_pt

    def project_pt(p: Point3D) -> Tuple[float, float, float]:
        # Centraliza aeronave
        dx = p[0] - xc
        dy = p[1] - yc
        dz = p[2] - zc
        # Rotação Yaw (em torno de Z_ac)
        x1 = dx * cy - dy * sy
        y1 = dx * sy + dy * cy
        z1 = dz
        # Rotação Pitch (em torno de Y1)
        x2 = x1 * cp + z1 * sp
        y2 = y1
        z2 = -x1 * sp + z1 * cp
        # Rotação Roll (no plano de tela Y2, Z2)
        u_scr = y2 * cr - z2 * sr
        v_scr = y2 * sr + z2 * cr
        depth = x2
        return (u_scr, v_scr, depth)

    # Direção de luz principal e luz de preenchimento (no espaço de câmera: u_scr, v_scr, depth)
    l1x, l1y, l1z = -0.35, 0.60, -0.72
    l2x, l2y, l2z = 0.50, -0.30, -0.81

    projected_faces = []
    for comp_name, tris, base_rgb in components:
        r0, g0, b0 = base_rgb
        for p1, p2, p3 in tris:
            q1 = project_pt(p1)
            q2 = project_pt(p2)
            q3 = project_pt(p3)

            ux, uy, uz = q2[0] - q1[0], q2[1] - q1[1], q2[2] - q1[2]
            vx, vy, vz = q3[0] - q1[0], q3[1] - q1[1], q3[2] - q1[2]
            nx = uy * vz - uz * vy
            ny = uz * vx - ux * vz
            nz = ux * vy - uy * vx
            nlen = math.sqrt(nx * nx + ny * ny + nz * nz)
            if nlen < 1e-6:
                continue
            nx, ny, nz = nx / nlen, ny / nlen, nz / nlen
            # Garante iluminação de dupla face caso alguma normal esteja invertida
            if nz > 0:
                nx, ny, nz = -nx, -ny, -nz

            diff1 = max(0.0, nx * l1x + ny * l1y + nz * l1z)
            diff2 = max(0.0, nx * l2x + ny * l2y + nz * l2z)
            spec = max(0.0, -nz) ** 16 * 0.18
            shade = 0.34 + 0.54 * diff1 + 0.22 * diff2 + spec

            rc = min(255, int(r0 * shade))
            gc = min(255, int(g0 * shade))
            bc = min(255, int(b0 * shade))

            z_avg = (q1[2] + q2[2] + q3[2]) / 3.0
            projected_faces.append((z_avg, q1, q2, q3, (rc, gc, bc)))

    # Ordena do mais distante (maior depth) para o mais próximo (menor depth)
    projected_faces.sort(key=lambda item: item[0], reverse=True)

    cx_pix = W * 0.5 + pan_x * ss
    cy_pix = H * 0.5 + pan_y * ss
    scale = zoom_scale * ss

    for _, q1, q2, q3, col in projected_faces:
        pts_2d = [
            (cx_pix + q1[0] * scale, cy_pix - q1[1] * scale),
            (cx_pix + q2[0] * scale, cy_pix - q2[1] * scale),
            (cx_pix + q3[0] * scale, cy_pix - q3[1] * scale),
        ]
        draw.polygon(pts_2d, fill=col)

    return img.resize((width, height), Image.Resampling.LANCZOS)


def main() -> None:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    stl_out = os.path.join(base_dir, "stl", "DLG_Mini_950_Full_Assembly.stl")
    bp_dir = os.path.join(base_dir, "blueprints")
    os.makedirs(bp_dir, exist_ok=True)

    print("1. Construindo montagem 3D completa do DLG-Mini 950 3DP (Opcao Destro e Opcao Canhoto)...")
    components = build_assembled_dlg_components(peg_side="both")
    components_left = build_assembled_dlg_components(peg_side="left")
    components_right = build_assembled_dlg_components(peg_side="right")

    all_tris_left: List[Triangle] = [t for _, tris, _ in components_left for t in tris]
    all_tris_right: List[Triangle] = [t for _, tris, _ in components_right for t in tris]

    stl_out_right = os.path.join(base_dir, "stl", "DLG_Mini_950_Full_Assembly_RightPeg.stl")
    cad.write_binary_stl(stl_out, all_tris_left, "DLG-Mini 950 3DP Full Assembly (Left Peg - Right Handed)")
    cad.write_binary_stl(stl_out_right, all_tris_right, "DLG-Mini 950 3DP Full Assembly (Right Peg - Left Handed)")
    print(f"   -> STL Montado (Destro - Pino Esq): {stl_out} ({len(all_tris_left)} triangulos)")
    print(f"   -> STL Montado (Canhoto - Pino Dir): {stl_out_right} ({len(all_tris_right)} triangulos)")

    print("2. Renderizando Studio 3D Multi-Vista em alta resolucao...")
    W_tot, H_tot = 1800, 1250
    canvas = Image.new("RGB", (W_tot, H_tot), (10, 20, 36))
    draw = ImageDraw.Draw(canvas)

    try:
        font_title = ImageFont.truetype("/System/Library/Fonts/Monaco.ttf", 21)
        font_sub = ImageFont.truetype("/System/Library/Fonts/Monaco.ttf", 15)
        font_lbl = ImageFont.truetype("/System/Library/Fonts/Monaco.ttf", 13)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_lbl = ImageFont.load_default()

    # Cabeçalho
    draw.rectangle([20, 18, 1780, 78], fill=(7, 16, 30), outline=(90, 175, 255), width=2)
    draw.text(
        (38, 35),
        "RENDER 3D DO PROJETO MONTADO: DLG-MINI 950 3DP (ENVERGADURA 950mm | COMP. 640mm | DIEDRO 10° TOTAL)",
        fill=(255, 255, 255),
        font=font_title,
    )

    # Painel 1 (Superior Esquerdo - Grande): Perspectiva 3/4 Frontal-Superior (Bico à frente)
    p1_img = render_view_panel(
        components, width=1020, height=640, yaw_deg=-38.0, pitch_deg=-24.0, zoom_scale=1.04, pan_x=-25.0, pan_y=15.0
    )
    canvas.paste(p1_img, (20, 92))
    draw.rectangle([20, 92, 1040, 732], outline=(65, 130, 205), width=2)
    draw.text(
        (36, 106),
        "1. VISTA ISOMÉTRICA 3/4 FRONTAL-SUPERIOR (AERONAVE COMPLETA MONTADA)",
        fill=(255, 210, 102),
        font=font_sub,
    )
    draw.text(
        (36, 704),
        "[Branco/Azul] Asas LW-PLA (W1+W2)   [Coral] Flaperons/Leme/Profundor   [Azul] Canopy   [Amarelo] Pino Carbono Ø4mm",
        fill=(190, 220, 255),
        font=font_lbl,
    )

    # Painel 2 (Superior Direito): Perspectiva 3/4 Traseira-Superior (Destaque X-Tail + Pino de Lançamento)
    p2_img = render_view_panel(
        components, width=720, height=640, yaw_deg=-138.0, pitch_deg=24.0, zoom_scale=0.76, pan_x=-15.0, pan_y=20.0
    )
    canvas.paste(p2_img, (1060, 92))
    draw.rectangle([1060, 92, 1780, 732], outline=(65, 130, 205), width=2)
    draw.text(
        (1076, 106),
        "2. VISTA 3/4 TRASEIRA (EMPENAGEM X-TAIL + FLAPERONS)",
        fill=(255, 210, 102),
        font=font_sub,
    )
    draw.text(
        (1076, 704),
        "Tubo de Cauda Carbono Ø8x6mm + Estabilizador 240mm + Deriva 175mm",
        fill=(190, 220, 255),
        font=font_lbl,
    )

    # Painel 3 (Inferior Esquerdo): Vista Frontal Direta (Destaque do Diedro em V de 5°/lado = 10° Total)
    p3_img = render_view_panel(
        components, width=870, height=480, yaw_deg=0.0, pitch_deg=-3.0, zoom_scale=0.84, pan_x=0.0, pan_y=15.0
    )
    canvas.paste(p3_img, (20, 750))
    draw.rectangle([20, 750, 890, 1230], outline=(65, 130, 205), width=2)
    draw.text(
        (36, 764),
        "3. VISTA FRONTAL — DIEDRO EM 'V' DE 5.0° POR SEMI-ASA (10.0° TOTAL = +41.4mm NAS PONTAS)",
        fill=(255, 210, 102),
        font=font_sub,
    )
    draw.text(
        (36, 1202),
        "Pino Ø4mm Ambidestro: Asa Esquerda [Amarelo - Destros] OU Asa Direita [Verde - Canhotos] + Diedro 5°/lado",
        fill=(190, 220, 255),
        font=font_lbl,
    )

    # Painel 4 (Inferior Direito): Vista Lateral Esquerda (Perfil do Nose Pod 245mm + Boom + X-Tail)
    p4_img = render_view_panel(
        components, width=870, height=480, yaw_deg=-90.0, pitch_deg=0.0, zoom_scale=1.12, pan_x=-30.0, pan_y=10.0
    )
    canvas.paste(p4_img, (910, 750))
    draw.rectangle([910, 750, 1780, 1230], outline=(65, 130, 205), width=2)
    draw.text(
        (926, 764),
        "4. VISTA LATERAL ESQUERDA — PERFIL DO POD (245mm), TUBO Ø8mm E X-TAIL (640mm TOTAL)",
        fill=(255, 210, 102),
        font=font_sub,
    )
    draw.text(
        (926, 1202),
        "Bico ogival Haack + Cabine p/ 4 Servos Sub-Micro + Deriva Simétrica Superior (105mm) e Sub-Fin Inferior (70mm)",
        fill=(190, 220, 255),
        font=font_lbl,
    )

    png_path = os.path.join(bp_dir, "DLG_Mini_950_3D_Assembly_Render.png")
    jpg_path = os.path.join(bp_dir, "DLG_Mini_950_3D_Assembly_Render.jpg")
    canvas.save(png_path, "PNG")
    canvas.save(jpg_path, "JPEG", quality=96)

    # Renderiza Painel Triplo Estilo "FlightPoint Luft CAD" em DLG_Mini_950_Rounded_Wingtip_Detail.jpg:
    # - Painel 1 (Esquerda Grande): Aeronave Completa estilo FlightPoint Luft (Asas em Azul CAD com corte interno
    #   revelando nervuras geodésicas + longarinas de carbono pretas + Pod Dourado/Champagne)
    # - Painel 2 (Superior Direito): Close-up 3D da Ponta da Asa Arredondada (Exterior - Zero degrau no bordo de fuga!)
    # - Painel 3 (Inferior Direito): Close-up 3D em Corte Interno (Nervuras Geodésicas + Tubo Ø6mm + Pino Ø4mm)
    dih = math.radians(cad.DIHEDRAL_DEG)
    sp_l0 = (49.0, 0.0, 9.2)
    sp_l1 = (76.0, -450.0 * math.cos(dih), 9.2 + 450.0 * math.sin(dih))
    sp_r0 = (49.0, 0.0, 9.2)
    sp_r1 = (76.0, 450.0 * math.cos(dih), 9.2 + 450.0 * math.sin(dih))
    spar_cyl_l = make_cylinder_along_axis(sp_l0, sp_l1, 2.7, 20, 24)
    spar_cyl_r = make_cylinder_along_axis(sp_r0, sp_r1, 2.7, 20, 24)

    aux_l0 = (96.8, 0.0, 9.2)
    aux_l1 = (96.8, -450.0 * math.cos(dih), 9.2 + 450.0 * math.sin(dih))
    aux_cyl_l = make_cylinder_along_axis(aux_l0, aux_l1, 1.1, 16, 20)

    # Pinos-Eixo Retilíneos das Dobradiças Mecânicas Intercaladas (Hinge Pins Ø2.0mm nas Asas/Flaperons)
    hp_l0 = (115.5, 0.0, 9.2)
    hp_l1 = (109.5, -425.0 * math.cos(dih), 9.2 + 425.0 * math.sin(dih))
    hp_r0 = (115.5, 0.0, 9.2)
    hp_r1 = (109.5, 425.0 * math.cos(dih), 9.2 + 425.0 * math.sin(dih))
    hinge_pin_wing_l = make_cylinder_along_axis(hp_l0, hp_l1, 0.95, 16, 24)
    hinge_pin_wing_r = make_cylinder_along_axis(hp_r0, hp_r1, 0.95, 16, 24)

    def remove_upper_skin_wing(tris_in: List[Triangle]) -> List[Triangle]:
        out_t: List[Triangle] = []
        for p1, p2, p3 in tris_in:
            ux, uy, uz = p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]
            vx, vy, vz = p3[0] - p1[0], p3[1] - p1[1], p3[2] - p1[2]
            nx = uy * vz - uz * vy
            ny = uz * vx - ux * vz
            nz = ux * vy - uy * vx
            nlen = math.sqrt(nx * nx + ny * ny + nz * nz)
            if nlen > 1e-6:
                nz_u = nz / nlen
                z_avg_t = (p1[2] + p2[2] + p3[2]) / 3.0
                y_avg_t = abs((p1[1] + p2[1] + p3[1]) / 3.0)
                if abs(nz_u) > 0.62 and z_avg_t > (9.2 + y_avg_t * math.tan(dih) + 0.55):
                    continue
            out_t.append((p1, p2, p3))
        return out_t

    tip_solid_comps = [c for c in components if c[0] in ("W2_Left_Outer", "Flaperon_Left_Outer", "Carbon_Launch_Peg_4mm")]
    tip_solid_comps.append(("Hinge_Pin_Wing_L", hinge_pin_wing_l, (255, 215, 70)))

    w2_cutaway_tris: List[Triangle] = []
    for name, tris, _ in components:
        if name in ("W2_Left_Outer", "Flaperon_Left_Outer"):
            w2_cutaway_tris.extend(remove_upper_skin_wing(tris))

    peg_only = [c[1] for c in components if c[0] == "Carbon_Launch_Peg_4mm"][0]
    tip_xray_comps: List[Tuple[str, List[Triangle], ColorRGB]] = [
        ("W2_Cutaway_Blue", w2_cutaway_tris, (38, 172, 245)),
        ("Internal_Carbon_Spar_6mm", spar_cyl_l, (32, 36, 44)),
        ("Internal_Aux_Spar_2mm", aux_cyl_l, (32, 36, 44)),
        ("Hinge_Pin_Wing_L", hinge_pin_wing_l, (255, 215, 70)),
        ("Carbon_Launch_Peg_4mm", peg_only, (255, 205, 56)),
    ]

    # Monta a versão completa estilo FlightPoint Luft (Asas e Cauda em Azul Ciano com corte interno + Pod Dourado)
    luft_style_comps: List[Tuple[str, List[Triangle], ColorRGB]] = []
    for name, tris, col in components:
        if name in ("Fuselage_Nose_Pod_245mm", "Fuselage_Canopy_Hatch"):
            luft_style_comps.append((name, tris, (218, 178, 92)))  # Pod Dourado/Champagne estilo FlightPoint Luft
        elif name in ("W1_Left_Inner", "W2_Left_Outer", "Flaperon_Left_Inner", "Flaperon_Left_Outer"):
            luft_style_comps.append((name, remove_upper_skin_wing(tris), (38, 172, 245)))
        elif name in ("W1_Right_Inner", "W2_Right_Outer", "Flaperon_Right_Inner", "Flaperon_Right_Outer"):
            luft_style_comps.append((name, remove_upper_skin_wing(tris), (48, 182, 250)))
        elif name.startswith("XTail_"):
            luft_style_comps.append((name, tris, (42, 175, 248)))
        else:
            luft_style_comps.append((name, tris, col))
    luft_style_comps.append(("Spar_L", spar_cyl_l, (30, 34, 42)))
    luft_style_comps.append(("Spar_R", spar_cyl_r, (30, 34, 42)))
    luft_style_comps.append(("Aux_L", aux_cyl_l, (30, 34, 42)))
    luft_style_comps.append(("Hinge_Pin_L", hinge_pin_wing_l, (255, 215, 70)))
    luft_style_comps.append(("Hinge_Pin_R", hinge_pin_wing_r, (255, 215, 70)))

    tip_canvas = Image.new("RGB", (1800, 1080), (10, 20, 36))
    tip_draw = ImageDraw.Draw(tip_canvas)
    tip_draw.rectangle([18, 16, 1782, 74], fill=(7, 16, 30), outline=(90, 175, 255), width=2)
    tip_draw.text(
        (34, 34),
        "SISTEMA DE DOBRADIÇAS MECÂNICAS INTERCALADAS (PIN-HINGE) + PONTA FLIGHTPOINT LUFT + OPÇÃO AMBIDESTRA",
        fill=(255, 255, 255),
        font=font_title,
    )

    p_luft_full = render_view_panel(
        luft_style_comps,
        width=980,
        height=970,
        yaw_deg=-38.0,
        pitch_deg=-30.0,
        zoom_scale=1.02,
        pan_x=-20.0,
        pan_y=20.0,
    )
    p_tip_ext = render_view_panel(
        tip_solid_comps,
        width=760,
        height=475,
        yaw_deg=-35.0,
        pitch_deg=-34.0,
        zoom_scale=2.65,
        pan_x=0.0,
        pan_y=10.0,
        center_pt=(78.0, -365.0, 42.0),
    )
    p_tip_int = render_view_panel(
        tip_xray_comps,
        width=760,
        height=475,
        yaw_deg=-35.0,
        pitch_deg=-34.0,
        zoom_scale=2.65,
        pan_x=0.0,
        pan_y=10.0,
        center_pt=(78.0, -365.0, 42.0),
    )
    tip_canvas.paste(p_luft_full, (18, 88))
    tip_canvas.paste(p_tip_ext, (1022, 88))
    tip_canvas.paste(p_tip_int, (1022, 583))
    tip_draw.rectangle([18, 88, 998, 1058], outline=(65, 130, 205), width=2)
    tip_draw.rectangle([1022, 88, 1782, 563], outline=(65, 130, 205), width=2)
    tip_draw.rectangle([1022, 583, 1782, 1058], outline=(65, 130, 205), width=2)
    tip_draw.text(
        (34, 102),
        "1. VISTA COMPLETA FLIGHTPOINT LUFT — OPÇÃO AMBIDESTRA DE PINO (ESQ [AMARELO] OU DIR [VERDE])",
        fill=(255, 210, 102),
        font=font_sub,
    )
    tip_draw.text(
        (1038, 102),
        "2. DOBRADIÇAS INTERCALADAS (KNUCKLE PIN-HINGE) + PONTA ARREDONDADA",
        fill=(255, 210, 102),
        font=font_sub,
    )
    tip_draw.text(
        (1038, 597),
        "3. CORTE INTERNO: EIXO DA DOBRADIÇA Ø2mm + NERVURAS + LONGARINAS",
        fill=(255, 210, 102),
        font=font_sub,
    )

    tip_jpg = os.path.join(bp_dir, "DLG_Mini_950_Rounded_Wingtip_Detail.jpg")
    tip_canvas.save(tip_jpg, "JPEG", quality=96)
    print(f"   -> Renders salvos em:\n      {png_path}\n      {jpg_path}\n      {tip_jpg}")


if __name__ == "__main__":
    main()
