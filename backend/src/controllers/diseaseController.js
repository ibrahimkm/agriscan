import Disease from '../models/Disease.js';

export const getDiseases = async (req, res, next) => {
  try {
    const { crop, search } = req.query;
    let query = {};

    if (crop) {
      query.cropTypes = { $regex: crop, $options: 'i' };
    }

    if (search) {
      query.$or = [
        { diseaseName: { $regex: search, $options: 'i' } },
        { scientificName: { $regex: search, $options: 'i' } },
      ];
    }

    const diseases = await Disease.find(query);
    res.json({ success: true, count: diseases.length, data: diseases });
  } catch (error) {
    next(error);
  }
};

export const getDiseaseById = async (req, res, next) => {
  try {
    const disease = await Disease.findById(req.params.id);
    if (!disease) {
      return res.status(404).json({ success: false, message: 'Disease reference not found' });
    }
    res.json({ success: true, data: disease });
  } catch (error) {
    next(error);
  }
};
