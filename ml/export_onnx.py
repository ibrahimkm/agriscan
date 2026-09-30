import os
import sys
import json
import argparse
from pathlib import Path

# Add ml folder and project root to sys.path to support execution from any directory
_ml_dir = str(Path(__file__).resolve().parent)
_proj_root = str(Path(__file__).resolve().parent.parent)
for p in [_ml_dir, _proj_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

import torch
import numpy as np
import onnx
import onnxruntime as ort

try:
    from ml.model import get_model
except ImportError:
    from model import get_model

try:
    from ml.dataset import LEAF_DISEASE_CLASSES
except ImportError:
    from dataset import LEAF_DISEASE_CLASSES

DEFAULT_CHECKPOINT_PATH = os.path.join(_ml_dir, "checkpoints", "best_leaf_model.pth")
DEFAULT_OUTPUT_ONNX = os.path.join(_proj_root, "frontend", "public", "models", "leaf_disease_model.onnx")
DEFAULT_OUTPUT_JSON = os.path.join(_proj_root, "frontend", "public", "models", "disease_classes.json")

# Multilingual agronomic guidance catalog for all detected diseases
DISEASE_METADATA = {
    "Tomato___Early_blight": {
        "crop": "Tomato",
        "disease": "Early Blight",
        "scientificName": "Alternaria solani",
        "severity": "moderate",
        "affectedPercentage": 32,
        "descriptions": {
            "en": {
                "whatIsIt": "Early blight is a fungal disease caused by Alternaria solani affecting tomato and potato foliage. It manifests as dark concentric rings surrounded by yellow halos.",
                "symptoms": ["Dark brown spots with concentric target-rings", "Chlorotic yellowing around leaf lesions", "Starts on lower, mature leaves"],
                "recommendedAction": "Apply a copper-based fungicide (Copper Hydroxide) or Chlorothalonil early morning and ensure proper spacing for airflow.",
                "immediateActionTitle": "Isolate & Prune Foliage",
                "immediateActionDesc": "Prune infected bottom leaves and safely destroy them to halt fungal spore progression."
            },
            "hi": {
                "whatIsIt": "अगेती झुलसा (Early Blight) एक फफूंद जनित रोग है जो पत्तियों पर काले छल्लेदार धब्बे और पीलापन पैदा करता है।",
                "symptoms": ["पत्तियों पर गहरे भूरे रंग के संकेंद्रित छल्ले", "धब्बों के चारों ओर पीलापन", "निचली पत्तियों से शुरू होता है"],
                "recommendedAction": "तुरंत कॉपर युक्त कवकनाशी का छिड़काव करें और पौधों के बीच हवा का प्रवाह सुनिश्चित करें।",
                "immediateActionTitle": "प्रभावित पत्तियां हटाएं",
                "immediateActionDesc": "रोगग्रस्त निचली पत्तियों को तुरंत काटकर नष्ट कर दें ताकि फफूंद न फैले।"
            },
            "te": {
                "whatIsIt": "ముందస్తు మచ్చ తెగులు ఆకులపై గోధుమ రంగు వలయాలు మరియు పసుపు రంగు మచ్చలను కలిగిస్తుంది.",
                "symptoms": ["ఆకులపై వలయాకారపు గోధుమ రంగు మచ్చలు", "మచ్చల చుట్టూ పసుపు రంగు అంచులు", "దిగువ పాత ఆకుల నుండి మొదలవుతుంది"],
                "recommendedAction": "వెంటనే రాగి ఆధారిత శిలీంధ్ర సంహారిణి (కాపర్ హైడ్రాక్సైడ్) పిచికారీ చేయండి.",
                "immediateActionTitle": "ఆకులను తొలగించండి",
                "immediateActionDesc": "తెగులు సోకిన దిగువ ఆకులను కత్తిరించి నాశనం చేయండి."
            },
            "ta": {
                "whatIsIt": "ஆரம்பகால கருகல் நோய் இலைகளில் அடர் பழுப்பு நிற வளையங்களையும் மஞ்சள் புள்ளிகளையும் உருவாக்குகிறது.",
                "symptoms": ["இலைகளில் அடர் பழுப்பு நிற வட்ட வடிவ புள்ளிகள்", "புள்ளிகளை சுற்றி மஞ்சள் வளையம்", "கீழ் இலைகளில் தொடங்கி பரவுகிறது"],
                "recommendedAction": "உடனடியாக காப்பர் சார்ந்த பூஞ்சைக்கொல்லி தெளிக்கவும்.",
                "immediateActionTitle": "பாதிக்கப்பட்ட இலைகளை அகற்றவும்",
                "immediateActionDesc": "நோய் பரவாமல் தடுக்க பாதிக்கப்பட்ட கீழ் இலைகளை வெட்டி அழிக்கவும்."
            }
        }
    },
    "Tomato___Late_blight": {
        "crop": "Tomato",
        "disease": "Late Blight",
        "scientificName": "Phytophthora infestans",
        "severity": "severe",
        "affectedPercentage": 45,
        "descriptions": {
            "en": {
                "whatIsIt": "Late blight is a destructive water-mold pathogen causing large, irregular water-soaked lesions that turn dark brown and rot rapidly.",
                "symptoms": ["Large irregular water-soaked spots", "White fuzzy mold on underside of leaves in wet weather", "Rapid wilting and leaf collapse"],
                "recommendedAction": "Apply systemic fungicides like Metalaxyl or Mancozeb immediately. Avoid sprinkler irrigation.",
                "immediateActionTitle": "Emergency Protective Spray",
                "immediateActionDesc": "Apply systemic fungicide within 12 hours and remove collapsing vines."
            },
            "hi": {
                "whatIsIt": "पछेती झुलसा (Late Blight) बहुत तेजी से फैलने वाला रोग है जिससे पत्तियां सड़ने और सूखने लगती हैं।",
                "symptoms": ["पत्तियों पर बड़े अनियमित काले धब्बे", "पत्ती के नीचे सफेद फफूंद", "पौधे का तेजी से मुरझाना"],
                "recommendedAction": "तुरंत मैंकोजेब या मेटालेक्सिल कवकनाशी का छिड़काव करें।",
                "immediateActionTitle": "आपातकालीन कवकनाशी स्प्रे",
                "immediateActionDesc": "12 घंटे के भीतर दवा का छिड़काव करें और खराब शाखाओं को हटाएं।"
            }
        }
    },
    "Tomato___healthy": {
        "crop": "Tomato",
        "disease": "Healthy Leaf",
        "scientificName": "Solanum lycopersicum",
        "severity": "none",
        "affectedPercentage": 0,
        "descriptions": {
            "en": {
                "whatIsIt": "Leaf tissue is vibrant, robust, and shows no symptoms of fungal, bacterial, or viral disease.",
                "symptoms": ["Uniform green pigmentation", "Intact leaf margins", "No necrotic spots or yellowing"],
                "recommendedAction": "Maintain balanced N-P-K fertilization and consistent soil moisture.",
                "immediateActionTitle": "Routine Maintenance",
                "immediateActionDesc": "Continue regular monitoring and optimal drip irrigation."
            },
            "hi": {
                "whatIsIt": "पत्ती पूरी तरह स्वस्थ है और इसमें किसी भी बीमारी के लक्षण नहीं हैं।",
                "symptoms": ["एकसमान हरा रंग", "मजबूत पत्ती संरचना", "कोई धब्बा या पीलापन नहीं"],
                "recommendedAction": "नियमित रूप से संतुलित खाद और पानी देते रहें।",
                "immediateActionTitle": "नियमित देखभाल",
                "immediateActionDesc": "फसल की सामान्य निगरानी जारी रखें।"
            }
        }
    },
    "Potato___Early_blight": {
        "crop": "Potato",
        "disease": "Early Blight",
        "scientificName": "Alternaria solani",
        "severity": "moderate",
        "affectedPercentage": 28,
        "descriptions": {
            "en": {
                "whatIsIt": "Potato early blight produces target-like circular dark brown lesions on foliage, impairing tuber sizing.",
                "symptoms": ["Concentric dark brown rings", "Yellow halos on foliage", "Premature defoliation"],
                "recommendedAction": "Apply protectant fungicides (Chlorothalonil, Mancozeb) every 7-10 days under warm humid conditions.",
                "immediateActionTitle": "Prevent Spore Spread",
                "immediateActionDesc": "Spray protectant fungicide and avoid excessive nitrogen stress."
            }
        }
    },
    "Potato___Late_blight": {
        "crop": "Potato",
        "disease": "Late Blight",
        "scientificName": "Phytophthora infestans",
        "severity": "severe",
        "affectedPercentage": 52,
        "descriptions": {
            "en": {
                "whatIsIt": "Late blight can completely defoliate potato canopies in days and infect tubers with dry rot.",
                "symptoms": ["Water-soaked dark lesions", "White sporulation on leaf underside", "Foul odor and vine collapse"],
                "recommendedAction": "Immediately spray Cymoxanil + Mancozeb or Dimethomorph formulations.",
                "immediateActionTitle": "Critical Chemical Intervention",
                "immediateActionDesc": "Halt overhead irrigation and apply systemic curative fungicide immediately."
            }
        }
    },
    "Potato___healthy": {
        "crop": "Potato",
        "disease": "Healthy Potato Leaf",
        "scientificName": "Solanum tuberosum",
        "severity": "none",
        "affectedPercentage": 0,
        "descriptions": {
            "en": {
                "whatIsIt": "The potato foliage is vigorous and free from pathological distress.",
                "symptoms": ["Healthy chlorophyll distribution", "No leaf blights or curling"],
                "recommendedAction": "Ensure regular hilling and balanced potassium application.",
                "immediateActionTitle": "Preventive Care",
                "immediateActionDesc": "Keep canopy aerated and scout fields weekly."
            }
        }
    },
    "Rice___Leaf_Blast": {
        "crop": "Rice",
        "disease": "Rice Leaf Blast",
        "scientificName": "Magnaporthe oryzae",
        "severity": "severe",
        "affectedPercentage": 42,
        "descriptions": {
            "en": {
                "whatIsIt": "Rice blast is a destructive fungal disease causing diamond or spindle-shaped lesions with gray centers and brown margins.",
                "symptoms": ["Spindle/diamond-shaped lesions", "Gray or whitish center with reddish-brown border", "Severe lodging under heavy attack"],
                "recommendedAction": "Apply Tricyclazole 75 WP (0.6g/L) or Isoprothiolane at the onset of lesions.",
                "immediateActionTitle": "Apply Tricyclazole",
                "immediateActionDesc": "Spray blast-specific fungicide and avoid excessive nitrogen application."
            }
        }
    },
    "Rice___Brown_Spot": {
        "crop": "Rice",
        "disease": "Rice Brown Spot",
        "scientificName": "Bipolaris oryzae",
        "severity": "moderate",
        "affectedPercentage": 30,
        "descriptions": {
            "en": {
                "whatIsIt": "Brown spot causes oval to circular dark brown spots across rice leaf blades and panicles, often linked to nutrient-deficient soil.",
                "symptoms": ["Small cylindrical to oval brown spots", "Yellowish halo surrounding dark core", "Reduced grain filling"],
                "recommendedAction": "Apply balanced potassium and spray Propiconazole or Hexaconazole.",
                "immediateActionTitle": "Soil Nutrition & Spray",
                "immediateActionDesc": "Correct soil potash deficiency and apply foliar fungicide."
            }
        }
    },
    "Rice___healthy": {
        "crop": "Rice",
        "disease": "Healthy Rice Leaf",
        "scientificName": "Oryza sativa",
        "severity": "none",
        "affectedPercentage": 0,
        "descriptions": {
            "en": {
                "whatIsIt": "Rice leaf shows clean erect blades with strong tillering and no fungal spots.",
                "symptoms": ["Bright green foliage", "Smooth leaf surface without lesions"],
                "recommendedAction": "Maintain optimal standing water depth (2-5cm) during active tillering.",
                "immediateActionTitle": "Water Management",
                "immediateActionDesc": "Maintain recommended water levels and split nitrogen doses."
            }
        }
    }
}

def export_model_to_onnx(
    checkpoint_path="ml/checkpoints/best_leaf_model.pth",
    output_onnx_path="frontend/public/models/leaf_disease_model.onnx",
    output_json_path="frontend/public/models/disease_classes.json",
    img_size=224
):
    os.makedirs(os.path.dirname(output_onnx_path), exist_ok=True)
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    
    print(f"[ONNX Export] Loading model from {checkpoint_path}...")
    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    classes = checkpoint.get('classes', LEAF_DISEASE_CLASSES)
    model_variant = checkpoint.get('model_variant', 'small')
    
    # Initialize and load weights
    model = get_model(num_classes=len(classes), model_variant=model_variant, pretrained=False)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    
    # Create dummy input tensor (Batch, Channels, Height, Width)
    dummy_input = torch.randn(1, 3, img_size, img_size, dtype=torch.float32)
    
    print(f"[ONNX Export] Exporting to ONNX: {output_onnx_path} ...")
    torch.onnx.export(
        model,
        (dummy_input,),
        output_onnx_path,
        export_params=True,
        opset_version=14,
        do_constant_folding=True,
        input_names=['input_image'],
        output_names=['class_probabilities'],
        dynamic_axes={
            'input_image': {0: 'batch_size'},
            'class_probabilities': {0: 'batch_size'}
        },
        dynamo=False
    )
    
    # Verify ONNX model integrity
    onnx_model = onnx.load(output_onnx_path)
    onnx.checker.check_model(onnx_model)
    print("  [Validation] ONNX model structure verified successfully!")
    
    # Run test inference with ONNX Runtime to verify parity with PyTorch
    ort_session = ort.InferenceSession(output_onnx_path)
    ort_inputs = {ort_session.get_inputs()[0].name: dummy_input.numpy()}
    ort_outs = ort_session.run(None, ort_inputs)
    
    with torch.no_grad():
        pytorch_outs = model(dummy_input).numpy()
        
    np.testing.assert_allclose(pytorch_outs, ort_outs[0], rtol=1e-03, atol=1e-04)  # pyrefly: ignore[no-matching-overload]
    print("  [Validation] PyTorch and ONNX Runtime outputs match within tight tolerance!")
    
    file_size_mb = os.path.getsize(output_onnx_path) / (1024 * 1024)
    print(f"  [ONNX Export] Exported ONNX File Size: {file_size_mb:.2f} MB (Ultra-compact for Offline Browser WASM!)")
    
    # Generate Rich Disease Metadata JSON for Frontend
    classes_metadata = []
    for idx, cls_name in enumerate(classes):
        parts = cls_name.split("___")
        crop = parts[0].replace("_", " ")
        disease_clean = parts[1].replace("_", " ") if len(parts) > 1 else "Unknown"
        
        meta = DISEASE_METADATA.get(cls_name, {
            "crop": crop,
            "disease": disease_clean,
            "scientificName": f"{crop} Pathogen",
            "severity": "none" if "healthy" in cls_name.lower() else "moderate",
            "affectedPercentage": 0 if "healthy" in cls_name.lower() else 30,
            "descriptions": {
                "en": {
                    "whatIsIt": f"{disease_clean} is a condition affecting {crop} leaves.",
                    "symptoms": [f"Visual lesions characteristic of {disease_clean}", "Altered leaf pigmentation"],
                    "recommendedAction": "Inspect leaf canopy, isolate infected sections, and consult local agronomic guidelines.",
                    "immediateActionTitle": "Isolate & Monitor",
                    "immediateActionDesc": "Isolate the plant and monitor surrounding foliage."
                }
            }
        })
        
        classes_metadata.append({
            "index": idx,
            "rawClass": cls_name,
            "crop": meta.get("crop", crop),
            "disease": meta.get("disease", disease_clean),
            "scientificName": meta.get("scientificName", f"{crop} leaf"),
            "severity": meta.get("severity", "moderate"),
            "affectedPercentage": meta.get("affectedPercentage", 25),
            "descriptions": meta.get("descriptions", {})
        })
        
    final_json = {
        "modelName": f"MobileNetV3-{model_variant.capitalize()}-LeafDisease",
        "inputShape": [1, 3, img_size, img_size],
        "normalization": {
            "mean": [0.485, 0.456, 0.406],
            "std": [0.229, 0.224, 0.225]
        },
        "classes": classes_metadata
    }
    
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(final_json, f, indent=2, ensure_ascii=False)
        
    print(f"[JSON Metadata] Generated {output_json_path} with {len(classes_metadata)} disease profiles.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export PyTorch model to ONNX for Offline Web Inference")
    parser.add_argument("--checkpoint", type=str, default=DEFAULT_CHECKPOINT_PATH)
    parser.add_argument("--output_onnx", type=str, default=DEFAULT_OUTPUT_ONNX)
    parser.add_argument("--output_json", type=str, default=DEFAULT_OUTPUT_JSON)
    args = parser.parse_args()
    
    export_model_to_onnx(
        checkpoint_path=args.checkpoint,
        output_onnx_path=args.output_onnx,
        output_json_path=args.output_json
    )
