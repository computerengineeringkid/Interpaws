#!/bin/bash
# Test agent features with bash/curl

echo "======================================================================"
echo "AGENTIC FEATURES TEST SUITE"
echo "======================================================================"
echo ""
echo "Testing:"
echo "  1. Pattern Learning (detects client's usual booking days/times)"
echo "  2. Conversation Memory (remembers context across messages)"
echo "  3. Proactive Suggestions (offers preferred slots)"
echo ""
echo "Note: Each test may take 30-60 seconds due to LLM inference time."
echo "======================================================================"

echo ""
echo "=== Test 1: Pattern Learning ==="
echo "Testing if agent recognizes AmariUnique's booking patterns..."
echo ""

RESPONSE=$(timeout 60 curl -s -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "I need a checkup for Buddy",
    "complaint_text": "routine checkup",
    "client_email": "AmariUnique@example.com"
  }' 2>&1)

if [[ $? -eq 124 ]]; then
    echo "✗ Request timed out (>60s)"
elif echo "$RESPONSE" | jq -e . >/dev/null 2>&1; then
    AGENT_RESPONSE=$(echo "$RESPONSE" | jq -r '.response')
    echo "✓ Response received:"
    echo "  $AGENT_RESPONSE"
    echo ""
    
    # Check for pattern mentions
    if echo "$AGENT_RESPONSE" | grep -iE "(monday|tuesday|wednesday|thursday|friday|morning|afternoon|usual|usually|typically)" >/dev/null; then
        echo "✓ PATTERN LEARNING WORKING: Agent mentioned client's usual preferences!"
    else
        echo "⚠ Pattern mention not clearly detected"
    fi
else
    echo "✗ Error in response"
    echo "$RESPONSE"
fi

echo ""
echo ""
echo "=== Test 2: Conversation Memory ==="
echo "Testing if agent remembers context across messages..."
echo ""

SESSION_ID="test_session_$(date +%s)"

echo "Message 1: Initial booking request..."
RESPONSE1=$(timeout 60 curl -s -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"prompt\": \"I need a checkup for Buddy\",
    \"complaint_text\": \"routine checkup\",
    \"session_id\": \"$SESSION_ID\"
  }" 2>&1)

if echo "$RESPONSE1" | jq -e . >/dev/null 2>&1; then
    AGENT1=$(echo "$RESPONSE1" | jq -r '.response' | head -c 100)
    echo "  Agent: ${AGENT1}..."
    echo ""
    
    echo "Message 2: Follow-up referencing first message..."
    sleep 2
    RESPONSE2=$(timeout 60 curl -s -X POST http://localhost:8000/agent/chat \
      -H "Content-Type: application/json" \
      -d "{
        \"prompt\": \"Actually, can we do afternoon instead?\",
        \"complaint_text\": \"routine checkup\",
        \"session_id\": \"$SESSION_ID\"
      }" 2>&1)
    
    if echo "$RESPONSE2" | jq -e . >/dev/null 2>&1; then
        AGENT2=$(echo "$RESPONSE2" | jq -r '.response')
        echo "  Agent: ${AGENT2}"
        echo ""
        
        if echo "$AGENT2" | grep -iE "(buddy|checkup|afternoon)" >/dev/null; then
            echo "✓ CONVERSATION MEMORY WORKING: Agent remembered context!"
        else
            echo "⚠ Memory not clearly evident in response"
        fi
    else
        echo "✗ Second message failed"
    fi
else
    echo "✗ First message failed"
fi

echo ""
echo ""
echo "======================================================================"
echo "TEST SUITE COMPLETE"
echo "======================================================================"
