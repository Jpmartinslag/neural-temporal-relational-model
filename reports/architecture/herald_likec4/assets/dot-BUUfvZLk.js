var e=e=>{switch(e){case`index`:return`digraph {
    graph [TBbalance=min,
        bgcolor=transparent,
        compound=true,
        fontname=Arial,
        fontsize=20,
        labeljust=l,
        labelloc=t,
        layout=dot,
        likec4_viewId=index,
        nodesep=1.528,
        outputorder=nodesfirst,
        pad=0.209,
        rankdir=TB,
        ranksep=1.667,
        splines=spline
    ];
    node [color="#2563eb",
        fillcolor="#3b82f6",
        fontcolor="#eff6ff",
        fontname=Arial,
        label="\\N",
        penwidth=0,
        shape=rect,
        style=filled
    ];
    edge [arrowsize=0.75,
        color="#8D8D8D",
        fontcolor="#C9C9C9",
        fontname=Arial,
        fontsize=14,
        penwidth=2
    ];
    france [height=2.5,
        label=<<TABLE BORDER="0" CELLPADDING="0" CELLSPACING="4"><TR><TD><FONT POINT-SIZE="20">HERALD France</FONT></TD></TR><TR><TD><FONT POINT-SIZE="15" COLOR="#bfdbfe">Modele de prevision territoriale des<BR/>creations d etablissements par zone d emploi.</FONT></TD></TR></TABLE>>,
        likec4_id=france,
        likec4_level=0,
        margin="0.223,0.223",
        width=4.445];
}
`;case`view_14htaoj`:return`digraph {
    graph [TBbalance=min,
        bgcolor=transparent,
        compound=true,
        fontname=Arial,
        fontsize=20,
        labeljust=l,
        labelloc=t,
        layout=dot,
        likec4_viewId=view_14htaoj,
        nodesep=1.528,
        outputorder=nodesfirst,
        pad=0.209,
        rankdir=TB,
        ranksep=1.667,
        splines=spline
    ];
    node [color="#2563eb",
        fillcolor="#3b82f6",
        fontcolor="#eff6ff",
        fontname=Arial,
        label="\\N",
        penwidth=0,
        shape=rect,
        style=filled
    ];
    edge [arrowsize=0.75,
        color="#8D8D8D",
        fontcolor="#C9C9C9",
        fontname=Arial,
        fontsize=14,
        penwidth=2
    ];
    subgraph cluster_france {
        graph [color="#1b3d88",
            fillcolor="#194b9e",
            label=<<FONT POINT-SIZE="11" COLOR="#bfdbfeb3"><B>HERALD FRANCE</B></FONT>>,
            likec4_depth=1,
            likec4_id=france,
            likec4_level=0,
            margin=40,
            style=filled
        ];
        data [height=2.5,
            label=<<FONT POINT-SIZE="20">Donnees observees</FONT>>,
            likec4_id="france.data",
            likec4_level=1,
            margin="0.223,0.223",
            width=4.445];
        priors [height=2.5,
            label=<<FONT POINT-SIZE="20">Priors territoriaux</FONT>>,
            likec4_id="france.priors",
            likec4_level=1,
            margin="0.223,0.223",
            width=4.445];
        ridge [height=2.5,
            label=<<TABLE BORDER="0" CELLPADDING="0" CELLSPACING="4"><TR><TD><FONT POINT-SIZE="20">Ridge AR</FONT></TD></TR><TR><TD><FONT POINT-SIZE="15" COLOR="#bfdbfe">Baseline mathematique lineaire: lags locaux +<BR/>regression Ridge.</FONT></TD></TR></TABLE>>,
            likec4_id="france.ridge",
            likec4_level=1,
            margin="0.223,0.223",
            width=4.445];
        herald [height=2.5,
            label=<<TABLE BORDER="0" CELLPADDING="0" CELLSPACING="4"><TR><TD><FONT POINT-SIZE="20">HERALD</FONT></TD></TR><TR><TD><FONT POINT-SIZE="15" COLOR="#bfdbfe">Modele hybride: Ridge AR + correction neurale<BR/>territoriale.</FONT></TD></TR></TABLE>>,
            likec4_id="france.herald",
            likec4_level=1,
            margin="0.223,0.223",
            width=4.445];
        intelligence [height=2.5,
            label=<<TABLE BORDER="0" CELLPADDING="0" CELLSPACING="4"><TR><TD><FONT POINT-SIZE="20">HERALD Intelligence v0</FONT></TD></TR><TR><TD><FONT POINT-SIZE="15" COLOR="#bfdbfe">Couche exploratoire de post-traitement:<BR/>scores, alertes et contexte.</FONT></TD></TR></TABLE>>,
            likec4_id="france.intelligence",
            likec4_level=1,
            margin="0.223,0.223",
            width=4.445];
        dashboard [height=2.5,
            label=<<FONT POINT-SIZE="20">Dashboard HERALD France</FONT>>,
            likec4_id="france.dashboard",
            likec4_level=1,
            margin="0.223,0.223",
            width=4.445];
    }
    data -> ridge [arrowhead=normal,
        label=<<TABLE BORDER="0" CELLPADDING="3" CELLSPACING="0" BGCOLOR="#18191BA0"><TR><TD ALIGN="TEXT" BALIGN="LEFT"><FONT POINT-SIZE="14"><B>[...]</B></FONT></TD></TR></TABLE>>,
        likec4_id="19n7v1j",
        style=dashed];
    data -> herald [arrowhead=normal,
        label=<<TABLE BORDER="0" CELLPADDING="3" CELLSPACING="0" BGCOLOR="#18191BA0"><TR><TD ALIGN="TEXT" BALIGN="LEFT"><FONT POINT-SIZE="14">garantit train passe seulement</FONT></TD></TR></TABLE>>,
        likec4_id=itguoc,
        style=dashed];
    priors -> herald [arrowhead=normal,
        likec4_id=w27ri1,
        minlen=1,
        style=dashed];
    ridge -> herald [arrowhead=normal,
        label=<<TABLE BORDER="0" CELLPADDING="3" CELLSPACING="0" BGCOLOR="#18191BA0"><TR><TD ALIGN="TEXT" BALIGN="LEFT"><FONT POINT-SIZE="14">composante mathematique</FONT></TD></TR></TABLE>>,
        likec4_id=ef6upt,
        style=dashed];
    ridge -> dashboard [arrowhead=normal,
        likec4_id="1u7x82b",
        style=dashed];
    herald -> ridge [arrowhead=normal,
        label=<<TABLE BORDER="0" CELLPADDING="3" CELLSPACING="0" BGCOLOR="#18191BA0"><TR><TD ALIGN="TEXT" BALIGN="LEFT"><FONT POINT-SIZE="14">reutilise la base Ridge</FONT></TD></TR></TABLE>>,
        likec4_id=ydo0v5,
        style=dashed];
    herald -> intelligence [arrowhead=normal,
        likec4_id="1aawqfd",
        style=dashed];
    herald -> dashboard [arrowhead=normal,
        likec4_id=xxq320,
        style=dashed];
    intelligence -> dashboard [arrowhead=normal,
        likec4_id="6nrvyz",
        style=dashed];
}
`;case`view_1yuis9v`:return`digraph {
    graph [TBbalance=min,
        bgcolor=transparent,
        compound=true,
        fontname=Arial,
        fontsize=20,
        labeljust=l,
        labelloc=t,
        layout=dot,
        likec4_viewId=view_1yuis9v,
        nodesep=1.528,
        outputorder=nodesfirst,
        pad=0.209,
        rankdir=TB,
        ranksep=1.667,
        splines=spline
    ];
    node [color="#2563eb",
        fillcolor="#3b82f6",
        fontcolor="#eff6ff",
        fontname=Arial,
        label="\\N",
        penwidth=0,
        shape=rect,
        style=filled
    ];
    edge [arrowsize=0.75,
        color="#8D8D8D",
        fontcolor="#C9C9C9",
        fontname=Arial,
        fontsize=14,
        penwidth=2
    ];
    subgraph cluster_ridge {
        graph [color="#1b3d88",
            fillcolor="#194b9e",
            label=<<FONT POINT-SIZE="11" COLOR="#bfdbfeb3"><B>RIDGE AR</B></FONT>>,
            likec4_depth=1,
            likec4_id="france.ridge",
            likec4_level=0,
            margin=40,
            style=filled
        ];
        features [group="france.ridge",
            height=2.5,
            label=<<TABLE BORDER="0" CELLPADDING="0" CELLSPACING="4"><TR><TD><FONT POINT-SIZE="20">Features locales</FONT></TD></TR><TR><TD><FONT POINT-SIZE="15" COLOR="#bfdbfe">side_lag_1, side_lag_2, side_lag_3,<BR/>growth_1y, growth_2y.</FONT></TD></TR></TABLE>>,
            likec4_id="france.ridge.features",
            likec4_level=1,
            margin="0.223,0.223",
            width=4.445];
        preprocessing [group="france.ridge",
            height=2.5,
            label=<<FONT POINT-SIZE="20">Imputation + standardisation</FONT>>,
            likec4_id="france.ridge.preprocessing",
            likec4_level=1,
            margin="0.223,0.223",
            width=4.445];
        linear [group="france.ridge",
            height=2.5,
            label=<<FONT POINT-SIZE="20">Regression Ridge(alpha=1)</FONT>>,
            likec4_id="france.ridge.linear",
            likec4_level=1,
            margin="0.223,0.223",
            width=4.445];
        ridgepred [group="france.ridge",
            height=2.5,
            label=<<FONT POINT-SIZE="20">Prediction Ridge</FONT>>,
            likec4_id="france.ridge.ridgePred",
            likec4_level=1,
            margin="0.223,0.223",
            width=4.445];
    }
    data [height=2.5,
        label=<<FONT POINT-SIZE="20">Donnees observees</FONT>>,
        likec4_id="france.data",
        likec4_level=0,
        margin="0.223,0.223",
        width=4.445];
    data -> features [arrowhead=normal,
        label=<<TABLE BORDER="0" CELLPADDING="3" CELLSPACING="0" BGCOLOR="#18191BA0"><TR><TD ALIGN="TEXT" BALIGN="LEFT"><FONT POINT-SIZE="14">fournit l historique local</FONT></TD></TR></TABLE>>,
        likec4_id="1qhmk9a",
        minlen=1,
        style=dashed];
    herald [height=2.5,
        label=<<TABLE BORDER="0" CELLPADDING="0" CELLSPACING="4"><TR><TD><FONT POINT-SIZE="20">HERALD</FONT></TD></TR><TR><TD><FONT POINT-SIZE="15" COLOR="#bfdbfe">Modele hybride: Ridge AR + correction neurale<BR/>territoriale.</FONT></TD></TR></TABLE>>,
        likec4_id="france.herald",
        likec4_level=0,
        margin="0.223,0.223",
        width=4.445];
    herald -> linear [arrowhead=normal,
        label=<<TABLE BORDER="0" CELLPADDING="3" CELLSPACING="0" BGCOLOR="#18191BA0"><TR><TD ALIGN="TEXT" BALIGN="LEFT"><FONT POINT-SIZE="14">reutilise la base Ridge</FONT></TD></TR></TABLE>>,
        likec4_id="1yjn9qq",
        style=dashed];
    features -> preprocessing [arrowhead=normal,
        likec4_id=dxg9z5,
        style=dashed,
        weight=2];
    preprocessing -> linear [arrowhead=normal,
        likec4_id="1l4ol4r",
        style=dashed,
        weight=2];
    linear -> ridgepred [arrowhead=normal,
        likec4_id=ormmll,
        style=dashed,
        weight=2];
    ridgepred -> herald [arrowhead=normal,
        label=<<TABLE BORDER="0" CELLPADDING="3" CELLSPACING="0" BGCOLOR="#18191BA0"><TR><TD ALIGN="TEXT" BALIGN="LEFT"><FONT POINT-SIZE="14">composante mathematique</FONT></TD></TR></TABLE>>,
        likec4_id="1vejwgh",
        style=dashed];
    dashboard [height=2.5,
        label=<<FONT POINT-SIZE="20">Dashboard HERALD France</FONT>>,
        likec4_id="france.dashboard",
        likec4_level=0,
        margin="0.223,0.223",
        width=4.445];
    ridgepred -> dashboard [arrowhead=normal,
        likec4_id="10b524j",
        minlen=1,
        style=dashed];
}
`;case`view_1mz8h1l`:return`digraph {
    graph [TBbalance=min,
        bgcolor=transparent,
        compound=true,
        fontname=Arial,
        fontsize=20,
        labeljust=l,
        labelloc=t,
        layout=dot,
        likec4_viewId=view_1mz8h1l,
        nodesep=1.528,
        outputorder=nodesfirst,
        pad=0.209,
        rankdir=TB,
        ranksep=1.667,
        splines=spline
    ];
    node [color="#2563eb",
        fillcolor="#3b82f6",
        fontcolor="#eff6ff",
        fontname=Arial,
        label="\\N",
        penwidth=0,
        shape=rect,
        style=filled
    ];
    edge [arrowsize=0.75,
        color="#8D8D8D",
        fontcolor="#C9C9C9",
        fontname=Arial,
        fontsize=14,
        penwidth=2
    ];
    subgraph cluster_herald {
        graph [color="#1b3d88",
            fillcolor="#194b9e",
            label=<<FONT POINT-SIZE="11" COLOR="#bfdbfeb3"><B>HERALD</B></FONT>>,
            likec4_depth=1,
            likec4_id="france.herald",
            likec4_level=0,
            margin=40,
            style=filled
        ];
        sequences [height=2.5,
            label=<<FONT POINT-SIZE="20">Sequences forecast-safe</FONT>>,
            likec4_id="france.herald.sequences",
            likec4_level=1,
            margin="0.223,0.223",
            width=4.445];
        local [height=2.5,
            label=<<TABLE BORDER="0" CELLPADDING="0" CELLSPACING="4"><TR><TD><FONT POINT-SIZE="20">Encodeur local</FONT></TD></TR><TR><TD><FONT POINT-SIZE="15" COLOR="#bfdbfe">Projection annuelle, encodeur trimestriel et<BR/>memoire GRU locale.</FONT></TD></TR></TABLE>>,
            likec4_id="france.herald.local",
            likec4_level=1,
            margin="0.223,0.223",
            width=4.445];
        dynamicgraph [height=2.5,
            label=<<TABLE BORDER="0" CELLPADDING="0" CELLSPACING="4"><TR><TD><FONT POINT-SIZE="20">Graphe dynamique</FONT></TD></TR><TR><TD><FONT POINT-SIZE="15" COLOR="#bfdbfe">Attention QK conditionnee par regime, prior<BR/>geo et prior mobilite.</FONT></TD></TR></TABLE>>,
            likec4_id="france.herald.dynamicGraph",
            likec4_level=1,
            margin="0.223,0.223",
            width=4.445];
        graphmessages [height=2.5,
            label=<<TABLE BORDER="0" CELLPADDING="0" CELLSPACING="4"><TR><TD><FONT POINT-SIZE="20">Messages territoriaux</FONT></TD></TR><TR><TD><FONT POINT-SIZE="15" COLOR="#bfdbfe">Aggregation A_t @ embeddings des zones<BR/>connectees.</FONT></TD></TR></TABLE>>,
            likec4_id="france.herald.graphMessages",
            likec4_level=1,
            margin="0.223,0.223",
            width=4.445];
        internals [height=2.5,
            label=<<TABLE BORDER="0" CELLPADDING="0" CELLSPACING="4"><TR><TD><FONT POINT-SIZE="20">Internals graphe</FONT></TD></TR><TR><TD><FONT POINT-SIZE="15" COLOR="#bfdbfe">dynamic_adj, gate, alpha, gamma_geo,<BR/>gamma_mob.</FONT></TD></TR></TABLE>>,
            likec4_id="france.herald.internals",
            likec4_level=1,
            margin="0.223,0.223",
            width=4.445];
        mix [height=2.5,
            label=<<TABLE BORDER="0" CELLPADDING="0" CELLSPACING="4"><TR><TD><FONT POINT-SIZE="20">Gate / Alpha</FONT></TD></TR><TR><TD><FONT POINT-SIZE="15" COLOR="#bfdbfe">Arbitrage entre signal local, signal graphe<BR/>et correction residuelle.</FONT></TD></TR></TABLE>>,
            likec4_id="france.herald.mix",
            likec4_level=1,
            margin="0.223,0.223",
            width=4.445];
        residual [height=2.5,
            label=<<FONT POINT-SIZE="20">Tete residuelle</FONT>>,
            likec4_id="france.herald.residual",
            likec4_level=1,
            margin="0.223,0.223",
            width=4.445];
        sector [height=2.5,
            label=<<FONT POINT-SIZE="20">Tete A10</FONT>>,
            likec4_id="france.herald.sector",
            likec4_level=1,
            margin="0.223,0.223",
            width=4.445];
        heraldpred [height=2.5,
            label=<<FONT POINT-SIZE="20">Prediction HERALD</FONT>>,
            likec4_id="france.herald.heraldPred",
            likec4_level=1,
            margin="0.223,0.223",
            width=4.445];
        sectorpred [height=2.5,
            label=<<FONT POINT-SIZE="20">Predictions A10</FONT>>,
            likec4_id="france.herald.sectorPred",
            likec4_level=1,
            margin="0.223,0.223",
            width=4.445];
    }
    data [height=2.5,
        label=<<FONT POINT-SIZE="20">Donnees observees</FONT>>,
        likec4_id="france.data",
        likec4_level=0,
        margin="0.223,0.223",
        width=4.445];
    data -> sequences [arrowhead=normal,
        label=<<TABLE BORDER="0" CELLPADDING="3" CELLSPACING="0" BGCOLOR="#18191BA0"><TR><TD ALIGN="TEXT" BALIGN="LEFT"><FONT POINT-SIZE="14">garantit train passe seulement</FONT></TD></TR></TABLE>>,
        likec4_id=y3dgz2,
        minlen=1,
        style=dashed];
    ridge [height=2.5,
        label=<<TABLE BORDER="0" CELLPADDING="0" CELLSPACING="4"><TR><TD><FONT POINT-SIZE="20">Ridge AR</FONT></TD></TR><TR><TD><FONT POINT-SIZE="15" COLOR="#bfdbfe">Baseline mathematique lineaire: lags locaux +<BR/>regression Ridge.</FONT></TD></TR></TABLE>>,
        likec4_id="france.ridge",
        likec4_level=0,
        margin="0.223,0.223",
        width=4.445];
    ridge -> heraldpred [arrowhead=normal,
        label=<<TABLE BORDER="0" CELLPADDING="3" CELLSPACING="0" BGCOLOR="#18191BA0"><TR><TD ALIGN="TEXT" BALIGN="LEFT"><FONT POINT-SIZE="14">composante mathematique</FONT></TD></TR></TABLE>>,
        likec4_id="1fr5fmi",
        style=dashed];
    priors [height=2.5,
        label=<<FONT POINT-SIZE="20">Priors territoriaux</FONT>>,
        likec4_id="france.priors",
        likec4_level=0,
        margin="0.223,0.223",
        width=4.445];
    priors -> dynamicgraph [arrowhead=normal,
        likec4_id="11u24y6",
        minlen=1,
        style=dashed];
    sequences -> ridge [arrowhead=normal,
        label=<<TABLE BORDER="0" CELLPADDING="3" CELLSPACING="0" BGCOLOR="#18191BA0"><TR><TD ALIGN="TEXT" BALIGN="LEFT"><FONT POINT-SIZE="14">reutilise la base Ridge</FONT></TD></TR></TABLE>>,
        likec4_id=lw7fcz,
        style=dashed];
    sequences -> local [arrowhead=normal,
        likec4_id="1hwfmej",
        style=dashed,
        weight=2];
    local -> dynamicgraph [arrowhead=normal,
        likec4_id=epkj5q,
        style=dashed,
        weight=2];
    local -> mix [arrowhead=normal,
        likec4_id=ef3bqz,
        style=dashed];
    dynamicgraph -> graphmessages [arrowhead=normal,
        likec4_id="1tix18n",
        style=dashed,
        weight=2];
    dynamicgraph -> internals [arrowhead=normal,
        likec4_id="5uozlz",
        style=dashed,
        weight=2];
    graphmessages -> mix [arrowhead=normal,
        likec4_id="1vpe30i",
        style=dashed];
    intelligence [height=2.5,
        label=<<TABLE BORDER="0" CELLPADDING="0" CELLSPACING="4"><TR><TD><FONT POINT-SIZE="20">HERALD Intelligence v0</FONT></TD></TR><TR><TD><FONT POINT-SIZE="15" COLOR="#bfdbfe">Couche exploratoire de post-traitement:<BR/>scores, alertes et contexte.</FONT></TD></TR></TABLE>>,
        likec4_id="france.intelligence",
        likec4_level=0,
        margin="0.223,0.223",
        width=4.445];
    internals -> intelligence [arrowhead=normal,
        likec4_id=ul3dwz,
        style=dashed];
    mix -> residual [arrowhead=normal,
        likec4_id="1ekhr5z",
        style=dashed];
    mix -> sector [arrowhead=normal,
        likec4_id="1ry5ofe",
        style=dashed];
    residual -> heraldpred [arrowhead=normal,
        label=<<TABLE BORDER="0" CELLPADDING="3" CELLSPACING="0" BGCOLOR="#18191BA0"><TR><TD ALIGN="TEXT" BALIGN="LEFT"><FONT POINT-SIZE="14">Ridge + residual * zone_std</FONT></TD></TR></TABLE>>,
        likec4_id="19lhf4e",
        style=dashed,
        weight=2];
    sector -> sectorpred [arrowhead=normal,
        likec4_id=apj8fd,
        style=dashed,
        weight=2];
    heraldpred -> intelligence [arrowhead=normal,
        likec4_id="1lwz7bm",
        style=dashed];
    dashboard [height=2.5,
        label=<<FONT POINT-SIZE="20">Dashboard HERALD France</FONT>>,
        likec4_id="france.dashboard",
        likec4_level=0,
        margin="0.223,0.223",
        width=4.445];
    heraldpred -> dashboard [arrowhead=normal,
        likec4_id="1s1o003",
        style=dashed];
    sectorpred -> intelligence [arrowhead=normal,
        likec4_id="1eegt6g",
        style=dashed];
    sectorpred -> dashboard [arrowhead=normal,
        likec4_id=g4wpux,
        style=dashed];
}
`;case`view_1py4btl`:return`digraph {
    graph [TBbalance=min,
        bgcolor=transparent,
        compound=true,
        fontname=Arial,
        fontsize=20,
        labeljust=l,
        labelloc=t,
        layout=dot,
        likec4_viewId=view_1py4btl,
        nodesep=1.528,
        outputorder=nodesfirst,
        pad=0.209,
        rankdir=TB,
        ranksep=1.667,
        splines=spline
    ];
    node [color="#2563eb",
        fillcolor="#3b82f6",
        fontcolor="#eff6ff",
        fontname=Arial,
        label="\\N",
        penwidth=0,
        shape=rect,
        style=filled
    ];
    edge [arrowsize=0.75,
        color="#8D8D8D",
        fontcolor="#C9C9C9",
        fontname=Arial,
        fontsize=14,
        penwidth=2
    ];
    priors [height=2.5,
        label=<<FONT POINT-SIZE="20">Priors territoriaux</FONT>>,
        likec4_id="france.priors",
        likec4_level=0,
        margin="0.223,0.223",
        width=4.445];
    dynamicgraph [height=2.5,
        label=<<TABLE BORDER="0" CELLPADDING="0" CELLSPACING="4"><TR><TD><FONT POINT-SIZE="20">Graphe dynamique</FONT></TD></TR><TR><TD><FONT POINT-SIZE="15" COLOR="#bfdbfe">Attention QK conditionnee par regime, prior<BR/>geo et prior mobilite.</FONT></TD></TR></TABLE>>,
        likec4_id="france.herald.dynamicGraph",
        likec4_level=0,
        margin="0.223,0.223",
        width=4.445];
    priors -> dynamicgraph [arrowhead=normal,
        likec4_id="11u24y6",
        minlen=1,
        style=dashed];
    local [height=2.5,
        label=<<TABLE BORDER="0" CELLPADDING="0" CELLSPACING="4"><TR><TD><FONT POINT-SIZE="20">Encodeur local</FONT></TD></TR><TR><TD><FONT POINT-SIZE="15" COLOR="#bfdbfe">Projection annuelle, encodeur trimestriel et<BR/>memoire GRU locale.</FONT></TD></TR></TABLE>>,
        likec4_id="france.herald.local",
        likec4_level=0,
        margin="0.223,0.223",
        width=4.445];
    local -> dynamicgraph [arrowhead=normal,
        likec4_id=epkj5q,
        minlen=1,
        style=dashed,
        weight=2];
    graphmessages [height=2.5,
        label=<<TABLE BORDER="0" CELLPADDING="0" CELLSPACING="4"><TR><TD><FONT POINT-SIZE="20">Messages territoriaux</FONT></TD></TR><TR><TD><FONT POINT-SIZE="15" COLOR="#bfdbfe">Aggregation A_t @ embeddings des zones<BR/>connectees.</FONT></TD></TR></TABLE>>,
        likec4_id="france.herald.graphMessages",
        likec4_level=0,
        margin="0.223,0.223",
        width=4.445];
    dynamicgraph -> graphmessages [arrowhead=normal,
        likec4_id="1tix18n",
        minlen=1,
        style=dashed,
        weight=2];
    internals [height=2.5,
        label=<<TABLE BORDER="0" CELLPADDING="0" CELLSPACING="4"><TR><TD><FONT POINT-SIZE="20">Internals graphe</FONT></TD></TR><TR><TD><FONT POINT-SIZE="15" COLOR="#bfdbfe">dynamic_adj, gate, alpha, gamma_geo,<BR/>gamma_mob.</FONT></TD></TR></TABLE>>,
        likec4_id="france.herald.internals",
        likec4_level=0,
        margin="0.223,0.223",
        width=4.445];
    dynamicgraph -> internals [arrowhead=normal,
        likec4_id="5uozlz",
        minlen=1,
        style=dashed,
        weight=2];
}
`;case`view_1dglhfw`:return`digraph {
    graph [TBbalance=min,
        bgcolor=transparent,
        compound=true,
        fontname=Arial,
        fontsize=20,
        labeljust=l,
        labelloc=t,
        layout=dot,
        likec4_viewId=view_1dglhfw,
        nodesep=1.528,
        outputorder=nodesfirst,
        pad=0.209,
        rankdir=TB,
        ranksep=1.667,
        splines=spline
    ];
    node [color="#2563eb",
        fillcolor="#3b82f6",
        fontcolor="#eff6ff",
        fontname=Arial,
        label="\\N",
        penwidth=0,
        shape=rect,
        style=filled
    ];
    edge [arrowsize=0.75,
        color="#8D8D8D",
        fontcolor="#C9C9C9",
        fontname=Arial,
        fontsize=14,
        penwidth=2
    ];
    subgraph cluster_intelligence {
        graph [color="#1b3d88",
            fillcolor="#194b9e",
            label=<<FONT POINT-SIZE="11" COLOR="#bfdbfeb3"><B>HERALD INTELLIGENCE V0</B></FONT>>,
            likec4_depth=1,
            likec4_id="france.intelligence",
            likec4_level=0,
            margin=40,
            style=filled
        ];
        scores [height=2.5,
            label=<<FONT POINT-SIZE="20">Scores opportunite/risque</FONT>>,
            likec4_id="france.intelligence.scores",
            likec4_level=1,
            margin="0.223,0.223",
            width=4.445];
        maps [height=2.5,
            label=<<FONT POINT-SIZE="20">Cartes interpretatives</FONT>>,
            likec4_id="france.intelligence.maps",
            likec4_level=1,
            margin="0.223,0.223",
            width=4.445];
        alerts [height=2.5,
            label=<<FONT POINT-SIZE="20">Alertes territoriales</FONT>>,
            likec4_id="france.intelligence.alerts",
            likec4_level=1,
            margin="0.223,0.223",
            width=4.445];
    }
    herald [height=2.5,
        label=<<TABLE BORDER="0" CELLPADDING="0" CELLSPACING="4"><TR><TD><FONT POINT-SIZE="20">HERALD</FONT></TD></TR><TR><TD><FONT POINT-SIZE="15" COLOR="#bfdbfe">Modele hybride: Ridge AR + correction neurale<BR/>territoriale.</FONT></TD></TR></TABLE>>,
        likec4_id="france.herald",
        likec4_level=0,
        margin="0.223,0.223",
        width=4.445];
    herald -> scores [arrowhead=normal,
        likec4_id="11ygp6k",
        style=dashed];
    herald -> maps [arrowhead=normal,
        likec4_id="1tblilk",
        style=dashed];
    scores -> alerts [arrowhead=normal,
        likec4_id=vfttcc,
        minlen=0,
        style=dashed,
        weight=2];
    dashboard [height=2.5,
        label=<<FONT POINT-SIZE="20">Dashboard HERALD France</FONT>>,
        likec4_id="france.dashboard",
        likec4_level=0,
        margin="0.223,0.223",
        width=4.445];
    maps -> dashboard [arrowhead=normal,
        likec4_id="1whqewq",
        minlen=1,
        style=dashed];
}
`;default:throw Error(`Unknown viewId: `+e)}},t=e=>{switch(e){case`index`:return`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"
 "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<!-- Generated by graphviz version 14.1.3 (0)
 -->
<!-- Pages: 1 -->
<svg width="375pt" height="210pt"
 viewBox="0.00 0.00 375.00 210.00" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
<g id="graph0" class="graph" transform="scale(1 1) rotate(0) translate(15.05 195.05)">
<!-- france -->
<g id="node1" class="node">
<title>france</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="345.28,-180 0,-180 0,0 345.28,0 345.28,-180"/>
<text xml:space="preserve" text-anchor="start" x="98.17" y="-102" font-family="Arial" font-size="20.00" fill="#eff6ff">HERALD France</text>
<text xml:space="preserve" text-anchor="start" x="55.91" y="-79" font-family="Arial" font-size="15.00" fill="#bfdbfe">Modele de prevision territoriale des</text>
<text xml:space="preserve" text-anchor="start" x="20.06" y="-61" font-family="Arial" font-size="15.00" fill="#bfdbfe">creations d etablissements par zone d emploi.</text>
</g>
</g>
</svg>
`;case`view_14htaoj`:return`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"
 "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<!-- Generated by graphviz version 14.1.3 (0)
 -->
<!-- Pages: 1 -->
<svg width="998pt" height="1575pt"
 viewBox="0.00 0.00 998.00 1575.00" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
<g id="graph0" class="graph" transform="scale(1 1) rotate(0) translate(15.05 1559.85)">
<g id="clust1" class="cluster">
<title>cluster_france</title>
<polygon fill="#194b9e" stroke="#1b3d88" points="8,-8 8,-1536.8 960,-1536.8 960,-8 8,-8"/>
<text xml:space="preserve" text-anchor="start" x="16" y="-1523.9" font-family="Arial" font-weight="bold" font-size="11.00" fill="#bfdbfe" fill-opacity="0.701961">HERALD FRANCE</text>
</g>
<!-- data -->
<g id="node1" class="node">
<title>data</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="462.02,-1475.6 141.98,-1475.6 141.98,-1295.6 462.02,-1295.6 462.02,-1475.6"/>
<text xml:space="preserve" text-anchor="start" x="213.05" y="-1377.6" font-family="Arial" font-size="20.00" fill="#eff6ff">Donnees observees</text>
</g>
<!-- priors -->
<g id="node2" class="node">
<title>priors</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="920.02,-1475.6 599.98,-1475.6 599.98,-1295.6 920.02,-1295.6 920.02,-1475.6"/>
<text xml:space="preserve" text-anchor="start" x="683.87" y="-1377.6" font-family="Arial" font-size="20.00" fill="#eff6ff">Priors territoriaux</text>
</g>
<!-- ridge -->
<g id="node3" class="node">
<title>ridge</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="393.85,-1152.8 48.15,-1152.8 48.15,-972.8 393.85,-972.8 393.85,-1152.8"/>
<text xml:space="preserve" text-anchor="start" x="178.2" y="-1074.8" font-family="Arial" font-size="20.00" fill="#eff6ff">Ridge AR</text>
<text xml:space="preserve" text-anchor="start" x="68.2" y="-1051.8" font-family="Arial" font-size="15.00" fill="#bfdbfe">Baseline mathematique lineaire: lags locaux +</text>
<text xml:space="preserve" text-anchor="start" x="162.22" y="-1033.8" font-family="Arial" font-size="15.00" fill="#bfdbfe">regression Ridge.</text>
</g>
<!-- herald -->
<g id="node4" class="node">
<title>herald</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="692.18,-830 339.82,-830 339.82,-650 692.18,-650 692.18,-830"/>
<text xml:space="preserve" text-anchor="start" x="475.43" y="-752" font-family="Arial" font-size="20.00" fill="#eff6ff">HERALD</text>
<text xml:space="preserve" text-anchor="start" x="359.87" y="-729" font-family="Arial" font-size="15.00" fill="#bfdbfe">Modele hybride: Ridge AR + correction neurale</text>
<text xml:space="preserve" text-anchor="start" x="480.57" y="-711" font-family="Arial" font-size="15.00" fill="#bfdbfe">territoriale.</text>
</g>
<!-- intelligence -->
<g id="node5" class="node">
<title>intelligence</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="489.02,-529 168.98,-529 168.98,-349 489.02,-349 489.02,-529"/>
<text xml:space="preserve" text-anchor="start" x="221.72" y="-451" font-family="Arial" font-size="20.00" fill="#eff6ff">HERALD Intelligence v0</text>
<text xml:space="preserve" text-anchor="start" x="197.26" y="-428" font-family="Arial" font-size="15.00" fill="#bfdbfe">Couche exploratoire de post&#45;traitement:</text>
<text xml:space="preserve" text-anchor="start" x="239.37" y="-410" font-family="Arial" font-size="15.00" fill="#bfdbfe">scores, alertes et contexte.</text>
</g>
<!-- dashboard -->
<g id="node6" class="node">
<title>dashboard</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="489.02,-228 168.98,-228 168.98,-48 489.02,-48 489.02,-228"/>
<text xml:space="preserve" text-anchor="start" x="202.83" y="-130" font-family="Arial" font-size="20.00" fill="#eff6ff">Dashboard HERALD France</text>
</g>
<!-- data&#45;&gt;ridge -->
<g id="edge1" class="edge">
<title>data&#45;&gt;ridge</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M279.54,-1295.67C269.12,-1254.38 256.69,-1205.15 245.97,-1162.7"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="248.55,-1162.19 244.17,-1155.56 243.46,-1163.48 248.55,-1162.19"/>
<polygon fill="#18191b" fill-opacity="0.627451" stroke="none" points="263.93,-1212.8 263.93,-1235.6 290.92,-1235.6 290.92,-1212.8 263.93,-1212.8"/>
<text xml:space="preserve" text-anchor="start" x="266.93" y="-1221" font-family="Arial" font-weight="bold" font-size="14.00" fill="#c9c9c9">[...]</text>
</g>
<!-- data&#45;&gt;herald -->
<g id="edge2" class="edge">
<title>data&#45;&gt;herald</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M375.19,-1295.78C444.03,-1205.74 541.9,-1059.2 579,-912.8 585.1,-888.71 581.6,-863.3 573.78,-839.63"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="576.34,-838.98 571.34,-832.8 571.39,-840.75 576.34,-838.98"/>
<polygon fill="#18191b" fill-opacity="0.627451" stroke="none" points="559.6,-1051.4 559.6,-1074.2 753.15,-1074.2 753.15,-1051.4 559.6,-1051.4"/>
<text xml:space="preserve" text-anchor="start" x="562.6" y="-1057.2" font-family="Arial" font-size="14.00" fill="#c9c9c9">garantit train passe seulement</text>
</g>
<!-- priors&#45;&gt;herald -->
<g id="edge3" class="edge">
<title>priors&#45;&gt;herald</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M786.86,-1295.87C807.97,-1209.38 826.79,-1076.15 780,-972.8 755.74,-919.2 712.28,-873.09 667.53,-836.42"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="669.31,-834.48 661.82,-831.82 666.01,-838.57 669.31,-834.48"/>
</g>
<!-- ridge&#45;&gt;herald -->
<g id="edge4" class="edge">
<title>ridge&#45;&gt;herald</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M302.78,-972.87C341.47,-930.8 387.74,-880.48 427.27,-837.49"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="429.12,-839.36 432.27,-832.06 425.26,-835.8 429.12,-839.36"/>
<polygon fill="#18191b" fill-opacity="0.627451" stroke="none" points="377.35,-890 377.35,-912.8 552.22,-912.8 552.22,-890 377.35,-890"/>
<text xml:space="preserve" text-anchor="start" x="380.35" y="-895.8" font-family="Arial" font-size="14.00" fill="#c9c9c9">composante mathematique</text>
</g>
<!-- ridge&#45;&gt;dashboard -->
<g id="edge5" class="edge">
<title>ridge&#45;&gt;dashboard</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M174.76,-972.95C166.29,-953.56 158.43,-932.83 153,-912.8 87.29,-670.37 16.52,-580.49 114,-349 132.17,-305.86 164.01,-267.16 197.7,-235.1"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="199.47,-237.04 203.16,-230 195.89,-233.2 199.47,-237.04"/>
</g>
<!-- herald&#45;&gt;ridge -->
<g id="edge6" class="edge">
<title>herald&#45;&gt;ridge</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M340.02,-780.15C281.93,-802.33 223.48,-836.77 189.26,-890 175.35,-911.62 174.13,-937.76 178.72,-963.05"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="176.1,-963.3 180.22,-970.1 181.23,-962.22 176.1,-963.3"/>
<polygon fill="#18191b" fill-opacity="0.627451" stroke="none" points="189.26,-890 189.26,-912.8 333,-912.8 333,-890 189.26,-890"/>
<text xml:space="preserve" text-anchor="start" x="192.26" y="-895.8" font-family="Arial" font-size="14.00" fill="#c9c9c9">reutilise la base Ridge</text>
</g>
<!-- herald&#45;&gt;intelligence -->
<g id="edge7" class="edge">
<title>herald&#45;&gt;intelligence</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M460.4,-650.1C438.22,-614.64 412.62,-573.71 389.94,-537.44"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="392.35,-536.35 386.15,-531.38 387.9,-539.13 392.35,-536.35"/>
</g>
<!-- herald&#45;&gt;dashboard -->
<g id="edge8" class="edge">
<title>herald&#45;&gt;dashboard</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M544.71,-650.07C565.96,-568.49 584.84,-445.97 544,-349 525.83,-305.86 493.99,-267.16 460.3,-235.1"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="462.11,-233.2 454.84,-230 458.53,-237.04 462.11,-233.2"/>
</g>
<!-- intelligence&#45;&gt;dashboard -->
<g id="edge9" class="edge">
<title>intelligence&#45;&gt;dashboard</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M329,-349.1C329,-314.24 329,-274.09 329,-238.28"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="331.63,-238.34 329,-230.84 326.38,-238.34 331.63,-238.34"/>
</g>
</g>
</svg>
`;case`view_1yuis9v`:return`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"
 "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<!-- Generated by graphviz version 14.1.3 (0)
 -->
<!-- Pages: 1 -->
<svg width="812pt" height="1768pt"
 viewBox="0.00 0.00 812.00 1768.00" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
<g id="graph0" class="graph" transform="scale(1 1) rotate(0) translate(15.05 1752.85)">
<g id="clust1" class="cluster">
<title>cluster_ridge</title>
<polygon fill="#194b9e" stroke="#1b3d88" points="26.02,-282.8 26.02,-1467 426.02,-1467 426.02,-282.8 26.02,-282.8"/>
<text xml:space="preserve" text-anchor="start" x="34.02" y="-1454.1" font-family="Arial" font-weight="bold" font-size="11.00" fill="#bfdbfe" fill-opacity="0.701961">RIDGE AR</text>
</g>
<!-- features -->
<g id="node1" class="node">
<title>features</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="386.04,-1405.8 66,-1405.8 66,-1225.8 386.04,-1225.8 386.04,-1405.8"/>
<text xml:space="preserve" text-anchor="start" x="152.65" y="-1327.8" font-family="Arial" font-size="20.00" fill="#eff6ff">Features locales</text>
<text xml:space="preserve" text-anchor="start" x="106.76" y="-1304.8" font-family="Arial" font-size="15.00" fill="#bfdbfe">side_lag_1, side_lag_2, side_lag_3,</text>
<text xml:space="preserve" text-anchor="start" x="150.56" y="-1286.8" font-family="Arial" font-size="15.00" fill="#bfdbfe">growth_1y, growth_2y.</text>
</g>
<!-- preprocessing -->
<g id="node2" class="node">
<title>preprocessing</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="386.04,-1104.8 66,-1104.8 66,-924.8 386.04,-924.8 386.04,-1104.8"/>
<text xml:space="preserve" text-anchor="start" x="100.11" y="-1006.8" font-family="Arial" font-size="20.00" fill="#eff6ff">Imputation + standardisation</text>
</g>
<!-- linear -->
<g id="node3" class="node">
<title>linear</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="386.04,-803.8 66,-803.8 66,-623.8 386.04,-623.8 386.04,-803.8"/>
<text xml:space="preserve" text-anchor="start" x="104" y="-705.8" font-family="Arial" font-size="20.00" fill="#eff6ff">Regression Ridge(alpha=1)</text>
</g>
<!-- ridgepred -->
<g id="node4" class="node">
<title>ridgepred</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="386.04,-502.8 66,-502.8 66,-322.8 386.04,-322.8 386.04,-502.8"/>
<text xml:space="preserve" text-anchor="start" x="152.65" y="-404.8" font-family="Arial" font-size="20.00" fill="#eff6ff">Prediction Ridge</text>
</g>
<!-- data -->
<g id="node5" class="node">
<title>data</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="386.04,-1737.8 66,-1737.8 66,-1557.8 386.04,-1557.8 386.04,-1737.8"/>
<text xml:space="preserve" text-anchor="start" x="137.07" y="-1639.8" font-family="Arial" font-size="20.00" fill="#eff6ff">Donnees observees</text>
</g>
<!-- herald -->
<g id="node6" class="node">
<title>herald</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="782.2,-180 429.84,-180 429.84,0 782.2,0 782.2,-180"/>
<text xml:space="preserve" text-anchor="start" x="565.45" y="-102" font-family="Arial" font-size="20.00" fill="#eff6ff">HERALD</text>
<text xml:space="preserve" text-anchor="start" x="449.89" y="-79" font-family="Arial" font-size="15.00" fill="#bfdbfe">Modele hybride: Ridge AR + correction neurale</text>
<text xml:space="preserve" text-anchor="start" x="570.59" y="-61" font-family="Arial" font-size="15.00" fill="#bfdbfe">territoriale.</text>
</g>
<!-- dashboard -->
<g id="node7" class="node">
<title>dashboard</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="320.04,-180 0,-180 0,0 320.04,0 320.04,-180"/>
<text xml:space="preserve" text-anchor="start" x="33.85" y="-82" font-family="Arial" font-size="20.00" fill="#eff6ff">Dashboard HERALD France</text>
</g>
<!-- features&#45;&gt;preprocessing -->
<g id="edge3" class="edge">
<title>features&#45;&gt;preprocessing</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M226.02,-1225.9C226.02,-1191.04 226.02,-1150.89 226.02,-1115.08"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="228.65,-1115.14 226.02,-1107.64 223.4,-1115.14 228.65,-1115.14"/>
</g>
<!-- preprocessing&#45;&gt;linear -->
<g id="edge4" class="edge">
<title>preprocessing&#45;&gt;linear</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M226.02,-924.9C226.02,-890.04 226.02,-849.89 226.02,-814.08"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="228.65,-814.14 226.02,-806.64 223.4,-814.14 228.65,-814.14"/>
</g>
<!-- linear&#45;&gt;ridgepred -->
<g id="edge5" class="edge">
<title>linear&#45;&gt;ridgepred</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M226.02,-623.9C226.02,-589.04 226.02,-548.89 226.02,-513.08"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="228.65,-513.14 226.02,-505.64 223.4,-513.14 228.65,-513.14"/>
</g>
<!-- ridgepred&#45;&gt;herald -->
<g id="edge6" class="edge">
<title>ridgepred&#45;&gt;herald</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M278.45,-322.95C298,-294.34 321.89,-263.89 348.14,-240 370.22,-219.91 395.45,-201.3 421.29,-184.54"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="422.62,-186.8 427.52,-180.55 419.79,-182.38 422.62,-186.8"/>
<polygon fill="#18191b" fill-opacity="0.627451" stroke="none" points="348.14,-240 348.14,-262.8 523.02,-262.8 523.02,-240 348.14,-240"/>
<text xml:space="preserve" text-anchor="start" x="351.14" y="-245.8" font-family="Arial" font-size="14.00" fill="#c9c9c9">composante mathematique</text>
</g>
<!-- ridgepred&#45;&gt;dashboard -->
<g id="edge7" class="edge">
<title>ridgepred&#45;&gt;dashboard</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M207.72,-322.87C199.23,-281.58 189.1,-232.35 180.37,-189.9"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="182.99,-189.61 178.91,-182.79 177.85,-190.67 182.99,-189.61"/>
</g>
<!-- data&#45;&gt;features -->
<g id="edge1" class="edge">
<title>data&#45;&gt;features</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M226.02,-1557.93C226.02,-1514.1 226.02,-1461.08 226.02,-1415.94"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="228.65,-1416.07 226.02,-1408.57 223.4,-1416.07 228.65,-1416.07"/>
<polygon fill="#18191b" fill-opacity="0.627451" stroke="none" points="226.02,-1475 226.02,-1497.8 375.21,-1497.8 375.21,-1475 226.02,-1475"/>
<text xml:space="preserve" text-anchor="start" x="229.02" y="-1480.8" font-family="Arial" font-size="14.00" fill="#c9c9c9">fournit l historique local</text>
</g>
<!-- herald&#45;&gt;linear -->
<g id="edge2" class="edge">
<title>herald&#45;&gt;linear</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M583.01,-179.76C557.58,-267.18 510.76,-401.9 441.02,-502.8 412.7,-543.77 375.6,-583.39 340.22,-616.96"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="338.57,-614.91 334.9,-621.96 342.16,-618.74 338.57,-614.91"/>
<polygon fill="#18191b" fill-opacity="0.627451" stroke="none" points="547.53,-401.4 547.53,-424.2 691.27,-424.2 691.27,-401.4 547.53,-401.4"/>
<text xml:space="preserve" text-anchor="start" x="550.53" y="-407.2" font-family="Arial" font-size="14.00" fill="#c9c9c9">reutilise la base Ridge</text>
</g>
</g>
</svg>
`;case`view_1mz8h1l`:return`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"
 "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<!-- Generated by graphviz version 14.1.3 (0)
 -->
<!-- Pages: 1 -->
<svg width="1730pt" height="2693pt"
 viewBox="0.00 0.00 1730.00 2693.00" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
<g id="graph0" class="graph" transform="scale(1 1) rotate(0) translate(15.05 2677.65)">
<g id="clust1" class="cluster">
<title>cluster_herald</title>
<polygon fill="#194b9e" stroke="#1b3d88" points="360.02,-261 360.02,-2391.8 1308.02,-2391.8 1308.02,-261 360.02,-261"/>
<text xml:space="preserve" text-anchor="start" x="368.02" y="-2378.9" font-family="Arial" font-weight="bold" font-size="11.00" fill="#bfdbfe" fill-opacity="0.701961">HERALD</text>
</g>
<!-- sequences -->
<g id="node1" class="node">
<title>sequences</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="1209.04,-2330.6 889,-2330.6 889,-2150.6 1209.04,-2150.6 1209.04,-2330.6"/>
<text xml:space="preserve" text-anchor="start" x="938.4" y="-2232.6" font-family="Arial" font-size="20.00" fill="#eff6ff">Sequences forecast&#45;safe</text>
</g>
<!-- local -->
<g id="node2" class="node">
<title>local</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="1211.24,-2029.6 886.8,-2029.6 886.8,-1849.6 1211.24,-1849.6 1211.24,-2029.6"/>
<text xml:space="preserve" text-anchor="start" x="982.87" y="-1951.6" font-family="Arial" font-size="20.00" fill="#eff6ff">Encodeur local</text>
<text xml:space="preserve" text-anchor="start" x="906.86" y="-1928.6" font-family="Arial" font-size="15.00" fill="#bfdbfe">Projection annuelle, encodeur trimestriel et</text>
<text xml:space="preserve" text-anchor="start" x="977.33" y="-1910.6" font-family="Arial" font-size="15.00" fill="#bfdbfe">memoire GRU locale.</text>
</g>
<!-- dynamicgraph -->
<g id="node3" class="node">
<title>dynamicgraph</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="1156.32,-1728.6 827.72,-1728.6 827.72,-1548.6 1156.32,-1548.6 1156.32,-1728.6"/>
<text xml:space="preserve" text-anchor="start" x="906.97" y="-1650.6" font-family="Arial" font-size="20.00" fill="#eff6ff">Graphe dynamique</text>
<text xml:space="preserve" text-anchor="start" x="847.77" y="-1627.6" font-family="Arial" font-size="15.00" fill="#bfdbfe">Attention QK conditionnee par regime, prior</text>
<text xml:space="preserve" text-anchor="start" x="924.07" y="-1609.6" font-family="Arial" font-size="15.00" fill="#bfdbfe">geo et prior mobilite.</text>
</g>
<!-- graphmessages -->
<g id="node4" class="node">
<title>graphmessages</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="1155.78,-1405.8 830.26,-1405.8 830.26,-1225.8 1155.78,-1225.8 1155.78,-1405.8"/>
<text xml:space="preserve" text-anchor="start" x="897.43" y="-1327.8" font-family="Arial" font-size="20.00" fill="#eff6ff">Messages territoriaux</text>
<text xml:space="preserve" text-anchor="start" x="850.31" y="-1304.8" font-family="Arial" font-size="15.00" fill="#bfdbfe">Aggregation A_t @ embeddings des zones</text>
<text xml:space="preserve" text-anchor="start" x="952.58" y="-1286.8" font-family="Arial" font-size="15.00" fill="#bfdbfe">connectees.</text>
</g>
<!-- internals -->
<g id="node5" class="node">
<title>internals</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="720.04,-1405.8 400,-1405.8 400,-1225.8 720.04,-1225.8 720.04,-1405.8"/>
<text xml:space="preserve" text-anchor="start" x="487.75" y="-1327.8" font-family="Arial" font-size="20.00" fill="#eff6ff">Internals graphe</text>
<text xml:space="preserve" text-anchor="start" x="428.69" y="-1304.8" font-family="Arial" font-size="15.00" fill="#bfdbfe">dynamic_adj, gate, alpha, gamma_geo,</text>
<text xml:space="preserve" text-anchor="start" x="514.17" y="-1286.8" font-family="Arial" font-size="15.00" fill="#bfdbfe">gamma_mob.</text>
</g>
<!-- mix -->
<g id="node6" class="node">
<title>mix</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="1178.04,-1104.8 858,-1104.8 858,-924.8 1178.04,-924.8 1178.04,-1104.8"/>
<text xml:space="preserve" text-anchor="start" x="962.43" y="-1026.8" font-family="Arial" font-size="20.00" fill="#eff6ff">Gate / Alpha</text>
<text xml:space="preserve" text-anchor="start" x="880.02" y="-1003.8" font-family="Arial" font-size="15.00" fill="#bfdbfe">Arbitrage entre signal local, signal graphe</text>
<text xml:space="preserve" text-anchor="start" x="940.48" y="-985.8" font-family="Arial" font-size="15.00" fill="#bfdbfe">et correction residuelle.</text>
</g>
<!-- residual -->
<g id="node7" class="node">
<title>residual</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="1244.04,-803.8 924,-803.8 924,-623.8 1244.04,-623.8 1244.04,-803.8"/>
<text xml:space="preserve" text-anchor="start" x="1018.43" y="-705.8" font-family="Arial" font-size="20.00" fill="#eff6ff">Tete residuelle</text>
</g>
<!-- sector -->
<g id="node8" class="node">
<title>sector</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="814.04,-803.8 494,-803.8 494,-623.8 814.04,-623.8 814.04,-803.8"/>
<text xml:space="preserve" text-anchor="start" x="613.44" y="-705.8" font-family="Arial" font-size="20.00" fill="#eff6ff">Tete A10</text>
</g>
<!-- heraldpred -->
<g id="node9" class="node">
<title>heraldpred</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="1244.04,-481 924,-481 924,-301 1244.04,-301 1244.04,-481"/>
<text xml:space="preserve" text-anchor="start" x="996.21" y="-383" font-family="Arial" font-size="20.00" fill="#eff6ff">Prediction HERALD</text>
</g>
<!-- sectorpred -->
<g id="node10" class="node">
<title>sectorpred</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="814.04,-481 494,-481 494,-301 814.04,-301 814.04,-481"/>
<text xml:space="preserve" text-anchor="start" x="583.98" y="-383" font-family="Arial" font-size="20.00" fill="#eff6ff">Predictions A10</text>
</g>
<!-- data -->
<g id="node11" class="node">
<title>data</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="1209.04,-2662.6 889,-2662.6 889,-2482.6 1209.04,-2482.6 1209.04,-2662.6"/>
<text xml:space="preserve" text-anchor="start" x="960.07" y="-2564.6" font-family="Arial" font-size="20.00" fill="#eff6ff">Donnees observees</text>
</g>
<!-- ridge -->
<g id="node12" class="node">
<title>ridge</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="1699.87,-803.8 1354.17,-803.8 1354.17,-623.8 1699.87,-623.8 1699.87,-803.8"/>
<text xml:space="preserve" text-anchor="start" x="1484.22" y="-725.8" font-family="Arial" font-size="20.00" fill="#eff6ff">Ridge AR</text>
<text xml:space="preserve" text-anchor="start" x="1374.22" y="-702.8" font-family="Arial" font-size="15.00" fill="#bfdbfe">Baseline mathematique lineaire: lags locaux +</text>
<text xml:space="preserve" text-anchor="start" x="1468.24" y="-684.8" font-family="Arial" font-size="15.00" fill="#bfdbfe">regression Ridge.</text>
</g>
<!-- priors -->
<g id="node13" class="node">
<title>priors</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="320.04,-2029.6 0,-2029.6 0,-1849.6 320.04,-1849.6 320.04,-2029.6"/>
<text xml:space="preserve" text-anchor="start" x="83.89" y="-1931.6" font-family="Arial" font-size="20.00" fill="#eff6ff">Priors territoriaux</text>
</g>
<!-- intelligence -->
<g id="node14" class="node">
<title>intelligence</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="814.04,-180 494,-180 494,0 814.04,0 814.04,-180"/>
<text xml:space="preserve" text-anchor="start" x="546.74" y="-102" font-family="Arial" font-size="20.00" fill="#eff6ff">HERALD Intelligence v0</text>
<text xml:space="preserve" text-anchor="start" x="522.28" y="-79" font-family="Arial" font-size="15.00" fill="#bfdbfe">Couche exploratoire de post&#45;traitement:</text>
<text xml:space="preserve" text-anchor="start" x="564.39" y="-61" font-family="Arial" font-size="15.00" fill="#bfdbfe">scores, alertes et contexte.</text>
</g>
<!-- dashboard -->
<g id="node15" class="node">
<title>dashboard</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="1244.04,-180 924,-180 924,0 1244.04,0 1244.04,-180"/>
<text xml:space="preserve" text-anchor="start" x="957.85" y="-82" font-family="Arial" font-size="20.00" fill="#eff6ff">Dashboard HERALD France</text>
</g>
<!-- sequences&#45;&gt;local -->
<g id="edge5" class="edge">
<title>sequences&#45;&gt;local</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M1049.02,-2150.7C1049.02,-2115.84 1049.02,-2075.69 1049.02,-2039.88"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="1051.65,-2039.94 1049.02,-2032.44 1046.4,-2039.94 1051.65,-2039.94"/>
</g>
<!-- sequences&#45;&gt;ridge -->
<g id="edge4" class="edge">
<title>sequences&#45;&gt;ridge</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M1209,-2197.98C1330.57,-2155.58 1477.02,-2076.34 1477.02,-1940.6 1477.02,-1940.6 1477.02,-1940.6 1477.02,-1013.8 1477.02,-946.52 1489.49,-871.89 1501.97,-814.01"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="1504.52,-814.62 1503.57,-806.73 1499.39,-813.49 1504.52,-814.62"/>
<polygon fill="#18191b" fill-opacity="0.627451" stroke="none" points="1477.02,-1465.8 1477.02,-1488.6 1620.76,-1488.6 1620.76,-1465.8 1477.02,-1465.8"/>
<text xml:space="preserve" text-anchor="start" x="1480.02" y="-1471.6" font-family="Arial" font-size="14.00" fill="#c9c9c9">reutilise la base Ridge</text>
</g>
<!-- local&#45;&gt;dynamicgraph -->
<g id="edge6" class="edge">
<title>local&#45;&gt;dynamicgraph</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M1032.07,-1849.7C1025.4,-1814.69 1017.71,-1774.34 1010.86,-1738.42"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="1013.5,-1738.27 1009.52,-1731.39 1008.34,-1739.25 1013.5,-1738.27"/>
</g>
<!-- local&#45;&gt;mix -->
<g id="edge7" class="edge">
<title>local&#45;&gt;mix</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M1138.34,-1849.8C1167.35,-1815.01 1195.94,-1772.84 1211.02,-1728.6 1283.12,-1517.09 1292.17,-1434.01 1211.02,-1225.8 1194.51,-1183.44 1165.02,-1144.46 1133.99,-1111.88"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="1136.14,-1110.32 1129.03,-1106.77 1132.37,-1113.98 1136.14,-1110.32"/>
</g>
<!-- dynamicgraph&#45;&gt;graphmessages -->
<g id="edge8" class="edge">
<title>dynamicgraph&#45;&gt;graphmessages</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M992.3,-1548.67C992.43,-1507.47 992.58,-1458.36 992.71,-1415.97"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="995.34,-1416.16 992.73,-1408.66 990.09,-1416.15 995.34,-1416.16"/>
</g>
<!-- dynamicgraph&#45;&gt;internals -->
<g id="edge9" class="edge">
<title>dynamicgraph&#45;&gt;internals</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M872.26,-1548.67C814.9,-1506.07 746.17,-1455.03 687.8,-1411.69"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="689.66,-1409.8 682.07,-1407.43 686.53,-1414.01 689.66,-1409.8"/>
</g>
<!-- graphmessages&#45;&gt;mix -->
<g id="edge10" class="edge">
<title>graphmessages&#45;&gt;mix</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M1000.45,-1225.9C1003.37,-1191.04 1006.73,-1150.89 1009.72,-1115.08"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="1012.33,-1115.33 1010.34,-1107.63 1007.1,-1114.89 1012.33,-1115.33"/>
</g>
<!-- internals&#45;&gt;intelligence -->
<g id="edge11" class="edge">
<title>internals&#45;&gt;intelligence</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M441.3,-1225.84C384.22,-1172.31 328.02,-1098.59 328.02,-1015.8 328.02,-1015.8 328.02,-1015.8 328.02,-390 328.02,-293.86 405.98,-220.24 485.65,-170.12"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="486.79,-172.5 491.79,-166.32 484.03,-168.03 486.79,-172.5"/>
</g>
<!-- mix&#45;&gt;residual -->
<g id="edge12" class="edge">
<title>mix&#45;&gt;residual</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M1037.64,-924.9C1045.37,-889.89 1054.28,-849.54 1062.21,-813.62"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="1064.71,-814.46 1063.76,-806.57 1059.58,-813.33 1064.71,-814.46"/>
</g>
<!-- mix&#45;&gt;sector -->
<g id="edge13" class="edge">
<title>mix&#45;&gt;sector</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M909.79,-924.9C865.81,-888.77 814.9,-846.95 770.14,-810.18"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="771.94,-808.27 764.48,-805.54 768.61,-812.33 771.94,-808.27"/>
</g>
<!-- residual&#45;&gt;heraldpred -->
<g id="edge14" class="edge">
<title>residual&#45;&gt;heraldpred</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M1084.02,-623.87C1084.02,-582.67 1084.02,-533.56 1084.02,-491.17"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="1086.65,-491.36 1084.02,-483.86 1081.4,-491.36 1086.65,-491.36"/>
<polygon fill="#18191b" fill-opacity="0.627451" stroke="none" points="1084.02,-541 1084.02,-563.8 1261.63,-563.8 1261.63,-541 1084.02,-541"/>
<text xml:space="preserve" text-anchor="start" x="1087.02" y="-546.8" font-family="Arial" font-size="14.00" fill="#c9c9c9">Ridge + residual * zone_std</text>
</g>
<!-- sector&#45;&gt;sectorpred -->
<g id="edge15" class="edge">
<title>sector&#45;&gt;sectorpred</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M654.02,-623.87C654.02,-582.67 654.02,-533.56 654.02,-491.17"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="656.65,-491.36 654.02,-483.86 651.4,-491.36 656.65,-491.36"/>
</g>
<!-- heraldpred&#45;&gt;intelligence -->
<g id="edge16" class="edge">
<title>heraldpred&#45;&gt;intelligence</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M956.17,-301.1C903.88,-264.74 843.32,-222.63 790.21,-185.7"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="791.89,-183.67 784.23,-181.54 788.89,-187.98 791.89,-183.67"/>
</g>
<!-- heraldpred&#45;&gt;dashboard -->
<g id="edge17" class="edge">
<title>heraldpred&#45;&gt;dashboard</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M1084.02,-301.1C1084.02,-266.24 1084.02,-226.09 1084.02,-190.28"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="1086.65,-190.34 1084.02,-182.84 1081.4,-190.34 1086.65,-190.34"/>
</g>
<!-- sectorpred&#45;&gt;intelligence -->
<g id="edge18" class="edge">
<title>sectorpred&#45;&gt;intelligence</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M654.02,-301.1C654.02,-266.24 654.02,-226.09 654.02,-190.28"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="656.65,-190.34 654.02,-182.84 651.4,-190.34 656.65,-190.34"/>
</g>
<!-- sectorpred&#45;&gt;dashboard -->
<g id="edge19" class="edge">
<title>sectorpred&#45;&gt;dashboard</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M781.87,-301.1C834.16,-264.74 894.72,-222.63 947.83,-185.7"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="949.15,-187.98 953.81,-181.54 946.15,-183.67 949.15,-187.98"/>
</g>
<!-- data&#45;&gt;sequences -->
<g id="edge1" class="edge">
<title>data&#45;&gt;sequences</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M1049.02,-2482.73C1049.02,-2438.9 1049.02,-2385.88 1049.02,-2340.74"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="1051.65,-2340.87 1049.02,-2333.37 1046.4,-2340.87 1051.65,-2340.87"/>
<polygon fill="#18191b" fill-opacity="0.627451" stroke="none" points="1049.02,-2399.8 1049.02,-2422.6 1242.57,-2422.6 1242.57,-2399.8 1049.02,-2399.8"/>
<text xml:space="preserve" text-anchor="start" x="1052.02" y="-2405.6" font-family="Arial" font-size="14.00" fill="#c9c9c9">garantit train passe seulement</text>
</g>
<!-- ridge&#45;&gt;heraldpred -->
<g id="edge2" class="edge">
<title>ridge&#45;&gt;heraldpred</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M1404.21,-623.87C1345.39,-581.27 1274.91,-530.23 1215.06,-486.89"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="1216.75,-484.88 1209.14,-482.6 1213.67,-489.13 1216.75,-484.88"/>
<polygon fill="#18191b" fill-opacity="0.627451" stroke="none" points="1318.8,-541 1318.8,-563.8 1493.68,-563.8 1493.68,-541 1318.8,-541"/>
<text xml:space="preserve" text-anchor="start" x="1321.8" y="-546.8" font-family="Arial" font-size="14.00" fill="#c9c9c9">composante mathematique</text>
</g>
<!-- priors&#45;&gt;dynamicgraph -->
<g id="edge3" class="edge">
<title>priors&#45;&gt;dynamicgraph</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M319.81,-1855.21C324.24,-1853.28 328.65,-1851.41 333.02,-1849.6 493.66,-1783.23 683.34,-1724.77 817.85,-1686.5"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="818.43,-1689.06 824.93,-1684.49 817,-1684.01 818.43,-1689.06"/>
</g>
</g>
</svg>
`;case`view_1py4btl`:return`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"
 "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<!-- Generated by graphviz version 14.1.3 (0)
 -->
<!-- Pages: 1 -->
<svg width="999pt" height="810pt"
 viewBox="0.00 0.00 999.00 810.00" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
<g id="graph0" class="graph" transform="scale(1 1) rotate(0) translate(15.05 795.05)">
<!-- priors -->
<g id="node1" class="node">
<title>priors</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="320.04,-780 0,-780 0,-600 320.04,-600 320.04,-780"/>
<text xml:space="preserve" text-anchor="start" x="83.89" y="-682" font-family="Arial" font-size="20.00" fill="#eff6ff">Priors territoriaux</text>
</g>
<!-- dynamicgraph -->
<g id="node2" class="node">
<title>dynamicgraph</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="756.32,-480 427.72,-480 427.72,-300 756.32,-300 756.32,-480"/>
<text xml:space="preserve" text-anchor="start" x="506.97" y="-402" font-family="Arial" font-size="20.00" fill="#eff6ff">Graphe dynamique</text>
<text xml:space="preserve" text-anchor="start" x="447.77" y="-379" font-family="Arial" font-size="15.00" fill="#bfdbfe">Attention QK conditionnee par regime, prior</text>
<text xml:space="preserve" text-anchor="start" x="524.07" y="-361" font-family="Arial" font-size="15.00" fill="#bfdbfe">geo et prior mobilite.</text>
</g>
<!-- local -->
<g id="node3" class="node">
<title>local</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="754.24,-780 429.8,-780 429.8,-600 754.24,-600 754.24,-780"/>
<text xml:space="preserve" text-anchor="start" x="525.87" y="-702" font-family="Arial" font-size="20.00" fill="#eff6ff">Encodeur local</text>
<text xml:space="preserve" text-anchor="start" x="449.86" y="-679" font-family="Arial" font-size="15.00" fill="#bfdbfe">Projection annuelle, encodeur trimestriel et</text>
<text xml:space="preserve" text-anchor="start" x="520.33" y="-661" font-family="Arial" font-size="15.00" fill="#bfdbfe">memoire GRU locale.</text>
</g>
<!-- graphmessages -->
<g id="node4" class="node">
<title>graphmessages</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="538.78,-180 213.26,-180 213.26,0 538.78,0 538.78,-180"/>
<text xml:space="preserve" text-anchor="start" x="280.43" y="-102" font-family="Arial" font-size="20.00" fill="#eff6ff">Messages territoriaux</text>
<text xml:space="preserve" text-anchor="start" x="233.31" y="-79" font-family="Arial" font-size="15.00" fill="#bfdbfe">Aggregation A_t @ embeddings des zones</text>
<text xml:space="preserve" text-anchor="start" x="335.58" y="-61" font-family="Arial" font-size="15.00" fill="#bfdbfe">connectees.</text>
</g>
<!-- internals -->
<g id="node5" class="node">
<title>internals</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="969.04,-180 649,-180 649,0 969.04,0 969.04,-180"/>
<text xml:space="preserve" text-anchor="start" x="736.75" y="-102" font-family="Arial" font-size="20.00" fill="#eff6ff">Internals graphe</text>
<text xml:space="preserve" text-anchor="start" x="677.69" y="-79" font-family="Arial" font-size="15.00" fill="#bfdbfe">dynamic_adj, gate, alpha, gamma_geo,</text>
<text xml:space="preserve" text-anchor="start" x="763.17" y="-61" font-family="Arial" font-size="15.00" fill="#bfdbfe">gamma_mob.</text>
</g>
<!-- priors&#45;&gt;dynamicgraph -->
<g id="edge1" class="edge">
<title>priors&#45;&gt;dynamicgraph</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M288.76,-600.2C341.04,-564.13 401.52,-522.41 454.66,-485.76"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="455.94,-488.06 460.63,-481.64 452.96,-483.74 455.94,-488.06"/>
</g>
<!-- dynamicgraph&#45;&gt;graphmessages -->
<g id="edge3" class="edge">
<title>dynamicgraph&#45;&gt;graphmessages</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M527.8,-300.4C502.13,-264.99 472.49,-224.1 446.26,-187.9"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="448.67,-186.76 442.14,-182.23 444.42,-189.84 448.67,-186.76"/>
</g>
<!-- dynamicgraph&#45;&gt;internals -->
<g id="edge4" class="edge">
<title>dynamicgraph&#45;&gt;internals</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M656.54,-300.4C682.32,-264.99 712.1,-224.1 738.46,-187.9"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="740.3,-189.83 742.59,-182.22 736.06,-186.74 740.3,-189.83"/>
</g>
<!-- local&#45;&gt;dynamicgraph -->
<g id="edge2" class="edge">
<title>local&#45;&gt;dynamicgraph</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M592.02,-600.4C592.02,-565.73 592.02,-525.81 592.02,-490.19"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="594.65,-490.3 592.02,-482.8 589.4,-490.3 594.65,-490.3"/>
</g>
</g>
</svg>
`;case`view_1dglhfw`:return`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"
 "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<!-- Generated by graphviz version 14.1.3 (0)
 -->
<!-- Pages: 1 -->
<svg width="1306pt" height="810pt"
 viewBox="0.00 0.00 1306.00 810.00" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
<g id="graph0" class="graph" transform="scale(1 1) rotate(0) translate(15.05 795.05)">
<g id="clust1" class="cluster">
<title>cluster_intelligence</title>
<polygon fill="#194b9e" stroke="#1b3d88" points="8,-260 8,-541.2 1268,-541.2 1268,-260 8,-260"/>
<text xml:space="preserve" text-anchor="start" x="16" y="-528.3" font-family="Arial" font-weight="bold" font-size="11.00" fill="#bfdbfe" fill-opacity="0.701961">HERALD INTELLIGENCE V0</text>
</g>
<!-- scores -->
<g id="node1" class="node">
<title>scores</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="368.02,-480 47.98,-480 47.98,-300 368.02,-300 368.02,-480"/>
<text xml:space="preserve" text-anchor="start" x="94.04" y="-382" font-family="Arial" font-size="20.00" fill="#eff6ff">Scores opportunite/risque</text>
</g>
<!-- maps -->
<g id="node2" class="node">
<title>maps</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="1228.02,-480 907.98,-480 907.98,-300 1228.02,-300 1228.02,-480"/>
<text xml:space="preserve" text-anchor="start" x="972.96" y="-382" font-family="Arial" font-size="20.00" fill="#eff6ff">Cartes interpretatives</text>
</g>
<!-- alerts -->
<g id="node3" class="node">
<title>alerts</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="798.02,-480 477.98,-480 477.98,-300 798.02,-300 798.02,-480"/>
<text xml:space="preserve" text-anchor="start" x="554.64" y="-382" font-family="Arial" font-size="20.00" fill="#eff6ff">Alertes territoriales</text>
</g>
<!-- herald -->
<g id="node4" class="node">
<title>herald</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="814.18,-780 461.82,-780 461.82,-600 814.18,-600 814.18,-780"/>
<text xml:space="preserve" text-anchor="start" x="597.43" y="-702" font-family="Arial" font-size="20.00" fill="#eff6ff">HERALD</text>
<text xml:space="preserve" text-anchor="start" x="481.87" y="-679" font-family="Arial" font-size="15.00" fill="#bfdbfe">Modele hybride: Ridge AR + correction neurale</text>
<text xml:space="preserve" text-anchor="start" x="602.57" y="-661" font-family="Arial" font-size="15.00" fill="#bfdbfe">territoriale.</text>
</g>
<!-- dashboard -->
<g id="node5" class="node">
<title>dashboard</title>
<polygon fill="#3b82f6" stroke="#2563eb" stroke-width="0" points="1228.02,-180 907.98,-180 907.98,0 1228.02,0 1228.02,-180"/>
<text xml:space="preserve" text-anchor="start" x="941.83" y="-82" font-family="Arial" font-size="20.00" fill="#eff6ff">Dashboard HERALD France</text>
</g>
<!-- scores&#45;&gt;alerts -->
<g id="edge3" class="edge">
<title>scores&#45;&gt;alerts</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M367.99,-390C401.29,-390 434.58,-390 467.88,-390"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="467.68,-392.63 475.18,-390 467.68,-387.38 467.68,-392.63"/>
</g>
<!-- maps&#45;&gt;dashboard -->
<g id="edge4" class="edge">
<title>maps&#45;&gt;dashboard</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M1068,-300.4C1068,-265.73 1068,-225.81 1068,-190.19"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="1070.63,-190.3 1068,-182.8 1065.38,-190.3 1070.63,-190.3"/>
</g>
<!-- herald&#45;&gt;scores -->
<g id="edge1" class="edge">
<title>herald&#45;&gt;scores</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M508.28,-600.06C480.14,-580.7 450.55,-560.29 423,-541.2 397.25,-523.36 369.81,-504.25 343.45,-485.86"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="345.07,-483.79 337.42,-481.65 342.06,-488.09 345.07,-483.79"/>
</g>
<!-- herald&#45;&gt;maps -->
<g id="edge2" class="edge">
<title>herald&#45;&gt;maps</title>
<path fill="none" stroke="#8d8d8d" stroke-width="2" stroke-dasharray="5,2" d="M767.72,-600.06C795.86,-580.7 825.45,-560.29 853,-541.2 878.75,-523.36 906.19,-504.25 932.55,-485.86"/>
<polygon fill="#8d8d8d" stroke="#8d8d8d" stroke-width="2" points="933.94,-488.09 938.58,-481.65 930.93,-483.79 933.94,-488.09"/>
</g>
</g>
</svg>
`;default:throw Error(`Unknown viewId: `+e)}};export{e as dotSource,t as svgSource};