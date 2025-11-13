# Sprint 8: Dynamic Slot-Filling - Quick Reference

## 🎯 What Is This?

When an admin cancels a booking, the system automatically suggests clients who:
- Have appointments **later the same day**
- Have stated preferences for **earlier appointment times**
- Could benefit from moving to the newly-available slot

## 🚀 Quick Start

### For Admins (Using the UI)

1. Go to Admin Dashboard
2. Find a booking and change status to "cancelled"
3. **Automatic**: A blue banner appears showing suggested clients
4. Click "Contact" or use the email to reach out
5. Reschedule the client's later booking to the cancelled slot
6. Click **X** to dismiss the banner when done

### For Developers (Using the API)

```bash
# Get suggestions for a cancelled booking
curl -X GET "http://localhost:8000/admin/cancellation_suggestion/123" \
  -H "Authorization: Bearer <admin_token>"
```

**Response:**
```json
{
  "cancelled_slot_time": "2025-11-14T09:00:00",
  "suggestions": [
    {
      "client_name": "Jane Doe",
      "client_email": "jane@example.com",
      "current_booking_id": 456,
      "current_booking_time": "2025-11-14T14:00:00",
      "match_score": 0.543,
      "reason": "Prefers morning appointments (currently at 02:00 PM)"
    }
  ]
}
```

## 📋 API Reference

### Endpoint

```
GET /admin/cancellation_suggestion/{booking_id}
```

**Authentication**: Admin JWT token required

**Path Parameters:**
- `booking_id` (int): ID of the cancelled booking

**Returns:**
- `CancellationSuggestionResponse` object

**Status Codes:**
- `200 OK`: Suggestions generated successfully
- `404 Not Found`: Booking doesn't exist
- `400 Bad Request`: Booking is not cancelled
- `401 Unauthorized`: Not authenticated as admin

### Schemas

#### CancellationSuggestion
```python
{
  "client_name": str,
  "client_email": str,
  "current_booking_id": int,
  "current_booking_time": datetime,
  "match_score": float,  # 0.0 to 1.0
  "reason": str
}
```

#### CancellationSuggestionResponse
```python
{
  "cancelled_slot_time": datetime,
  "suggestions": List[CancellationSuggestion]  # Max 3 items
}
```

## 🧠 How It Works (Simple Explanation)

1. **When**: Admin cancels a booking at 9:00 AM
2. **Find**: All bookings later that day (e.g., 2:00 PM, 4:00 PM)
3. **Match**: Check which clients' preferences say "I prefer earlier times"
4. **Score**: Calculate how well each client's preference matches (0-100%)
5. **Suggest**: Show top 3 matches to the admin

## 🎨 Frontend Integration

### Dashboard State
```javascript
const [cancellationSuggestions, setCancellationSuggestions] = useState(null);
```

### API Call (in AdminBookingList.js)
```javascript
if (newStatus === 'cancelled') {
  const response = await fetch(`/api/admin/cancellation_suggestion/${bookingId}`);
  if (response.ok) {
    const suggestions = await response.json();
    if (suggestions.suggestions.length > 0) {
      setCancellationSuggestions(suggestions);
    }
  }
}
```

### Display Banner (in dashboard page.js)
```javascript
{cancellationSuggestions && cancellationSuggestions.suggestions.length > 0 && (
  <Card className="mb-6 border-l-4 border-l-blue-500 bg-blue-50">
    {/* Suggestion UI */}
  </Card>
)}
```

## 🔍 Example Scenarios

### Scenario 1: Morning Cancellation
**Cancelled**: 9:00 AM appointment  
**Later Bookings**: 2:00 PM, 4:00 PM, 6:00 PM  
**Client Preferences**:
- Jane: "I prefer morning appointments" → **Match: 54%** ✅
- Bob: "Evenings work better for me" → Not suggested ❌
- Alice: "Earlier in the day is ideal" → **Match: 43%** ✅

**Result**: Suggests Jane (54%) and Alice (43%)

### Scenario 2: Afternoon Cancellation
**Cancelled**: 2:00 PM appointment  
**Later Bookings**: 4:00 PM, 6:00 PM  
**Client Preferences**:
- Mike: "I like to come in early" → **Match: 38%** ✅
- Sarah: "No time preference" → Not suggested ❌

**Result**: Suggests Mike (38%)

### Scenario 3: Last Appointment Cancelled
**Cancelled**: 6:00 PM appointment  
**Later Bookings**: None  

**Result**: Empty suggestions (no one to move up)

## 📊 Match Score Interpretation

| Score Range | Meaning | Action |
|-------------|---------|--------|
| **60-100%** | Strong match | Highly recommend contacting |
| **40-59%** | Good match | Worth reaching out |
| **20-39%** | Moderate match | Consider if time aligns well |
| **0-19%** | Weak match | Probably not relevant |

## 🧪 Testing

### Run Integration Test
```bash
docker-compose exec backend python -m app.test_sprint8_cancellation
```

### Expected Output
```
🎉 SPRINT 8 TEST PASSED!
✅ Suggestions correctly sorted by match score
✅ All suggestions are for later times on same day
```

### Manual Testing
1. Create a client with preference: "I prefer morning appointments"
2. Book them at 2:00 PM tomorrow
3. Create another booking at 9:00 AM tomorrow
4. Cancel the 9:00 AM booking
5. Check dashboard for suggestion banner

## 🛠️ Common Issues

### Issue: No Suggestions Appear
**Check:**
- ✓ Is the cancelled booking on a future date?
- ✓ Are there other bookings later the same day?
- ✓ Do those clients have preferences saved?
- ✓ Are the preferences related to time/scheduling?

### Issue: Match Scores Are Low
**Reason:** Client preferences don't mention time/timing  
**Solution:** Encourage clients to specify time preferences when creating accounts

### Issue: API Returns 404
**Check:**
- ✓ Does the booking_id exist?
- ✓ Is the booking status set to 'cancelled'?
- ✓ Are you using an admin token (not client token)?

## 📁 File Locations

**Backend:**
- Schemas: `backend/app/schemas.py`
- Endpoint: `backend/app/main.py` (search for `/admin/cancellation_suggestion`)
- Tests: `backend/app/test_sprint8_cancellation.py`

**Frontend:**
- Dashboard: `frontend/src/app/admin/dashboard/page.js`
- Booking List: `frontend/src/components/AdminBookingList.js`

## 🔐 Security

- ✅ **Admin-only**: Uses `get_current_admin_user` dependency
- ✅ **No PII leakage**: Only returns necessary client info
- ✅ **Rate limiting**: Standard FastAPI rate limits apply
- ✅ **Input validation**: Booking ID validated before processing

## 🎓 Tips & Best Practices

### For Admins
1. **Act Quickly**: Contact suggested clients right away for best response
2. **Explain Benefits**: Mention it's an earlier time that aligns with their preference
3. **Be Flexible**: If first suggestion declines, try the next one
4. **Track Success**: Note which clients accept to improve future outreach

### For Developers
1. **Monitor Performance**: Watch query times for large booking sets
2. **Tune Match Threshold**: Adjust minimum score if too many/few suggestions
3. **Add Logging**: Track suggestion acceptance rates for analytics
4. **Consider Caching**: Cache embeddings for "earlier appointment" text

## 📈 Success Metrics

Track these to measure Sprint 8 impact:
- **Fill Rate**: % of cancelled slots filled via suggestions
- **Response Time**: How quickly admins contact suggested clients
- **Acceptance Rate**: % of suggestions that lead to reschedules
- **Client Satisfaction**: Feedback from clients who get better times

## 🔗 Related Features

- **Sprint 7 (Wellness Outreach)**: Proactive client engagement
- **Admin Calendar**: Visual booking management
- **Client Preferences**: Foundation for matching algorithm
- **Booking Management**: Core scheduling functionality

## 📞 Support

For questions or issues:
1. Check the main implementation summary: `SPRINT8_DYNAMIC_SLOT_FILLING_SUMMARY.md`
2. Review test file: `backend/app/test_sprint8_cancellation.py`
3. Check copilot instructions: `.github/copilot-instructions.md`

---

**Version**: 1.0  
**Status**: ✅ Production Ready  
**Last Updated**: November 13, 2025
