const express = require('express');
const bodyParser = require('body-parser');

const app = express();
const PORT = process.env.PORT || 5050;

app.use(bodyParser.json());

const formatMissingFields = (fields, location) =>
  fields.map((field) => ({
    field,
    message: `Missing required ${location} field: ${field}`,
    loc: [location, field],
  }));

const sendValidationError = (res, fields, location) => {
  return res.status(422).json({
    error: 'ValidationError',
    details: formatMissingFields(fields, location),
  });
};

app.get('/health', (_req, res) => {
  return res.status(200).json({ status: 'ok' });
});

app.get('/users', (req, res) => {
  const { email } = req.query;

  if (!email) {
    return sendValidationError(res, ['email'], 'query');
  }

  return res.status(200).json({
    user: {
      email,
    },
  });
});

app.get('/search', (req, res) => {
  const { q } = req.query;

  if (!q) {
    return res.status(400).json({
      error: 'ValidationError',
      message: 'Missing required query parameter: q',
    });
  }

  return res.status(200).json({
    query: q,
    results: ['alpha', 'beta', 'gamma'].map((text) => `${q}-${text}`),
  });
});

app.post('/login', (req, res) => {
  const { username, password } = req.body || {};
  const missingFields = [];

  if (!username) {
    missingFields.push('username');
  }
  if (!password) {
    missingFields.push('password');
  }

  if (missingFields.length) {
    return sendValidationError(res, missingFields, 'body');
  }

  return res.status(200).json({ token: 'abc123' });
});

app.get('/secure-data', (req, res) => {
  const auth = req.header('authorization');
  const expected = 'Bearer testtoken';

  if (auth !== expected) {
    return res.status(401).json({
      error: 'Unauthorized',
      message: 'Missing or invalid Authorization header',
    });
  }

  return res.status(200).json({ data: 'secure' });
});

app.get('/items/:itemId', (req, res) => {
  const { itemId } = req.params;

  if (!itemId) {
    return sendValidationError(res, ['itemId'], 'path');
  }

  if (!/^[0-9]+$/.test(itemId)) {
    return res.status(422).json({
      error: 'ValidationError',
      details: [
        {
          field: 'itemId',
          message: 'itemId must be a numeric identifier',
          loc: ['path', 'itemId'],
        },
      ],
    });
  }

  return res.status(200).json({
    itemId,
    name: `Demo item ${itemId}`,
    available: true,
  });
});

app.post('/orders', (req, res) => {
  const { orderId, quantity, shippingAddress } = req.body || {};
  const missingFields = [];

  if (orderId === undefined || orderId === null) missingFields.push('orderId');
  if (quantity === undefined || quantity === null) missingFields.push('quantity');
  if (!shippingAddress) missingFields.push('shippingAddress');

  if (missingFields.length) {
    return sendValidationError(res, missingFields, 'body');
  }

  return res.status(201).json({
    orderId,
    quantity,
    shippingAddress,
    status: 'queued',
  });
});

app.get('/reports', (req, res) => {
  const token = req.header('x-report-token');

  if (!token) {
    return res.status(401).json({
      error: 'Unauthorized',
      message: 'Missing X-Report-Token header',
    });
  }

  return res.status(200).json({
    report: 'compliance',
    token,
  });
});

app.patch('/users/:userId/status', (req, res) => {
  const { userId } = req.params;
  const { status } = req.body || {};

  if (!userId) {
    return sendValidationError(res, ['userId'], 'path');
  }

  if (!status) {
    return sendValidationError(res, ['status'], 'body');
  }

  return res.status(200).json({
    userId,
    status,
  });
});

app.listen(PORT, () => {
  console.log(`Test API listening on http://localhost:${PORT}`);
});
