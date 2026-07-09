import express from 'express';
import { ImageController } from '../controllers/imageController.js';

const router = express.Router();

// POST /api/generate
router.post('/generate', ImageController.generate);

export default router;
