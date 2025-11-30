# I-TUTOR Frontend - Deployment Guide

## Quick Start Deployment

### Local Development (5 minutes)

```bash
# 1. Install dependencies
pip install -r frontend/requirements.txt

# 2. Start Ollama (separate terminal)
ollama serve

# 3. Initialize RAG (if needed)
python3 -c "from scripts.rag import initialize_rag_system; initialize_rag_system()"

# 4. Run Streamlit
streamlit run frontend/app_ui.py

# 5. Open browser
# http://localhost:8501
```

---

## Render Deployment (10 minutes)

### Prerequisites
- GitHub account with repository
- Render account (free tier available)
- All code committed to GitHub

### Step-by-Step

#### 1. Prepare Repository
```bash
# Ensure all files are committed
git status
git add .
git commit -m "Add Phase 8 Frontend"
git push origin main
```

#### 2. Create Render Service

1. Go to [render.com](https://render.com)
2. Sign in with GitHub
3. Click "New +" button
4. Select "Web Service"
5. Choose your repository
6. Configure:

**Name**: `i-tutor-frontend`

**Environment**: `Python 3`

**Region**: `Oregon (US West)` (or closest to you)

**Build Command**:
```
pip install -r frontend/requirements.txt
```

**Start Command**:
```
streamlit run frontend/app_ui.py --server.port=$PORT --server.address=0.0.0.0
```

#### 3. Set Environment Variables

In Render dashboard, add:

```
PYTHONUNBUFFERED=1
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_SERVER_ENABLEXSRFPROTECTION=false
```

#### 4. Create Service

Click "Create Web Service"

Render will:
- Install dependencies
- Build the application
- Start the service
- Assign a URL

#### 5. Access Your App

Your app will be available at:
```
https://i-tutor-frontend.onrender.com
```

---

## Docker Deployment

### Create Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Copy requirements
COPY frontend/requirements.txt .
COPY requirements.txt ../

# Install dependencies
RUN pip install -r requirements.txt

# Copy application
COPY . .

# Set environment variables
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ENABLEXSRFPROTECTION=false

# Expose port
EXPOSE 8501

# Run Streamlit
CMD ["streamlit", "run", "frontend/app_ui.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Build and Run

```bash
# Build image
docker build -t i-tutor-frontend .

# Run container
docker run -p 8501:8501 i-tutor-frontend

# Access at http://localhost:8501
```

---

## Heroku Deployment

### Prerequisites
- Heroku account
- Heroku CLI installed

### Steps

```bash
# 1. Login to Heroku
heroku login

# 2. Create app
heroku create i-tutor-frontend

# 3. Add buildpack
heroku buildpacks:add heroku/python

# 4. Create Procfile
echo "web: streamlit run frontend/app_ui.py --server.port=\$PORT --server.address=0.0.0.0" > Procfile

# 5. Deploy
git push heroku main

# 6. View logs
heroku logs --tail

# 7. Open app
heroku open
```

---

## AWS Deployment

### Using Elastic Beanstalk

```bash
# 1. Install EB CLI
pip install awsebcli

# 2. Initialize
eb init -p python-3.10 i-tutor-frontend

# 3. Create environment
eb create i-tutor-env

# 4. Deploy
eb deploy

# 5. Open
eb open
```

---

## Environment Configuration

### Required Variables

```bash
# Ollama server (optional, defaults to localhost:11434)
OLLAMA_HOST=http://localhost:11434

# Data directory (optional, defaults to ./data)
DATA_DIR=./data

# Log level (optional, defaults to INFO)
LOG_LEVEL=INFO

# Streamlit specific
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_SERVER_ENABLEXSRFPROTECTION=false
PYTHONUNBUFFERED=1
```

### Render-Specific

In Render dashboard:
```
PYTHONUNBUFFERED=1
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_SERVER_ENABLEXSRFPROTECTION=false
```

---

## Troubleshooting Deployment

### Issue: "Build failed"

**Check logs**:
```bash
# Render: Check build logs in dashboard
# Heroku: heroku logs --tail
# Docker: docker build -t i-tutor-frontend . (verbose)
```

**Common causes**:
- Missing requirements
- Python version mismatch
- Path issues

**Solution**:
```bash
# Ensure all dependencies are in requirements.txt
pip freeze > requirements.txt
pip freeze > frontend/requirements.txt

# Commit and push
git add .
git commit -m "Update requirements"
git push
```

### Issue: "App crashes after deploy"

**Check logs**:
```bash
# Render: Dashboard → Logs
# Heroku: heroku logs --tail
# Docker: docker logs <container_id>
```

**Common causes**:
- Ollama not accessible
- FAISS index not found
- Import errors

**Solution**:
```bash
# Ensure backend is initialized
python3 -c "from scripts.rag import initialize_rag_system; initialize_rag_system()"

# Verify imports work
python3 -c "from mcp.client import MCPClient; from scripts.rag import RAGSystem"

# Check paths are relative
# All imports should use relative paths
```

### Issue: "Port already in use"

**Solution**:
```bash
# Render: Automatically uses $PORT variable
# Heroku: Automatically uses $PORT variable
# Local: Use different port
streamlit run frontend/app_ui.py --server.port 8502
```

### Issue: "Slow response times"

**Solutions**:
1. Reduce `top_k` default value
2. Disable RAG by default
3. Use smaller embedding model
4. Increase Render instance size

---

## Performance Optimization

### For Render (Free Tier)

1. **Reduce RAG top_k**:
   - Change default from 3 to 1
   - Users can increase if needed

2. **Disable RAG by default**:
   - Change `use_rag = st.checkbox(..., value=False)`

3. **Cache aggressively**:
   - `@st.cache_resource` for backend
   - `@st.cache_data` for static data

4. **Optimize imports**:
   - Lazy load heavy modules
   - Only import when needed

### For Production

1. **Use paid tier**:
   - More memory
   - Better CPU
   - Faster response times

2. **Add caching layer**:
   - Redis for answer caching
   - Memcached for embeddings

3. **Load balancing**:
   - Multiple instances
   - Nginx reverse proxy

4. **Database**:
   - PostgreSQL for metadata
   - MongoDB for conversations

---

## Monitoring & Logs

### Render

1. Go to dashboard
2. Select service
3. Click "Logs" tab
4. View real-time logs

### Heroku

```bash
# View logs
heroku logs --tail

# View specific dyno
heroku logs --dyno=web.1

# View historical logs
heroku logs --num=100
```

### Docker

```bash
# View logs
docker logs <container_id>

# Follow logs
docker logs -f <container_id>

# View specific lines
docker logs --tail=50 <container_id>
```

---

## Scaling

### Render

1. Dashboard → Service → Settings
2. Scroll to "Instance Type"
3. Upgrade from free to paid
4. Restart service

### Heroku

```bash
# Scale dynos
heroku ps:scale web=2

# Check dynos
heroku ps
```

### Docker

```bash
# Use Docker Compose for multiple instances
# Or use Kubernetes for orchestration
```

---

## Security Checklist

- [ ] No hardcoded secrets
- [ ] Use environment variables
- [ ] HTTPS enabled (automatic on Render/Heroku)
- [ ] Input validation
- [ ] CORS configured
- [ ] Rate limiting (optional)
- [ ] Logging enabled
- [ ] Error handling

---

## Maintenance

### Regular Tasks

1. **Update dependencies**:
```bash
pip list --outdated
pip install --upgrade <package>
```

2. **Monitor logs**:
```bash
# Check for errors
# Monitor response times
# Track usage patterns
```

3. **Backup data**:
```bash
# Backup FAISS index
# Backup metadata
# Backup logs
```

4. **Test functionality**:
```bash
# Test question submission
# Test RAG retrieval
# Test all modes
```

---

## Rollback

### Render

1. Dashboard → Service → Deployments
2. Select previous deployment
3. Click "Deploy"

### Heroku

```bash
# View releases
heroku releases

# Rollback to previous
heroku rollback v<number>
```

### Docker

```bash
# Use previous image tag
docker run -p 8501:8501 i-tutor-frontend:previous
```

---

## Cost Estimation

### Render (Free Tier)
- Cost: $0/month
- Limitations: Spins down after 15 min inactivity
- Good for: Development, testing

### Render (Starter)
- Cost: $7/month
- Always on, 0.5GB RAM
- Good for: Small production

### Heroku
- Cost: $7/month (Eco dyno)
- Always on, 512MB RAM
- Good for: Small production

### AWS
- Cost: $5-50/month (varies)
- Scalable, many options
- Good for: Production

---

## Support

### Documentation
- [README.md](README.md) - Frontend guide
- [../README_MVP.md](../README_MVP.md) - Main project
- [../PHASE7_RAG_SUMMARY.md](../PHASE7_RAG_SUMMARY.md) - RAG guide

### Troubleshooting
1. Check logs
2. Verify imports
3. Test locally first
4. Check environment variables
5. Review error messages

---

## Quick Reference

### Local
```bash
streamlit run frontend/app_ui.py
```

### Render
```
https://i-tutor-frontend.onrender.com
```

### Docker
```bash
docker run -p 8501:8501 i-tutor-frontend
```

### Heroku
```bash
heroku open
```

---

**Status**: ✅ Deployment Ready
**Version**: 0.1.0 (MVP)
**Last Updated**: November 30, 2025
