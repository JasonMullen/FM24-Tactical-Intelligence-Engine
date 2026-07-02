ROLE_PROFILES = {
    # Goalkeepers
    "Goalkeeper": {
        "category": "Goalkeeper",
        "attributes": {
            "Ref": 1.25, "Han": 1.20, "1v1": 1.10, "Cmd": 1.00,
            "Aer": 1.00, "Com": 0.95, "Kic": 0.85, "Thr": 0.80,
            "Cnt": 1.00, "Dec": 0.95
        },
        "stats": ["Av Rat", "Saves/90", "xSV %", "Shutouts", "Pens Saved Ratio"],
        "description": "Traditional shot-stopping goalkeeper."
    },
    "Sweeper Keeper": {
        "category": "Goalkeeper",
        "attributes": {
            "Ref": 1.15, "1v1": 1.10, "Kic": 1.15, "Thr": 1.05,
            "TRO": 1.20, "Com": 1.00, "Cmd": 0.95, "Pas": 0.90,
            "Fir": 0.85, "Dec": 1.05
        },
        "stats": ["Av Rat", "Saves/90", "xSV %", "Ps C/90", "Pas %", "Shutouts"],
        "description": "Goalkeeper who supports build-up and controls space behind the line."
    },

    # Center backs
    "Central Defender": {
        "category": "Defender",
        "attributes": {
            "Tck": 1.15, "Mar": 1.15, "Pos": 1.20, "Ant": 1.10,
            "Hea": 1.05, "Str": 1.00, "Jum": 1.00, "Cnt": 1.05,
            "Dec": 1.00
        },
        "stats": ["Av Rat", "Tck/90", "Int/90", "Hdr %", "Clear", "Blk/90"],
        "description": "Reliable defender who protects the box and wins duels."
    },
    "Ball Playing Defender": {
        "category": "Defender",
        "attributes": {
            "Pas": 1.25, "Fir": 1.10, "Tec": 1.05, "Cmp": 1.10,
            "Dec": 1.15, "Pos": 1.10, "Ant": 1.05, "Tck": 1.00,
            "Mar": 0.95, "Pac": 0.85
        },
        "stats": ["Av Rat", "Pas %", "Ps C/90", "Tck/90", "Int/90", "Clear"],
        "description": "Defender who can defend and progress the ball from the back."
    },
    "No-Nonsense Centre-Back": {
        "category": "Defender",
        "attributes": {
            "Tck": 1.20, "Mar": 1.15, "Hea": 1.20, "Str": 1.15,
            "Jum": 1.10, "Bra": 1.05, "Agg": 1.00, "Pos": 1.10,
            "Cnt": 1.00
        },
        "stats": ["Av Rat", "Clear", "Blk/90", "Hdr %", "Tck/90", "Int/90"],
        "description": "Direct, physical defender focused on clearing danger."
    },
    "Wide Centre-Back": {
        "category": "Defender",
        "attributes": {
            "Pac": 1.05, "Acc": 1.00, "Pas": 1.05, "Fir": 1.00,
            "Tck": 1.05, "Mar": 1.00, "Pos": 1.00, "Ant": 1.00,
            "Sta": 0.95
        },
        "stats": ["Av Rat", "Tck/90", "Int/90", "Ps C/90", "Pas %", "Sprints/90"],
        "description": "Center back who can defend wide spaces and support progression."
    },
    "Libero": {
        "category": "Defender",
        "attributes": {
            "Pas": 1.25, "Fir": 1.10, "Tec": 1.10, "Vis": 1.10,
            "Dec": 1.20, "Cmp": 1.10, "Pos": 1.00, "Ant": 1.00,
            "Tck": 0.95
        },
        "stats": ["Av Rat", "Pas %", "Ps C/90", "OP-KP", "Tck/90", "Int/90"],
        "description": "Creative defender who steps into midfield and progresses play."
    },

    # Fullbacks / wingbacks
    "Full Back": {
        "category": "Wide Defender",
        "attributes": {
            "Tck": 1.10, "Mar": 1.00, "Pos": 1.05, "Sta": 1.10,
            "Wor": 1.05, "Acc": 0.95, "Pac": 0.95, "Cro": 0.90,
            "Pas": 0.85
        },
        "stats": ["Av Rat", "Tck/90", "Int/90", "Cr C/90", "Pas %", "Sprints/90"],
        "description": "Balanced wide defender."
    },
    "Wing Back": {
        "category": "Wide Defender",
        "attributes": {
            "Sta": 1.20, "Wor": 1.15, "Acc": 1.05, "Pac": 1.05,
            "Cro": 1.15, "Dri": 0.95, "Tck": 0.95, "OtB": 0.95,
            "Tea": 1.00
        },
        "stats": ["Av Rat", "Cr C/90", "OP-Crs C/90", "Sprints/90", "Ast", "Tck/90"],
        "description": "Wide defender who provides width and attacking support."
    },
    "Complete Wing Back": {
        "category": "Wide Defender",
        "attributes": {
            "Sta": 1.25, "Wor": 1.15, "Acc": 1.10, "Pac": 1.10,
            "Cro": 1.20, "Dri": 1.05, "Tec": 1.00, "OtB": 1.00,
            "Tck": 0.90
        },
        "stats": ["Av Rat", "Cr C/90", "OP-KP/90", "Sprints/90", "Asts/90", "Drb/90"],
        "description": "Aggressive wingback who drives play high and wide."
    },
    "Inverted Wing Back": {
        "category": "Wide Defender",
        "attributes": {
            "Pas": 1.20, "Fir": 1.10, "Tec": 1.05, "Dec": 1.20,
            "Pos": 1.10, "Tea": 1.10, "Tck": 0.95, "Sta": 1.00,
            "Cmp": 1.00
        },
        "stats": ["Av Rat", "Pas %", "Ps C/90", "Poss Won/90", "Tck/90", "Int/90"],
        "description": "Wide defender who moves inside to create midfield control."
    },
    "No-Nonsense Full Back": {
        "category": "Wide Defender",
        "attributes": {
            "Tck": 1.20, "Mar": 1.15, "Pos": 1.15, "Ant": 1.05,
            "Str": 0.95, "Sta": 1.00, "Cnt": 1.05, "Agg": 0.95
        },
        "stats": ["Av Rat", "Tck/90", "Int/90", "Clear", "Blk/90"],
        "description": "Defensive fullback focused on stopping danger."
    },

    # Defensive midfield
    "Defensive Midfielder": {
        "category": "Midfielder",
        "attributes": {
            "Tck": 1.15, "Pos": 1.20, "Ant": 1.10, "Dec": 1.10,
            "Tea": 1.05, "Wor": 1.05, "Pas": 0.95, "Cnt": 1.05
        },
        "stats": ["Av Rat", "Tck/90", "Int/90", "Poss Won/90", "Pas %", "Ps C/90"],
        "description": "Midfield protector who screens the defense."
    },
    "Anchor": {
        "category": "Midfielder",
        "attributes": {
            "Pos": 1.30, "Ant": 1.15, "Tck": 1.20, "Mar": 1.10,
            "Cnt": 1.10, "Str": 0.95, "Tea": 1.00, "Dec": 1.05
        },
        "stats": ["Av Rat", "Tck/90", "Int/90", "Poss Won/90", "Clear"],
        "description": "Disciplined holding midfielder who protects central space."
    },
    "Half Back": {
        "category": "Midfielder",
        "attributes": {
            "Pos": 1.20, "Ant": 1.10, "Tck": 1.05, "Pas": 1.10,
            "Fir": 1.05, "Dec": 1.15, "Cmp": 1.05, "Tea": 1.00
        },
        "stats": ["Av Rat", "Pas %", "Ps C/90", "Tck/90", "Int/90"],
        "description": "Defensive midfielder who drops into the back line during build-up."
    },
    "Ball Winning Midfielder": {
        "category": "Midfielder",
        "attributes": {
            "Tck": 1.25, "Agg": 1.15, "Wor": 1.20, "Sta": 1.10,
            "Tea": 1.00, "Ant": 1.00, "Bravery": 0.90, "Dec": 0.90
        },
        "stats": ["Av Rat", "Tck/90", "Poss Won/90", "Int/90", "Fls"],
        "description": "Aggressive midfielder who wins duels and regains possession."
    },
    "Deep Lying Playmaker": {
        "category": "Midfielder",
        "attributes": {
            "Pas": 1.30, "Fir": 1.15, "Tec": 1.10, "Vis": 1.25,
            "Dec": 1.25, "Cmp": 1.15, "Ant": 1.00, "Tea": 1.00,
            "Pos": 0.90
        },
        "stats": ["Av Rat", "Pas %", "Ps C/90", "OP-KP/90", "Poss Lost/90"],
        "description": "Midfield controller who receives under pressure and dictates rhythm."
    },
    "Regista": {
        "category": "Midfielder",
        "attributes": {
            "Pas": 1.35, "Vis": 1.30, "Tec": 1.15, "Fir": 1.10,
            "Dec": 1.20, "Cmp": 1.10, "Fla": 1.05, "OtB": 0.95
        },
        "stats": ["Av Rat", "Pas %", "Ps C/90", "OP-KP/90", "Ch C/90"],
        "description": "Creative deep midfielder who controls play and breaks lines."
    },
    "Segundo Volante": {
        "category": "Midfielder",
        "attributes": {
            "Sta": 1.15, "Wor": 1.10, "Tck": 1.00, "Pas": 1.05,
            "OtB": 1.15, "Fin": 0.95, "Dec": 1.05, "Acc": 0.95
        },
        "stats": ["Av Rat", "Gls/90", "Asts/90", "Tck/90", "Poss Won/90", "OP-KP/90"],
        "description": "Dynamic defensive midfielder who breaks forward from deep."
    },
    "Roaming Playmaker": {
        "category": "Midfielder",
        "attributes": {
            "Pas": 1.20, "Fir": 1.10, "Tec": 1.10, "Vis": 1.20,
            "Dec": 1.15, "Sta": 1.10, "Wor": 1.00, "OtB": 1.00
        },
        "stats": ["Av Rat", "Pas %", "Ps C/90", "OP-KP/90", "Poss Won/90"],
        "description": "Mobile playmaker who supports every phase."
    },

    # Central midfield / attacking midfield
    "Central Midfielder": {
        "category": "Midfielder",
        "attributes": {
            "Pas": 1.10, "Fir": 1.00, "Dec": 1.10, "Tea": 1.05,
            "Wor": 1.00, "Sta": 0.95, "Tck": 0.90, "OtB": 0.90
        },
        "stats": ["Av Rat", "Pas %", "Ps C/90", "Tck/90", "OP-KP/90"],
        "description": "Balanced midfielder who links play."
    },
    "Box To Box Midfielder": {
        "category": "Midfielder",
        "attributes": {
            "Sta": 1.30, "Wor": 1.25, "Tea": 1.10, "Pas": 1.00,
            "Tck": 1.00, "OtB": 1.00, "Dec": 1.00, "Acc": 0.90,
            "Str": 0.85
        },
        "stats": ["Av Rat", "Tck/90", "Poss Won/90", "OP-KP/90", "Gls/90", "Asts/90"],
        "description": "High-energy midfielder who contributes in both attack and defense."
    },
    "Carrilero": {
        "category": "Midfielder",
        "attributes": {
            "Sta": 1.15, "Wor": 1.15, "Tea": 1.15, "Pas": 1.00,
            "Tck": 0.95, "Pos": 1.00, "Dec": 1.00, "Ant": 0.95
        },
        "stats": ["Av Rat", "Pas %", "Ps C/90", "Tck/90", "Int/90"],
        "description": "Shuttling midfielder who supports wide and central spaces."
    },
    "Mezzala": {
        "category": "Midfielder",
        "attributes": {
            "Pas": 1.10, "Fir": 1.05, "Tec": 1.10, "Dri": 1.05,
            "OtB": 1.20, "Vis": 1.10, "Dec": 1.05, "Sta": 0.95
        },
        "stats": ["Av Rat", "OP-KP/90", "Ch C/90", "Drb/90", "Gls/90", "Asts/90"],
        "description": "Advanced central midfielder who drifts into half-spaces."
    },
    "Advanced Playmaker": {
        "category": "Creator",
        "attributes": {
            "Pas": 1.25, "Fir": 1.15, "Tec": 1.20, "Vis": 1.30,
            "Fla": 1.10, "Dec": 1.15, "Cmp": 1.05, "OtB": 0.95,
            "Dri": 0.95
        },
        "stats": ["Av Rat", "OP-KP/90", "Ch C/90", "xA/90", "Asts/90", "Pas %"],
        "description": "Creative midfielder who finds final balls and unlocks blocks."
    },
    "Attacking Midfielder": {
        "category": "Creator",
        "attributes": {
            "Fir": 1.15, "Tec": 1.15, "Pas": 1.10, "Vis": 1.10,
            "OtB": 1.15, "Cmp": 1.05, "Dec": 1.05, "Fin": 0.95
        },
        "stats": ["Av Rat", "OP-KP/90", "Ch C/90", "xG/90", "xA/90", "Gls/90", "Asts/90"],
        "description": "Advanced central creator and box threat."
    },
    "Enganche": {
        "category": "Creator",
        "attributes": {
            "Pas": 1.25, "Vis": 1.30, "Tec": 1.20, "Fir": 1.15,
            "Cmp": 1.10, "Dec": 1.10, "Fla": 1.10
        },
        "stats": ["Av Rat", "OP-KP/90", "Ch C/90", "xA/90", "Pas %"],
        "description": "Static central creator who acts as the attacking hub."
    },
    "Shadow Striker": {
        "category": "Attacker",
        "attributes": {
            "Fin": 1.20, "OtB": 1.25, "Acc": 1.05, "Pac": 1.00,
            "Cmp": 1.05, "Ant": 1.00, "Dec": 1.00, "Fir": 0.95
        },
        "stats": ["Av Rat", "Gls/90", "xG/90", "Shot/90", "ShT/90", "Asts/90"],
        "description": "Attacking midfielder who makes striker-like runs into the box."
    },
    "Trequartista": {
        "category": "Creator",
        "attributes": {
            "Tec": 1.25, "Vis": 1.30, "Pas": 1.20, "Fir": 1.15,
            "Fla": 1.20, "Cmp": 1.05, "Dri": 1.00, "OtB": 1.00
        },
        "stats": ["Av Rat", "OP-KP/90", "Ch C/90", "xA/90", "Drb/90"],
        "description": "Free creative attacker who finds space between lines."
    },

    # Wide players
    "Wide Midfielder": {
        "category": "Wide Player",
        "attributes": {
            "Sta": 1.05, "Wor": 1.10, "Tea": 1.05, "Cro": 1.05,
            "Pas": 1.00, "Tck": 0.90, "Acc": 0.90, "Dec": 0.90
        },
        "stats": ["Av Rat", "Cr C/90", "Asts/90", "Tck/90", "Sprints/90"],
        "description": "Balanced wide player who contributes both ways."
    },
    "Winger": {
        "category": "Wide Player",
        "attributes": {
            "Acc": 1.15, "Pac": 1.15, "Dri": 1.20, "Cro": 1.20,
            "Tec": 1.00, "OtB": 1.00, "Fir": 0.95, "Dec": 0.90
        },
        "stats": ["Av Rat", "Cr C/90", "OP-Crs C/90", "Drb/90", "Asts/90", "Sprints/90"],
        "description": "Wide attacker who beats players and creates from crosses."
    },
    "Defensive Winger": {
        "category": "Wide Player",
        "attributes": {
            "Wor": 1.25, "Sta": 1.20, "Tck": 1.05, "Acc": 0.95,
            "Pac": 0.95, "Cro": 0.95, "Tea": 1.05, "Pos": 0.95
        },
        "stats": ["Av Rat", "Tck/90", "Poss Won/90", "Cr C/90", "Sprints/90"],
        "description": "Wide player who presses, tracks back, and still attacks space."
    },
    "Inverted Winger": {
        "category": "Wide Player",
        "attributes": {
            "Dri": 1.15, "Tec": 1.15, "Fir": 1.10, "Pas": 1.10,
            "Vis": 1.05, "OtB": 1.05, "Acc": 1.00, "Dec": 1.00
        },
        "stats": ["Av Rat", "OP-KP/90", "Drb/90", "xA/90", "Asts/90", "Ch C/90"],
        "description": "Wide creator who moves inside to combine and create."
    },
    "Inside Forward": {
        "category": "Wide Player",
        "attributes": {
            "Dri": 1.20, "Fin": 1.15, "Fir": 1.05, "Tec": 1.10,
            "OtB": 1.15, "Acc": 1.05, "Pac": 1.05, "Cmp": 0.95,
            "Dec": 0.95
        },
        "stats": ["Av Rat", "Gls/90", "xG/90", "Drb/90", "Shot/90", "ShT/90"],
        "description": "Wide attacker who cuts inside to create and score."
    },
    "Raumdeuter": {
        "category": "Wide Player",
        "attributes": {
            "OtB": 1.35, "Ant": 1.15, "Fin": 1.10, "Cmp": 1.05,
            "Dec": 1.00, "Acc": 0.95, "Pac": 0.95, "Fir": 0.90
        },
        "stats": ["Av Rat", "Gls/90", "xG/90", "Shot/90", "Asts/90"],
        "description": "Space interpreter who attacks dangerous zones from wide positions."
    },
    "Wide Target Forward": {
        "category": "Wide Player",
        "attributes": {
            "Str": 1.20, "Hea": 1.20, "Jum": 1.15, "OtB": 1.00,
            "Fin": 0.95, "Fir": 0.95, "Cmp": 0.90, "Agg": 0.90
        },
        "stats": ["Av Rat", "Hdr %", "Hdrs W/90", "Gls/90", "Asts/90"],
        "description": "Physical wide forward who wins aerial duels and creates knockdowns."
    },

    # Strikers
    "Target Forward": {
        "category": "Forward",
        "attributes": {
            "Str": 1.25, "Hea": 1.20, "Jum": 1.20, "Fir": 1.00,
            "Cmp": 0.95, "Fin": 1.00, "OtB": 0.95, "Agg": 0.90
        },
        "stats": ["Av Rat", "Hdr %", "Hdrs W/90", "Gls/90", "Asts/90"],
        "description": "Physical forward who holds up play and attacks crosses."
    },
    "Deep Lying Forward": {
        "category": "Forward",
        "attributes": {
            "Fir": 1.15, "Pas": 1.10, "Tec": 1.10, "Vis": 1.00,
            "Cmp": 1.05, "OtB": 1.00, "Fin": 1.00, "Dec": 1.05
        },
        "stats": ["Av Rat", "Asts/90", "OP-KP/90", "xA/90", "Gls/90", "Pas %"],
        "description": "Forward who links play and creates for runners."
    },
    "Advanced Forward": {
        "category": "Forward",
        "attributes": {
            "Fin": 1.25, "OtB": 1.25, "Acc": 1.10, "Pac": 1.10,
            "Cmp": 1.05, "Ant": 1.00, "Fir": 0.95, "Dec": 0.95
        },
        "stats": ["Av Rat", "Gls/90", "xG/90", "Shot/90", "ShT/90", "Conv %"],
        "description": "Forward who stretches the line and attacks space."
    },
    "Pressing Forward": {
        "category": "Forward",
        "attributes": {
            "Wor": 1.30, "Sta": 1.20, "Agg": 1.05, "Ant": 1.00,
            "Acc": 1.00, "Pac": 1.00, "Fin": 1.00, "OtB": 1.05,
            "Tea": 1.10
        },
        "stats": ["Av Rat", "Gls/90", "xG/90", "Poss Won/90", "Sprints/90", "Tck/90"],
        "description": "Forward who leads the press and attacks space."
    },
    "Complete Forward": {
        "category": "Forward",
        "attributes": {
            "Fin": 1.20, "Fir": 1.10, "Tec": 1.05, "Pas": 0.95,
            "OtB": 1.15, "Cmp": 1.05, "Dec": 1.00, "Pac": 1.00,
            "Str": 1.00, "Hea": 0.90
        },
        "stats": ["Av Rat", "Gls/90", "xG/90", "Asts/90", "OP-KP/90", "Shot/90"],
        "description": "Complete striker who can score, link, run channels, and lead the line."
    },
    "Poacher": {
        "category": "Forward",
        "attributes": {
            "Fin": 1.35, "OtB": 1.25, "Ant": 1.15, "Cmp": 1.10,
            "Acc": 0.95, "Fir": 0.95
        },
        "stats": ["Av Rat", "Gls/90", "xG/90", "ShT/90", "Conv %"],
        "description": "Box striker who focuses on finishing chances."
    },
    "False Nine": {
        "category": "Forward",
        "attributes": {
            "Fir": 1.20, "Pas": 1.15, "Tec": 1.15, "Vis": 1.10,
            "Dec": 1.10, "OtB": 1.05, "Cmp": 1.05, "Dri": 0.95
        },
        "stats": ["Av Rat", "OP-KP/90", "Asts/90", "xA/90", "Gls/90", "Pas %"],
        "description": "Forward who drops off to create space and link attacks."
    },
}
