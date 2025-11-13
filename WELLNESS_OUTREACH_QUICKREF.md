# Wellness Outreach Quick Reference

**Sprint 7** | **Last Updated:** November 13, 2025

## 🚀 Quick Start

```bash
# FIRST: Install new dependency (one-time setup)
docker-compose exec backend pip install schedule
# OR rebuild: docker-compose build backend

# Run manually
./run_wellness_outreach.sh

# Or directly
docker-compose exec backend python -m app.wellness_outreach

# Run tests
docker-compose exec backend python -m app.test_wellness_outreach

# Run scheduler (continuous)
docker-compose exec backend python -m app.wellness_scheduler
```

## 📁 Files

| File                                    | Purpose             | Lines |
| --------------------------------------- | ------------------- | ----- |
| `backend/app/wellness_outreach.py`      | Core implementation | 420   |
| `backend/app/wellness_scheduler.py`     | Scheduler service   | 95    |
| `backend/app/test_wellness_outreach.py` | Test suite          | 530   |
| `run_wellness_outreach.sh`              | Runner script       | 35    |
| `WELLNESS_OUTREACH_GUIDE.md`            | Full documentation  | 350+  |

## ⚙️ Configuration

Edit `backend/app/wellness_outreach.py`:

```python
LOOKBACK_MONTHS = 12          # Pet eligibility window
LOOKAHEAD_DAYS = 7            # Slot search window
SLOT_DURATION_HOURS = 1       # Appointment length
BUSINESS_START_HOUR = 9       # 9 AM
BUSINESS_END_HOUR = 17        # 5 PM (last slot at 4)
```

## 🔄 Workflow

```
1. get_target_pets()         → Find pets needing care
2. find_open_slots()         → Search available appointments
3. match_slot_to_preference()→ Vector similarity matching
4. generate_outreach_email() → LLM-powered email generation
5. process_outreach()        → Execute & log results
```

## 📊 Output

**Console:** Live progress with emoji indicators  
**Log File:** `backend/outreach_log.txt`

## 🧪 Testing

```bash
# Full test suite (5 tests)
docker-compose exec backend python -m app.test_wellness_outreach

# Creates test data, runs all tests, cleans up
# Expected: 5/5 tests pass
```

## 🐳 Docker Service

Add to `docker-compose.yml`:

```yaml
wellness-scheduler:
  build: ./backend
  command: python -m app.wellness_scheduler
  depends_on: [db, ollama, backend]
  environment:
    - DATABASE_URL=postgresql://user:password@db/interpawsdb
    - OLLAMA_HOST=http://ollama:11434
  restart: unless-stopped
```

## 📋 Checklist Before Running

- ✅ Docker containers running (`docker-compose ps`)
- ✅ **NEW:** `schedule` package installed (`docker-compose exec backend pip install schedule`)
- ✅ Database seeded with staff/clients
- ✅ Ollama has `llama3` model (`ollama list`)
- ✅ Test with `test_wellness_outreach.py` first

**See [SPRINT_7_SETUP.md](SPRINT_7_SETUP.md) for first-time setup.**

## 🔧 Troubleshooting

| Issue              | Solution                                        |
| ------------------ | ----------------------------------------------- |
| No pets found      | Normal if all pets have recent/future bookings  |
| No slots available | Check staff exist, verify business hours        |
| Ollama error       | `docker-compose exec ollama ollama pull llama3` |
| Import error       | `docker-compose restart backend`                |

## 📖 Full Docs

See **[WELLNESS_OUTREACH_GUIDE.md](WELLNESS_OUTREACH_GUIDE.md)** for complete documentation.

## 🎯 Key Functions

```python
# In backend/app/wellness_outreach.py

get_target_pets(db: Session) -> List[Tuple[Pet, Client]]
# Returns pets with no future bookings + no visits in 12 months

find_open_slots(db: Session, days_ahead: int) -> List[dict]
# Returns available slots with metadata

match_slot_to_preference(client: Client, open_slots: List[dict], db: Session) -> dict
# Returns best matching slot using L2 distance

generate_outreach_email(pet: Pet, client: Client, slot: dict) -> str
# Returns AI-generated personalized email

process_outreach(db: Session, log_to_file: bool) -> dict
# Executes full workflow, returns summary
```

## 💡 Usage Examples

**Manual run with custom config:**

```python
# Edit wellness_outreach.py temporarily
LOOKAHEAD_DAYS = 14  # Search 2 weeks instead of 7

# Then run
docker-compose exec backend python -m app.wellness_outreach
```

**Schedule for 8 AM Mondays:**

```python
# Edit wellness_scheduler.py
SCHEDULE_DAY = "monday"
SCHEDULE_TIME = "08:00"

# Run scheduler
docker-compose exec backend python -m app.wellness_scheduler
```

**Create test scenario:**

```python
# Use test_wellness_outreach.py as template
# Or manually create client with old booking
```

---

**Quick Links:**

- Full Guide: [WELLNESS_OUTREACH_GUIDE.md](WELLNESS_OUTREACH_GUIDE.md)
- Implementation Summary: [SPRINT_7_SUMMARY.md](SPRINT_7_SUMMARY.md)
- Main README: [README.md](README.md)
