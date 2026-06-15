#!/usr/bin/env python3
"""
Test script for SSE (Server-Sent Events) streaming endpoint.
Tests the new /ask/stream endpoint that streams AI suggestions in real-time.

Usage:
  1. Start Ollama: ollama serve
  2. Start backend: python3 backend.py
  3. Run this test: python3 test_streaming.py
"""

import requests
import json
import time
from typing import Optional

BASE_URL = "http://localhost:5005"
OLLAMA_URL = "http://localhost:11434"


def check_ollama() -> bool:
    """Verify Ollama is running."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        return resp.status_code == 200
    except Exception:
        return False


def check_backend() -> bool:
    """Verify Flask backend is running."""
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=2)
        return resp.status_code == 200
    except Exception:
        return False


def test_streaming_endpoint():
    """Test the /ask/stream endpoint with SSE."""
    print("\n" + "="*70)
    print("TEST: /ask/stream Endpoint (Server-Sent Events Streaming)")
    print("="*70)

    # Sample candidate profile
    profile = {
        "name": "Test Candidate",
        "target_roles": ["Software Engineer", "Backend Developer"],
        "skills": {"languages": ["Python", "Swift"], "tools": ["Git", "Docker"]},
        "projects": [
            {"name": "Interview Assistant", "description": "AI-powered interview prep"}
        ],
        "experience": "3 years in software development",
        "background": "Computer Science graduate",
        "japanese_level": "N2",
    }

    # Sample question
    question = "Tell me about your most impactful project"

    # Request body
    body = {
        "question": question,
        "profile": profile,
        "lang": "en",
    }

    print(f"\nQuestion: {question}")
    print(f"Profile: {profile['name']} - {', '.join(profile['target_roles'])}")
    print(f"\nStreaming response from /ask/stream:")
    print("-" * 70)

    try:
        # Make streaming request
        resp = requests.post(
            f"{BASE_URL}/ask/stream",
            json=body,
            stream=True,
            timeout=60,
        )

        if resp.status_code != 200:
            print(f"❌ HTTP {resp.status_code}")
            print(resp.text)
            return False

        full_response = ""
        source = None
        token_count = 0

        # Parse SSE messages
        for line in resp.iter_lines():
            if not line:
                continue

            line_str = line.decode("utf-8") if isinstance(line, bytes) else line

            # Check for SSE data format
            if line_str.startswith("data: "):
                data_str = line_str[6:]  # Remove "data: " prefix

                if data_str == "[DONE]":
                    print("\n" + "-" * 70)
                    print("\n✅ Stream completed successfully!\n")
                    break

                # Parse JSON
                try:
                    data = json.loads(data_str)

                    # Handle source
                    if "source" in data:
                        source = data["source"]
                        print(f"[Source: {source}]", end=" ", flush=True)

                    # Handle tokens
                    if "token" in data:
                        token = data["token"]
                        full_response += token
                        print(token, end="", flush=True)
                        token_count += 1

                    # Handle errors
                    if "error" in data:
                        error = data["error"]
                        print(f"\n❌ Error: {error}")
                        return False

                except json.JSONDecodeError as e:
                    print(f"\n⚠️  Could not parse JSON: {e}")
                    continue

        # Summary
        print(f"\n📊 Statistics:")
        print(f"   - Tokens received: {token_count}")
        print(f"   - Total length: {len(full_response)} characters")
        print(f"   - Source: {source}")
        return True

    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to backend at {BASE_URL}")
        print("   Make sure backend is running: python3 backend.py")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ Request timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_regular_endpoint():
    """Test the regular /ask endpoint for comparison."""
    print("\n" + "="*70)
    print("TEST: /ask Endpoint (Regular, non-streaming)")
    print("="*70)

    profile = {
        "name": "Test Candidate",
        "target_roles": ["Software Engineer"],
        "skills": {"languages": ["Python", "Swift"]},
        "projects": [],
        "experience": "3 years",
        "background": "CS graduate",
        "japanese_level": "N2",
    }

    question = "What's your weakness?"

    body = {
        "question": question,
        "profile": profile,
        "lang": "en",
    }

    print(f"\nQuestion: {question}")

    try:
        start = time.time()
        resp = requests.post(f"{BASE_URL}/ask", json=body, timeout=30)
        elapsed = time.time() - start

        if resp.status_code == 200:
            data = resp.json()
            suggestion = data.get("suggestion", "")
            source = data.get("source", "unknown")
            print(f"\nResponse (from {source}):")
            print("-" * 70)
            print(suggestion)
            print("-" * 70)
            print(f"\n✅ Completed in {elapsed:.2f}s")
            return True
        else:
            print(f"❌ HTTP {resp.status_code}")
            print(resp.json())
            return False

    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to backend at {BASE_URL}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print("\n" + "="*70)
    print("STREAMING IMPLEMENTATION TEST")
    print("="*70)

    # Check prerequisites
    print("\n📋 Checking prerequisites...")

    if not check_ollama():
        print("❌ Ollama not running on localhost:11434")
        print("   Start with: ollama serve")
        return

    print("✅ Ollama is running")

    if not check_backend():
        print("❌ Flask backend not running on localhost:5005")
        print("   Start with: python3 backend.py")
        return

    print("✅ Flask backend is running")

    # Run tests
    print("\n🧪 Running tests...\n")

    # Test streaming endpoint
    streaming_ok = test_streaming_endpoint()

    # Test regular endpoint
    regular_ok = test_regular_endpoint()

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Streaming endpoint (/ask/stream): {'✅ PASS' if streaming_ok else '❌ FAIL'}")
    print(f"Regular endpoint (/ask):          {'✅ PASS' if regular_ok else '❌ FAIL'}")
    print("="*70)

    if streaming_ok and regular_ok:
        print("\n🎉 All tests passed! Streaming implementation is working correctly.")
        print("\nNext steps:")
        print("1. Build and run the iOS app")
        print("2. Connect to the backend")
        print("3. Ask a question and watch the suggestion stream in real-time!")
    else:
        print("\n⚠️  Some tests failed. Please check the output above.")


if __name__ == "__main__":
    main()
