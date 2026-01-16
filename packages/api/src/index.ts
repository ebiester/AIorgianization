import express from 'express';
import cors from 'cors';
import { taskRoutes } from './routes/tasks.js';
import { dashboardRoutes } from './routes/dashboard.js';

const app = express();
const PORT = process.env.AIO_PORT || 3847;

app.use(cors());
app.use(express.json());

// API routes
app.use('/api/tasks', taskRoutes);
app.use('/api/dashboard', dashboardRoutes);

// Health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

export function startServer() {
  app.listen(PORT, () => {
    console.log(`AIorgianization API running at http://localhost:${PORT}`);
  });
}

// Start if run directly
if (process.argv[1]?.endsWith('index.js') || process.argv[1]?.endsWith('index.ts')) {
  startServer();
}

export { app };
