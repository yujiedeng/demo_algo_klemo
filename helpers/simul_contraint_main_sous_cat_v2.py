import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
from scipy.stats import norm
import random
import copy
import json


# Fonction pour générer une valeur en fonction de plages
def valeur_en_fonction_de_plage(valeur, plages):
    if valeur < 0 or valeur > 1:
        return "Valeur hors de l'intervalle [0, 1]"
    
    plages_triees = sorted(plages.items())
    for borne_sup, texte in plages_triees:
        if valeur < borne_sup:
            return texte
    return plages_triees[-1][1]


def generate_correlated_variable(var1, min_val1, max_val1, min_val2, max_val2):   
    #selon étude corr patrimoine brut et revenu serait de 0.5
    correlation=0.5
    # Normalisation de var1 pour qu'elle soit entre 0 et 1
    normalized_var1 = (var1 - min_val1) / (max_val1 - min_val1)
    
    # Génération d'une variable aléatoire standardisée (moyenne 0, variance 1) corrélée à var1
    #np.random.seed(0)  # si besoin de reproductibilité
    std_var = np.random.normal(0, 1)
    
    # Calcul de la valeur attendue de var2 en fonction de la corrélation et de la valeur normalisée de var1
    expected_normalized_var2 = correlation * normalized_var1
    
    # Ajout de la composante aléatoire non corrélée pour obtenir une variance totale de 1
    var2_normalized = expected_normalized_var2 + std_var * np.sqrt(1 - correlation**2)
    
    # Ajustement de la plage pour var2 en repassant par la fonction de répartition de la loi centré réduite
    var2 = norm.cdf(var2_normalized) * (max_val2 - min_val2) + min_val2
    
    return var2

def list_item(a):
    resultat = []
    for libelle, count in a.items():
        resultat.extend([libelle] * count)
    return resultat

def list_type_manual(nb, TYPES):
    list_type = {f"list{type_}": list_item(nb[type_]) for type_ in TYPES}
    return list_type

def list_nb_manual(nb, list_type, TYPES):
    list_nb={f"nb{type_}": len(list_type[f"list{type_}"]) for type_ in TYPES}
    return list_nb

def list_nb_auto(plage_nb, TYPES):
    list_nb={f"nb{type_}": valeur_en_fonction_de_plage(random.random(), plage_nb[f"nb{type_}"]) for type_ in TYPES}
    return list_nb

def list_type_auto(list_nb, plage_type, TYPES):
    """Génère aléatoirement les types pour chaque catégorie, selon les distributions."""
    list_type = {}
    for type_ in TYPES:
        nb_type = list_nb[f"nb{type_}"]
        # Génère la liste des types pour chaque produit
        if nb_type == 0:
            list_type[f"list{type_}"] = []
        else:
            list_type[f"list{type_}"] = [valeur_en_fonction_de_plage(random.random(), plage_type[f"type{type_}"]) for i in range(nb_type)]
    return list_type


################################
##### SITUATION PERSONNELLE ####
################################

# Définition du type structuré
perso_dtype = np.dtype([
    ('Civilite', 'U3'),  
    ('Age', 'int32'),   
    ('nbEnfants', 'int32'),  
    ('typeUnion', 'U30'),  
    ('regimeMatrimonial', 'U30') 
])

# Définition des plages pour chaque champ
perso_plages={
    "civilite_plages" : {0.484: 'M', 1.0: 'Mme'},
    "nb_enfants_plages": {0.25:0, 0.52: 1, 0.84: 2, 0.96: 3, 1.0: 4},
    "age_enfants":{1:28, 2: 31, 3:33, 4:35},
    "type_union_plages": {
        0.23: 'Célibataire',
        0.30: 'Divorcé(e)/FinDePacs',
        0.38: 'Veuf(ve)',
        0.50: 'Union Libre',
        0.54: 'Pacsé(e)',
        1.0: 'Marié(e)'
    },
    "regime_matrimonial_plages" : {0.85: 'communauté réduite aux acquêts', 1.0: 'séparation de biens'}
}

# Génération des valeurs aléatoires
def situation_perso_random(perso_plages):
    civilite = valeur_en_fonction_de_plage(random.random(), perso_plages["civilite_plages"])
    age = random.randint(25, 70)
    nb_enfants = valeur_en_fonction_de_plage(random.random(), perso_plages["nb_enfants_plages"])
    #ajuste nombre enfants à age
    if age<perso_plages["age_enfants"][1]:
        nb_enfants=0
    elif age<perso_plages["age_enfants"][2]:
        nb_enfants=min(nb_enfants,1)
    elif age<perso_plages["age_enfants"][3]:
        nb_enfants=min(nb_enfants,2)
    elif age<perso_plages["age_enfants"][4]:
        nb_enfants=min(nb_enfants,3)
    
    type_union = valeur_en_fonction_de_plage(random.random(), perso_plages["type_union_plages"])
    if type_union == 'Marié(e)':
        regime_matrimonial = valeur_en_fonction_de_plage(random.random(), perso_plages["regime_matrimonial_plages"])
    else:
        regime_matrimonial = 'non applicable'
    
    # Création du tableau structuré
    random_perso = [(civilite, age, nb_enfants, type_union, regime_matrimonial)]

    return(random_perso)

def perso_from_dict(perso_dict):
    return np.array([(
        perso_dict.get("Civilite", "M"),
        perso_dict.get("Age", 40),
        perso_dict.get("nbEnfants", 0),
        perso_dict.get("typeUnion", "Célibataire"),
        perso_dict.get("regimeMatrimonial", "séparation de biens")
    )], dtype=perso_dtype)

def cashflow_from_dict(cashflow_dict):
    return np.array([(
        cashflow_dict.get("revenusActivite", 0),
        cashflow_dict.get("pensionRetraite", 0),
        cashflow_dict.get("depensesCourantes", 0),
        cashflow_dict.get("revenusActiviteConjoint", 0),
        cashflow_dict.get("pensionRetraiteConjoint", 0),
        cashflow_dict.get("nbPartFiscal", 1)
    )], dtype=cashflow_dtype)


################################
##### CASHFLOW ####
################################

# Définition du type structuré
cashflow_dtype = np.dtype([
    ('revenusActivite', 'float64'), 
    ('pensionRetraite', 'float64'),   
    ('depensesCourantes', 'float64'),      
    ('revenusActiviteConjoint', 'float64'),
    ('pensionRetraiteConjoint', 'float64'),      
    ('nbPartFiscal', 'float64')
])

#Définition des plages de tirage aléatoire
cashflow_plages={
    "revenusActivite":{"min": 60000, "max":1000000},
    "pensionRetraite":{"min": 20000, "max":300000},
    "depensesCourantes":{"min": 3000, "max":8000},
    "coefRepartRevenu":{"min": 20, "max":80},
    "age_enfants":{1:28, 2: 31, 3:33, 4:35}
}
									
# Génération des valeurs aléatoires
def cashflow_random(cashflow_plages, isCelib, rand_perso):

    # Calculer l'âge de chaque enfant
    age_mere = rand_perso['Age'][0]  # Âge de la mère
    nb_enfants = rand_perso['nbEnfants'][0]  # Nombre d'enfants    
    nb_enfants_moins_25=0
    if nb_enfants>0 :
        # Calculer les âges des enfants
        ages_enfants = [age_mere - cashflow_plages['age_enfants'][i] for i in range(1, nb_enfants + 1)]
        # détermine le nombre de part fisccal à partir de l'age des enfants
        nb_enfants_moins_25 = sum(age < 25 for age in ages_enfants)
    nb_part_fiscale = 1+ (0 if isCelib else 1) + 0.5 * min(nb_enfants_moins_25,2) + max(nb_enfants_moins_25-2,0)
    #coef repart revenu
    coefRepartRevenu =1 if isCelib else random.randint(cashflow_plages["coefRepartRevenu"]["min"], cashflow_plages["coefRepartRevenu"]["max"])/100
    # Liste pour stocker les emprunts
    revenusActivite = 0 if age_mere>= 64 else coefRepartRevenu * random.randint(cashflow_plages["revenusActivite"]["min"], cashflow_plages["revenusActivite"]["max"])
    pensionRetraite = 0 if age_mere<64 else coefRepartRevenu * random.randint(cashflow_plages["pensionRetraite"]["min"], cashflow_plages["pensionRetraite"]["max"])
    depensesCourantes = random.randint(cashflow_plages["depensesCourantes"]["min"], cashflow_plages["depensesCourantes"]["max"])
    revenusActiviteConjoint = revenusActivite*(1-coefRepartRevenu)/coefRepartRevenu 
    pensionRetraiteConjoint = pensionRetraite*(1-coefRepartRevenu)/coefRepartRevenu 
    nbPartFiscal = nb_part_fiscale

    cashflow = [(revenusActivite, pensionRetraite, depensesCourantes, revenusActiviteConjoint, pensionRetraiteConjoint, nbPartFiscal)]
    return cashflow 

################################
##### FIN ####
################################
# Définition du type structuré
fin_dtype = np.dtype([
    ('typeProd', 'U50'),  
    ('value', 'float64'), 
    ('pctDetention', 'float64'),      
    ('pctDetentionConjoint', 'float64')    
])

#Définition des plages de tirage aléatoire pour les nombres et types
fin_plage_nb={
    "nbLivretA" : {0.15: 0, 1.0: 1},
    "nbLDDS" : {0.53: 0, 1.0: 1},
    "nbCash" : {0.44: 0, 0.84 :1, 0.97:2, 1.0:3},
    "nbCTO" : {0.90: 0, 1.0: 1},
    "nbPEA" : {0.85: 0, 1.0:2},
    "nbAssurance" : {0.59: 0, 1.0: 1},
    "nbRetraite" : {0.83: 0, 1.0: 1},
    "nbEpargneSalariale" : {0.85: 0, 1.0: 1},
    "nbCrypto" : {0.85: 0, 1.0: 1},
    "nbVoiture" : {0.14: 0, 0.84: 1, 1.0: 2},
    "nbAutres" : {0.99: 0, 1.0: 1},
}
fin_plage_type={
    "typeLivretA":{0.9:"LivretA",1.0:"LvretBleu"},
    "typeLDDS":{1:"LDDS"},
    "typeCash":{0.29:"LivretJeune",  0.36:"LEP",  0.57:"PEL", 0.71:"CEL", 0.86:"CAT", 1.0:"Compte"},
    "typeCTO":{0.5:"CTO", 0.8: "CTO Fonds", 0.95:"CTODefisc", 1.0:"CTODette"},
    "typePEA":{0.9:"PEA", 0.92:"PEA-Ass", 1.0:"PEAPME"},
    "typeAssurance":{0.9:"AV", 1.0:"CAPI"},
    "typeRetraite":{0.6:"PER", 0.7:"PERP",0.8:"MADELIN",0.9:"PERO",1.0:"ART83"},
    "typeEpargneSalariale":{0.4:"PEE", 0.7:"PERECO",1.0:"PERCO"},
    "typeCrypto":{1:"Crypto"},
    "typeVoiture":{1:"Voiture"},
    "typeAutres":{0.1:"NFT", 0.15:"BiensToken", 0.3:"Art", 0.6:"Vins", 0.9:"Meubles", 1.0:"Autre"}
}
#Définition des plages de tirage aléatoire
fin_plage_montant={
    "montantLivretA":{"min": 1000, "max":22950},
    "montantLDDS":{"min": 1000, "max":12000},
    "montantCash":{"min": 1000, "max":20000},
    "montantCTO":{"min": 5000, "max":20000},
    "montantPEA":{"min": 5000, "max":40000},
    "montantAssurance":{"min": 10000, "max":30000},
    "montantRetraite":{"min": 1000, "max":10000},
    "montantEpargneSalariale":{"min": 5000, "max":8000},
    "montantCrypto":{"min": 1000, "max":10000},
    "montantVoiture":{"min": 5000, "max":30000},
    "montantAutres":{"min": 1000, "max":10000},
}


# Génération des valeurs aléatoires
def fin_random(mode, nb_fin=None, isCelib=True, cashflow_plages=None, rand_cashflow=None):
    TYPES = ["LivretA", "LDDS", "Cash", "CTO", "PEA", "Assurance",
        "Retraite", "EpargneSalariale", "Crypto", "Voiture", "Autres"]
    if mode == "manual":
        list_type = list_type_manual(nb_fin, TYPES)
        list_nb = list_nb_manual(nb_fin, list_type, TYPES)
    else: 
        #mode = "auto":
        list_nb = list_nb_auto(fin_plage_nb, TYPES)
        list_type = list_type_auto(list_nb, fin_plage_type, TYPES)

    fin = []
    pct1 = 1 if isCelib else 0.5
    pct2 = 0 if isCelib else 0.5
    var1 = rand_cashflow['revenusActivite'][0]
    min_val1 = cashflow_plages['revenusActivite']['min']
    max_val1 = cashflow_plages['revenusActivite']['max']

    for type_ in TYPES:
        nb = list_nb[f"nb{type_}"]
        liste_types = list_type[f"list{type_}"]
        plage_montant = fin_plage_montant[f"montant{type_}"]
        for i in range(nb):
            montantFin = generate_correlated_variable(
                var1, min_val1, max_val1,
                min_val2=plage_montant["min"], max_val2=plage_montant["max"]
            )
            typeFin = liste_types[i] 
            fin.append((typeFin, montantFin, pct1, pct2))
            
    return fin

def fin_from_amounts(montants_fin, isCelib=True):
    fin = []
    pct1 = 1 if isCelib else 0.5
    pct2 = 0 if isCelib else 0.5

    for type_, sous_dict in montants_fin.items():
        for sous_type, values in sous_dict.items():
            if isinstance(values, list) and len(values) > 0:
                for v in values:
                    if v and v > 0:
                        fin.append((sous_type, v, pct1, pct2))
    return fin

################################
##### IMMO ####
################################
# Définition du type structuré
immo_dtype = np.dtype([
    ('typeImmo', 'U50'),  
    ('dispositif', 'U50'),  
    ('value', 'float64'), 
    ('pctDetention', 'float64'),      
    ('pctDetentionConjoint', 'float64')
])

immo_plage_montant = {
    "montantRP": {"min": 100000, "max":500000},
    "montantRS": {"min": 50000, "max":300000},
    "montantRL": {"min": 80000, "max":300000},
    "montantSCPI": {"min": 1000, "max":50000},
    "montantForet": {"min": 5000, "max":30000},
    "montantTerrain": {"min": 5000, "max":100000}
}
immo_plage_nb = {
    "nbRP" : {0.42: 0, 1.0: 1},
    "nbRS" : {0.90: 0, 1.0: 1},
    "nbRL-Nue" : {0.81: 0, 0.95: 1, 1.0:2},
    "nbRL" : {0.81: 0, 0.95: 1, 1.0:2},
    "nbSCPI" : {0.95: 0, 1.0: 1},
    "nbForet" : {0.95: 0, 1.0: 1},
    "nbTerrain" : {0.99: 0, 1.0: 1}
}
    
immo_plage_type = {
    "typeRP": {1:"RP"},
    "typeRS": {1:"RS"},
    "typeRL": {
        0.70: "RL-Nue",
        0.90: "RL-Meuble",
        0.95: "Achat-NuePropriete", 
        0.98: "Achat-Viager", 
        1.00: "Achat-JouissanceDiffere"},
    "typeSCPI": {1: "SCPI-SCI"},
    "typeForet": {0.95: "Foret", 1.0: "GFI/GFF"},
    "typeTerrain": {0.5: "Terrain constructible", 1.0: "Terrain non constructible"}    
}

immo_dispositif={    
    "RL-Nue": {
        0.40: "aucun", 
        0.65: "Pinel",
        0.67: "Pinel+",
        0.74: "ScellierIntBBC",  
        0.81: "ScellierIntNonBBC",  
        0.87: "Denormandie",  
        0.94: "LocAvantage",  
        0.97: "Malraux",  
        1.00: "MonumentHistorique"  
    },
    "RL-Meuble": {
        0.14: "aucun",  
        0.40: "CensiBouvard",  
        0.70: "TourismeClasse",  
        1.00: "TourismeNonClasse"
    }
}

immo_dispositif_manual={
    "RL-Nue": "aucun", 
    "RL-Nue Pinel": "Pinel",
    "RL-Nue Pinel+": "Pinel+",
    "RL-Nue ScellierIntBBC": "ScellierIntBBC", 
    "RL-Nue ScellierIntNonBBC": "ScellierIntNonBBC",
    "RL-Nue Denormandie": "Denormandie",  
    "RL-Nue LocAvantage": "LocAvantage", 
    "RL-Nue Malraux": "Malraux",  
    "RL-Nue MonumentHistorique": "MonumentHistorique",
    "RL-Meuble Meublé LT": "Meublé LT",
    "RL-Meuble Meublé CensiBouvard": "Meublé CensiBouvard", 
    "RL-Meuble Meublé TourismeClasse": "Meublé TourismeClasse",
    "RL-Meuble Meublé TourismeNonClasse": "Meublé TourismeNonClasse",
}

def immo_type_manual(type_immo):
    if type_immo in ["RL-Nue", "RL-Nue Pinel", "RL-Nue Pinel+", "RL-Nue ScellierIntBBC", "RL-Nue ScellierIntNonBBC", 
        "RL-Nue Denormandie",  "RL-Nue LocAvantage", "RL-Nue Malraux", "RL-Nue MonumentHistorique"]:
        return("RL-Nue")
    elif type_immo in ["RL-Meuble Meublé LT", "RL-Meuble Meublé CensiBouvard", "RL-Meuble Meublé TourismeClasse", 
    "RL-Meuble Meublé TourismeNonClasse"]:
        return("RL-Meuble")
    else:
        return(type_immo)

# Génération des valeurs aléatoires
def immo_random(mode, nb_immo=None, isCelib=True, cashflow_plages=None, rand_cashflow=None):
    TYPES = ["RP", "RS", "RL", "SCPI", "Foret", "Terrain"]
    if mode == "manual":
        list_type_ext = list_type_manual(nb_immo, TYPES)
        list_type = {
            key: [immo_type_manual(item) for item in sublist]
            for key, sublist in list_type_ext.items()
        }
        list_nb = list_nb_manual(nb_immo, list_type, TYPES)
    else: 
        #mode = "auto":
        list_nb = list_nb_auto(immo_plage_nb, TYPES)
        list_type = list_type_auto(list_nb, immo_plage_type, TYPES)

    immo = []
    pct1 = 1 if isCelib else 0.5
    pct2 = 0 if isCelib else 0.5
    var1 = rand_cashflow['revenusActivite'][0]
    min_val1 = cashflow_plages['revenusActivite']['min']
    max_val1 = cashflow_plages['revenusActivite']['max']

    for type_ in TYPES:
        nb_type = list_nb[f"nb{type_}"]
        liste_types = list_type[f"list{type_}"]
        liste_types_ext = list_type_ext[f"list{type_}"]
        plage_montant = immo_plage_montant[f"montant{type_}"]
        for i in range(nb_type):
            montantImmo = generate_correlated_variable(
                var1, min_val1, max_val1,
                min_val2=plage_montant["min"], max_val2=plage_montant["max"]
            )
            typeImmo = liste_types[i]
            if typeImmo in ["RL-Nue","RL-Meuble"]:
                if mode=="manual":
                    dispositif = immo_dispositif_manual[f"{liste_types_ext[i]}"]
                else:
                    dispositif = valeur_en_fonction_de_plage(random.random(), immo_dispositif[f"{typeImmo}"])
            else:
                dispositif="aucun"
            immo.append((typeImmo, dispositif, montantImmo, pct1, pct2))
            
    return immo

def immo_from_amounts(montants_immo, isCelib=True):
    immo = []
    pct1 = 1 if isCelib else 0.5
    pct2 = 0 if isCelib else 0.5

    for type_, sous_dict in montants_immo.items():
        for sous_type, values in sous_dict.items():
            if isinstance(values, list) and len(values)>0:
                for v in values:
                    if v and v > 0:
                        if type_ == "RL":
                            typeImmo = immo_type_manual(sous_type)
                            dispositif = immo_dispositif_manual.get(sous_type, "aucun")
                        else:
                            typeImmo = sous_type
                            dispositif = "aucun"
                        immo.append((typeImmo, dispositif, v, pct1, pct2))
    return immo


################################
##### PRO ####
################################
# Définition du type structuré
pro_dtype = np.dtype([
    ('typeBienPro', 'U50'),  
    ('value', 'float64'), 
    ('pctDetention', 'float64'),      
    ('pctDetentionConjoint', 'float64')
])

pro_plage_montant={
    "montantSte":{"min": 2000, "max":300000},
    "montantSci":{"min": 50000, "max":500000},
    "montantAutres":{"min": 50000, "max":500000}
}

pro_plage_nb={
    "nbSte" : {0.95: 0, 1.0: 1},
    "nbSci" : {0.98: 0, 1.0: 1},
    "nbAutres" : {0.95: 0, 1.0:1},
}

pro_plage_type={
    "typeSte":{	1: "Société"},
    "typeSci":{	0.7: "SCI-Famille", 1.0: "SCI-Pro"},
    "typeAutre":{0.50:"Fonds Commerce", 0.80:"Bien Exploitation",0.95:"CCA",  1.0:"Brevet"}
}
									
# Génération des valeurs aléatoires
def pro_random(mode, nb_pro=None, isCelib=True, cashflow_plages=None, rand_cashflow=None):
    TYPES = ["Ste", "Sci", "Autres"]
    if mode == "manual":
        list_type = list_type_manual(nb_pro, TYPES)
        list_nb = list_nb_manual(nb_pro, list_type, TYPES)
    else: 
        #mode = "auto":
        list_nb = list_nb_auto(pro_plage_nb, TYPES)
        list_type = list_type_auto(list_nb, pro_plage_type, TYPES)

    pro = []
    pct1 = 1 if isCelib else 0.5
    pct2 = 0 if isCelib else 0.5
    var1 = rand_cashflow['revenusActivite'][0]
    min_val1 = cashflow_plages['revenusActivite']['min']
    max_val1 = cashflow_plages['revenusActivite']['max']

    for type_ in TYPES:
        nb_type = list_nb[f"nb{type_}"]
        liste_types = list_type[f"list{type_}"]
        plage_montant = pro_plage_montant[f"montant{type_}"]
        for i in range(nb_type):
            montantPro = generate_correlated_variable(
                var1, min_val1, max_val1,
                min_val2=plage_montant["min"], max_val2=plage_montant["max"]
            )
            typeBienPro = liste_types[i]
            pro.append((typeBienPro, montantPro, pct1, pct2))
            
    return pro

def pro_from_amounts(montants_pro, isCelib=True):
    pro = []
    pct1 = 1 if isCelib else 0.5
    pct2 = 0 if isCelib else 0.5

    for type_, sous_dict in montants_pro.items():
        for sous_type, values in sous_dict.items():
            if isinstance(values, list) and len(values)>0:
                for v in values:
                    if v and v > 0:
                        pro.append((sous_type, v, pct1, pct2))
    return pro

################################
##### EMPRUNT ####
################################
# Définition du type structuré
emprunt_dtype = np.dtype([
    ('typeEmprunt', 'U50'),  
    ('dtFin', 'datetime64[D]'),
    ('montantRestantDu', 'float64'), 
    ('pctEmprunt', 'float64'),      
    ('pctEmpruntConjoint', 'float64'),
    ('ImmoLie', 'int32')
])

emprunt_plage_montant= {
    "montantPretImmo":{"min": 50000, "max":500000},
    "montantPretConso":{"min": 5000, "max":20000},
    "montantPretAuto":{"min": 5000, "max":20000},
    "montantPretPro":{"min": 10000, "max":300000},
    "montantPretAutre":{"min": 10000, "max":20000}
}
emprunt_plage_nb={
    "nbPretImmo" : {0.18: 0, 0.86:1, 0.96:2, 1.0: 3},
    "nbPretConso" : {0.8: 0, 1.0: 1},
    "nbPretAuto" : {0.8: 0, 1.0: 1},
    "nbPretPro" : {0.88: 0, 1.0: 1},
    "nbPretAutre" : {0.9: 0, 1.0: 1}
}
emprunt_plage_type={
    "typePretImmo":{0.81:"Immo TxFixe", 0.92:"Immo TxFixe Différé",  0.95:"Immo TxFixe InFine", 0.99:"Immo TxVar", 1:"Immo PVH"},
    "typePretConso":{0.95:"Conso",1:"Avance"},
    "typePretAuto":{1:"Auto"},
    "typePretPro":{0.5:"Pro TxFixe", 0.7:"Pro TxFixe Différé", 0.8:"Pro TxFixe InFine", 0.90:"Pro TxVar",0.95:"Lease", 1.0:"CCA"}
}

# Génération des emprunts de manière aléatoire
def emprunt_random(mode, rand_immo, nb_emprunt=None, isCelib=True, cashflow_plages=None, rand_cashflow=None):
    current_date = datetime.now()
    TYPES = ["PretImmo", "PretConso", "PretAuto","PretPro"]
    if mode == "manual":
        list_type = list_type_manual(nb_emprunt, TYPES)
        list_nb = list_nb_manual(nb_emprunt, list_type, TYPES)
    else: 
        #mode = "auto":
        list_nb = list_nb_auto(emprunt_plage_nb, TYPES)
        list_type = list_type_auto(list_nb, emprunt_plage_type, TYPES)

    emprunt = []
    pct1 = 1 if isCelib else 0.5
    pct2 = 0 if isCelib else 0.5
    var1 = rand_cashflow['revenusActivite'][0]
    min_val1 = cashflow_plages['revenusActivite']['min']
    max_val1 = cashflow_plages['revenusActivite']['max']

    for type_ in TYPES:
        nb_type = list_nb[f"nb{type_}"]
        liste_types = list_type[f"list{type_}"]
        plage_montant = emprunt_plage_montant[f"montant{type_}"]
        #Affecte aléatoirement les prêts immobilier
        if type_=="PretImmo":
            # Simuler les prêts immobiliers
            if rand_immo.size > 0:
                selected_immo = random.sample(range(len(rand_immo)), nb_type)
            else:
                selected_immo =[]
        for i in range(nb_type):
            typePret = liste_types[i]
            pretLie = -1
            if rand_immo.size > 0:
                pretLie = selected_immo[i] if type_=="PretImmo" else -1
                montantPret = min( 
                        generate_correlated_variable(
                            var1, min_val1, max_val1, 
                            min_val2=plage_montant["min"], max_val2=plage_montant["max"]
                            ), 
                        rand_immo['value'][selected_immo[i]]
                    )
            else:
                montantPret = generate_correlated_variable(
                        var1, min_val1, max_val1, 
                        min_val2=plage_montant["min"], max_val2=plage_montant["max"]
                    )
            if type_=="PretImmo":
                dtFin = (current_date + relativedelta(years= random.randint(2, 25))).date()
            elif type_=="PretPro":
                dtFin = (current_date + relativedelta(years= random.randint(1, 10))).date()
            else:
                if typePret=="Immo PVH":
                    dtFin = (current_date + relativedelta(years= 90)).date()
                else: 
                    dtFin = (current_date + relativedelta(years= random.randint(1, 5))).date()
            emprunt.append((typePret, dtFin, montantPret, pct1, pct2, pretLie))
            
    return emprunt

def emprunt_from_amounts(montants_emprunt, rand_immo, isCelib=True):
    emprunt = []
    current_date = datetime.now()
    pct1 = 1 if isCelib else 0.5
    pct2 = 0 if isCelib else 0.5

    for type_, sous_dict in montants_emprunt.items():
        for sous_type, values in sous_dict.items():
            if isinstance(values, list) and len(values)>0:
                for v in values:
                    if v and v > 0:
                        pretLie = -1
                        if type_ == "PretImmo" and rand_immo.size > 0:
                            pretLie = 0
                            v = min(v, rand_immo['value'][pretLie])

                        if type_ == "PretImmo":
                            if sous_type == "Immo PVH":
                                dtFin = (current_date + relativedelta(years=90)).date()
                            else:
                                dtFin = (current_date + relativedelta(years=20)).date()
                        elif type_ == "PretPro":
                            dtFin = (current_date + relativedelta(years=7)).date()
                        else:
                            dtFin = (current_date + relativedelta(years=5)).date()

                        emprunt.append((sous_type, dtFin, v, pct1, pct2, pretLie))
    return emprunt


def simul_obj_client(mode, nb_fin=None, nb_immo=None, nb_pro=None, nb_emprunt=None):
    # Exemple d'utilisation
    isCelib = valeur_en_fonction_de_plage(random.random(), {0.30: True, 1.0: False})
    #perso
    perso=situation_perso_random(perso_plages)
    rand_perso = np.array(perso,dtype=perso_dtype)
    #cashflow
    cashflow=cashflow_random(cashflow_plages, isCelib, rand_perso)
    rand_cashflow = np.array(cashflow,dtype=cashflow_dtype)
    #fin
    fin = fin_random(mode, nb_fin, isCelib, cashflow_plages, rand_cashflow)
    rand_fin = np.array(fin,dtype=fin_dtype)
    #immo
    immo=immo_random(mode, nb_immo, isCelib, cashflow_plages, rand_cashflow)
    rand_immo = np.array(immo,dtype=immo_dtype)
    #pro
    pro = pro_random(mode, nb_pro, isCelib, cashflow_plages, rand_cashflow)
    rand_pro = np.array(pro,dtype=pro_dtype)
    #emprunt
    emprunt = emprunt_random(mode, rand_immo, nb_emprunt, isCelib, cashflow_plages, rand_cashflow)
    rand_emprunt = np.array(emprunt,dtype=emprunt_dtype)
    
    pat={
        'perso': rand_perso,
        'cashflow': rand_cashflow,
        'fin': rand_fin,
        'immo': rand_immo,
        'pro': rand_pro,
        'emprunt':rand_emprunt
    }
    return(pat)

def simul_obj_client_from_dicts(situation_dict, montants_fin, montants_immo, montants_pro, montants_emprunt):
    # isCelib
    isCelib = situation_dict.get("isCelib", True)

    # perso
    rand_perso = perso_from_dict(situation_dict["perso"])

    # cashflow
    rand_cashflow = cashflow_from_dict(situation_dict["cashflow"])

    # fin
    fin = fin_from_amounts(montants_fin, isCelib)
    rand_fin = np.array(fin, dtype=fin_dtype) if fin else np.array([], dtype=fin_dtype)

    # immo
    immo = immo_from_amounts(montants_immo, isCelib)
    rand_immo = np.array(immo, dtype=immo_dtype) if immo else np.array([], dtype=immo_dtype)

    # pro
    pro = pro_from_amounts(montants_pro, isCelib)
    rand_pro = np.array(pro, dtype=pro_dtype) if pro else np.array([], dtype=pro_dtype)

    # emprunt
    emprunt = emprunt_from_amounts(montants_emprunt, rand_immo, isCelib)
    rand_emprunt = np.array(emprunt, dtype=emprunt_dtype) if emprunt else np.array([], dtype=emprunt_dtype)

    return {
        'perso': rand_perso,
        'cashflow': rand_cashflow,
        'fin': rand_fin,
        'immo': rand_immo,
        'pro': rand_pro,
        'emprunt': rand_emprunt
    }


def import_json(JSON_file_name: str):
    with open(JSON_file_name, 'r') as file:
        return json.load(file)
    
def classifFin(st):
    mapping = {
        "LivretA": "1-Epargne de précaution",
        "LivretBleu": "1-Epargne de précaution",
        "LDDS": "1-Epargne de précaution",
        "LivretJeune": "1-Epargne de précaution",
        "LEP": "1-Epargne de précaution",
        "LEE": "1-Epargne de précaution",
        "PEL": "1-Epargne de précaution",
        "CEL": "1-Epargne de précaution",
        "CAT": "1-Epargne de précaution",
        "Compte": "1-Epargne de précaution",
        "PEA": "2-Epargne MT/ LT",
        "PEAPME": "2-Epargne MT/ LT",
        "PEA-ass": "2-Epargne MT/ LT",
        "AV": "2-Epargne MT/ LT",
        "Capi": "2-Epargne MT/ LT",
        "CTO": "2-Epargne MT/ LT",
        "CTOFonds":"2-Epargne MT/ LT",
        "CTODette":"2-Epargne MT/ LT",
        "CTODefisc":"2-Epargne MT/ LT",
        "Crypto":"2-Epargne MT/ LT",
        "PEE": "2-Epargne MT/ LT",
        "PEI": "2-Epargne MT/ LT",
        "PER": "3-Epargne Retraite",
        "PERP": "3-Epargne Retraite",
        "PREFON": "3-Epargne Retraite",
        "MADELIN": "3-Epargne Retraite",
        "PERO": "3-Epargne Retraite",
        "ART83": "3-Epargne Retraite",
        "PERECO": "3-Epargne Retraite",
        "PERCO": "3-Epargne Retraite"
    }
    if st is not None:
        return mapping.get(st, "4-Autre")
    return "4-Autre"

def classifImmo(st):
    mapping = {
        "RP": "1-Résidence principale",
        "RS": "2-Résidence secondaire",
        "RL-Nue": "3-Résidence locative nue",
        "RL-Meuble": "4-Résidence locative meublée",
        "Achat-NuePropriete": "5-Achat nue-propriété/ viager",
        "Achat-Viager": "5-Achat nue-propriété/ viager",
        "Achat-JouissanceDiffere": "5-Achat nue-propriété/ viager",
        "SCPI-SCI": "6-SCPI/SCI",
        "Terrain": "7-Terrain",
        "Foret": "8-Forêt",
        "GFI/GFF": "8-Forêt"
    }
    if st is not None:
        return mapping.get(st, "9-Autre")
    return "9-Autre"

def classifEmprunt(st):
    mapping = {
        "Immo": "1-Emprunt immobilier",
        "Immo TxFixe": "1-Emprunt immobilier",
        "Immo TxFixe InFine": "1-Emprunt immobilier",
        "Immo TxVar": "1-Emprunt immobilier",
        "Immo PVH": "1-Emprunt immobilier",
        "Auto": "2-Emprunt auto",
        "Conso": "3-Emprunt conso",
        "Pro TxFixe": "4-Emprunt pro",
        "Pro TxFixe InFine": "4-Emprunt pro",
        "Pro TxVar": "4-Emprunt pro",
        "CCA": "4-Emprunt pro"
    }
    if st is not None:
        return mapping.get(st, "5-Autre")
    return "5-Autre"

def classifPro(st):
    mapping = {
        "Société": "1-Société",
        "SCI": "2-SCI",
        "Fond Commerce": "3-Fond de commerce"
    }
    if st is not None:
        return mapping.get(st, "4-Autre")
    return "4-Autre"

def impute_json(input_vide, p1):
    #### impute client part ####
    client_rd   = p1["perso"]
    input_vide["Client"]["PatClientDetail"][0]={**copy.deepcopy(input_vide["Client"]["PatClientDetail"][0]),  # Copie propre du dictionnaire de base
        "civilite":          client_rd[0]["Civilite"].item(),
        "dateNaissance":     f'{2025-client_rd[0]["Age"].item()}-01-01',  # Convertit np.float64 en float standard Python
        "nbEnfants":         client_rd[0]["nbEnfants"].item(),
        "typeUnion":         client_rd[0]["typeUnion"].item()}
    print("DONE imputing client part")

    #### impute cashflow part ####
    cashflow_rd         = p1["cashflow"]
    cashflow_result     = {key: cashflow_rd[0][key].item() for key in ["revenusActivite", "pensionRetraite","depensesCourantes", "revenusActiviteConjoint","pensionRetraiteConjoint","nbPartFiscal"]}
    cashflow_result["depensesCourantes"] = cashflow_result["depensesCourantes"]
    input_vide["Cashflow"]["PatCashflowDetail"][0].update(cashflow_result)
    print("DONE imputing cashflow part")

    #### impute fin part ####
    fin_rd                            = p1["fin"]
    if len(fin_rd) == 0 :
        print("fin part vide")
        input_vide["Fin"]["PatFinDetail"]=[]
    else:
        input_vide["Fin"]["PatFinDetail"] = [
        {**copy.deepcopy(input_vide["Fin"]["PatFinDetail"][0]),  # Copie propre du dictionnaire de base
            "typeProd":              row["typeProd"].item(),
            "catProd":               classifFin(row["typeProd"].item()),
            "value":                 row["value"].item(),  # Convertit np.float64 en float standard Python
            "quotePart":             row["value"].item(),  
            "pctDetention":          row["pctDetention"].item(),
            "pctDetentionConjoint":  row["pctDetentionConjoint"].item(),
            "dateValue":             datetime.today().strftime("%Y-%m-%d")}
        for row in fin_rd]
        print("DONE imputing fin part")

    #### impute Immo part ####
    immo_rd                            = p1["immo"]
    if len(immo_rd) == 0 :
        print("Immo part vide")
        input_vide["Immo"]["PatImmoDetail"]=[]
    else:
        input_vide["Immo"]["PatImmoDetail"] = [
            {**copy.deepcopy(input_vide["Immo"]["PatImmoDetail"][0]),  # Copie propre du dictionnaire de base
            "typeImmo":             row["typeImmo"].item(),
            "catImmo":              classifImmo(row["typeImmo"].item()),
            "dispositif":           row["dispositif"].item(),  # Convertit np.float64 en float standard Python
            "value":                row["value"].item(),
            "quotePart":            row["value"].item(),
            "pctDetention":           row["pctDetention"].item(),     
            "pctDetentionConjoint":   row["pctDetentionConjoint"].item(),
            "dateValue":            datetime.today().strftime("%Y-%m-%d")}
            for row in immo_rd]
        print("DONE Impute Immo part vide")
    #### impute Pro part ####
    pro_rd                            = p1["pro"]
    if len(pro_rd) == 0 :
        print("pro vide tout va bien")
        input_vide["Pro"]["PatProDetail"]=[]
    else:
        input_vide["Pro"]["PatProDetail"] = [
            {**copy.deepcopy(input_vide["Pro"]["PatProDetail"][0]),  # Copie propre du dictionnaire de base
            "typeBienPro":          row["typeBienPro"].item(),
            "catBienPro":           classifPro(row["typeBienPro"].item()),
            "value":                row["value"].item(),
            "quotePart":            row["value"].item(),
            "pctDetention":           row["pctDetention"].item(),     
            "pctDetentionConjoint":   row["pctDetentionConjoint"].item(),
            "dateValue":            datetime.today().strftime("%Y-%m-%d")}
        for row in pro_rd]
        print("DONE imputing pro part")
    #### impute empruint part ####
    emprunt_rd                            = p1["emprunt"]
    if len(emprunt_rd) == 0 :
        input_vide["Emprunt"]["PatEmpruntDetail"] = []
        print("emprunt vide tout va bien")
    else: 
        input_vide["Emprunt"]["PatEmpruntDetail"] = [
            {**copy.deepcopy(input_vide["Emprunt"]["PatEmpruntDetail"][0]),  # Copie propre du dictionnaire de base
            "typeEmprunt":        row["typeEmprunt"].item(),
            "catEmprunt":         classifEmprunt(row["typeEmprunt"].item()),
            "dtFin":              row["dtFin"].item().strftime("%Y-%m-%d"),  # Convertit np.float64 en float standard Python
            "montantRestantDu":   row["montantRestantDu"].item(),
            "quotePart":          row["montantRestantDu"].item(),
            "pctEmprunt":         row["pctEmprunt"].item(),     
            "pctEmpruntConjoint": row["pctEmpruntConjoint"].item(),
            "ImmoLie":            row["ImmoLie"].item(),
            "dateValue":          datetime.today().strftime("%Y-%m-%d")}
        for row in emprunt_rd]
        print("DONE imputing emprunt part")