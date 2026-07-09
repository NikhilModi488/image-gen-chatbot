import express from 'express';
import cors from 'cors';
import path from 'path';
import { config } from './config/config.js';
import imageRoutes from './src/routes/imageRoutes.js';

const app = express();

// Middleware
app.use(cors());
app.use(express.json({ limit: '10mb' })); // Allow slightly larger JSON request limits if needed
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Serve frontend static assets from public folder
app.use(express.static(config.publicPath));

// API Routes
app.use('/api', imageRoutes);

// Fallback route: serve frontend index.html for any other requests
app.get('*', (req, res) => {
  res.sendFile(path.join(config.publicPath, 'index.html'));
});

// Start listening
app.listen(config.port, () => {
  console.log('==================================================');
  console.log(` Text-to-Image Chatbot Server is starting up...`);
  console.log(` Running on port: ${config.port}`);
  console.log(` Local URL: http://localhost:${config.port}`);
  console.log(` Environment Mode: ${process.env.NODE_ENV || 'development'}`);
  console.log(` Default Generation Provider: ${config.generator.provider}`);
  console.log('==================================================');
});
