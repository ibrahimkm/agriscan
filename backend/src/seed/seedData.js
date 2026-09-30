import mongoose from 'mongoose';
import bcrypt from 'bcryptjs';
import { connectDB } from '../config/db.js';
import User from '../models/User.js';
import Crop from '../models/Crop.js';
import Disease from '../models/Disease.js';
import Diagnosis from '../models/Diagnosis.js';
import YoloDetection from '../models/YoloDetection.js';

export const seedDatabase = async () => {
  console.log('[Seed] Seeding database with realistic agricultural data for multiple farmers...');

  // Clear existing
  await User.deleteMany({});
  await Crop.deleteMany({});
  await Disease.deleteMany({});
  await Diagnosis.deleteMany({});
  await YoloDetection.deleteMany({});

  const salt = await bcrypt.genSalt(10);
  const passwordHash = await bcrypt.hash('password123', salt);

  // 1. Create Multiple Farmer Accounts
  const raviUser = await User.create({
    name: 'Ravi Sharma',
    email: 'farmer@agriscan.io',
    phone: '+91 98765 43210',
    passwordHash,
    preferredLanguage: 'en',
    location: {
      farmName: 'Surya Agro Farms',
      region: 'Ludhiana, Punjab',
      climateZone: 'Subtropical Semi-arid',
      latitude: 30.901,
      longitude: 75.8573,
    },
    avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80',
  });

  const priyaUser = await User.create({
    name: 'Priya Patel',
    email: 'priya@agriscan.io',
    phone: '+91 98234 56789',
    passwordHash,
    preferredLanguage: 'hi',
    location: {
      farmName: 'Patel Organic Fields',
      region: 'Rajkot, Gujarat',
      climateZone: 'Semi-arid Tropical',
      latitude: 22.3039,
      longitude: 70.8022,
    },
    avatar: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150&auto=format&fit=crop&q=80',
  });

  const carlosUser = await User.create({
    name: 'Carlos Rodriguez',
    email: 'carlos@agriscan.io',
    phone: '+52 55 1234 5678',
    passwordHash,
    preferredLanguage: 'es',
    location: {
      farmName: 'Rancho Los Arcos',
      region: 'Michoacán, Mexico',
      climateZone: 'Subtropical Highland',
      latitude: 19.4326,
      longitude: -99.1332,
    },
    avatar: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80',
  });

  console.log(`[Seed] Created 3 Farmer Accounts (all password: password123):`);
  console.log(` - ${raviUser.name} (${raviUser.email})`);
  console.log(` - ${priyaUser.name} (${priyaUser.email})`);
  console.log(` - ${carlosUser.name} (${carlosUser.email})`);

  // 2. Create Disease Reference Library
  const diseases = await Disease.create([
    {
      diseaseName: 'Early Blight',
      scientificName: 'Alternaria solani',
      cropTypes: ['Tomato', 'Potato'],
      defaultSeverity: 'moderate',
      microscopicImageUrl: 'https://images.unsplash.com/photo-1530836369250-ef72a3f5cda8?w=800&auto=format&fit=crop&q=80',
      sampleImageUrl: 'https://images.unsplash.com/photo-1592417817098-8f3d6eb2260f?w=800&auto=format&fit=crop&q=80',
      description: 'Early blight is a fungal disease caused by Alternaria solani that primarily affects tomato and potato plants. It manifests as dark concentric rings with chlorotic halos, starting on the lower leaves and moving upwards as the canopy matures.',
      whyItHappens: {
        conditions: [
          'High humidity (>80%) accompanied by warm temperatures (24°C - 29°C)',
          'Frequent overhead irrigation or prolonged rain splashing fungal spores from soil',
          'Poor plant canopy spacing impeding rapid leaf drying',
        ],
        pathogenSpread: 'Conidia (spores) overwinter in infected plant debris and soil, becoming airborne or water-splashed onto lower leaves during irrigation or rain.',
        optimalTemp: '24°C - 29°C',
        optimalHumidity: '85%+',
      },
      symptoms: {
        summary: [
          'Dark brown spots with concentric rings (target-like pattern)',
          'Yellowing around lesions (chlorosis)',
          'Starts on lower, older leaves and advances upward',
        ],
        onLeaves: 'Small circular brown spots expanding up to 1/2 inch with concentric rings resembling a target board, bordered by yellow chlorotic margins.',
        onStems: 'Dark, elongated, slightly sunken lesions with concentric markings that can girdle stems near the soil line (collar rot).',
        onFruit: 'Dark, leathery, sunken spots near the stem attachment (calyx) that expand into concentric sunken zones.',
      },
      immediateAction: {
        title: 'Immediate Action Required',
        description: 'Remove and destroy heavily infected lower leaves to prevent spore spread. Do not compost these leaves.',
        priority: 'High Priority',
      },
      treatmentSteps: [
        {
          id: 'step-1',
          title: 'Apply Fungicide',
          description: 'Apply a copper-based fungicide or chlorothalonil immediately.',
        },
        {
          id: 'step-2',
          title: 'Improve Airflow',
          description: 'Prune dense foliage to ensure better air circulation around the plants.',
        },
        {
          id: 'step-3',
          title: 'Adjust Irrigation',
          description: 'Switch to drip irrigation to keep leaves dry. Avoid overhead watering.',
        },
      ],
      preventionTips: [
        'Rotate crops annually (avoid nightshades in the same spot for 2-3 years).',
        'Ensure adequate spacing between plants next season (at least 60cm).',
        'Apply organic straw mulch to prevent soil splashing onto foliage.',
        'Use disease-resistant tomato varieties for future plantings.',
        'Regularly sanitize pruning tools with 70% alcohol between cuts.',
      ],
      safetyNotice: 'Always wear appropriate protective equipment when applying fungicides. Adhere strictly to the pre-harvest interval (PHI) specified on the product label before harvesting any fruit.',
    },
    {
      diseaseName: 'Tomato Late Blight',
      scientificName: 'Phytophthora infestans',
      cropTypes: ['Tomato', 'Potato'],
      defaultSeverity: 'severe',
      microscopicImageUrl: 'https://images.unsplash.com/photo-1576086213369-97a306d36557?w=800&auto=format&fit=crop&q=80',
      sampleImageUrl: 'https://images.unsplash.com/photo-1592417817098-8f3d6eb2260f?w=800&auto=format&fit=crop&q=80',
      description: 'Late blight is a highly destructive disease caused by a fungus-like oomycete organism. It affects tomatoes and potatoes, often striking later in the growing season. It is the same pathogen that caused the Irish Potato Famine, and remains one of the most serious threats to tomato farmers today.',
      whyItHappens: {
        conditions: [
          'Cool, wet weather: High humidity (above 90%) and temperatures between 60°F and 70°F (15°C - 21°C)',
          'Wind and Rain: Spores are easily carried by wind over miles and splashed by rain onto healthy plants',
        ],
        pathogenSpread: 'Sporangia germinate directly in cool water films, producing swimming zoospores that penetrate stomata within 2 hours.',
        optimalTemp: '15°C - 21°C',
        optimalHumidity: '90%+',
      },
      symptoms: {
        summary: [
          'Large, irregular water-soaked spots that turn dark brown',
          'White downy fungal growth on leaf undersides in high humidity',
          'Rapid total canopy wilting within 48 to 72 hours',
        ],
        onLeaves: 'Large, irregular, water-soaked spots that turn dark brown. Often surrounded by a pale green or pale yellow halo.',
        onStems: 'Dark brown to black lesions that can encircle the stem, causing the plant above the lesion to wilt and die.',
        onFruit: 'Firm, dark, greasy-looking spots that can expand rapidly to cover the entire tomato, rendering it inedible.',
      },
      immediateAction: {
        title: 'Severe Risk: Action Required Immediately',
        description: 'Late blight spreads rapidly in cool, wet weather and can destroy an entire tomato crop within days if left untreated.',
        priority: 'High Priority',
      },
      treatmentSteps: [
        {
          id: 'step-1',
          title: 'Spray Systemic Oomycete Fungicide',
          description: 'Apply Mandipropamid, Cymoxanil, or Dimethomorph combined with Mancozeb.',
        },
        {
          id: 'step-2',
          title: 'Eradicate Inoculum Source',
          description: 'Bag and incinerate or deeply bury severely blighted plants immediately.',
        },
        {
          id: 'step-3',
          title: 'Reduce Canopy Moisture',
          description: 'Halt all overhead watering and facilitate maximum ventilation.',
        },
      ],
      preventionTips: [
        'Plant certified disease-free transplants and seed tubers.',
        'Destroy cull piles and volunteer potatoes near tomato fields.',
        'Apply protective copper fungicides prior to rainy cool periods.',
        'Choose late-blight resistant cultivars (e.g., Mountain Magic, Defiant).',
      ],
      safetyNotice: 'Always wear protective respiratory gear and chemical-resistant gloves when handling oomycete fungicides. Observe 7-day PHI.',
    },
    {
      diseaseName: 'Septoria Brown Spot',
      scientificName: 'Septoria glycines / Septoria lycopersici',
      cropTypes: ['Soybeans', 'Tomato'],
      defaultSeverity: 'moderate',
      microscopicImageUrl: 'https://images.unsplash.com/photo-1530836369250-ef72a3f5cda8?w=800&auto=format&fit=crop&q=80',
      sampleImageUrl: 'https://images.unsplash.com/photo-1574943320219-553eb213f72d?w=800&auto=format&fit=crop&q=80',
      description: 'Septoria brown spot produces numerous small, circular brown lesions with grayish centers and dark borders. As spots coalesce, foliage yellows and prematurely defoliates from the lower canopy upward.',
      whyItHappens: {
        conditions: ['Frequent summer showers', 'Warm temperatures (20°C - 25°C)', 'Dense leaf canopies'],
        pathogenSpread: 'Pycnidia spores disperse via rain splashes and farm equipment movement.',
        optimalTemp: '20°C - 26°C',
        optimalHumidity: '80%+',
      },
      symptoms: {
        summary: [
          'Multiple tiny dark spots with distinct dark margins',
          'Lower leaf chlorosis and premature drop',
          'Tiny black specks (pycnidia) visible inside lesions under magnification',
        ],
        onLeaves: 'Circular spots 1.5 to 3mm in diameter with dark borders and tan centers studded with black fruiting bodies.',
        onStems: 'Elongated brown superficial spots on petioles.',
        onFruit: 'Rarely affects fruit directly, but defoliation leads to sunscald.',
      },
      immediateAction: {
        title: 'Moderate Severity Action',
        description: 'Spray protective strobilurin or copper fungicide to halt upward progression into upper trifoliates.',
        priority: 'High Priority',
      },
      treatmentSteps: [
        {
          id: 'step-1',
          title: 'Apply Azoxystrobin or Chlorothalonil',
          description: 'Spray when symptoms appear on lower canopy before bloom/pod development.',
        },
        {
          id: 'step-2',
          title: 'Improve Drainage',
          description: 'Eliminate standing puddles in field furrows.',
        },
      ],
      preventionTips: [
        'Tillage to bury residue in high-risk fields.',
        '2-year rotation with non-host grass crops like corn or wheat.',
      ],
      safetyNotice: 'Ensure correct dilution rates to avoid phytotoxicity.',
    },
    {
      diseaseName: 'Rice Blast',
      scientificName: 'Magnaporthe oryzae',
      cropTypes: ['Rice'],
      defaultSeverity: 'severe',
      microscopicImageUrl: 'https://images.unsplash.com/photo-1576086213369-97a306d36557?w=800&auto=format&fit=crop&q=80',
      sampleImageUrl: 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=800&auto=format&fit=crop&q=80',
      description: 'Rice blast is one of the most destructive diseases of rice worldwide. It causes diamond or spindle-shaped lesions on leaves and neck rot on panicles, causing complete grain sterilization.',
      whyItHappens: {
        conditions: ['High nitrogen fertilization', 'Prolonged dew periods', 'Temperatures between 22°C - 28°C'],
        pathogenSpread: 'Airborne conidia travel long distances on air currents.',
        optimalTemp: '24°C - 28°C',
        optimalHumidity: '90%+',
      },
      symptoms: {
        summary: ['Spindle-shaped lesions with gray/white center and brown margin', 'Rotting panicle neck nodes', 'Whiteheads and blank grain panicles'],
        onLeaves: 'Spindle-shaped lesions with pointed ends, gray centers, and brown borders.',
        onStems: 'Blackened node rot causing upper stem breakage.',
        onFruit: 'Empty whitish panicles standing erect instead of drooping with grain weight.',
      },
      immediateAction: {
        title: 'Critical Emergency Treatment',
        description: 'Apply Tricyclazole or Isoprothiolane immediately to protect emerging panicles.',
        priority: 'High Priority',
      },
      treatmentSteps: [
        { id: 'step-1', title: 'Spray Tricyclazole 75% WP', description: 'Apply 0.6g/liter at early tillering and boot leaf emergence.' },
        { id: 'step-2', title: 'Reduce Excess Nitrogen', description: 'Split nitrogen fertilizer applications; avoid excessive urea.' },
      ],
      preventionTips: ['Use blast-resistant rice cultivars.', 'Treat seeds with Carbendazim before sowing.'],
      safetyNotice: 'Wear water-repellent boots and PPE in flooded paddy fields.',
    },
  ]);

  console.log(`[Seed] Created ${diseases.length} disease references`);

  // 3. Create Crops for Ravi Sharma (matching Stitch UI)
  const raviCrops = await Crop.create([
    {
      userId: raviUser._id,
      cropName: 'Tomato',
      cropType: 'Solanum lycopersicum',
      variety: 'Roma VF / San Marzano',
      imageUrl: 'https://images.unsplash.com/photo-1592417817098-8f3d6eb2260f?w=400&auto=format&fit=crop&q=80',
      fieldInfo: { block: 'Block B', acreage: 3.2, soilType: 'Sandy Loam' },
      healthStatus: 'at_risk',
      diagnosesCount: 12,
      lastDiagnosis: {
        date: new Date('2026-08-24T09:15:00Z'),
        diseaseName: 'Early Blight',
        severity: 'moderate',
      },
    },
    {
      userId: raviUser._id,
      cropName: 'Winter Wheat',
      cropType: 'Triticum aestivum',
      variety: 'HD-2967',
      imageUrl: 'https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?w=400&auto=format&fit=crop&q=80',
      fieldInfo: { block: 'Block A', acreage: 5.0, soilType: 'Alluvial Loam' },
      healthStatus: 'healthy',
      diagnosesCount: 4,
      lastDiagnosis: {
        date: new Date('2026-08-20T14:30:00Z'),
        diseaseName: 'Healthy Canopy',
        severity: 'healthy',
      },
    },
    {
      userId: raviUser._id,
      cropName: 'Soybeans',
      cropType: 'Glycine max',
      variety: 'JS-335',
      imageUrl: 'https://images.unsplash.com/photo-1574943320219-553eb213f72d?w=400&auto=format&fit=crop&q=80',
      fieldInfo: { block: 'Block B', acreage: 4.0, soilType: 'Clay Loam' },
      healthStatus: 'at_risk',
      diagnosesCount: 6,
      lastDiagnosis: {
        date: new Date('2026-08-24T09:15:00Z'),
        diseaseName: 'Septoria Brown Spot',
        severity: 'moderate',
      },
    },
    {
      userId: raviUser._id,
      cropName: 'Rice',
      cropType: 'Oryza sativa',
      variety: 'Basmati Pusa 1121',
      imageUrl: 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400&auto=format&fit=crop&q=80',
      fieldInfo: { block: 'Block C', acreage: 6.5, soilType: 'Clay Soil' },
      healthStatus: 'healthy',
      diagnosesCount: 5,
      lastDiagnosis: {
        date: new Date('2026-08-22T11:00:00Z'),
        diseaseName: 'Healthy Foliage',
        severity: 'healthy',
      },
    },
    {
      userId: raviUser._id,
      cropName: 'Potato',
      cropType: 'Solanum tuberosum',
      variety: 'Kufri Jyoti',
      imageUrl: 'https://images.unsplash.com/photo-1518977676601-b53f82aba655?w=400&auto=format&fit=crop&q=80',
      fieldInfo: { block: 'Block D', acreage: 2.8, soilType: 'Silt Loam' },
      healthStatus: 'diseased',
      diagnosesCount: 8,
      lastDiagnosis: {
        date: new Date('2026-08-23T16:45:00Z'),
        diseaseName: 'Tomato Late Blight',
        severity: 'severe',
      },
    },
    {
      userId: raviUser._id,
      cropName: 'Cotton',
      cropType: 'Gossypium hirsutum',
      variety: 'Bt Cotton RCH-659',
      imageUrl: 'https://images.unsplash.com/photo-1606041008023-472dfb5e530f?w=400&auto=format&fit=crop&q=80',
      fieldInfo: { block: 'Block E', acreage: 3.5, soilType: 'Black Cotton Soil' },
      healthStatus: 'healthy',
      diagnosesCount: 2,
    },
    {
      userId: raviUser._id,
      cropName: 'Maize',
      cropType: 'Zea mays',
      variety: 'Pioneer 3396',
      imageUrl: 'https://images.unsplash.com/photo-1551754655-cd27e38d2076?w=400&auto=format&fit=crop&q=80',
      fieldInfo: { block: 'Block F', acreage: 4.5, soilType: 'Loamy' },
      healthStatus: 'healthy',
      diagnosesCount: 15,
    },
    {
      userId: raviUser._id,
      cropName: 'Sunflower',
      cropType: 'Helianthus annuus',
      variety: 'KBSH-44',
      imageUrl: 'https://images.unsplash.com/photo-1597848212624-a19eb35e2651?w=400&auto=format&fit=crop&q=80',
      fieldInfo: { block: 'Block G', acreage: 1.8, soilType: 'Sandy' },
      healthStatus: 'healthy',
      diagnosesCount: 1,
    },
  ]);

  // 4. Create Crops for Priya Patel (Gujarat)
  await Crop.create([
    {
      userId: priyaUser._id,
      cropName: 'Cotton',
      cropType: 'Gossypium hirsutum',
      variety: 'Organic Shankar-6',
      imageUrl: 'https://images.unsplash.com/photo-1606041008023-472dfb5e530f?w=400&auto=format&fit=crop&q=80',
      fieldInfo: { block: 'North Plot', acreage: 6.0, soilType: 'Black Soil' },
      healthStatus: 'healthy',
      diagnosesCount: 3,
    },
    {
      userId: priyaUser._id,
      cropName: 'Groundnut',
      cropType: 'Arachis hypogaea',
      variety: 'GG-20',
      imageUrl: 'https://images.unsplash.com/photo-1568644396922-5c3bfae12521?w=400&auto=format&fit=crop&q=80',
      fieldInfo: { block: 'South Plot', acreage: 3.5, soilType: 'Sandy Soil' },
      healthStatus: 'healthy',
      diagnosesCount: 1,
    },
    {
      userId: priyaUser._id,
      cropName: 'Wheat',
      cropType: 'Triticum aestivum',
      variety: 'Lokwan',
      imageUrl: 'https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?w=400&auto=format&fit=crop&q=80',
      fieldInfo: { block: 'East Field', acreage: 4.0, soilType: 'Loam' },
      healthStatus: 'at_risk',
      diagnosesCount: 4,
    },
  ]);

  // 5. Create Crops for Carlos Rodriguez (Mexico)
  await Crop.create([
    {
      userId: carlosUser._id,
      cropName: 'Tomato',
      cropType: 'Solanum lycopersicum',
      variety: 'Jitomatillo Heirloom',
      imageUrl: 'https://images.unsplash.com/photo-1592417817098-8f3d6eb2260f?w=400&auto=format&fit=crop&q=80',
      fieldInfo: { block: 'Sector 1', acreage: 5.0, soilType: 'Volcanic Soil' },
      healthStatus: 'healthy',
      diagnosesCount: 7,
    },
    {
      userId: carlosUser._id,
      cropName: 'Maize',
      cropType: 'Zea mays',
      variety: 'Maíz Criollo Blanco',
      imageUrl: 'https://images.unsplash.com/photo-1551754655-cd27e38d2076?w=400&auto=format&fit=crop&q=80',
      fieldInfo: { block: 'Sector 2', acreage: 8.0, soilType: 'Rich Loam' },
      healthStatus: 'healthy',
      diagnosesCount: 2,
    },
  ]);

  // 6. Create Sample Diagnoses for Ravi Sharma
  const tomatoCrop = raviCrops[0];
  const soybeanCrop = raviCrops[2];

  const diag1 = await Diagnosis.create({
    userId: raviUser._id,
    cropId: tomatoCrop._id,
    cropName: 'Tomato',
    cropVariety: 'San Marzano Heirloom',
    fieldBlock: 'Block B',
    imageUrl: 'https://images.unsplash.com/photo-1592417817098-8f3d6eb2260f?w=800&auto=format&fit=crop&q=80',
    predictedDisease: 'Early Blight',
    scientificName: 'Alternaria solani',
    confidence: 94,
    severity: 'moderate',
    affectedPercentage: 32,
    whatIsIt: 'Early blight is a fungal disease caused by Alternaria solani that primarily affects tomato and potato plants. It manifests as dark concentric rings with chlorotic halos.',
    symptoms: [
      'Dark brown spots with concentric rings',
      'Yellowing around lesions (chlorosis)',
      'Starts on lower, older leaves',
    ],
    recommendedAction: 'Apply a copper-based fungicide and ensure proper spacing for air circulation. Remove heavily infected lower leaves immediately to slow the spread.',
    immediateAction: {
      title: 'Immediate Action Required',
      description: 'Remove and destroy heavily infected lower leaves to prevent spore spread. Do not compost these leaves.',
      priority: 'High Priority',
    },
    treatmentSteps: [
      { id: 'step-1', title: 'Apply Fungicide', description: 'Apply a copper-based fungicide or chlorothalonil immediately.', completed: false },
      { id: 'step-2', title: 'Improve Airflow', description: 'Prune dense foliage to ensure better air circulation around the plants.', completed: false },
      { id: 'step-3', title: 'Adjust Irrigation', description: 'Switch to drip irrigation to keep leaves dry. Avoid overhead watering.', completed: false },
    ],
    preventionTips: [
      'Rotate crops annually (avoid nightshades in the same spot).',
      'Ensure adequate spacing between plants next season.',
      'Apply organic mulch to prevent soil splashing onto leaves.',
      'Use disease-resistant tomato varieties for future plantings.',
      'Regularly sanitize pruning tools between cuts.',
    ],
    safetyNotice: 'Always wear appropriate protective equipment when applying fungicides. Adhere strictly to the pre-harvest interval (PHI) specified on the product label before harvesting any fruit.',
    modelVersion: 'AgriScan-Vision-v2.4-Hybrid',
    diagnosisStatus: 'completed',
    syncStatus: 'synced',
    createdAt: new Date('2026-08-24T09:15:00Z'),
  });

  const diag2 = await Diagnosis.create({
    userId: raviUser._id,
    cropId: soybeanCrop._id,
    cropName: 'Soybeans',
    cropVariety: 'JS-335',
    fieldBlock: 'Block B',
    imageUrl: 'https://images.unsplash.com/photo-1574943320219-553eb213f72d?w=800&auto=format&fit=crop&q=80',
    predictedDisease: 'Septoria Brown Spot',
    scientificName: 'Septoria glycines',
    confidence: 87,
    severity: 'moderate',
    affectedPercentage: 24,
    whatIsIt: 'Septoria brown spot causes numerous small brown lesions with yellow halos on soybean leaves.',
    symptoms: ['Brown spots on lower leaves', 'Premature defoliation', 'Reduced pod fill'],
    recommendedAction: 'Apply foliar strobilurin fungicide and ensure proper row spacing.',
    immediateAction: {
      title: 'Action Recommended',
      description: 'Monitor weather conditions and apply fungicide before rainy periods.',
      priority: 'High Priority',
    },
    treatmentSteps: [
      { id: 'step-1', title: 'Foliar Spray', description: 'Apply azoxystrobin spray before pod filling.', completed: false },
    ],
    preventionTips: ['Rotate with corn or sorghum.', 'Bury crop residue.'],
    safetyNotice: 'Follow fungicide safety guidelines.',
    modelVersion: 'AgriScan-Vision-v2.4-Hybrid',
    diagnosisStatus: 'completed',
    syncStatus: 'synced',
    createdAt: new Date('2026-08-24T09:15:00Z'),
  });

  // 7. Create Sample YOLO Detection
  await YoloDetection.create({
    userId: raviUser._id,
    diagnosisId: diag1._id,
    cropName: 'Tomato',
    imageUrl: 'https://images.unsplash.com/photo-1592417817098-8f3d6eb2260f?w=800&auto=format&fit=crop&q=80',
    detections: [
      {
        classLabel: 'Early Blight Primary Lesion',
        confidence: 94,
        severity: 'severe',
        boundingBox: { x: 26, y: 22, width: 42, height: 38 },
      },
      {
        classLabel: 'Chlorotic Zone (Yellow Halo)',
        confidence: 89,
        severity: 'moderate',
        boundingBox: { x: 18, y: 15, width: 58, height: 52 },
      },
      {
        classLabel: 'Secondary Fungal Spot',
        confidence: 91,
        severity: 'moderate',
        boundingBox: { x: 70, y: 58, width: 18, height: 22 },
      },
    ],
    overallSeverity: 'moderate',
    affectedPercentage: 32,
    modelVersion: 'YOLOv8x-Agri-Disease-v3.1',
    qaThread: [
      {
        question: 'How quickly will this early blight lesion spread to my healthy tomatoes?',
        answer: 'Given the moderate severity and 32% affected area detected across 3 lesion zones, this fungus can spread to neighboring tomato plants within 48 to 72 hours if relative humidity stays above 80% with temperatures around 24-28°C. Immediate canopy pruning and copper spray is strongly advised.',
        askedAt: new Date('2026-08-24T09:20:00Z'),
        suggestedActions: [
          'Isolate affected plant row immediately',
          'Prune lowest leaves showing dark concentric rings',
          'Apply preventive bio-fungicide to neighboring plants',
        ],
      },
    ],
  });

  console.log('[Seed] Database seed completed successfully!');
};

// If run directly
if (process.argv[1].endsWith('seedData.js')) {
  (async () => {
    await connectDB();
    await seedDatabase();
    process.exit(0);
  })();
}
