import React, { createContext, useContext, useState, useEffect } from 'react';

const LanguageContext = createContext(null);

export const translations = {
  en: {
    // Nav & Common
    appTitle: 'AgriScan',
    home: 'Home',
    diagnose: 'Diagnose',
    myCrops: 'My Crops',
    history: 'History',
    profile: 'Profile',
    yoloTitle: 'YOLO Object Analysis',
    analytics: 'Farm Health Analytics',
    online: 'Online',
    offline: 'Offline',
    cloudSynced: 'Cloud Synced',
    offlineMode: 'Offline Mode (Local Storage)',
    syncNow: 'Sync Now',
    syncing: 'Syncing...',
    healthy: 'Healthy',
    atRisk: 'At Risk',
    diseased: 'Diseased',
    moderateSeverity: 'Moderate Severity',
    severeRisk: 'Severe Risk',
    lowSeverity: 'Low Severity',
    confidence: 'Confidence',
    affectedArea: 'Affected Area',
    cancel: 'Cancel',
    save: 'Save',
    share: 'Share',
    back: 'Back',

    // Onboarding
    onboarding1Title: 'Identify crop diseases instantly.',
    onboarding1Sub: 'Point your camera at a leaf and let our on-device AI diagnose the issue in seconds — no internet needed.',
    onboarding2Title: 'Actionable treatment and prevention.',
    onboarding2Sub: 'Receive clear, farmer-tested remedies, chemical dosages, and long-term soil prevention guidelines.',
    onboarding3Title: '100% Offline in the Field.',
    onboarding3Sub: 'Scan your crops anywhere in remote farms. All analyses and detections run completely offline on your device.',
    skip: 'Skip',
    getStarted: 'Get Started',
    continue: 'Continue',

    // Login & Auth
    farmerSignIn: 'Farmer Sign In',
    signInSub: 'Sign in to track your crops, soil health & AI diagnoses',
    email: 'Email Address',
    password: 'Password',
    signInBtn: 'Sign In to Farm',
    newFarmer: 'New Farmer?',
    createAccount: 'Create an Account',
    registerTitle: 'Create AgriScan Account',
    fullName: 'Full Name',
    farmName: 'Farm Name',

    // Home
    goodMorning: 'Good morning',
    farmResilient: 'Your farm is looking resilient today.',
    temperature: 'TEMPERATURE',
    soilMoisture: 'SOIL MOISTURE',
    optimal: 'Optimal',
    diagnoseCropCTA: 'Diagnose a Crop',
    viewAll: 'View All',
    recentDiagnosis: 'Recent Diagnosis',
    viewDetails: 'View Details',
    suspected: 'Suspected',

    // My Crops
    myCropsTitle: 'My Crops',
    myCropsSub: 'Select a crop to view diagnoses or initiate a new scan.',
    searchCrops: 'Search crops...',
    allCrops: 'All Crops',
    previousDiagnoses: 'previous diagnoses',

    // Viewfinder
    positionLeaf: 'Position the leaf within the frame in good light for an accurate scan.',
    gallery: 'Gallery',
    flash: 'Flash',
    retake: 'Retake',
    analyzeLeaf: 'Analyze Leaf',

    // Diagnostic Process
    diagnosticProcess: 'Diagnostic Process',
    complete: 'Complete',
    step1: 'Checking image quality',
    step1Sub: 'Resolution and lighting optimal.',
    step2: 'Identifying crop',
    step2Sub: 'Confirmed as Solanum lycopersicum (Tomato).',
    step3: 'Detecting symptoms',
    step3Sub: 'Scanning for necrosis and chlorosis patterns...',
    step4: 'Comparing disease patterns',
    step4Sub: 'Matching against botanical pathology database...',
    step5: 'Estimating severity',
    step5Sub: 'Calculating affected leaf area & spread risk...',
    cancelAnalysis: 'Cancel Analysis',

    // Diagnosis Result
    original: 'Original',
    aiAnalysis: 'AI Analysis',
    affectedMask: 'Affected Area',
    whatIsIt: 'What is it?',
    symptoms: 'Symptoms',
    recommendedAction: 'Recommended Action',
    viewFullTreatment: 'View Full Treatment Plan',

    // Disease Explanation
    backToScan: 'Back to Scan',
    highConfidenceMatch: 'High Confidence Match',
    severeRiskTitle: 'Severe Risk: Action Required Immediately',
    severeRiskDesc: 'Spreads rapidly in cool, wet weather and can destroy an entire crop within days if left untreated.',
    whyItHappens: 'Why it happens',
    coolWetWeather: 'Cool, wet weather: High humidity (>80%) and moderate temperatures.',
    windRain: 'Wind and Rain: Spores are easily carried by wind and splashed by rain onto foliage.',
    keySymptoms: 'Key Symptoms to Look For',
    onLeaves: 'On Leaves',
    onStems: 'On Stems',
    onFruit: 'On Fruit',
    logObservation: 'Log Observation',
    viewTreatmentPlan: 'View Treatment Plan',

    // Treatment Plan
    diagnosisComplete: 'Diagnosis Complete',
    treatmentPlanTitle: 'Treatment Plan',
    immediateActionReq: 'Immediate Action Required',
    highPriority: 'High Priority',
    treatmentSteps: 'Treatment Steps',
    preventionTips: 'Prevention Tips',
    safetyNotice: 'Safety Notice',
    safetyNoticeDesc: 'Always wear appropriate protective equipment when applying fungicides. Adhere strictly to the pre-harvest interval (PHI) specified on the product label before harvesting any fruit.',
    shareReport: 'Share Report',
    saveDiagnosis: 'Save Diagnosis',
    savedToHistory: 'Diagnosis Saved to History ✓',

    // YOLO Screen
    yoloHeader: 'Upload & Analyze Leaf',
    yoloSub: 'Run localized on-device YOLO object detection to locate lesions, then consult the agronomist AI with grounded follow-up inquiries.',
    dragDropText: 'Tap or drag leaf photo here to analyze',
    runningYolo: 'Running YOLOv8 Object Detection on-device...',
    detectedEntities: 'Detected Lesion Entities',
    askAgronomist: 'Ask Agronomist About This Detection',
    recommendedInquiries: 'Recommended Agronomist Inquiries:',
    askPlaceholder: 'Ask a question about this detection...',
    offlineInferenceBadge: '100% Offline On-Device Model Active',

    // History & Analytics
    diagnosisHistory: 'Diagnosis History',
    historySub: 'Review all past leaf diagnoses, sync statuses, and historical severity progression.',
    farmHealthAnalytics: 'Farm Health Analytics',
    analyticsSub: 'Aggregate pathology metrics, disease incidence frequency, and environmental risk factors.',
    healthyDistribution: 'Healthy Crops',
    pathogenDistribution: 'Pathogen Frequency Distribution',
    canopyRiskIndex: 'Canopy Risk Index',

    // Profile & Languages
    profileSettings: 'Profile & Settings',
    languageDialect: 'Language & Dialect',
    offlineStorageTitle: 'Offline Storage & Synchronization',
    localCache: 'Local Diagnostic Cache',
    aiModelInfo: 'AI Pathology Model Info',
    signOut: 'Sign Out of Account',

    // Crop Names
    Tomato: 'Tomato',
    'Winter Wheat': 'Winter Wheat',
    Wheat: 'Wheat',
    Soybeans: 'Soybeans',
    Rice: 'Rice',
    Potato: 'Potato',
    Cotton: 'Cotton',
    Maize: 'Maize',
    Sunflower: 'Sunflower',
    Groundnut: 'Groundnut',

    // Disease Names
    'Early Blight': 'Early Blight',
    'Tomato Late Blight': 'Tomato Late Blight',
    'Late Blight': 'Late Blight',
    'Septoria Brown Spot': 'Septoria Brown Spot',
    'Rice Blast': 'Rice Blast',
    'Healthy Canopy': 'Healthy Canopy',
    'Healthy Foliage': 'Healthy Foliage',
  },

  hi: {
    // Nav & Common
    appTitle: 'एग्रीस्कैन',
    home: 'होम',
    diagnose: 'जाँच करें',
    myCrops: 'मेरी फसलें',
    history: 'इतिहास',
    profile: 'प्रोफ़ाइल',
    yoloTitle: 'YOLO रोग पहचान',
    analytics: 'खेत स्वास्थ्य विश्लेषण',
    online: 'ऑनलाइन',
    offline: 'ऑफ़लाइन',
    cloudSynced: 'क्लाउड सिंक हुआ',
    offlineMode: 'ऑफ़लाइन मोड (स्थानीय स्टोरेज)',
    syncNow: 'अभी सिंक करें',
    syncing: 'सिंक हो रहा है...',
    healthy: 'स्वस्थ',
    atRisk: 'जोखिम में',
    diseased: 'रोगग्रस्त',
    moderateSeverity: 'मध्यम गंभीरता',
    severeRisk: 'गंभीर जोखिम',
    lowSeverity: 'कम गंभीरता',
    confidence: 'सटीकता',
    affectedArea: 'प्रभावित क्षेत्र',
    cancel: 'रद्द करें',
    save: 'सहेजें',
    share: 'साझा करें',
    back: 'पीछे',

    // Onboarding
    onboarding1Title: 'फसलों के रोगों की तुरंत पहचान करें।',
    onboarding1Sub: 'पत्ती पर कैमरा केंद्रित करें और हमारा ऑन-डिवाइस AI बिना इंटरनेट के सेकंडों में रोग पहचानेगा।',
    onboarding2Title: 'सटीक उपचार और रोकथाम के उपाय।',
    onboarding2Sub: 'किसानों द्वारा परीक्षित दवाएं, रासायनिक छिड़काव मात्रा और दीर्घकालिक मिट्टी सुरक्षा निर्देश पाएं।',
    onboarding3Title: 'खेत में 100% ऑफ़लाइन काम करता है।',
    onboarding3Sub: 'दूरदराज के खेतों में बिना इंटरनेट के अपनी फसलों की जांच करें। सभी विश्लेषण आपके फोन पर ही होते हैं।',
    skip: 'छोड़ें',
    getStarted: 'शुरू करें',
    continue: 'आगे बढ़ें',

    // Login & Auth
    farmerSignIn: 'किसान लॉगिन',
    signInSub: 'अपनी फसलों, मिट्टी के स्वास्थ्य और AI जांच रिकॉर्ड के लिए लॉगिन करें',
    email: 'ईमेल या फोन',
    password: 'पासवर्ड',
    signInBtn: 'खेत में प्रवेश करें',
    newFarmer: 'नए किसान?',
    createAccount: 'नया खाता बनाएं',
    registerTitle: 'एग्रीस्कैन खाता बनाएं',
    fullName: 'पूरा नाम',
    farmName: 'खेत का नाम',

    // Home
    goodMorning: 'शुभ प्रभात',
    farmResilient: 'आज आपका खेत सुरक्षित और स्वस्थ दिख रहा है।',
    temperature: 'तापमान',
    soilMoisture: 'मिट्टी की नमी',
    optimal: 'उत्तम',
    diagnoseCropCTA: 'फसल की जांच करें',
    viewAll: 'सभी देखें',
    recentDiagnosis: 'हालिया रोग जांच',
    viewDetails: 'विवरण देखें',
    suspected: 'संभावित',

    // My Crops
    myCropsTitle: 'मेरी फसलें',
    myCropsSub: 'रोग इतिहास देखने या नई जांच शुरू करने के लिए फसल चुनें।',
    searchCrops: 'फसल खोजें...',
    allCrops: 'सभी फसलें',
    previousDiagnoses: 'पिछली जांचें',

    // Viewfinder
    positionLeaf: 'सटीक जांच के लिए पत्ती को अच्छी रोशनी में फ्रेम के अंदर रखें।',
    gallery: 'गैलरी',
    flash: 'फ्लैश',
    retake: 'दोबारा लें',
    analyzeLeaf: 'पत्ती का विश्लेषण करें',

    // Diagnostic Process
    diagnosticProcess: 'रोग निदान प्रक्रिया',
    complete: 'पूर्ण',
    step1: 'तस्वीर की गुणवत्ता जांच',
    step1Sub: 'रोशनी और स्पष्टता उत्तम है।',
    step2: 'फसल की पहचान',
    step2Sub: 'टमाटर (Solanum lycopersicum) के रूप में सत्यापित।',
    step3: 'रोग के लक्षणों की पहचान',
    step3Sub: 'धब्बों और पीलेपन के पैटर्न स्कैन किए जा रहे हैं...',
    step4: 'रोग पैटर्न की तुलना',
    step4Sub: 'पादप रोग डेटाबेस से मिलान किया जा रहा है...',
    step5: 'गंभीरता का अनुमान',
    step5Sub: 'प्रभावित क्षेत्र और फैलने के जोखिम की गणना...',
    cancelAnalysis: 'जांच रद्द करें',

    // Diagnosis Result
    original: 'मूल तस्वीर',
    aiAnalysis: 'AI हीटमैप',
    affectedMask: 'प्रभावित क्षेत्र',
    whatIsIt: 'यह क्या है?',
    symptoms: 'रोग के लक्षण',
    recommendedAction: 'अनुशंसित उपाय',
    viewFullTreatment: 'पूरा उपचार प्लान देखें',

    // Disease Explanation
    backToScan: 'स्कैन पर वापस जाएं',
    highConfidenceMatch: 'उच्च सटीकता मिलान',
    severeRiskTitle: 'गंभीर जोखिम: तुरंत कार्रवाई आवश्यक',
    severeRiskDesc: 'ठंडे और नम मौसम में तेजी से फैलता है और ध्यान न देने पर कुछ दिनों में पूरी फसल नष्ट कर सकता है।',
    whyItHappens: 'यह क्यों होता है?',
    coolWetWeather: 'ठंडा और नम मौसम: 80% से अधिक नमी और मध्यम तापमान।',
    windRain: 'हवा और बारिश: फफूंद के बीजाणु हवा और पानी के छींटों से आसानी से फैलते हैं।',
    keySymptoms: 'मुख्य लक्षण',
    onLeaves: 'पत्तियों पर',
    onStems: 'तनों पर',
    onFruit: 'फलों पर',
    logObservation: 'अवलोकन दर्ज करें',
    viewTreatmentPlan: 'उपचार योजना देखें',

    // Treatment Plan
    diagnosisComplete: 'जांच पूर्ण हुई',
    treatmentPlanTitle: 'उपचार योजना',
    immediateActionReq: 'तुरंत करने योग्य कार्य',
    highPriority: 'उच्च प्राथमिकता',
    treatmentSteps: 'उपचार के चरण',
    preventionTips: 'रोकथाम के सुझाव',
    safetyNotice: 'सुरक्षा सूचना',
    safetyNoticeDesc: 'कवकनाशी दवाएं छिड़कते समय हमेशा मास्क और दस्ताने पहनें। फल तोड़ने से पहले लेबल पर दी गई प्रतीक्षा अवधि (PHI) का पालन करें।',
    shareReport: 'रिपोर्ट साझा करें',
    saveDiagnosis: 'जांच सहेजें',
    savedToHistory: 'इतिहास में सहेजा गया ✓',

    // YOLO Screen
    yoloHeader: 'पत्ती अपलोड करें और YOLO जांचें',
    yoloSub: 'पत्तियों पर धब्बों की सटीक स्थिति देखने के लिए ऑन-डिवाइस YOLO मॉडल चलाएं और कृषि विशेषज्ञ AI से सलाह लें।',
    dragDropText: 'जांच के लिए पत्ती की फोटो यहां खींचें या टैप करें',
    runningYolo: 'फोन पर YOLOv8 रोग पहचान चल रही है...',
    detectedEntities: 'पहचाने गए रोग धब्बे',
    askAgronomist: 'इस जांच के बारे में कृषि विशेषज्ञ से पूछें',
    recommendedInquiries: 'सुझाए गए प्रश्न:',
    askPlaceholder: 'इस रोग के बारे में सवाल पूछें...',
    offlineInferenceBadge: '100% ऑफ़लाइन ऑन-डिवाइस AI सक्रिय',

    // History & Analytics
    diagnosisHistory: 'रोग इतिहास',
    historySub: 'सभी पिछली जांचें, सिंक स्थिति और रोग की गंभीरता का रिकॉर्ड देखें।',
    farmHealthAnalytics: 'खेत स्वास्थ्य विश्लेषण',
    analyticsSub: 'रोगों की आवृत्ति, प्रसार दर और मौसमी जोखिम सूचकांक।',
    healthyDistribution: 'स्वस्थ फसलें',
    pathogenDistribution: 'रोग आवृत्ति वितरण',
    canopyRiskIndex: 'कैनोपी जोखिम सूचकांक',

    // Profile & Languages
    profileSettings: 'प्रोफ़ाइल और सेटिंग्स',
    languageDialect: 'भाषा चुनें',
    offlineStorageTitle: 'ऑफ़लाइन स्टोरेज और डेटा',
    localCache: 'स्थानीय डेटा कैश',
    aiModelInfo: 'AI रोग मॉडल विवरण',
    signOut: 'खाते से लॉग आउट करें',

    // Crop Names
    Tomato: 'टमाटर',
    'Winter Wheat': 'शरदकालीन गेहूं',
    Wheat: 'गेहूं',
    Soybeans: 'सोयाबीन',
    Rice: 'धान / चावल',
    Potato: 'आलू',
    Cotton: 'कपास',
    Maize: 'मक्का',
    Sunflower: 'सूरजमुखी',
    Groundnut: 'मूंगफली',

    // Disease Names
    'Early Blight': 'अगेती झुलसा (Early Blight)',
    'Tomato Late Blight': 'पछेती झुलसा (Late Blight)',
    'Late Blight': 'पछेती झुलसा',
    'Septoria Brown Spot': 'सेप्टोरिया भूरा धब्बा',
    'Rice Blast': 'धान का झोंका रोग (Rice Blast)',
    'Healthy Canopy': 'स्वस्थ पत्तियां',
    'Healthy Foliage': 'स्वस्थ फसल',
  },

  te: {
    // Nav & Common
    appTitle: 'అగ్రిస్కాన్',
    home: 'హోమ్',
    diagnose: 'వ్యాధి నిర్ధారణ',
    myCrops: 'నా పంటలు',
    history: 'చరిత్ర',
    profile: 'ప్రొఫైల్',
    yoloTitle: 'YOLO వ్యాధి గుర్తింపు',
    analytics: 'పంట ఆరోగ్య విశ్లేషణ',
    online: 'ఆన్‌లైన్',
    offline: 'ఆఫ్‌లైన్',
    cloudSynced: 'క్లౌడ్ సింక్ అయింది',
    offlineMode: 'ఆఫ్‌లైన్ మోడ్ (స్థానిక నిల్వ)',
    syncNow: 'ఇప్పుడే సింక్ చేయండి',
    syncing: 'సింక్ అవుతోంది...',
    healthy: 'ఆరోగ్యంగా ఉంది',
    atRisk: 'ప్రమాదంలో ఉంది',
    diseased: 'తెగులు సోకింది',
    moderateSeverity: 'మధ్యస్థ తీవ్రత',
    severeRisk: 'తీవ్రమైన ప్రమాదం',
    lowSeverity: 'తక్కువ తీవ్రత',
    confidence: 'ఖచ్చితత్వం',
    affectedArea: 'ప్రభావిత ప్రాంతం',
    cancel: 'రద్దు చేయి',
    save: 'సేవ్ చేయి',
    share: 'షేర్ చేయి',
    back: 'వెనుకకు',

    // Onboarding
    onboarding1Title: 'పంట తెగుళ్లను క్షణాల్లో గుర్తించండి.',
    onboarding1Sub: 'ఆకుపై కెమెరా పెట్టండి, మా ఆన్-డివైస్ AI ఇంటర్నెట్ లేకుండా సెకన్లలో వ్యాధిని గుర్తిస్తుంది.',
    onboarding2Title: 'ఖచ్చితమైన నివారణ మరియు మందులు.',
    onboarding2Sub: 'రైతు పరీక్షించిన మందుల మోతాదులు, పిచికారీ సూచనలు మరియు దీర్ఘకాలిక నేల సంరక్షణ మార్గదర్శకాలు.',
    onboarding3Title: 'పొలంలో 100% ఆఫ్‌లైన్ పనిచేస్తుంది.',
    onboarding3Sub: 'నెట్‌వర్క్ లేని మారుమూల పొలాల్లో కూడా వ్యాధి నిర్ధారణ చేయండి. పూర్తి విశ్లేషణ మీ ఫోన్‌లోనే జరుగుతుంది.',
    skip: 'దాటవేయి',
    getStarted: 'ప్రారంభించండి',
    continue: 'కొనసాగించండి',

    // Login & Auth
    farmerSignIn: 'రైతు లాగిన్',
    signInSub: 'మీ పంటలు, నేల ఆరోగ్యం & వ్యాధి రికార్డుల కోసం లాగిన్ అవ్వండి',
    email: 'ఈమెయిల్ లేదా ఫోన్',
    password: 'పాస్‌వర్డ్',
    signInBtn: 'పొలంలోకి ప్రవేశించండి',
    newFarmer: 'కొత్త రైతులా?',
    createAccount: 'కొత్త ఖాతా తెరవండి',
    registerTitle: 'అగ్రిస్కాన్ ఖాతా సృష్టించండి',
    fullName: 'పూర్తి పేరు',
    farmName: 'పొలం పేరు',

    // Home
    goodMorning: 'శుభోదయం',
    farmResilient: 'ఈ రోజు మీ పొలం ఆరోగ్యంగా మరియు పచ్చగా కనిపిస్తోంది.',
    temperature: 'ఉష్ణోగ్రత',
    soilMoisture: 'నేల తేమ',
    optimal: 'సరైన స్థితి',
    diagnoseCropCTA: 'పంటను పరీక్షించండి',
    viewAll: 'అన్నీ చూడండి',
    recentDiagnosis: 'ఇటీవలి వ్యాధి నిర్ధారణ',
    viewDetails: 'వివరాలు చూడండి',
    suspected: 'అనుమానిత తెగులు',

    // My Crops
    myCropsTitle: 'నా పంటలు',
    myCropsSub: 'వ్యాధి చరిత్రను చూడటానికి లేదా కొత్త స్కాన్ ప్రారంభించడానికి పంటను ఎంచుకోండి.',
    searchCrops: 'పంటలను వెతకండి...',
    allCrops: 'అన్ని పంటలు',
    previousDiagnoses: 'మునుపటి పరీక్షలు',

    // Viewfinder
    positionLeaf: 'ఖచ్చితమైన స్కాన్ కోసం ఆకును మంచి కాంతిలో ఫ్రేమ్ లోపల ఉంచండి.',
    gallery: 'గ్యాలరీ',
    flash: 'ఫ్లాష్',
    retake: 'మళ్ళీ తీయండి',
    analyzeLeaf: 'ఆకును విశ్లేషించండి',

    // Diagnostic Process
    diagnosticProcess: 'రోగ నిర్ధారణ ప్రక్రియ',
    complete: 'పూర్తయింది',
    step1: 'చిత్ర నాణ్యత తనిఖీ',
    step1Sub: 'కాంతి మరియు స్పష్టత సరిగ్గా ఉన్నాయి.',
    step2: 'పంట గుర్తింపు',
    step2Sub: 'టమోటా (Solanum lycopersicum) గా గుర్తించబడింది.',
    step3: 'తెగులు లక్షణాల గుర్తింపు',
    step3Sub: 'మచ్చలు మరియు పసుపు రంగు తీరును స్కాన్ చేస్తోంది...',
    step4: 'తెగులు పోలికల తనిఖీ',
    step4Sub: 'మొక్కల వ్యాధుల డేటాబేస్‌తో సరిపోలుస్తోంది...',
    step5: 'తీవ్రత అంచనా',
    step5Sub: 'సోకిన విస్తీర్ణం మరియు వ్యాప్తి ప్రమాదాన్ని లెక్కిస్తోంది...',
    cancelAnalysis: 'విశ్లేషణను రద్దు చేయి',

    // Diagnosis Result
    original: 'అసలు చిత్రం',
    aiAnalysis: 'AI విశ్లేషణ',
    affectedMask: 'సోకిన ప్రాంతం',
    whatIsIt: 'ఇది ఏమిటి?',
    symptoms: 'లక్షణాలు',
    recommendedAction: 'సిఫార్సు చేసిన చర్య',
    viewFullTreatment: 'పూర్తి నివారణ ప్రణాళిక చూడండి',

    // Disease Explanation
    backToScan: 'స్కాన్‌కి తిరిగి వెళ్ళు',
    highConfidenceMatch: 'ఖచ్చితమైన సరిపోలిక',
    severeRiskTitle: 'తీవ్రమైన ప్రమాదం: తక్షణ చర్య అవసరం',
    severeRiskDesc: 'చల్లని, తేమతో కూడిన వాతావరణంలో ఇది వేగంగా వ్యాపిస్తుంది. చికిత్స చేయకపోతే కొన్ని రోజుల్లో మొత్తం పంట నాశనమవుతుంది.',
    whyItHappens: 'ఇది ఎందుకు వస్తుంది?',
    coolWetWeather: 'చల్లని, తేమ వాతావరణం: 80% పైగా గాలి తేమ మరియు మితమైన ఉష్ణోగ్రత.',
    windRain: 'గాలి మరియు వర్షం: శిలీంధ్ర బీజాలు గాలి మరియు నీటి తుంపర్ల ద్వారా సులభంగా వ్యాపిస్తాయి.',
    keySymptoms: 'ముఖ్యమైన లక్షణాలు',
    onLeaves: 'ఆకులపై',
    onStems: 'కాండంపై',
    onFruit: 'కాయలపై / పండ్లపై',
    logObservation: 'గమనికను నమోదు చేయండి',
    viewTreatmentPlan: 'నివారణ ప్రణాళిక చూడండి',

    // Treatment Plan
    diagnosisComplete: 'వ్యాధి నిర్ధారణ పూర్తయింది',
    treatmentPlanTitle: 'నివారణ ప్రణాళిక',
    immediateActionReq: 'వెంటనే చేయవలసిన పని',
    highPriority: 'అత్యవసరం',
    treatmentSteps: 'చికిత్సా చర్యలు',
    preventionTips: 'నివారణ సూచనలు',
    safetyNotice: 'రక్షణ హెచ్చరిక',
    safetyNoticeDesc: 'పురుగుమందులు పిచికారీ చేసేటప్పుడు ఎల్లప్పుడూ రక్షణ తొడుగులు మరియు మాస్క్ ధరించండి. కోతకు ముందు నిర్దేశిత వ్యవధిని (PHI) పాటించండి.',
    shareReport: 'రిపోర్ట్ షేర్ చేయండి',
    saveDiagnosis: 'రికార్డును సేవ్ చేయండి',
    savedToHistory: 'చరిత్రలో భద్రపరచబడింది ✓',

    // YOLO Screen
    yoloHeader: 'ఆకును అప్‌లోడ్ చేసి YOLO తో పరీక్షించండి',
    yoloSub: 'ఆకులపై మచ్చల ప్రాంతాలను గుర్తించడానికి ఆన్-డివైస్ YOLO మోడల్‌ను ఉపయోగించండి మరియు AI నిపుణుడిని అడగండి.',
    dragDropText: 'పరీక్షించడానికి ఆకు ఫోటోను ఇక్కడ వేయండి లేదా తాకండి',
    runningYolo: 'ఫోన్‌లో YOLOv8 రోగ గుర్తింపు నడుస్తోంది...',
    detectedEntities: 'గుర్తించిన తెగులు మచ్చలు',
    askAgronomist: 'వ్యవసాయ నిపుణుడిని అడగండి',
    recommendedInquiries: 'సిఫార్సు చేసిన ప్రశ్నలు:',
    askPlaceholder: 'ఈ తెగులు గురించి ప్రశ్న అడగండి...',
    offlineInferenceBadge: '100% ఆఫ్‌లైన్ AI మోడల్ పనిచేస్తోంది',

    // History & Analytics
    diagnosisHistory: 'వ్యాధి చరిత్ర',
    historySub: 'గత పరీక్షలు, సింక్ స్థితి మరియు వ్యాధి తీవ్రత వివరాలను సమీక్షించండి.',
    farmHealthAnalytics: 'పంట ఆరోగ్య విశ్లేషణ',
    analyticsSub: 'వ్యాధుల సంభవనీయత, వ్యాప్తి రేటు మరియు వాతావరణ ప్రమాద సూచికలు.',
    healthyDistribution: 'ఆరోగ్యకరమైన పంటలు',
    pathogenDistribution: 'తెగుళ్ల విస్తరణ రేటు',
    canopyRiskIndex: 'వాతావరణ ప్రమాద సూచిక',

    // Profile & Languages
    profileSettings: 'ప్రొఫైల్ & సెట్టింగ్‌లు',
    languageDialect: 'భాషను ఎంచుకోండి',
    offlineStorageTitle: 'ఆఫ్‌లైన్ నిల్వ & డేటా',
    localCache: 'స్థానిక డేటా నిల్వ',
    aiModelInfo: 'AI మోడల్ వివరాలు',
    signOut: 'ఖాతా నుండి లాగ్ అవుట్ అవ్వండి',

    // Crop Names
    Tomato: 'టమోటా',
    'Winter Wheat': 'శీతాకాల గోధుమ',
    Wheat: 'గోధుమ',
    Soybeans: 'సోయాబీన్',
    Rice: 'వరి / బియ్యం',
    Potato: 'బంగాళాదుంప',
    Cotton: 'పత్తి',
    Maize: 'మొక్కజొన్న',
    Sunflower: 'పొద్దుతిరుగుడు',
    Groundnut: 'వేరుశనగ',

    // Disease Names
    'Early Blight': 'ఆకు ఎండు తెగులు (Early Blight)',
    'Tomato Late Blight': 'లేట్ బ్లైట్ తెగులు (Late Blight)',
    'Late Blight': 'లేట్ బ్లైట్ తెగులు',
    'Septoria Brown Spot': 'సెప్టోరియా గోధుమ మచ్చ తెగులు',
    'Rice Blast': 'వరి అగ్గి తెగులు (Rice Blast)',
    'Healthy Canopy': 'ఆరోగ్యకరమైన పంట',
    'Healthy Foliage': 'ఆరోగ్యవంతమైన ఆకులు',
  },

  ta: {
    // Nav & Common
    appTitle: 'அக்ரிஸ்கேன்',
    home: 'முகப்பு',
    diagnose: 'நோய் கண்டறிதல்',
    myCrops: 'என் பயிர்கள்',
    history: 'வரலாறு',
    profile: 'சுயவிவரம்',
    yoloTitle: 'YOLO நோய் கண்டறிதல்',
    analytics: 'பயிர் நலப்பகுப்பாய்வு',
    online: 'ஆன்லைன்',
    offline: 'ஆஃப்லைன்',
    cloudSynced: 'கிளவுட் ஒத்திசைக்கப்பட்டது',
    offlineMode: 'ஆஃப்லைன் முறை (உள்ளூர் சேமிப்பு)',
    syncNow: 'இப்போதே ஒத்திசைக்கவும்',
    syncing: 'ஒத்திசைக்கப்படுகிறது...',
    healthy: 'ஆரோக்கியமானது',
    atRisk: 'ஆபத்தில் உள்ளது',
    diseased: 'நோய் தாக்கியது',
    moderateSeverity: 'நடுத்தர தீவிரம்',
    severeRisk: 'கடுமையான ஆபத்து',
    lowSeverity: 'குறைந்த தீவிரம்',
    confidence: 'துல்லியம்',
    affectedArea: 'பாதிக்கப்பட்ட பகுதி',
    cancel: 'ரத்து செய்',
    save: 'சேமி',
    share: 'பகிர்',
    back: 'பின்செல்',

    // Onboarding
    onboarding1Title: 'பயிர் நோய்களை உடனே கண்டறியுங்கள்.',
    onboarding1Sub: 'இலையின் மீது கேமராவை வையுங்கள், இணையம் இல்லாமலேயே நொடிகளில் எங்களின் AI நோய் கண்டறியும்.',
    onboarding2Title: 'துல்லியமான சிகிச்சை மற்றும் பாதுகாப்பு.',
    onboarding2Sub: 'விவசாயிகளால் பரிசோதிக்கப்பட்ட மருந்துகள், தெளிக்கும் அளவுகள் மற்றும் நீண்டகால மண் பாதுகாப்பு வழிகாட்டல்கள்.',
    onboarding3Title: 'பண்ணையில் 100% ஆஃப்லைனில் செயல்படும்.',
    onboarding3Sub: 'இணைய சேவை இல்லாத கிராமப்புறங்களிலும் பயிர்களை சோதிக்கலாம். அனைத்து பகுப்பாய்வும் உங்கள் போனிலேயே நடக்கும்.',
    skip: 'தவிர்',
    getStarted: 'தொடங்குங்கள்',
    continue: 'தொடரவும்',

    // Login & Auth
    farmerSignIn: 'விவசாயி உள்நுழைவு',
    signInSub: 'உங்கள் பயிர்கள், மண் நலம் மற்றும் AI பரிசோதனை வரலாற்றை அறிய உள்நுழையவும்',
    email: 'மின்னஞ்சல் அல்லது தொலைபேசி',
    password: 'கடவுச்சொல்',
    signInBtn: 'பண்ணைக்குள் நுழைக',
    newFarmer: 'புதிய விவசாயியா?',
    createAccount: 'புதிய கணக்கை உருவாக்கவும்',
    registerTitle: 'அக்ரிஸ்கேன் கணக்கு தொடங்கவும்',
    fullName: 'முழு பெயர்',
    farmName: 'பண்ணை பெயர்',

    // Home
    goodMorning: 'காலை வணக்கம்',
    farmResilient: 'இன்று உங்கள் பயிர்கள் ஆரோக்கியமாகவும் செழிப்பாகவும் உள்ளன.',
    temperature: 'வெப்பநிலை',
    soilMoisture: 'மண் ஈரப்பதம்',
    optimal: 'சரியான அளவு',
    diagnoseCropCTA: 'பயிரை பரிசோதிக்கவும்',
    viewAll: 'அனைத்தும் பார்க்க',
    recentDiagnosis: 'சமீபத்திய பரிசோதனை',
    viewDetails: 'விவரம் பார்க்க',
    suspected: 'சந்தேகிக்கப்படும் நோய்',

    // My Crops
    myCropsTitle: 'என் பயிர்கள்',
    myCropsSub: 'நோய் வரலாற்றை பார்க்க அல்லது புதிய பரிசோதனை செய்ய பயிரை தேர்ந்தெடுக்கவும்.',
    searchCrops: 'பயிர்களை தேடுங்கள்...',
    allCrops: 'அனைத்து பயிர்கள்',
    previousDiagnoses: 'முந்தைய பரிசோதனைகள்',

    // Viewfinder
    positionLeaf: 'துல்லியமான பரிசோதனைக்கு இலையை நல்ல வெளிச்சத்தில் சட்டத்திற்குள் வைக்கவும்.',
    gallery: 'புகைப்படங்கள்',
    flash: 'ஒளி (Flash)',
    retake: 'மீண்டும் எடு',
    analyzeLeaf: 'இலையை பகுப்பாய்வு செய்',

    // Diagnostic Process
    diagnosticProcess: 'நோய் கண்டறியும் முறை',
    complete: 'முடிந்தது',
    step1: 'படத் தரம் சரிபார்க்கப்படுகிறது',
    step1Sub: 'வெளிச்சமும் தெளிவும் சரியாக உள்ளன.',
    step2: 'பயிர் அடையாளம் காணப்படுகிறது',
    step2Sub: 'தக்காளி (Solanum lycopersicum) என உறுதி செய்யப்பட்டது.',
    step3: 'நோய் அறிகுறிகள் கண்டறிதல்',
    step3Sub: 'புள்ளிகள் மற்றும் மஞ்சள் நிற மாறுபாடுகள் ஸ்கேன் செய்யப்படுகின்றன...',
    step4: 'நோய் ஒப்பீடு செய்தல்',
    step4Sub: 'தாவர நோய் தரவுகளுடன் ஒப்பிடப்படுகிறது...',
    step5: 'தீவிரத்தை மதிப்பிடுதல்',
    step5Sub: 'பாதிக்கப்பட்ட பரப்பளவு மற்றும் பரவும் ஆபத்து கணக்கிடப்படுகிறது...',
    cancelAnalysis: 'பகுப்பாய்வை ரத்து செய்',

    // Diagnosis Result
    original: 'அசல் படம்',
    aiAnalysis: 'AI வெப்ப வரைபடம்',
    affectedMask: 'பாதிக்கப்பட்ட பகுதி',
    whatIsIt: 'இது என்ன நோய்?',
    symptoms: 'அறிகுறிகள்',
    recommendedAction: 'பரிந்துரைக்கப்பட்ட சிகிச்சை',
    viewFullTreatment: 'முழு சிகிச்சை முறையை காண்க',

    // Disease Explanation
    backToScan: 'ஸ்கேனுக்கு திரும்பு',
    highConfidenceMatch: 'துல்லியமான பொருத்தம்',
    severeRiskTitle: 'கடுமையான ஆபத்து: உடனடி நடவடிக்கை தேவை',
    severeRiskDesc: 'குளிர்ந்த மற்றும் ஈரப்பதமான வானிலையில் இது வேகமாக பரவி சில நாட்களில் முழு பயிரையும் அழிக்கக்கூடும்.',
    whyItHappens: 'இது ஏன் ஏற்படுகிறது?',
    coolWetWeather: 'குளிர்ந்த, ஈரப்பதமான வானிலை: 80% க்கும் அதிகமான ஈரப்பதம் மற்றும் மிதமான வெப்பநிலை.',
    windRain: 'காற்று மற்றும் மழை: பூஞ்சை வித்துக்கள் காற்று மற்றும் மழைநீரின் மூலம் எளிதாக பரவுகின்றன.',
    keySymptoms: 'முக்கிய அறிகுறிகள்',
    onLeaves: 'இலைகளில்',
    onStems: 'தண்டுகளில்',
    onFruit: 'காய்கள் / பழங்களில்',
    logObservation: 'பதிவு செய்க',
    viewTreatmentPlan: 'சிகிச்சை திட்டத்தை காண்க',

    // Treatment Plan
    diagnosisComplete: 'பரிசோதனை முடிந்தது',
    treatmentPlanTitle: 'சிகிச்சை திட்டம்',
    immediateActionReq: 'உடனடியாக செய்ய வேண்டியவை',
    highPriority: 'அதிமுக்கியம்',
    treatmentSteps: 'சிகிச்சை படிகள்',
    preventionTips: 'தடுப்பு முறைகள்',
    safetyNotice: 'பாதுகாப்பு குறிப்பு',
    safetyNoticeDesc: 'பூஞ்சைக்கொல்லி தெளிக்கும் போது எப்போதும் முகக்கவசம் மற்றும் கையுறைகளை அணியுங்கள். அறுவடைக்கு முன் காத்திருப்பு காலத்தை (PHI) கட்டாயம் பின்பற்றவும்.',
    shareReport: 'அறிக்கையை பகிரவும்',
    saveDiagnosis: 'பரிசோதனையை சேமிக்கவும்',
    savedToHistory: 'வரலாற்றில் சேமிக்கப்பட்டது ✓',

    // YOLO Screen
    yoloHeader: 'இலையை பதிவேற்றி YOLO மூலம் கண்டறியவும்',
    yoloSub: 'இலையில் நோய் புள்ளிகளை துல்லியமாக கண்டறிய ஆஃப்லைன் YOLO மாதிரியை இயக்கவும் மற்றும் AI வேளாண் நிபுணரிடம் ஆலோசனை பெறவும்.',
    dragDropText: 'பரிசோதிக்க இலையின் புகைப்படத்தை இங்கே இழுக்கவும் அல்லது கிளிக் செய்யவும்',
    runningYolo: 'போனிலேயே YOLOv8 நோய் கண்டறிதல் நடக்கிறது...',
    detectedEntities: 'கண்டறியப்பட்ட நோய் புள்ளிகள்',
    askAgronomist: 'வேளாண் நிபுணரிடம் கேளுங்கள்',
    recommendedInquiries: 'பரிந்துரைக்கப்பட்ட கேள்விகள்:',
    askPlaceholder: 'இந்த நோய் பற்றி கேள்வி கேளுங்கள்...',
    offlineInferenceBadge: '100% ஆஃப்லைன் AI மாதிரி இயங்குகிறது',

    // History & Analytics
    diagnosisHistory: 'பரிசோதனை வரலாறு',
    historySub: 'முந்தைய அனைத்து பரிசோதனைகள், ஒத்திசைவு நிலை மற்றும் நோய் தீவிர பதிவுகளைப் பாருங்கள்.',
    farmHealthAnalytics: 'பயிர் நலப்பகுப்பாய்வு',
    analyticsSub: 'நோய்களின் பரவல் விகிதம், பாதிப்பு அதிர்வெண் மற்றும் வானிலை ஆபத்து குறியீடுகள்.',
    healthyDistribution: 'ஆரோக்கியமான பயிர்கள்',
    pathogenDistribution: 'நோய் அதிர்வெண் பரவல்',
    canopyRiskIndex: 'வானிலை ஆபத்து குறியீடு',

    // Profile & Languages
    profileSettings: 'சுயவிவரம் & அமைப்புகள்',
    languageDialect: 'மொழியை மாற்றவும்',
    offlineStorageTitle: 'ஆஃப்லைன் சேமிப்பகம் & தரவு',
    localCache: 'உள்ளூர் தரவு சேமிப்பு',
    aiModelInfo: 'AI மாதிரி விவரங்கள்',
    signOut: 'கணக்கிலிருந்து வெளியேறவும்',

    // Crop Names
    Tomato: 'தக்காளி',
    'Winter Wheat': 'கோதுமை',
    Wheat: 'கோதுமை',
    Soybeans: 'சோயாபீன்',
    Rice: 'நெல் / அரிசி',
    Potato: 'உருளைக்கிழங்கு',
    Cotton: 'பருத்தி',
    Maize: 'மக்காச்சோளம்',
    Sunflower: 'சூரியகாந்தி',
    Groundnut: 'நிலக்கடலை / வேர்க்கடலை',

    // Disease Names
    'Early Blight': 'ஆரம்ப கருகல் நோய் (Early Blight)',
    'Tomato Late Blight': 'பிற்பட்ட கருகல் நோய் (Late Blight)',
    'Late Blight': 'பிற்பட்ட கருகல் நோய்',
    'Septoria Brown Spot': 'செப்டோரியா பழுப்பு புள்ளி நோய்',
    'Rice Blast': 'நெல் குலை நோய் (Rice Blast)',
    'Healthy Canopy': 'ஆரோக்கியமான பயிர்',
    'Healthy Foliage': 'ஆரோக்கியமான இலைகள்',
  },
};

export const LanguageProvider = ({ children }) => {
  const [language, setLanguage] = useState(() => {
    return localStorage.getItem('agriscan_language') || 'en';
  });

  const changeLanguage = (langCode) => {
    if (translations[langCode]) {
      setLanguage(langCode);
      localStorage.setItem('agriscan_language', langCode);
    }
  };

  const t = (key) => {
    const dict = translations[language] || translations.en;
    return dict[key] || translations.en[key] || key;
  };

  const translateCrop = (cropName) => {
    if (!cropName) return '';
    const dict = translations[language] || translations.en;
    return dict[cropName] || cropName;
  };

  const translateDisease = (diseaseName) => {
    if (!diseaseName) return '';
    const dict = translations[language] || translations.en;
    return dict[diseaseName] || diseaseName;
  };

  return (
    <LanguageContext.Provider
      value={{
        language,
        changeLanguage,
        t,
        translateCrop,
        translateDisease,
        availableLanguages: [
          { code: 'en', label: 'English', native: 'English (US/UK)' },
          { code: 'hi', label: 'Hindi', native: 'हिन्दी (Hindi)' },
          { code: 'te', label: 'Telugu', native: 'తెలుగు (Telugu)' },
          { code: 'ta', label: 'Tamil', native: 'தமிழ் (Tamil)' },
        ],
      }}
    >
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => useContext(LanguageContext);
