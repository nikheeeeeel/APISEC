# APISec Frontend - Modern React UI

A modern, dark-themed React interface for APISec with shadcn/ui components.

## Features

### 🎨 Modern UI Design
- **Dark Theme**: Elegant dark mode with light mode toggle
- **Responsive Design**: Mobile-first responsive layout
- **shadcn/ui Components**: Modern, accessible component library
- **Smooth Animations**: Subtle transitions and micro-interactions

### 🔧 Advanced Functionality
- **Content-Type Adaptive Probing**: Automatic detection of JSON, multipart, form endpoints
- **Real-time Results**: Live parameter discovery with confidence scoring
- **Enhanced Visualization**: Parameter details with evidence display
- **Download Capabilities**: Export inference results and OpenAPI specs
- **Error Handling**: Comprehensive error states and user feedback

### 🛠️ Technical Stack
- **React 18**: Modern React with hooks
- **TypeScript**: Full type safety
- **Vite**: Fast development and building
- **Tailwind CSS**: Utility-first styling
- **shadcn/ui**: High-quality component library
- **Lucide Icons**: Beautiful icon set

## Getting Started

### Prerequisites
- Node.js 18+
- npm or yarn

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

The UI will be available at `http://localhost:3000`

### Building

```bash
npm run build
```

## Component Structure

```
src/
├── components/
│   ├── ui/              # shadcn/ui components
│   ├── InferenceForm.tsx
│   └── ResultsDisplay.tsx
├── hooks/
│   └── use-inference.ts
├── lib/
│   ├── api.ts          # API client
│   └── utils.ts        # Utility functions
├── App.tsx               # Main application
└── main.tsx              # Entry point
```

## Key Features

### 🌐 Content-Type Detection
- Automatically detects JSON, multipart/form-data, and application/x-www-form-urlencoded
- Adaptive probing strategies based on endpoint classification
- Real-time feedback during discovery process

### 📊 Results Visualization
- Parameter cards with confidence scoring
- Evidence display with error details
- Location and type indicators
- Execution metrics and endpoint classification

### 🎨 Dark Theme
- System preference detection
- Manual toggle with smooth transition
- Carefully chosen color palette for reduced eye strain
- Consistent design language

### 📱 Responsive Design
- Mobile-first approach
- Adaptive layouts for different screen sizes
- Touch-friendly interactions
- Optimized performance

## Integration with Backend

Vite proxies `/api/*` to `http://localhost:8000` so the production FastAPI backend can stay on port 8000 while the UI runs on port 3000. The helper found at `src/lib/api.ts` pulls `VITE_API_BASE_PATH` (currently set to `/api` in `frontend/.env`) so every fetch consistently targets:

- **Health Check**: `/api/health`
- **Parameter Inference**: `/api/infer`
- **Spec Generation**: `/api/spec`

All API calls include proper error handling and user feedback, and the proxy means no absolute backend URL must be embedded in the component code.

## Running the full stack for demos

1. **Backend server**
   ```bash
   cd backend
   python server.py
   ```
2. **Demo/Test API**
   ```bash
   cd ../test_api
   npm start
   ```
   The Express demo service listens on `http://localhost:5050` and returns structured validation errors so APISec can extract every type/query/header detail.
3. **Frontend**
   ```bash
   cd ../frontend
   npm run dev
   ```
   The UI launches at `http://localhost:3000`. Enter any `http://localhost:5050/...` route from the demo API to showcase the project’s capabilities.

## Demo/test API endpoints

Point the UI at these URLs during your presentation. Each response intentionally includes missing-field diagnostics or header failures so the inference engine surfaces specific parameter names and locations.

| Endpoint | Method | What it highlights | Required input |
| --- | --- | --- | --- |
| `/users?email=...` | GET | Query parameter inference | Query `email` |
| `/search?q=...` | GET | Query parameter search behavior | Query `q` |
| `/login` | POST | Required body fields (`username`, `password`) | JSON body with both keys |
| `/orders` | POST | Body validation across `orderId`, `quantity`, `shippingAddress` | JSON body with all three keys |
| `/items/:itemId` | GET | Path parameter inference (`itemId`) | URL such as `/items/42` |
| `/users/:userId/status` | PATCH | Path + body `status` updates | JSON body `{"status": "active"}` |
| `/secure-data` | GET | Header-based auth (`Authorization: Bearer testtoken`) | Header `Authorization: Bearer testtoken` |
| `/reports` | GET | Custom header validation (`X-Report-Token`) | Header `X-Report-Token: report123` |

## Development Notes

- Uses absolute imports with `@/` alias for clean paths
- TypeScript strict mode for type safety
- ESLint configuration for code quality
- Vite proxy configuration for seamless backend integration
