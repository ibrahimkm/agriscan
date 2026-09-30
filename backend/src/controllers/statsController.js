import Crop from '../models/Crop.js';
import Diagnosis from '../models/Diagnosis.js';
import YoloDetection from '../models/YoloDetection.js';

export const getDashboardStats = async (req, res, next) => {
  try {
    const userId = req.user.id;

    // Crop health distribution
    const crops = await Crop.find({ userId });
    let healthyCount = 0;
    let atRiskCount = 0;
    let diseasedCount = 0;

    crops.forEach((crop) => {
      if (crop.healthStatus === 'healthy') healthyCount++;
      else if (crop.healthStatus === 'at_risk') atRiskCount++;
      else if (crop.healthStatus === 'diseased') diseasedCount++;
    });

    // Recent Diagnoses
    const recentDiagnoses = await Diagnosis.find({ userId })
      .sort({ createdAt: -1 })
      .limit(5);

    // Disease Frequency aggregation
    const diseaseFrequency = await Diagnosis.aggregate([
      { $match: { userId: req.user._id } },
      { $group: { _id: '$predictedDisease', count: { $sum: 1 }, avgConfidence: { $avg: '$confidence' } } },
      { $sort: { count: -1 } },
      { $limit: 6 },
    ]);

    // Severity distribution
    const severityStats = await Diagnosis.aggregate([
      { $match: { userId: req.user._id } },
      { $group: { _id: '$severity', count: { $sum: 1 } } },
    ]);

    // Total counts
    const totalDiagnoses = await Diagnosis.countDocuments({ userId });
    const totalDetections = await YoloDetection.countDocuments({ userId });

    res.json({
      success: true,
      data: {
        summary: {
          healthy: healthyCount,
          atRisk: atRiskCount,
          diseased: diseasedCount,
          totalCrops: crops.length,
          totalDiagnoses,
          totalDetections,
        },
        environmentalMetrics: {
          temperature: '24°C',
          temperatureStatus: 'Normal',
          soilMoisture: 'Optimal (68%)',
          humidity: '72%',
          weatherCondition: 'Partly Cloudy',
        },
        recentDiagnoses,
        diseaseFrequency: diseaseFrequency.map((d) => ({
          name: d._id || 'Unknown',
          count: d.count,
          avgConfidence: Math.round(d.avgConfidence || 90),
        })),
        severityBreakdown: severityStats.map((s) => ({
          severity: s._id,
          count: s.count,
        })),
      },
    });
  } catch (error) {
    next(error);
  }
};
