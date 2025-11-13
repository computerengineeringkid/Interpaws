# 📋 Sprint 7 Post-Implementation Setup

**Important:** After pulling the Sprint 7 code, you need to install the new dependency.

## 🔧 Install New Dependency

The wellness scheduler requires the `schedule` package. Choose one of these methods:

### Method 1: Rebuild Container (Recommended)

```bash
# Stop containers
docker-compose down

# Rebuild backend with new dependencies
docker-compose build backend

# Start everything
docker-compose up -d

# Wait for services to be ready
sleep 10
```

### Method 2: Install in Running Container

```bash
# Install schedule package in the running container
docker-compose exec backend pip install schedule

# Verify installation
docker-compose exec backend pip show schedule
```

### Method 3: Use start.sh (Handles Everything)

```bash
# The start.sh script rebuilds containers automatically
./start.sh
```

---

## ✅ Verify Installation

```bash
# Check if schedule is installed
docker-compose exec backend python -c "import schedule; print('✅ Schedule installed successfully')"
```

Expected output: `✅ Schedule installed successfully`

---

## 🧪 Run Tests After Installation

```bash
# Test the wellness outreach system
docker-compose exec backend python -m app.test_wellness_outreach
```

Expected: **5/5 tests pass**

---

## 🚀 First Run

After installation, try a manual run:

```bash
./run_wellness_outreach.sh
```

Or run the scheduler:

```bash
docker-compose exec backend python -m app.wellness_scheduler
```

---

## ⚠️ Troubleshooting

### Error: "ModuleNotFoundError: No module named 'schedule'"

**Cause:** The `schedule` package hasn't been installed yet.

**Solution:** Use one of the installation methods above.

### Error: Pylance shows "Import 'schedule' could not be resolved"

**Cause:** This is a local IDE warning. The package will be available in Docker once installed.

**Solution:**

1. Install the package in the Docker container (see above)
2. The error will persist in your local IDE but won't affect execution in Docker
3. (Optional) For local development: `pip install schedule` on your host machine

### Container won't start after rebuild

**Cause:** May need to clear old volumes or images.

**Solution:**

```bash
docker-compose down -v
docker-compose build --no-cache backend
docker-compose up -d
```

---

## 📦 What Was Added

The following line was added to `backend/requirements.txt`:

```
schedule
```

This package provides cron-like scheduling for Python and is used by:

- `backend/app/wellness_scheduler.py` - Continuous scheduling service

---

## 🔄 CI/CD Note

If you have a CI/CD pipeline, ensure it rebuilds the Docker images to pick up the new dependency. The updated `requirements.txt` will be included automatically.

---

**Next:** Proceed to [SPRINT_7_COMPLETE.md](SPRINT_7_COMPLETE.md) for usage instructions.
