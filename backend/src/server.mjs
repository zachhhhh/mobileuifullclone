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

const state = {
  user: {
    authenticated: process.env.DEFAULT_AUTHENTICATED === 'true',
    name: process.env.DEFAULT_USER_NAME || 'Guest',
    avatarUrl: process.env.DEFAULT_USER_AVATAR || null,
    email: process.env.DEFAULT_USER_EMAIL || 'user@example.com',
    premium: process.env.DEFAULT_USER_PREMIUM === 'true',
  },
  onboarding: {
    completed: process.env.DEFAULT_ONBOARDING_COMPLETED === 'true',
    step: process.env.DEFAULT_ONBOARDING_STEP || 'welcome',
  },
  featureFlags: {
    paywallEnabled: process.env.FLAG_PAYWALL_ENABLED !== 'false',
    notificationsEnabled: process.env.FLAG_NOTIFICATIONS_ENABLED !== 'false',
  },
  feed: [
    {
      id: 'session-1',
      title: 'Daily Meditation',
      subtitle: '10 min • Mindfulness',
      imageUrl: 'https://example.com/assets/meditation.png',
      duration: 600,
      difficulty: 'Beginner',
      tags: ['mindfulness', 'focus'],
    },
    {
      id: 'session-2',
      title: 'Breathing Exercise',
      subtitle: '5 min • Stress Relief',
      imageUrl: 'https://example.com/assets/breathing.png',
      duration: 300,
      difficulty: 'All levels',
      tags: ['breathing', 'calm'],
    },
  ],
  content: {
    'session-1': {
      id: 'session-1',
      title: 'Daily Meditation',
      description: 'Ease into your day with a 10-minute guided meditation focused on mindful awareness.',
      audioUrl: 'https://cdn.example.com/audio/session-1.mp3',
      duration: 600,
      instructor: 'Jamie',
      coverUrl: 'https://example.com/assets/meditation.png',
    },
    'session-2': {
      id: 'session-2',
      title: 'Breathing Exercise',
      description: 'Reset quickly with a simple breathing technique to release stress.',
      audioUrl: 'https://cdn.example.com/audio/session-2.mp3',
      duration: 300,
      instructor: 'Priya',
      coverUrl: 'https://example.com/assets/breathing.png',
    },
  },
  progress: {},
  downloads: {},
  paywallPlans: [
    {
      id: 'monthly',
      title: 'Monthly Subscription',
      priceLocalized: '$12.99 / month',
      trial: '7-day free trial',
      bestValue: false,
    },
    {
      id: 'annual',
      title: 'Annual Subscription',
      priceLocalized: '$89.99 / year',
      trial: '7-day free trial',
      bestValue: true,
    },
  ],
  notificationPreview: {
    title: 'Time to breathe',
    body: 'Take 5 minutes to reset with your daily meditation.',
    deepLink: 'cloneapp://session/session-1',
  },
  analyticsEvents: [],
};

app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

app.get('/session', (req, res) => {
  res.json({
    status: 'ok',
    user: {
      authenticated: state.user.authenticated,
      name: state.user.name,
      avatarUrl: state.user.avatarUrl,
      premium: state.user.premium,
    },
    onboarding: { ...state.onboarding },
    featureFlags: { ...state.featureFlags },
    timestamp: new Date().toISOString(),
  });
});

app.post('/auth/login', (req, res) => {
  const { email, password } = req.body || {};
  const expectedEmail = state.user.email;
  const expectedPassword = process.env.DEFAULT_USER_PASSWORD || 'password123';
  if (email === expectedEmail && password === expectedPassword) {
    state.user.authenticated = true;
    state.user.name = process.env.DEFAULT_USER_NAME || 'Member';
    state.user.premium = process.env.DEFAULT_USER_PREMIUM === 'true';
    return res.json({ status: 'ok', message: 'Authenticated' });
  }
  res.status(401).json({ status: 'error', message: 'Invalid credentials' });
});

app.post('/auth/logout', (req, res) => {
  state.user.authenticated = false;
  state.user.premium = false;
  state.onboarding.completed = false;
  state.onboarding.step = 'welcome';
  res.json({ status: 'ok', message: 'Logged out' });
});

app.post('/onboarding/advance', (req, res) => {
  const { step, completed } = req.body || {};
  if (completed === true) {
    state.onboarding.completed = true;
    state.onboarding.step = 'completed';
  } else if (typeof step === 'string') {
    state.onboarding.step = step;
  }
  res.json({ status: 'ok', onboarding: { ...state.onboarding } });
});

app.get('/feed', (req, res) => {
  if (!state.user.authenticated) {
    return res.status(401).json({ status: 'error', message: 'Authentication required' });
  }
  res.json({ status: 'ok', items: state.feed });
});

app.get('/content/:id', (req, res) => {
  const { id } = req.params;
  const content = state.content[id];
  if (!content) {
    return res.status(404).json({ status: 'error', message: 'Content not found' });
  }
  res.json({ status: 'ok', content, progress: state.progress[id] || { position: 0, completed: false } });
});

app.post('/content/:id/progress', (req, res) => {
  const { id } = req.params;
  const content = state.content[id];
  if (!content) {
    return res.status(404).json({ status: 'error', message: 'Content not found' });
  }
  const { position = 0, completed = false } = req.body || {};
  state.progress[id] = {
    position: Math.min(position, content.duration),
    completed: completed || position >= content.duration,
    updatedAt: new Date().toISOString(),
  };
  res.json({ status: 'ok', progress: state.progress[id] });
});

app.post('/content/:id/download', (req, res) => {
  const { id } = req.params;
  if (!state.content[id]) {
    return res.status(404).json({ status: 'error', message: 'Content not found' });
  }
  state.downloads[id] = {
    id,
    status: 'downloaded',
    downloadedAt: new Date().toISOString(),
  };
  res.json({ status: 'ok', download: state.downloads[id] });
});

app.delete('/content/:id/download', (req, res) => {
  const { id } = req.params;
  delete state.downloads[id];
  res.json({ status: 'ok' });
});

app.get('/profile', (req, res) => {
  if (!state.user.authenticated) {
    return res.status(401).json({ status: 'error', message: 'Authentication required' });
  }
  res.json({
    status: 'ok',
    user: state.user,
    featureFlags: state.featureFlags,
  });
});

app.post('/profile', (req, res) => {
  if (!state.user.authenticated) {
    return res.status(401).json({ status: 'error', message: 'Authentication required' });
  }
  const { name } = req.body || {};
  if (name) {
    state.user.name = name;
  }
  res.json({ status: 'ok', user: state.user });
});

app.get('/paywall', (req, res) => {
  res.json({
    status: 'ok',
    paywallEnabled: state.featureFlags.paywallEnabled,
    plans: state.paywallPlans,
    premium: state.user.premium,
  });
});

app.post('/paywall/purchase', (req, res) => {
  const { planId } = req.body || {};
  if (!planId) {
    return res.status(400).json({ status: 'error', message: 'planId required' });
  }
  state.user.premium = true;
  res.json({ status: 'ok', premium: true, planId });
});

app.get('/notifications/preview', (req, res) => {
  if (!state.featureFlags.notificationsEnabled) {
    return res.status(403).json({ status: 'error', message: 'Notifications disabled' });
  }
  res.json({ status: 'ok', notification: state.notificationPreview });
});

app.post('/feature-flags', (req, res) => {
  const { paywallEnabled, notificationsEnabled } = req.body || {};
  if (typeof paywallEnabled === 'boolean') {
    state.featureFlags.paywallEnabled = paywallEnabled;
  }
  if (typeof notificationsEnabled === 'boolean') {
    state.featureFlags.notificationsEnabled = notificationsEnabled;
  }
  res.json({ status: 'ok', featureFlags: state.featureFlags });
});

app.post('/analytics/events', (req, res) => {
  const { name, properties } = req.body || {};
  if (!name) {
    return res.status(400).json({ status: 'error', message: 'name required' });
  }
  const event = {
    name,
    properties: properties || {},
    recordedAt: new Date().toISOString(),
  };
  state.analyticsEvents.push(event);
  res.json({ status: 'ok' });
});

// AUTO-ROUTERS

const port = process.env.PORT || 4000;
app.listen(port, () => {
  console.log(`Backend clone server listening on http://localhost:${port}`);
});
