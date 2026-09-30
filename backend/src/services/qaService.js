/**
 * Scoped Agronomy Q&A Service
 * Answers farmer questions grounded in the specific YOLO detection / Diagnosis context.
 */
export const answerDetectionQuestion = async ({ detectionRecord, question }) => {
  const qLower = question.toLowerCase();
  const crop = detectionRecord?.cropName || 'Tomato';
  const severity = detectionRecord?.overallSeverity || 'moderate';
  const affected = detectionRecord?.affectedPercentage || 28;
  const numBoxes = detectionRecord?.detections?.length || 2;

  let answer = '';
  let actions = [];

  if (qLower.includes('spread') || qLower.includes('fast') || qLower.includes('how quickly')) {
    answer = `Given the ${severity} severity and ${affected}% affected leaf area detected across ${numBoxes} lesion zones, this pathogen can spread rapidly across adjacent foliage within 48 to 72 hours, particularly if relative humidity exceeds 85% and temperatures remain between 18°C and 25°C. Immediate canopy isolation is advised.`;
    actions = [
      'Isolate affected plant row immediately',
      'Prune lowest leaves showing dark concentric rings',
      'Apply preventive bio-fungicide to neighboring plants',
    ];
  } else if (qLower.includes('spray') || qLower.includes('fungicide') || qLower.includes('chemical') || qLower.includes('medicine')) {
    answer = `For ${crop} with ${severity} fungal infection, a broad-spectrum copper hydroxide (e.g., Kocide 3000) or Chlorothalonil fungicide is recommended. Apply in the early morning at 2.5g per liter of water. Ensure complete coverage of both upper and lower leaf surfaces.`;
    actions = [
      'Apply Copper Hydroxide (2.5g/L) before noon',
      'Wear protective mask and nitrile gloves',
      'Reapply after heavy rainfall (or after 7-10 days)',
    ];
  } else if (qLower.includes('safe') || qLower.includes('eat') || qLower.includes('harvest') || qLower.includes('fruit')) {
    answer = `While the fungal lesions primarily target foliage and stems, infected leaves compromise photosynthesis. Fruit from this plant is safe only if completely free of dark sunken lesions. Observe the 3-day Pre-Harvest Interval (PHI) after applying any copper-based treatment.`;
    actions = [
      'Inspect fruit calyx for brown ring rot',
      'Discard any softened or spotted fruit',
      'Maintain pre-harvest interval before picking',
    ];
  } else if (qLower.includes('water') || qLower.includes('irrigation') || qLower.includes('rain')) {
    answer = `Overhead watering is the primary vector for fungal splash dissemination. Switch to furrow or drip irrigation immediately to keep the upper leaf canopy completely dry. Irrigate early in the morning so surface moisture evaporates quickly.`;
    actions = [
      'Switch strictly to drip or root-zone irrigation',
      'Avoid overhead sprinklers',
      'Add 2 inches of organic straw mulch around base',
    ];
  } else {
    answer = `Based on the AI detection of ${numBoxes} localized lesion clusters on your ${crop} leaf (${affected}% coverage, ${severity} risk), we recommend sanitizing pruning shears with 70% isopropyl alcohol, removing infected bottom foliage, and initiating protective spray coverage within 24 hours.`;
    actions = [
      'Prune and safely discard diseased leaf matter',
      'Inspect adjacent plants for early yellow halos',
      'Record next inspection in AgriScan within 3 days',
    ];
  }

  return {
    question,
    answer,
    askedAt: new Date(),
    suggestedActions: actions,
  };
};
