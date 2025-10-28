#!/bin/bash
# Quick test script for eval framework with real LLM
# Run this after loading an LLM model in AI Runner

set -e

echo "🚀 AI Runner Eval Testing Quick Start"
echo "======================================"
echo ""

# Check if server is running
echo "📡 Checking if headless server is running..."
if curl -s http://localhost:8188/health > /dev/null 2>&1; then
    echo "✅ Server is running"
else
    echo "❌ Server not running. Starting headless server..."
    echo "   Run in another terminal: airunner-headless"
    exit 1
fi

# Test health
echo ""
echo "🏥 Testing /health endpoint..."
curl -s http://localhost:8188/health | python -m json.tool

# Test models
echo ""
echo "📋 Testing /llm/models endpoint..."
curl -s http://localhost:8188/llm/models | python -m json.tool

# Run simple eval test
echo ""
echo "🧪 Running simple eval test (health check)..."
pytest src/airunner/components/eval/tests/test_eval_examples.py::test_client_health_check -v

# Run one math test
echo ""
echo "🔢 Running one math eval test with LLM-as-judge..."
echo "   (This requires an LLM model to be loaded)"
pytest src/airunner/components/eval/tests/test_real_eval.py::TestMathReasoning::test_simple_addition -v -s

echo ""
echo "✅ Quick test complete!"
echo ""
echo "To run all eval tests:"
echo "  pytest -v -m llm_required"
echo ""
echo "To run specific category:"
echo "  pytest -v -k TestMathReasoning"
echo "  pytest -v -k TestGeneralKnowledge"
echo "  pytest -v -k TestCoding"
