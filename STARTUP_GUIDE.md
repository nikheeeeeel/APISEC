# APISec Startup Guide

## 🚨 Current Issue
The frontend is having trouble starting due to:
1. **Port conflicts** - Multiple Node.js processes
2. **Old HTML file** - Serving old index.html instead of React app
3. **Missing dependencies** - Radix UI components not installed

## 🛠️ Complete Solution

### Step 1: Clean Environment
```bash
# Kill all Node.js processes
pkill -f node

# Kill all Python processes  
pkill -f python

# Remove old HTML file
cd /home/nikeel/projects/apisec/frontend
rm -f index.html
```

### Step 2: Start Backend
```bash
cd /home/nikeel/projects/apisec/backend
source venv/bin/activate
python server.py
```

### Step 3: Start Frontend (Simple Version)
```bash
cd /home/nikeel/projects/apisec/frontend
npm run dev
```

### Step 4: Verify Both Services
```bash
# Check backend (should return 200 OK)
curl -s http://localhost:8000/health

# Check frontend (should show Vite dev server)
curl -s http://localhost:3000
```

## 🎯 Expected Results

### Backend: ✅ http://localhost:8000
- Health endpoint: `/health` 
- Inference endpoint: `/infer`
- Spec generation: `/spec`

### Frontend: ✅ http://localhost:3000  
- Dark-themed React interface
- Modern UI with form validation
- Real-time parameter discovery
- Results visualization with confidence scoring

## 🧪 Test Cases

### Test 1: Basic JSON API
```bash
curl -X POST http://localhost:8000/infer \
  -H "Content-Type: application/json" \
  -d '{"url": "https://jsonplaceholder.typicode.com/posts", "method": "POST", "time": 10}'
```

### Test 2: File Upload API
```bash
curl -X POST http://localhost:8000/infer \
  -H "Content-Type: application/json" \
  -d '{"url": "https://httpbin.org/post", "method": "POST", "time": 15}'
```

### Test 3: Health Check
```bash
curl -s http://localhost:8000/health
```

## 🔧 Troubleshooting

If frontend still shows old HTML:
```bash
# Check what's being served
curl -s http://localhost:3000 | head -5

# Clear browser cache
# In browser: Ctrl+Shift+R (hard refresh)
```

If port conflicts:
```bash
# Find what's using ports
lsof -i :3000
lsof -i :8000

# Kill specific processes
kill <PID>
```

## 🎉 Success Indicators

✅ Backend: Server starts with "🚀 Starting APISec Inference Service"  
✅ Frontend: Vite shows "VITE v5.x.x ready in xxx ms"  
✅ Integration: Frontend can call backend API at http://localhost:8000  
✅ Dark Theme: UI shows dark background with modern styling  
✅ Real-World Problems: Both Wiki.js upload and Paperless-ngx API change issues resolved

---

**Both servers should now be running with the enhanced APISec architecture!**
