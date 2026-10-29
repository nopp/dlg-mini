// ============================================================================
// DLG-Mini 950 3DP - Visualizador Paramétrico e Conjunto Completo (OpenSCAD)
// Baseado no RCRCM DLG-Mini X-Tail (950mm Envergadura, 640mm Comprimento)
// Otimizado para Bambu Lab P2S (256 x 256 x 256 mm)
// ============================================================================

wingspan = 950;
half_span = 475;
root_chord = 150;
mid_chord = 140;
tip_chord = 95;
cg_from_le = 45;
dihedral_deg = 5.5;

// Medidas comerciais das varetas e tubos de carbono
boom_od = 8.0;
boom_id = 6.0;
boom_length = 450;

main_spar_od = 6.0;
main_spar_id = 4.0;
joiner_rod_d = 4.0;
aux_spar_d = 2.0;

// Visualização dos STLs gerados
module complete_dlg_assembly() {
    // 1. Tubo de Carbono da Cauda Ø8x6mm (450mm)
    color([0.15, 0.15, 0.15])
    translate([190, 0, -6])
    rotate([0, 90, 0])
    cylinder(h=boom_length, d=boom_od, $fn=48);

    // 2. Pod Dianteiro 245mm (PETG)
    color([0.2, 0.55, 0.85, 0.85])
    translate([0, 0, -6])
    rotate([0, 90, 0])
    import("../stl/Plate3_PETG_Structural_Pod/Fuselage_Nose_Pod_245mm.stl");

    // 3. Semi-Asa Direita (W1 245mm + W2 230mm) com Diedro de 5.5 graus
    color([0.95, 0.95, 0.92])
    translate([135, 0, 6])
    rotate([dihedral_deg, 0, 0]) {
        rotate([-90, 0, 0])
        import("../stl/Plate1_LW-PLA_Wings/W1_Right_Inner_Wing_245mm.stl");
        translate([0, 245, 0])
        rotate([-90, 0, 0])
        import("../stl/Plate1_LW-PLA_Wings/W2_Right_Outer_Wing_230mm.stl");
    }

    // 4. Semi-Asa Esquerda (W1 245mm + W2 230mm com Peg)
    color([0.95, 0.95, 0.92])
    translate([135, 0, 6])
    rotate([-dihedral_deg, 0, 0]) {
        rotate([90, 0, 0])
        import("../stl/Plate1_LW-PLA_Wings/W1_Left_Inner_Wing_245mm.stl");
        translate([0, -245, 0])
        rotate([90, 0, 0])
        import("../stl/Plate1_LW-PLA_Wings/W2_Left_Outer_Wing_Peg_230mm.stl");
    }

    // 5. Empenagem X-Tail (Estabilizador Horizontal 240mm + Vertical 175mm)
    color([0.95, 0.45, 0.15])
    translate([585, -120, 0])
    rotate([-90, 0, 0])
    import("../stl/Plate2_LW-PLA_XTail/XTail_Horizontal_Stabilizer_240mm.stl");

    color([0.95, 0.45, 0.15])
    translate([585, 0, -70])
    import("../stl/Plate2_LW-PLA_XTail/XTail_Vertical_Fin_175mm.stl");
}

complete_dlg_assembly();
