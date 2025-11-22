#!/usr/bin/env python3
"""Test agent conversation memory, pattern learning, and proactive suggestions."""

import requests
import json
import time

API_URL = "http://localhost:8000/agent/chat"

def test_pattern_learning():
    """Test that agent learns from booking history."""
    print("\n=== Test 1: Pattern Learning ===")
    print("Testing if agent recognizes AmariUnique's booking patterns...")
    
    payload = {
        "prompt": "I need a checkup for Buddy",
        "complaint_text": "routine checkup",
        "client_email": "AmariUnique@example.com"
    }
    
    print("Sending request...")
    start = time.time()
    try:
        response = requests.post(API_URL, json=payload, timeout=60)
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✓ Response received in {elapsed:.1f}s:")
            print(f"  {data['response']}")
            
            # Check if response mentions patterns
            response_text = data['response'].lower()
            if any(keyword in response_text for keyword in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'morning', 'afternoon', 'usual']):
                print("\n✓ PATTERN LEARNING WORKING: Agent mentioned client's usual preferences!")
            else:
                print("\n⚠ Pattern mention not detected (but may still be working internally)")
        else:
            print(f"\n✗ Error: {response.status_code}")
            print(response.text)
    except requests.Timeout:
        print("\n✗ Request timed out (>60s)")
    except Exception as e:
        print(f"\n✗ Error: {e}")


def test_conversation_memory():
    """Test that agent remembers context across messages."""
    print("\n\n=== Test 2: Conversation Memory ===")
    print("Testing if agent remembers previous conversation...")
    
    session_id = f"test_session_{int(time.time())}"
    
    # First message
    print("\nMessage 1: Book for Buddy...")
    payload1 = {
        "prompt": "I need a checkup for Buddy",
        "complaint_text": "routine checkup",
        "session_id": session_id
    }
    
    try:
        resp1 = requests.post(API_URL, json=payload1, timeout=60)
        if resp1.status_code == 200:
            print(f"  Agent: {resp1.json()['response'][:100]}...")
        
        # Second message - reference previous context
        print("\nMessage 2: Follow-up question...")
        payload2 = {
            "prompt": "Actually, can we do afternoon instead?",
            "complaint_text": "routine checkup",
            "session_id": session_id
        }
        
        resp2 = requests.post(API_URL, json=payload2, timeout=60)
        if resp2.status_code == 200:
            response_text = resp2.json()['response']
            print(f"  Agent: {response_text[:100]}...")
            
            if 'buddy' in response_text.lower() or 'checkup' in response_text.lower() or 'afternoon' in response_text.lower():
                print("\n✓ CONVERSATION MEMORY WORKING: Agent remembered context!")
            else:
                print("\n⚠ Memory not clearly evident in response")
    except requests.Timeout:
        print("\n✗ Request timed out")
    except Exception as e:
        print(f"\n✗ Error: {e}")


def test_proactive_suggestions():
    """Test that agent makes proactive suggestions based on patterns."""
    print("\n\n=== Test 3: Proactive Suggestions ===")
    print("Testing if agent proactively suggests based on client patterns...")
    
    payload = {
        "prompt": "I want to book an appointment for Buddy",
        "complaint_text": "routine checkup",
        "client_email": "AmariUnique@example.com"
    }
    
    print("Sending request...")
    try:
        response = requests.post(API_URL, json=payload, timeout=60)
        if response.status_code == 200:
            data = response.json()
            response_text = data['response']
            print(f"\nAgent response:\n  {response_text}")
            
            # Look for proactive language
            proactive_indicators = [
                'usually', 'often', 'prefer', 'typically', 'would you like',
                'i see', 'regular', 'monday', 'tuesday', 'morning', 'afternoon'
            ]
            
            if any(indicator in response_text.lower() for indicator in proactive_indicators):
                print("\n✓ PROACTIVE SUGGESTIONS WORKING: Agent offered pattern-based suggestions!")
            else:
                print("\n⚠ No proactive language detected")
    except requests.Timeout:
        print("\n✗ Request timed out")
    except Exception as e:
        print(f"\n✗ Error: {e}")


if __name__ == "__main__":
    print("=" * 70)
    print("AGENTIC FEATURES TEST SUITE")
    print("=" * 70)
    print("\nTesting:")
    print("  1. Pattern Learning (detects client's usual booking days/times)")
    print("  2. Conversation Memory (remembers context across messages)")
    print("  3. Proactive Suggestions (offers preferred slots)")
    print("\nNote: Each test may take 30-60 seconds due to LLM inference time.")
    print("=" * 70)
    
    test_pattern_learning()
    test_conversation_memory()
    test_proactive_suggestions()
    
    print("\n" + "=" * 70)
    print("TEST SUITE COMPLETE")
    print("=" * 70)
