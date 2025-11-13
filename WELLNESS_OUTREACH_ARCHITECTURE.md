# Wellness Outreach System - Architecture Diagram

## System Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      WELLNESS OUTREACH SYSTEM                               │
│                         (wellness_outreach.py)                              │
└─────────────────────────────────────────────────────────────────────────────┘

                                    │
                                    ▼

┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 1: IDENTIFY TARGET PETS                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  get_target_pets(db)                                                        │
│                                                                             │
│  Query Database:                                                            │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐                               │
│  │  Clients │ ◄─┤   Pets   │ ◄─┤ Bookings │                               │
│  └──────────┘   └──────────┘   └──────────┘                               │
│                                                                             │
│  Criteria:                                                                  │
│  • No future bookings                                                       │
│  • AND (no past bookings OR last booking > 12 months ago)                  │
│                                                                             │
│  Returns: [(Pet, Client), (Pet, Client), ...]                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 2: FIND AVAILABLE SLOTS                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  find_open_slots(db, days_ahead=7)                                          │
│                                                                             │
│  For next 7 days (skip weekends):                                           │
│    For each business hour (9 AM - 4 PM):                                    │
│      For each staff member:                                                 │
│        ┌──────────────────────────────────────┐                            │
│        │  check_availability()                 │                            │
│        │  (from booking_logic.py)              │                            │
│        └──────────────────────────────────────┘                            │
│                                                                             │
│  Returns: [                                                                 │
│    {start_time, end_time, staff_id, staff_name,                             │
│     day_name: "Monday", time_period: "Morning",                             │
│     description: "Monday Morning"},                                         │
│    ...                                                                      │
│  ]                                                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 3: MATCH SLOTS TO PREFERENCES                                        │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  For each (Pet, Client):                                                    │
│                                                                             │
│    match_slot_to_preference(client, open_slots, db)                         │
│                                                                             │
│    ┌─────────────────────────────────────────────────┐                     │
│    │ Get client's Preferences                        │                     │
│    │ Has details_vector? ──► YES ─┐                  │                     │
│    │                        ▼      │                  │                     │
│    │                       NO      │                  │                     │
│    │                        │      │                  │                     │
│    │                        │      ▼                  │                     │
│    │                        │   Vector Search:        │                     │
│    │                        │   ┌────────────────┐    │                     │
│    │                        │   │ get_embedding() │    │                     │
│    │                        │   │ (each slot desc)│    │                     │
│    │                        │   └────────────────┘    │                     │
│    │                        │          │              │                     │
│    │                        │          ▼              │                     │
│    │                        │   Calculate L2 distance │                     │
│    │                        │   Return best match     │                     │
│    │                        │          │              │                     │
│    │                        ▼          │              │                     │
│    │                 Return first      │              │                     │
│    │                 available slot    │              │                     │
│    │                        │          │              │                     │
│    │                        └──────────┘              │                     │
│    └─────────────────────────────────────────────────┘                     │
│                                                                             │
│  Returns: Best matching slot for this client                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 4: GENERATE PERSONALIZED EMAIL                                       │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  generate_outreach_email(pet, client, slot)                                 │
│                                                                             │
│  Build Prompt:                                                              │
│  ┌────────────────────────────────────────────────┐                        │
│  │ Pet Name: {pet.name}                           │                        │
│  │ Pet Species: {pet.species}                     │                        │
│  │ Owner Name: {client.name}                      │                        │
│  │ Suggested Appointment: {formatted_slot_time}   │                        │
│  │ Veterinarian: {staff_name}                     │                        │
│  │                                                │                        │
│  │ Instructions:                                  │                        │
│  │ - Write warm, professional email               │                        │
│  │ - Mention it's been a while                    │                        │
│  │ - Suggest specific time                        │                        │
│  │ - Keep concise (3-4 paragraphs)                │                        │
│  └────────────────────────────────────────────────┘                        │
│                          │                                                  │
│                          ▼                                                  │
│  ┌─────────────────────────────────────────────┐                           │
│  │  get_ollama_recommendation(prompt)          │                           │
│  │  (Ollama/llama3 via ai_services.py)         │                           │
│  └─────────────────────────────────────────────┘                           │
│                          │                                                  │
│         ┌────────────────┴────────────────┐                                │
│         ▼                                  ▼                                │
│    SUCCESS                              ERROR                               │
│  Return LLM email                   Return fallback template                │
│                          │                                                  │
│                          ▼                                                  │
│  Returns: Personalized email text                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 5: OUTPUT & LOGGING                                                  │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  For each generated email:                                                  │
│                                                                             │
│  ┌─────────────────┐          ┌─────────────────┐                          │
│  │   Print to      │          │   Append to     │                          │
│  │   stdout        │          │   Log File      │                          │
│  │  (with emoji)   │          │ outreach_log.txt│                          │
│  └─────────────────┘          └─────────────────┘                          │
│                                                                             │
│  Format:                                                                    │
│  ═══════════════════════════════════════════                               │
│  TO: client@example.com (Client Name)                                       │
│  RE: Wellness Check for PetName                                             │
│  SUGGESTED SLOT: Monday, Nov 18 at 10:00 AM                                 │
│  ═══════════════════════════════════════════                               │
│  [Email body text...]                                                       │
│  ═══════════════════════════════════════════                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  SUMMARY & COMPLETION                                                      │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  Return Summary:                                                            │
│  {                                                                          │
│    "total_pets_identified": 15,                                             │
│    "emails_generated": 14,                                                  │
│    "errors": ["Error message if any"],                                      │
│    "emails": [                                                              │
│      {client_email, client_name, pet_name, slot_time, email_body},          │
│      ...                                                                    │
│    ]                                                                        │
│  }                                                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Execution Modes

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  MODE 1: MANUAL EXECUTION                                                  │
└─────────────────────────────────────────────────────────────────────────────┘

   User ──► ./run_wellness_outreach.sh
              │
              └──► docker-compose exec backend python -m app.wellness_outreach
                     │
                     └──► main() ──► process_outreach() ──► [Complete workflow]


┌─────────────────────────────────────────────────────────────────────────────┐
│  MODE 2: SCHEDULED EXECUTION (Cron)                                        │
└─────────────────────────────────────────────────────────────────────────────┘

   Cron Job ──► Every Monday 8 AM
                   │
                   └──► docker-compose exec -T backend python -m app.wellness_outreach
                          │
                          └──► main() ──► process_outreach() ──► [Complete workflow]


┌─────────────────────────────────────────────────────────────────────────────┐
│  MODE 3: CONTINUOUS SCHEDULER                                              │
└─────────────────────────────────────────────────────────────────────────────┘

   Docker Service ──► wellness-scheduler container
                         │
                         └──► python -m app.wellness_scheduler
                                │
                                └──► schedule.every().monday.at("08:00")
                                       │
                                       └──► Infinite loop
                                              │
                                              └──► scheduled_job()
                                                     │
                                                     └──► run_wellness_outreach()
```

## Data Flow Diagram

```
┌───────────────────────────────────────────────────────────────────────────┐
│                            DATABASE                                       │
│                                                                           │
│  ┌────────┐   ┌────────┐   ┌──────────┐   ┌────────────┐   ┌────────┐  │
│  │Clients │   │  Pets  │   │ Bookings │   │Preferences │   │ Staff  │  │
│  └────────┘   └────────┘   └──────────┘   └────────────┘   └────────┘  │
│       │            │              │               │              │       │
└───────┼────────────┼──────────────┼───────────────┼──────────────┼───────┘
        │            │              │               │              │
        ▼            ▼              ▼               ▼              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     WELLNESS OUTREACH SCRIPT                            │
│                                                                         │
│  ┌──────────────────────┐    ┌──────────────────────┐                 │
│  │  get_target_pets()   │    │  find_open_slots()   │                 │
│  └──────────────────────┘    └──────────────────────┘                 │
│              │                            │                            │
│              └────────────┬───────────────┘                            │
│                           ▼                                            │
│            ┌──────────────────────────────┐                            │
│            │ match_slot_to_preference()   │                            │
│            └──────────────────────────────┘                            │
│                           │                                            │
│                           ▼                                            │
└───────────────────────────┼────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       AI SERVICES                                       │
│                                                                         │
│  ┌──────────────────────┐    ┌─────────────────────────────────────┐  │
│  │   get_embedding()    │    │ get_ollama_recommendation()         │  │
│  │  (sentence-trans.)   │    │        (Ollama/llama3)              │  │
│  └──────────────────────┘    └─────────────────────────────────────┘  │
│            │                                │                          │
└────────────┼────────────────────────────────┼──────────────────────────┘
             │                                │
             ▼                                ▼
    Preference Vector              Personalized Email
       Matching                        Generation
             │                                │
             └────────────┬───────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          OUTPUT                                         │
│                                                                         │
│  ┌──────────────┐              ┌──────────────────┐                    │
│  │   Console    │              │  outreach_log.txt│                    │
│  │   (stdout)   │              │    (append)      │                    │
│  └──────────────┘              └──────────────────┘                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Dependencies

```
wellness_outreach.py
  │
  ├─► database.py (SessionLocal)
  │     │
  │     └─► SQLAlchemy engine
  │           │
  │           └─► PostgreSQL
  │
  ├─► models.py (Client, Pet, Booking, Preferences, Staff)
  │     │
  │     └─► SQLAlchemy models
  │
  ├─► ai_services.py
  │     │
  │     ├─► get_embedding()
  │     │     │
  │     │     └─► sentence-transformers (all-MiniLM-L6-v2)
  │     │
  │     └─► get_ollama_recommendation()
  │           │
  │           └─► Ollama (llama3 model)
  │
  └─► booking_logic.py (check_availability)
        │
        └─► Availability checking logic
```

## Error Handling Flow

```
┌───────────────────────────────────────────────────────────────┐
│                   process_outreach()                          │
└───────────────────────────────────────────────────────────────┘
                            │
                            ▼
                    For each (Pet, Client)
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
    Try Block          Try Block           Try Block
        │                   │                   │
   ┌────┴────┐         ┌────┴────┐       ┌─────┴─────┐
   │ Success │         │  Error  │       │  Success  │
   └────┬────┘         └────┬────┘       └─────┬─────┘
        │                   │                   │
        ▼                   ▼                   ▼
   Append to            Append to          Append to
    "emails"            "errors"            "emails"
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                            ▼
                  Return Complete Summary
                    (all emails + all errors)
```

Key Points:

- **Per-pet error isolation**: One failure doesn't stop the batch
- **Graceful degradation**: LLM failure → fallback template
- **Comprehensive logging**: All errors tracked in summary
- **Database safety**: Session cleanup in finally block

---

**Legend:**

- `│ ▼ ─ └ ┌ ┐ ┘ ├ ┤ ┬ ┴ ┼` - Flow connectors
- `┌─────┐` - Process/Component box
- `◄ ►` - Data flow direction
- `→` - Simple arrow
