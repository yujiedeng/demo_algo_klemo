ENUM_OPTIONS = {
    "Civilite": ["M", "Mme"],
    "typeUnion": ["Célibataire", "Union Libre", "Pacsé(e)", "Marié(e)"],
    "regimeMatrimonial": ["non applicable","communauté réduite aux acquêts", "communauté universelle", "séparation de biens","participation réduite aux acquêts"]
}

situation_dict = {
    "isCelib": False,
    "perso": {
        "Civilite": "M",
        "Age": 35,
        "nbEnfants": 0,
        "typeUnion": 'Célibataire', #'Célibataire' ou  'Union Libre' ou 'Pacsé(e)' ou 'Marié(e)'
        "regimeMatrimonial": 'aucun' # 'aucun' ou 'communauté réduite aux acquêts' ou 'séparation de biens'
    },
    "cashflow": {
        "revenusActivite": 80000,
        "pensionRetraite": 0,
        "depensesCourantes": 3000,
        "revenusActiviteConjoint": 0,
        "pensionRetraiteConjoint": 0,
        "nbPartFiscal": 1
    }
}
montants_fin = {
    "LivretA" : {
        "LivretA":   [18000],
        "LvretBleu": [0]
    },
    "LDDS" : {
        "LDDS":       [0]},
    "Cash" : {
        "LivretJeune":[0],  
        "LEP":        [0],  
        "PEL":        [0], 
        "CEL":        [0], 
        "CAT":        [0], 
        "Compte":     [0]
    },
    "CTO" : {
        "CTO":       [0], 
        "CTOFonds":  [0],
        "CTODefisc": [0], 
        "CTODette":  [0]
    },
    "PEA" : {
        "PEA":     [0], 
        "PEA-Ass": [0], 
        "PEAPME" : [0]
    },
    "Assurance" : {
        "AV":   [0],
        "Capi": [0]
    },
    "Retraite" : {
        "PER":     [1800], 
        "PERP":    [0],
        "MADELIN": [0],
        "PERO":    [0],
        "ART83":   [0]
    },
    "EpargneSalariale" : {
        "PEE":    [0], 
        "PERECO": [0],
        "PERCO":  [0]
    },
    "Crypto" : {"Crypto" :   [0]},
    "Voiture" : {"Voiture" : [0]},
    "Autres" : {
        "NFT":        [0], 
        "BiensToken": [0], 
        "Art":        [0], 
        "Vins":       [0], 
        "Meubles":    [0], 
        "Autre":      [0]
    }
}
montants_immo = {
    "RP" : {"RP" : [300000]},
    "RS" : {"RS" : [0]},
    "RL":{
        "RL-Nue": [0], 
        "RL-Nue Pinel": [180000],
        "RL-Nue Pinel+": [0],
        "RL-Nue ScellierIntBBC": [0], 
        "RL-Nue ScellierIntNonBBC": [0],
        "RL-Nue Denormandie": [0],  
        "RL-Nue LocAvantage": [0], 
        "RL-Nue Malraux": [0],  
        "RL-Nue MonumentHistorique": [0],
        "RL-Meuble Meublé LT": [0],
        "RL-Meuble Meublé CensiBouvard": [0], 
        "RL-Meuble Meublé TourismeClasse": [0],
        "RL-Meuble Meublé TourismeNonClasse": [0],
        "Achat-NuePropriete": [0],
        "Achat-Viager": [0], 
        "Achat-JouissanceDiffere": [70000]
    },
    "SCPI": {"SCPI-SCI": 2},
    "Foret" : {
        "Foret": [0],
        "GFI/GFF": [10000]
    },
    "Terrain" : {
        "Terrain constructible": [0],
        "Terrain non constructible": [0]
    }
}
montants_emprunt = {
    "PretImmo": {
        "Immo TxFixe":[120000], 
        "Immo TxFixe Différé":[0], 
        "Immo TxFixe InFine":[0], 
        "Immo PVH":[0],
        "Immo TxVar":[0]
    },
    "PretConso" : {
        "Conso" : [0],
        "Avance":[0],
        "Perso Autre":[0]
    },
    "PretAuto" : {"Auto" : [0]},
    "PretPro" : {
        "ProTxFixe":[0], 
        "ProTxFixeDifféré":[0], 
        "ProTxFixeInFine":[0], 
        "ProTxVar":[0],
        "Lease":[0], 
        "CCA":[0]
    }
}
montants_pro = {
    "Ste" : {"Société" : [0]},
    "Sci": {
        "SCI-Famille": [0], 
        "SCI-Pro": [0]
    },
    "Autres" : {
        "Fond Commerce": [0],
        "Bien Exploitation": [0], 
        "CCA": [0], 
        "Brevet": [0]
    }
}
