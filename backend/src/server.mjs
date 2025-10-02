import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';

const allowedOrigins = (process.env.ALLOWED_ORIGINS || '').split(',').filter(Boolean);

const app = express();
app.use(helmet());
app.use(cors({
  origin: allowedOrigins.length ? allowedOrigins : true,
}));
app.use(express.json());

app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

// AUTO-ROUTERS

const port = process.env.PORT || 4000;
app.listen(port, () => {
  console.log(`Backend clone server listening on http://localhost:${port}`);
});
