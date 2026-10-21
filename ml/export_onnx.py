import os
import sys
import json
import shutil
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

# Add ml folder and project root to sys.path
_ml_dir = str(Path(__file__).resolve().parent)
_proj_root = str(Path(__file__).resolve().parent.parent)
for p in [_ml_dir, _proj_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

import torch
import numpy as np
import onnx
import onnxruntime as ort

from ml.model import get_model
from ml.dataset import PLANTVILLAGE_CLASSES, NORMALIZE_MEAN, NORMALIZE_STD
from ml.atomic_write import (
    atomic_write_json,
    atomic_copy_file,
    validate_onnx_file,
    validate_json_file,
)

DEFAULT_CHECKPOINT_PATH = os.path.join(_ml_dir, "checkpoints", "best_leaf_model.pth")
DEFAULT_FRONTEND_ONNX = os.path.join(_proj_root, "frontend", "public", "models", "leaf_disease_model.onnx")
DEFAULT_FRONTEND_JSON = os.path.join(_proj_root, "frontend", "public", "models", "disease_classes.json")
DEFAULT_BACKEND_ONNX = os.path.join(_proj_root, "backend", "ml_models", "leaf_disease_model.onnx")
DEFAULT_BACKEND_JSON = os.path.join(_proj_root, "backend", "ml_models", "disease_classes.json")

PROTECTED_PRODUCTION_PATHS = {
    Path(DEFAULT_FRONTEND_ONNX).resolve(),
    Path(DEFAULT_FRONTEND_JSON).resolve(),
    Path(DEFAULT_BACKEND_ONNX).resolve(),
    Path(DEFAULT_BACKEND_JSON).resolve(),
    Path(DEFAULT_CHECKPOINT_PATH).resolve(),
    (Path(_ml_dir) / "artifacts" / "classes.json").resolve(),
}

PROTECTED_PRODUCTION_DIRS = {
    Path(DEFAULT_FRONTEND_ONNX).resolve().parent,
    Path(DEFAULT_BACKEND_ONNX).resolve().parent,
    Path(DEFAULT_CHECKPOINT_PATH).resolve().parent,
}

# Complete multilingual agronomic guidance catalog for all 38 PlantVillage classes
DISEASE_METADATA_TEMPLATE = {
    "Apple___Apple_scab": {
        "crop": "Apple",
        "disease": "Apple Scab",
        "scientificName": "Venturia inaequalis",
        "severity": "moderate",
        "affectedPercentage": 28,
        "descriptions": {
            "en": {
                "whatIsIt": "Apple scab is a severe fungal disease caused by Venturia inaequalis. It produces olive-green to dark velvety lesions on leaves and fruit, causing premature defoliation.",
                "symptoms": ["Olive-green or brownish velvety spots on leaf surface", "Curling, yellowing and premature leaf drop", "Corky scab lesions on fruit"],
                "recommendedAction": "Apply protective fungicides (Captan, Mancozeb) at bud break. Rake and destroy fallen leaves to reduce overwintering ascospore inoculum.",
                "immediateActionTitle": "Foliar Fungicide & Sanitation",
                "immediateActionDesc": "Apply captan or myclobutanil fungicide and rake up fallen leaves under canopy."
            },
            "hi": {
                "whatIsIt": "सेब का स्कैब (Apple Scab) एक फफूंद जनित रोग है जो पत्तियों और फलों पर काले-भूरे मखमली धब्बे बनाता है।",
                "symptoms": ["पत्तियों पर जैतून-हरे से काले धब्बे", "पत्तियों का मुड़ना और जल्दी गिरना", "फलों पर खुरदरे धब्बे"],
                "recommendedAction": "कली खिलते समय कैप्टन या मैंकोजेब कवकनाशी का छिड़काव करें और गिरी हुई पत्तियों को नष्ट करें।",
                "immediateActionTitle": "कवकनाशी छिड़काव",
                "immediateActionDesc": "तुरंत कैप्टन कवकनाशी का छिड़काव करें और बगीचे की सफाई करें।"
            }
        }
    },
    "Apple___Black_rot": {
        "crop": "Apple",
        "disease": "Black Rot",
        "scientificName": "Botryosphaeria obtusa",
        "severity": "severe",
        "affectedPercentage": 35,
        "descriptions": {
            "en": {
                "whatIsIt": "Black rot causes frogeye leaf spots, fruit rot, and twig cankers on apple trees, severely weakening the canopy.",
                "symptoms": ["Small purple specks enlarging into 'frogeye' spots with tan centers", "Black, mummified rotting fruit", "Sunken bark cankers on branches"],
                "recommendedAction": "Prune out dead wood, fire blight strikes, and cankers. Apply thiophanate-methyl or captan fungicide.",
                "immediateActionTitle": "Prune Cankers & Spray",
                "immediateActionDesc": "Prune dead wood and mummified fruit, then apply protective fungicide."
            }
        }
    },
    "Apple___Cedar_apple_rust": {
        "crop": "Apple",
        "disease": "Cedar Apple Rust",
        "scientificName": "Gymnosporangium juniperi-virginianae",
        "severity": "moderate",
        "affectedPercentage": 25,
        "descriptions": {
            "en": {
                "whatIsIt": "Cedar apple rust is a heteroecious rust fungus that requires both apple trees and eastern red cedar/juniper to complete its life cycle.",
                "symptoms": ["Bright orange-yellow circular leaf spots", "Small black pycnia in centers of spots", "Tube-like aecia on leaf undersides"],
                "recommendedAction": "Apply sterol inhibitor fungicides (myclobutanil) early in spring. Remove nearby wild red cedar galls.",
                "immediateActionTitle": "Apply Rust Fungicide",
                "immediateActionDesc": "Apply myclobutanil immediately and inspect nearby juniper trees."
            }
        }
    },
    "Apple___healthy": {
        "crop": "Apple",
        "disease": "Healthy Leaf",
        "scientificName": "Malus domestica",
        "severity": "healthy",
        "affectedPercentage": 0,
        "descriptions": {
            "en": {
                "whatIsIt": "Apple foliage displays optimal chlorophyll saturation with no pathogenic lesion signatures.",
                "symptoms": ["Vibrant green foliage", "Smooth margins without spotting", "Healthy venation"],
                "recommendedAction": "Maintain routine orchard sanitation, balanced fertilization, and moisture monitoring.",
                "immediateActionTitle": "Routine Maintenance",
                "immediateActionDesc": "No active intervention required; sustain preventive management."
            }
        }
    },
    "Blueberry___healthy": {
        "crop": "Blueberry",
        "disease": "Healthy Leaf",
        "scientificName": "Vaccinium corymbosum",
        "severity": "healthy",
        "affectedPercentage": 0,
        "descriptions": {
            "en": {
                "whatIsIt": "Blueberry foliage displays healthy photosynthetic pigmentation without necrotic symptoms.",
                "symptoms": ["Uniform green leaves", "No marginal scorching", "Strong root canopy vigor"],
                "recommendedAction": "Keep soil pH acidic (4.5 - 5.5) and sustain organic mulch.",
                "immediateActionTitle": "Optimal Canopy",
                "immediateActionDesc": "Maintain soil acidity and drip irrigation schedule."
            }
        }
    },
    "Cherry_(including_sour)___Powdery_mildew": {
        "crop": "Cherry",
        "disease": "Powdery Mildew",
        "scientificName": "Podosphaera clandestina",
        "severity": "moderate",
        "affectedPercentage": 30,
        "descriptions": {
            "en": {
                "whatIsIt": "Powdery mildew forms a circular white felt-like fungal coating on young cherry leaves and shoots.",
                "symptoms": ["White talcum-like powdery patches on leaves", "Leaf curling and distortion", "Stunted terminal growth"],
                "recommendedAction": "Apply sulfur or potassium bicarbonate early. Prune to improve canopy air circulation.",
                "immediateActionTitle": "Apply Sulfur / Biofungicide",
                "immediateActionDesc": "Spray micronized wettable sulfur or horticultural oil during cool periods."
            }
        }
    },
    "Cherry_(including_sour)___healthy": {
        "crop": "Cherry",
        "disease": "Healthy Leaf",
        "scientificName": "Prunus avium",
        "severity": "healthy",
        "affectedPercentage": 0,
        "descriptions": {
            "en": {
                "whatIsIt": "Cherry leaf canopy exhibits vigorous, uniform green structure.",
                "symptoms": ["Deep green coloration", "Intact leaf margins", "Active shoot elongation"],
                "recommendedAction": "Continue regular pruning and preventive dormancy sprays.",
                "immediateActionTitle": "Maintain Care",
                "immediateActionDesc": "No active pathogen found."
            }
        }
    },
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": {
        "crop": "Corn (Maize)",
        "disease": "Gray Leaf Spot",
        "scientificName": "Cercospora zeae-maydis",
        "severity": "severe",
        "affectedPercentage": 40,
        "descriptions": {
            "en": {
                "whatIsIt": "Gray leaf spot is a devastating foliar pathogen of corn, producing rectangular lesions delimited by leaf veins.",
                "symptoms": ["Long, narrow rectangular tan lesions", "Lesions restricted between parallel leaf veins", "Premature senescence of foliage"],
                "recommendedAction": "Apply strobilurin or triazole fungicides before tasseling. Implement crop rotation with non-host crops.",
                "immediateActionTitle": "Foliar Fungicide Application",
                "immediateActionDesc": "Apply pyraclostrobin or azoxystrobin before canopy closure."
            }
        }
    },
    "Corn_(maize)___Common_rust_": {
        "crop": "Corn (Maize)",
        "disease": "Common Rust",
        "scientificName": "Puccinia sorghi",
        "severity": "moderate",
        "affectedPercentage": 32,
        "descriptions": {
            "en": {
                "whatIsIt": "Common rust produces brick-red, powdery pustules on both upper and lower leaf surfaces of maize.",
                "symptoms": ["Oval to elongate cinnamon-brown powdery pustules", "Ruptured epidermis on leaf blades", "Pustules turning dark brown later"],
                "recommendedAction": "Plant resistant hybrids. In seed corn or sweet corn, apply triazole fungicides if rust appears before silking.",
                "immediateActionTitle": "Monitor & Treat if Widespread",
                "immediateActionDesc": "Inspect lower leaves and apply triazole fungicide if >5% leaf area affected."
            }
        }
    },
    "Corn_(maize)___Northern_Leaf_Blight": {
        "crop": "Corn (Maize)",
        "disease": "Northern Leaf Blight",
        "scientificName": "Exserohilum turcicum",
        "severity": "severe",
        "affectedPercentage": 45,
        "descriptions": {
            "en": {
                "whatIsIt": "Northern corn leaf blight causes large, cigar-shaped grayish-green lesions that destroy photosynthesizing tissue.",
                "symptoms": ["Long elliptical or cigar-shaped grayish lesions (2-15 cm)", "Dark fungal spores inside lesions during damp weather", "Extensive blighting of upper leaves"],
                "recommendedAction": "Rotate crops, till infected corn residue, and spray systemic fungicides when conditions favor spread.",
                "immediateActionTitle": "Emergency Protective Spray",
                "immediateActionDesc": "Apply strobilurin/triazole fungicide combination immediately."
            }
        }
    },
    "Corn_(maize)___healthy": {
        "crop": "Corn (Maize)",
        "disease": "Healthy Leaf",
        "scientificName": "Zea mays",
        "severity": "healthy",
        "affectedPercentage": 0,
        "descriptions": {
            "en": {
                "whatIsIt": "Corn plant shows robust leaf health with no blighting or pustules.",
                "symptoms": ["Broad deep green leaves", "No vein-limited striping", "Robust stalk and collar vigor"],
                "recommendedAction": "Maintain balanced nitrogen nutrition and soil drainage.",
                "immediateActionTitle": "Standard Agronomy",
                "immediateActionDesc": "Maintain irrigation and scout regularly."
            }
        }
    },
    "Grape___Black_rot": {
        "crop": "Grape",
        "disease": "Black Rot",
        "scientificName": "Guignardia bidwellii",
        "severity": "severe",
        "affectedPercentage": 38,
        "descriptions": {
            "en": {
                "whatIsIt": "Black rot affects all green vine parts, causing reddish-brown leaf spots with black border dots and shriveled black mummies.",
                "symptoms": ["Small reddish-brown circular leaf spots", "Tiny black fruiting bodies (pycnidia) in rings", "Fruit turning into hard black mummies"],
                "recommendedAction": "Apply myclobutanil or mancozeb at 10-14 day intervals from 1-inch shoot growth through post-bloom.",
                "immediateActionTitle": "Grapevine Fungicide Spray",
                "immediateActionDesc": "Spray myclobutanil and prune out all mummified fruit clusters."
            }
        }
    },
    "Grape___Esca_(Black_Measles)": {
        "crop": "Grape",
        "disease": "Esca (Black Measles)",
        "scientificName": "Phaeomoniella chlamydospora",
        "severity": "severe",
        "affectedPercentage": 42,
        "descriptions": {
            "en": {
                "whatIsIt": "Esca is a complex fungal vascular decline disease causing 'tiger-stripe' interveinal chlorosis and berry spotting.",
                "symptoms": ["Tiger-stripe pattern of yellow/red bands between veins", "Dried marginal leaf scorch", "Dark purple flecks on berries ('measles')"],
                "recommendedAction": "Prune during dry dormant periods. Seal pruning wounds with wound protectant. Replace severely stunted vines.",
                "immediateActionTitle": "Wound Protection & Pruning",
                "immediateActionDesc": "Sanitize pruning tools and seal large wood wounds."
            }
        }
    },
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)": {
        "crop": "Grape",
        "disease": "Leaf Blight",
        "scientificName": "Pseudocercospora vitis",
        "severity": "moderate",
        "affectedPercentage": 28,
        "descriptions": {
            "en": {
                "whatIsIt": "Isariopsis leaf spot produces irregular brown necrotic patches bordered by yellow halos on grape leaves.",
                "symptoms": ["Irregular angular dark brown spots", "Spots coalescing into large necrotic areas", "Premature defoliation before harvest"],
                "recommendedAction": "Apply copper or azoxystrobin fungicides. Prune excess vine canopy to encourage rapid airflow.",
                "immediateActionTitle": "Foliar Copper Treatment",
                "immediateActionDesc": "Apply copper hydroxide spray and prune dense inner canopy."
            }
        }
    },
    "Grape___healthy": {
        "crop": "Grape",
        "disease": "Healthy Leaf",
        "scientificName": "Vitis vinifera",
        "severity": "healthy",
        "affectedPercentage": 0,
        "descriptions": {
            "en": {
                "whatIsIt": "Grapevine canopy is in prime physiological health with strong photosynthetic efficiency.",
                "symptoms": ["Uniform green palmate leaves", "No interveinal discoloration", "Supple shoots and tendrils"],
                "recommendedAction": "Maintain canopy wire training and preventive pest management.",
                "immediateActionTitle": "Routine Canopy Management",
                "immediateActionDesc": "Canopy is healthy."
            }
        }
    },
    "Orange___Haunglongbing_(Citrus_greening)": {
        "crop": "Orange / Citrus",
        "disease": "Citrus Greening (HLB)",
        "scientificName": "Candidatus Liberibacter asiaticus",
        "severity": "severe",
        "affectedPercentage": 50,
        "descriptions": {
            "en": {
                "whatIsIt": "Citrus greening (Huanglongbing) is an incurable bacterial disease vectored by the Asian citrus psyllid, leading to tree decline.",
                "symptoms": ["Asymmetrical blotchy mottle on leaves", "Yellow shoots ('yellow dragon')", "Small, lopsided, bitter fruit with dark aborted seeds"],
                "recommendedAction": "Control psyllid vectors with targeted insecticides. Remove confirmed infected trees to protect surrounding grove.",
                "immediateActionTitle": "Psyllid Control & Quarantine",
                "immediateActionDesc": "Treat vector psyllids immediately and consult local agricultural quarantine."
            }
        }
    },
    "Peach___Bacterial_spot": {
        "crop": "Peach",
        "disease": "Bacterial Spot",
        "scientificName": "Xanthomonas campestris pv. pruni",
        "severity": "moderate",
        "affectedPercentage": 30,
        "descriptions": {
            "en": {
                "whatIsIt": "Bacterial spot causes water-soaked angular leaf lesions that drop out, giving foliage a 'shot-hole' appearance.",
                "symptoms": ["Angular water-soaked leaf spots turning purple-brown", "Lesion centers dropping out ('shot-hole')", "Cracked, pitted lesions on peach fruit"],
                "recommendedAction": "Apply copper sprays at bud break and oxytetracycline during the growing season. Plant resistant peach varieties.",
                "immediateActionTitle": "Apply Copper / Antibiotic Spray",
                "immediateActionDesc": "Spray low-rate copper hydroxide or oxytetracycline during early vegetative flush."
            }
        }
    },
    "Peach___healthy": {
        "crop": "Peach",
        "disease": "Healthy Leaf",
        "scientificName": "Prunus persica",
        "severity": "healthy",
        "affectedPercentage": 0,
        "descriptions": {
            "en": {
                "whatIsIt": "Peach tree foliage demonstrates clean, unspotted green lanceolate leaves.",
                "symptoms": ["Smooth unblemished leaves", "No shot-holes or curling", "Vigorous shoot growth"],
                "recommendedAction": "Maintain dormant copper sprays and balanced irrigation.",
                "immediateActionTitle": "Standard Orchard Practice",
                "immediateActionDesc": "Tree canopy is in excellent condition."
            }
        }
    },
    "Pepper,_bell___Bacterial_spot": {
        "crop": "Bell Pepper",
        "disease": "Bacterial Spot",
        "scientificName": "Xanthomonas campestris pv. vesicatoria",
        "severity": "severe",
        "affectedPercentage": 36,
        "descriptions": {
            "en": {
                "whatIsIt": "Bacterial spot on bell peppers produces small, circular, dark brown lesions that expand and cause severe leaf dropping.",
                "symptoms": ["Water-soaked circular lesions on lower leaf surfaces", "Brown, necrotic centers with yellow chlorotic rings", "Sunken rough spots on fruit"],
                "recommendedAction": "Apply fixed copper bactericide mixed with mancozeb. Avoid working in fields when foliage is wet.",
                "immediateActionTitle": "Copper Bactericide Application",
                "immediateActionDesc": "Spray copper hydroxide mixed with mancozeb to prevent bacterial spread."
            }
        }
    },
    "Pepper,_bell___healthy": {
        "crop": "Bell Pepper",
        "disease": "Healthy Leaf",
        "scientificName": "Capsicum annuum",
        "severity": "healthy",
        "affectedPercentage": 0,
        "descriptions": {
            "en": {
                "whatIsIt": "Bell pepper leaf is completely healthy with crisp green pigmentation.",
                "symptoms": ["Smooth ovate foliage", "No water-soaked spots", "Healthy flower buds"],
                "recommendedAction": "Maintain consistent drip moisture and balanced potassium-calcium feeding.",
                "immediateActionTitle": "Optimal Care",
                "immediateActionDesc": "No pathogen detected."
            }
        }
    },
    "Potato___Early_blight": {
        "crop": "Potato",
        "disease": "Early Blight",
        "scientificName": "Alternaria solani",
        "severity": "moderate",
        "affectedPercentage": 32,
        "descriptions": {
            "en": {
                "whatIsIt": "Early blight is a fungal disease causing target-like concentric rings on potato leaves, usually starting on mature lower canopy.",
                "symptoms": ["Dark brown spots with concentric ring pattern", "Yellow halos surrounding necrotic spots", "Premature vine defoliation"],
                "recommendedAction": "Apply chlorothalonil, mancozeb, or copper fungicides at 7-10 day intervals. Ensure adequate soil nitrogen.",
                "immediateActionTitle": "Apply Protective Fungicide",
                "immediateActionDesc": "Apply chlorothalonil spray and avoid overhead sprinkler watering."
            }
        }
    },
    "Potato___Late_blight": {
        "crop": "Potato",
        "disease": "Late Blight",
        "scientificName": "Phytophthora infestans",
        "severity": "severe",
        "affectedPercentage": 48,
        "descriptions": {
            "en": {
                "whatIsIt": "Late blight is the aggressive oomycete pathogen responsible for the Irish potato famine. It causes rapid rotting of vines and tubers.",
                "symptoms": ["Large irregular water-soaked spots on leaves", "White velvety sporulation on leaf underside in humid conditions", "Rapid brown wilt and vine collapse"],
                "recommendedAction": "Apply systemic fungicides (mefenoxam, cymoxanil, mandipropamid) immediately. Destroy severely blighted vines.",
                "immediateActionTitle": "Emergency Systemic Fungicide",
                "immediateActionDesc": "Apply systemic late blight fungicide within 24 hours to halt field epidemic."
            }
        }
    },
    "Potato___healthy": {
        "crop": "Potato",
        "disease": "Healthy Leaf",
        "scientificName": "Solanum tuberosum",
        "severity": "healthy",
        "affectedPercentage": 0,
        "descriptions": {
            "en": {
                "whatIsIt": "Potato plant foliage displays prime health and strong vegetative development.",
                "symptoms": ["Rich green compound leaves", "No target rings or water-soaked lesions", "Healthy stolon vigor"],
                "recommendedAction": "Continue preventive fungicide schedule during humid periods.",
                "immediateActionTitle": "Routine Scouting",
                "immediateActionDesc": "Maintain proper hilling and scouting."
            }
        }
    },
    "Raspberry___healthy": {
        "crop": "Raspberry",
        "disease": "Healthy Leaf",
        "scientificName": "Rubus idaeus",
        "severity": "healthy",
        "affectedPercentage": 0,
        "descriptions": {
            "en": {
                "whatIsIt": "Raspberry leaf exhibits healthy serrated structure and uniform pigmentation.",
                "symptoms": ["Pinnate green leaves with pale undersides", "No anthracnose lesions", "Strong primocane growth"],
                "recommendedAction": "Prune out spent floricanes after fruiting and keep rows well-ventilated.",
                "immediateActionTitle": "Canopy Maintenance",
                "immediateActionDesc": "Canes are healthy."
            }
        }
    },
    "Soybean___healthy": {
        "crop": "Soybean",
        "disease": "Healthy Leaf",
        "scientificName": "Glycine max",
        "severity": "healthy",
        "affectedPercentage": 0,
        "descriptions": {
            "en": {
                "whatIsIt": "Soybean trifoliate leaves are healthy with no fungal spotting or chlorosis.",
                "symptoms": ["Uniform green trifoliate leaves", "No Septoria brown spots", "Active nodulation"],
                "recommendedAction": "Scout weekly for pod pests and fungal rust during reproductive stages.",
                "immediateActionTitle": "Routine Scouting",
                "immediateActionDesc": "Soybean canopy is robust."
            }
        }
    },
    "Squash___Powdery_mildew": {
        "crop": "Squash",
        "disease": "Powdery Mildew",
        "scientificName": "Podosphaera xanthii",
        "severity": "moderate",
        "affectedPercentage": 34,
        "descriptions": {
            "en": {
                "whatIsIt": "Powdery mildew creates distinctive white dusty powder spots on both sides of cucurbit leaves, reducing yield.",
                "symptoms": ["White powdery talc-like spots on leaves and stems", "Leaves yellowing and drying prematurely", "Sunburn on fruit due to defoliation"],
                "recommendedAction": "Apply potassium bicarbonate, neem oil, or synthetic fungicides (myclobutanil). Avoid crowded plant spacing.",
                "immediateActionTitle": "Foliar Fungicide Spray",
                "immediateActionDesc": "Spray potassium bicarbonate or azoxystrobin early morning."
            }
        }
    },
    "Strawberry___Leaf_scorch": {
        "crop": "Strawberry",
        "disease": "Leaf Scorch",
        "scientificName": "Diplocarpon earlianum",
        "severity": "moderate",
        "affectedPercentage": 30,
        "descriptions": {
            "en": {
                "whatIsIt": "Leaf scorch produces numerous small purplish spots that enlarge and coalesce, giving the foliage a burned appearance.",
                "symptoms": ["Irregular purple blotches without distinct white centers", "Leaf edges curling upward and drying", "Burned, scorched look across planting"],
                "recommendedAction": "Remove infected leaves after harvest. Apply captan or dodine fungicide during spring leaf emergence.",
                "immediateActionTitle": "Prune & Protect Foliage",
                "immediateActionDesc": "Prune dry scorched leaves and apply protective fungicide."
            }
        }
    },
    "Strawberry___healthy": {
        "crop": "Strawberry",
        "disease": "Healthy Leaf",
        "scientificName": "Fragaria ananassa",
        "severity": "healthy",
        "affectedPercentage": 0,
        "descriptions": {
            "en": {
                "whatIsIt": "Strawberry crown foliage shows vibrant, unblemished trifoliate leaves.",
                "symptoms": ["Glossy green leaves", "No purplish angular spots", "Robust crown growth"],
                "recommendedAction": "Keep straw mulch fresh and avoid over-saturating crown.",
                "immediateActionTitle": "Routine Care",
                "immediateActionDesc": "Crown is healthy."
            }
        }
    },
    "Tomato___Bacterial_spot": {
        "crop": "Tomato",
        "disease": "Bacterial Spot",
        "scientificName": "Xanthomonas vesicatoria",
        "severity": "severe",
        "affectedPercentage": 38,
        "descriptions": {
            "en": {
                "whatIsIt": "Bacterial spot causes small, dark, greasy water-soaked lesions that turn brown with yellow halos, causing heavy leaf drop.",
                "symptoms": ["Dark brown water-soaked angular spots", "Yellow chlorotic halos around lesions", "Black scab-like spots on green tomatoes"],
                "recommendedAction": "Apply copper bactericide with mancozeb. Avoid overhead irrigation and sanitize pruning shears.",
                "immediateActionTitle": "Copper Bactericide Spray",
                "immediateActionDesc": "Apply fixed copper hydroxide and eliminate overhead watering."
            }
        }
    },
    "Tomato___Early_blight": {
        "crop": "Tomato",
        "disease": "Early Blight",
        "scientificName": "Alternaria solani",
        "severity": "moderate",
        "affectedPercentage": 32,
        "descriptions": {
            "en": {
                "whatIsIt": "Early blight is a fungal pathogen causing dark brown concentric target rings surrounded by yellow halos on tomato foliage.",
                "symptoms": ["Dark concentric target rings on leaves", "Chlorotic yellowing around leaf lesions", "Progression from lower mature leaves upward"],
                "recommendedAction": "Prune lower infected foliage. Apply copper hydroxide or chlorothalonil fungicide early in the morning.",
                "immediateActionTitle": "Prune & Apply Copper Fungicide",
                "immediateActionDesc": "Prune bottom leaves showing dark rings and spray copper fungicide."
            },
            "hi": {
                "whatIsIt": "अगेती झुलसा (Early Blight) टमाटर का एक फफूंद जनित रोग है जो पत्तियों पर संकेंद्रित छल्ले बनाता है।",
                "symptoms": ["काले छल्लेदार धब्बे", "धब्बों के चारों ओर पीलापन", "निचली पत्तियों से शुरुआत"],
                "recommendedAction": "तुरंत कॉपर युक्त कवकनाशी का छिड़काव करें और निचली खराब पत्तियां काटें।",
                "immediateActionTitle": "पत्तियां हटाएं और कवकनाशी छिड़कें",
                "immediateActionDesc": "प्रभावित पत्तियां हटाकर नष्ट करें।"
            }
        }
    },
    "Tomato___Late_blight": {
        "crop": "Tomato",
        "disease": "Late Blight",
        "scientificName": "Phytophthora infestans",
        "severity": "severe",
        "affectedPercentage": 46,
        "descriptions": {
            "en": {
                "whatIsIt": "Late blight is a fast-moving water mold that causes large pale green water-soaked spots turning rapidly dark brown and rotting vines.",
                "symptoms": ["Large greasy water-soaked lesions", "White fuzzy mold on leaf undersides in high humidity", "Rapid stem rot and fruit browning"],
                "recommendedAction": "Apply systemic fungicides (mancozeb, metalaxyl) immediately. Destroy collapsing infected plants.",
                "immediateActionTitle": "Emergency Systemic Treatment",
                "immediateActionDesc": "Apply systemic fungicide within 12 hours and prune rotting foliage."
            }
        }
    },
    "Tomato___Leaf_Mold": {
        "crop": "Tomato",
        "disease": "Leaf Mold",
        "scientificName": "Passalora fulva",
        "severity": "moderate",
        "affectedPercentage": 30,
        "descriptions": {
            "en": {
                "whatIsIt": "Leaf mold thrives in high relative humidity (>85%), causing pale greenish-yellow spots on upper leaf surfaces and olive-green velvet mold below.",
                "symptoms": ["Pale yellow spots on upper leaf surface", "Olive-green to grayish velvety mold on leaf underside", "Leaves curling, withering and dropping"],
                "recommendedAction": "Increase greenhouse ventilation and lower relative humidity below 80%. Apply copper or chlorothalonil fungicide.",
                "immediateActionTitle": "Improve Airflow & Spray",
                "immediateActionDesc": "Prune inner canopy to improve ventilation and apply protective spray."
            }
        }
    },
    "Tomato___Septoria_leaf_spot": {
        "crop": "Tomato",
        "disease": "Septoria Leaf Spot",
        "scientificName": "Septoria lycopersici",
        "severity": "moderate",
        "affectedPercentage": 34,
        "descriptions": {
            "en": {
                "whatIsIt": "Septoria leaf spot produces circular spots with dark brown margins and gray or tan centers containing tiny black dots.",
                "symptoms": ["Small circular spots with dark borders and tan centers", "Tiny black pycnidia specks inside spots", "Severe bottom-up leaf yellowing and defoliation"],
                "recommendedAction": "Apply organic mulch around plant base to prevent soil splash. Spray chlorothalonil or copper fungicide.",
                "immediateActionTitle": "Mulch Base & Fungicide Spray",
                "immediateActionDesc": "Apply mulch to stop soil splashing and apply copper spray."
            }
        }
    },
    "Tomato___Spider_mites Two-spotted_spider_mite": {
        "crop": "Tomato",
        "disease": "Two-Spotted Spider Mites",
        "scientificName": "Tetranychus urticae",
        "severity": "moderate",
        "affectedPercentage": 28,
        "descriptions": {
            "en": {
                "whatIsIt": "Two-spotted spider mites pierce plant cells to feed on sap, causing yellow stippling and fine silken webbing on leaf undersides.",
                "symptoms": ["Fine yellow or white stippling on leaf surface", "Delicate silken webbing on leaf undersides and shoot tips", "Leaves bronzing, drying and dropping"],
                "recommendedAction": "Spray insecticidal soap, neem oil, or abamectin miticide. Release predatory mites (Phytoseiulus persimilis).",
                "immediateActionTitle": "Apply Miticide / Insecticidal Soap",
                "immediateActionDesc": "Spray neem oil or insecticidal soap thoroughly on leaf undersides."
            }
        }
    },
    "Tomato___Target_Spot": {
        "crop": "Tomato",
        "disease": "Target Spot",
        "scientificName": "Corynespora cassiicola",
        "severity": "moderate",
        "affectedPercentage": 32,
        "descriptions": {
            "en": {
                "whatIsIt": "Target spot produces circular brown lesions with light brown centers and dark concentric rings across leaf blades and fruit.",
                "symptoms": ["Small pinpoint brown spots expanding into target patterns", "Lesions with light centers and dark concentric rings", "Sunken crater-like spots on green tomatoes"],
                "recommendedAction": "Apply azoxystrobin, chlorothalonil, or copper fungicides. Ensure adequate plant spacing to facilitate rapid foliage drying.",
                "immediateActionTitle": "Fungicide Spray & Spacing",
                "immediateActionDesc": "Apply azoxystrobin and increase canopy spacing."
            }
        }
    },
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": {
        "crop": "Tomato",
        "disease": "Yellow Leaf Curl Virus",
        "scientificName": "Tomato yellow leaf curl virus (TYLCV)",
        "severity": "severe",
        "affectedPercentage": 45,
        "descriptions": {
            "en": {
                "whatIsIt": "TYLCV is a devastating geminivirus transmitted by whiteflies (Bemisia tabaci), causing stunted growth, cupped leaves, and complete yield failure.",
                "symptoms": ["Severe upward curling and cupping of leaflets", "Interveinal chlorosis and yellow margins", "Extreme stunting of plants and bushy upright habit"],
                "recommendedAction": "Control whitefly vectors using yellow sticky traps and systemic insecticides. Rogue out infected plants immediately.",
                "immediateActionTitle": "Control Whiteflies & Isolate",
                "immediateActionDesc": "Rogue out infected plants immediately and treat whiteflies with imidacloprid or insecticidal soap."
            }
        }
    },
    "Tomato___Tomato_mosaic_virus": {
        "crop": "Tomato",
        "disease": "Tomato Mosaic Virus",
        "scientificName": "Tomato mosaic virus (ToMV)",
        "severity": "severe",
        "affectedPercentage": 40,
        "descriptions": {
            "en": {
                "whatIsIt": "ToMV is a highly stable tobamovirus spread easily by mechanical contact, pruning tools, and hands, causing mottled leaves and distortion.",
                "symptoms": ["Mottled light and dark green mosaic patterns on leaves", "Fern-like leaf distortion and stringy foliage", "Internal brown browning in tomato fruit"],
                "recommendedAction": "Wash hands with soap and disinfect pruning shears with 20% non-fat dry milk or trisodium phosphate. Remove infected plants.",
                "immediateActionTitle": "Sanitize & Remove Plant",
                "immediateActionDesc": "Remove infected plant, do not compost, and sanitize all tools thoroughly."
            }
        }
    },
    "Tomato___healthy": {
        "crop": "Tomato",
        "disease": "Healthy Leaf",
        "scientificName": "Solanum lycopersicum",
        "severity": "healthy",
        "affectedPercentage": 0,
        "descriptions": {
            "en": {
                "whatIsIt": "Tomato plant foliage is in pristine health with vibrant dark green chlorophyll and no pathogenic lesions.",
                "symptoms": ["Deep green compound foliage", "No chlorotic halos, curling, or necrotic spots", "Strong vascular stems and healthy trichomes"],
                "recommendedAction": "Maintain standard drip irrigation, calcium nutrition to prevent blossom end rot, and regular scouting.",
                "immediateActionTitle": "Routine Agronomic Care",
                "immediateActionDesc": "Plant is fully healthy; sustain balanced irrigation and nutrition."
            }
        }
    }
}


def build_disease_classes_json(
    classes: list,
    output_paths: list,
    allow_production: bool = False,
):
    """Generates disease_classes.json containing all detected classes."""
    catalog = {
        "modelName": "AgriScan-EfficientNet-B0-PlantVillage",
        "architecture": "EfficientNet-B0",
        "version": "v3.0-PlantVillage",
        "inputShape": [1, 3, 224, 224],
        "normalization": {
            "mean": NORMALIZE_MEAN,
            "std": NORMALIZE_STD,
        },
        "classes": [],
    }

    for idx, raw_cls in enumerate(classes):
        meta = DISEASE_METADATA_TEMPLATE.get(raw_cls, None)
        if meta is None:
            parts = raw_cls.split("___")
            crop = parts[0].replace("_", " ").title()
            disease = parts[1].replace("_", " ").title() if len(parts) > 1 else "Unknown"
            is_healthy = "healthy" in disease.lower()
            meta = {
                "crop": crop,
                "disease": disease,
                "scientificName": f"{crop} Pathogen",
                "severity": "healthy" if is_healthy else "moderate",
                "affectedPercentage": 0 if is_healthy else 30,
                "descriptions": {
                    "en": {
                        "whatIsIt": f"{disease} affecting {crop} leaves.",
                        "symptoms": [f"Visual lesions characteristic of {disease}"],
                        "recommendedAction": "Inspect leaf canopy and apply appropriate plant protection measures.",
                        "immediateActionTitle": "Isolate & Monitor",
                        "immediateActionDesc": "Isolate affected section and consult agronomic guidelines."
                    }
                }
            }

        item = {
            "index": idx,
            "rawClass": raw_cls,
            "crop": meta["crop"],
            "disease": meta["disease"],
            "scientificName": meta["scientificName"],
            "severity": meta["severity"],
            "affectedPercentage": meta["affectedPercentage"],
            "descriptions": meta["descriptions"],
        }
        catalog["classes"].append(item)

    for p in output_paths:
        p_path = Path(p).resolve()
        if not allow_production and (
            p_path in PROTECTED_PRODUCTION_PATHS
            or p_path.parent in PROTECTED_PRODUCTION_DIRS
        ):
            raise RuntimeError(
                f"SAFETY VIOLATION: Cannot write class metadata to production target '{p}' when production write is not authorized!"
            )
        atomic_write_json(p_path, catalog, indent=2, ensure_ascii=False)
        print(f"[Export] Saved class metadata catalog atomically to: {p}")

    return catalog


def export_model_to_onnx(
    checkpoint_path: str = DEFAULT_CHECKPOINT_PATH,
    frontend_onnx: str = DEFAULT_FRONTEND_ONNX,
    frontend_json: str = DEFAULT_FRONTEND_JSON,
    backend_onnx: str = DEFAULT_BACKEND_ONNX,
    backend_json: str = DEFAULT_BACKEND_JSON,
    output_onnx_path: Optional[str] = None,
    deploy: bool = True,
) -> str:
    """
    Exports fine-tuned PyTorch checkpoint to ONNX format, validates it with onnx and onnxruntime,
    and optionally deploys it to both frontend and backend directories.
    """
    print(f"\n[Export ONNX] Loading PyTorch checkpoint: {checkpoint_path}")
    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"Checkpoint not found at: {checkpoint_path}")

    device = torch.device("cpu")
    try:
        checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    except TypeError:
        checkpoint = torch.load(checkpoint_path, map_location=device)
    classes = checkpoint.get("classes", PLANTVILLAGE_CLASSES)
    model_variant = checkpoint.get("model_variant", "efficientnet_b0")

    model = get_model(num_classes=len(classes), model_variant=model_variant, pretrained=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    # Safety assertion: if deployment is disabled, strictly prohibit writing to any production targets
    if not deploy:
        if output_onnx_path:
            resolved_output = Path(output_onnx_path).resolve()
            if (
                resolved_output in PROTECTED_PRODUCTION_PATHS
                or resolved_output.parent in PROTECTED_PRODUCTION_DIRS
            ):
                raise RuntimeError(
                    f"SAFETY VIOLATION: Cannot write to production ONNX target '{output_onnx_path}' when deploy=False!"
                )

    # Export to intermediate/candidate ONNX path FIRST
    # NOTE: Metadata is NOT written here. Production metadata is only written after
    # ONNX export, checker, and PyTorch-to-ONNX numerical parity validation all succeed.
    dummy_input = torch.randn(1, 3, 224, 224, requires_grad=False)
    temp_onnx = (
        output_onnx_path
        if (output_onnx_path and not deploy)
        else os.path.join(_ml_dir, "artifacts", "model_export_temp.onnx")
    )
    os.makedirs(os.path.dirname(temp_onnx), exist_ok=True)

    print(f"[Export ONNX] Converting PyTorch graph to ONNX format...")
    export_kwargs = {
        "export_params": True,
        "opset_version": 17,
        "do_constant_folding": True,
        "input_names": ["input_image"],
        "output_names": ["class_probabilities"],
        "dynamic_axes": {
            "input_image": {0: "batch_size"},
            "class_probabilities": {0: "batch_size"},
        },
    }
    try:
        torch.onnx.export(model, (dummy_input,), temp_onnx, dynamo=False, **export_kwargs)
    except TypeError as exc:
        if "dynamo" in str(exc) or "unexpected keyword argument" in str(exc):
            torch.onnx.export(model, (dummy_input,), temp_onnx, **export_kwargs)
        else:
            raise

    # Validate ONNX model with checker
    print(f"[Export ONNX] Checking ONNX model integrity...")
    validate_onnx_file(temp_onnx)
    print("  ✓ ONNX graph verification passed.")

    # Validate with onnxruntime
    print(f"[Export ONNX] Testing onnxruntime inference session...")
    ort_session = ort.InferenceSession(temp_onnx)
    ort_input_name = ort_session.get_inputs()[0].name
    ort_inputs = {ort_input_name: dummy_input.detach().cpu().numpy()}
    ort_outs = ort_session.run(None, ort_inputs)

    with torch.no_grad():
        torch_out = model(dummy_input).detach().cpu().numpy()

    ort_out = np.asarray(ort_outs[0], dtype=np.float32)
    torch_out = np.asarray(torch_out, dtype=np.float32)

    np.testing.assert_allclose(actual=ort_out, desired=torch_out, rtol=1e-03, atol=1e-04)
    max_diff = float(np.max(np.abs(torch_out - ort_out)))
    print(f"  ✓ PyTorch and ONNX Runtime predictions match within tolerance (max diff: {max_diff:.6e}).")

    final_model_path = temp_onnx

    if deploy:
        # ORDERING FIX: Generate metadata catalog for deployment targets ONLY AFTER
        # ONNX export, ONNX structural validation, and numerical parity checks have all succeeded!
        print(f"[Export ONNX] Writing class metadata catalogs atomically...")
        build_disease_classes_json(classes, [frontend_json, backend_json], allow_production=True)

        # Deploy ONNX model atomically to frontend and backend targets
        for target in [frontend_onnx, backend_onnx]:
            atomic_copy_file(temp_onnx, target, validate_fn=validate_onnx_file)
            size_mb = os.path.getsize(target) / (1024 * 1024)
            print(f"[Export ONNX] Saved deployable ONNX model atomically to: {target} ({size_mb:.2f} MB)")

        if output_onnx_path and output_onnx_path != temp_onnx:
            atomic_copy_file(temp_onnx, output_onnx_path, validate_fn=validate_onnx_file)

        # Clean up temp intermediate ONNX file
        if os.path.exists(temp_onnx) and temp_onnx != output_onnx_path:
            os.remove(temp_onnx)

        final_model_path = backend_onnx

        print("\n" + "=" * 60)
        print("           ONNX MODEL EXPORT & DEPLOYMENT COMPLETE")
        print("=" * 60)
        print(f" Frontend Model: {frontend_onnx}")
        print(f" Frontend Meta:  {frontend_json}")
        print(f" Backend Model:  {backend_onnx}")
        print(f" Backend Meta:   {backend_json}")
        print("=" * 60)
    else:
        # When deploy=False, outputs remain strictly in candidate or temporary locations
        if output_onnx_path and output_onnx_path != temp_onnx:
            atomic_copy_file(temp_onnx, output_onnx_path, validate_fn=validate_onnx_file)
            if os.path.exists(temp_onnx):
                os.remove(temp_onnx)
            final_model_path = output_onnx_path
        size_mb = os.path.getsize(final_model_path) / (1024 * 1024)
        print(f"[Export ONNX] Non-deployed ONNX model saved to: {final_model_path} ({size_mb:.2f} MB)")

    return final_model_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export Trained PlantVillage Model to ONNX")
    parser.add_argument("--checkpoint", type=str, default=DEFAULT_CHECKPOINT_PATH)
    parser.add_argument("--output-onnx", type=str, default=None, help="Custom output path for exported ONNX model")
    parser.add_argument(
        "--no-deploy",
        action="store_true",
        help="Skip deploying model and metadata to frontend/backend production directories",
    )
    args = parser.parse_args()
    export_model_to_onnx(
        checkpoint_path=args.checkpoint,
        output_onnx_path=args.output_onnx,
        deploy=not args.no_deploy,
    )
