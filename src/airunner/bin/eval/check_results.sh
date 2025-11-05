#!/bin/bash
# Quick results checker

LOG_FILE="/tmp/math_test_results.log"

if [ ! -f "$LOG_FILE" ]; then
    echo "No results log found at $LOG_FILE"
    exit 1
fi

echo "=== MATH LEVEL 5 TEST RESULTS ==="
echo ""

# Extract the results summary
grep -A 10 "📊 RESULTS" "$LOG_FILE" | head -15

echo ""
echo "=== INDIVIDUAL PROBLEM RESULTS ==="
grep -E "^(✅|❌)" "$LOG_FILE" | nl

echo ""
echo "=== TIMING INFO ==="
grep "Time:" "$LOG_FILE" | awk '{sum+=$NF} END {print "Total problems:", NR, "| Average time:", sum/NR"s"}'
