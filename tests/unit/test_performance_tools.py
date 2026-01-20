"""
Unit Tests for Agent B (Performance & Architecture) Tools.

These tests verify the robust AST analysis capabilities:
1. Structure Analysis (God Classes, Coupling)
2. Loop Mechanics (N+1 Detection)
3. Async Safety (Blocking Calls)
4. Resource Usage (Memory Leaks)
"""

import unittest
import logging
import sys
from src.agents.performance.tools import (
    analyze_code_structure,
    inspect_loop_mechanics,
    map_async_execution,
    trace_data_flow
)

# --- Logging Configuration ---
# This ensures logs appear in your console when running tests
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("TestPerformance")

class TestPerformanceTools(unittest.TestCase):

    def setUp(self):
        # Print a separator before each test for readability
        print("-" * 60)

    # --- Tool 1: Code Structure (The Blueprint) ---

    def test_analyze_structure_god_class(self):
        """Test detection of a 'God Class' with too many methods."""
        logger.info("TEST: analyze_structure_god_class | Checking for Monolithic Class detection...")
        code = """
class GodObject:
    def __init__(self):
        self.a = 1
        self.b = 2
        self.c = 3
    
    def method_1(self): pass
    def method_2(self): pass
    def method_3(self): pass
    async def method_4(self): pass
"""
        result = analyze_code_structure(code)
        
        found_class = result["classes"][0]
        logger.info(f"Input: Class 'GodObject' with 5 methods, 3 attributes.")
        logger.info(f"Output: Detected '{found_class['name']}' | Methods: {found_class['method_count']} | Attributes: {found_class['attribute_count']}")

        self.assertEqual(len(result["classes"]), 1)
        self.assertEqual(found_class["name"], "GodObject")
        # Expect 5 methods: __init__ + method_1 + method_2 + method_3 + method_4
        self.assertEqual(found_class["method_count"], 5)
        self.assertEqual(found_class["attribute_count"], 3)

    def test_analyze_structure_coupling(self):
        """Test detection of tight coupling (external calls)."""
        logger.info("TEST: analyze_structure_coupling | Checking for Tight Coupling...")
        code = """
def process_payment(order):
    db.save(order)
    stripe.charge(order)
    email.send_confirmation(order)
    logger.info("Done")
"""
        result = analyze_code_structure(code)
        
        func = result["functions"][0]
        detected_calls = set(func["external_calls"])
        expected_calls = {"db.save", "stripe.charge", "email.send_confirmation", "logger.info"}
        
        logger.info(f"Input: Function calling {expected_calls}")
        logger.info(f"Output: Tool detected {detected_calls}")
        
        self.assertEqual(func["name"], "process_payment")
        self.assertTrue(expected_calls.issubset(detected_calls))


    # --- Tool 2: Loop Mechanics (N+1 Vision) ---

    def test_inspect_loop_n_plus_one(self):
        """Test detection of DB calls inside loops."""
        logger.info("TEST: inspect_loop_n_plus_one | Checking for N+1 Query patterns...")
        code = """
def get_users(ids):
    for uid in ids:
        user = User.objects.get(id=uid)
        print(user)
"""
        result = inspect_loop_mechanics(code)
        
        loop = result["risky_loops"][0]
        ops = loop["operations_inside"]
        
        logger.info(f"Input: Loop iterating over '{loop['loop_variable']}' calling 'User.objects.get'")
        logger.info(f"Output: Detected {len(ops)} operations inside loop.")
        logger.info(f"Details: {ops}")

        self.assertEqual(result["loops_analyzed"], 1)
        self.assertEqual(loop["loop_variable"], "uid")
        
        # This will now pass due to recursive attribute parsing
        self.assertTrue(any(op["call"] == "User.objects.get" for op in ops))
        self.assertTrue(any(op["type"] == "Potential IO/DB" for op in ops))

    def test_inspect_nested_loops(self):
        """Test that it correctly maps nested loop structures."""
        logger.info("TEST: inspect_nested_loops | Checking nested loop analysis...")
        code = """
for i in range(10):
    for j in range(5):
        api.fetch(j)
"""
        result = inspect_loop_mechanics(code)
        logger.info(f"Output: Analyzed {result['loops_analyzed']} loops (Expect 2).")
        
        self.assertEqual(result["loops_analyzed"], 2)


    # --- Tool 3: Async Map (Concurrency) ---

    def test_async_blocking_sleep(self):
        """Test detection of time.sleep inside async def."""
        logger.info("TEST: async_blocking_sleep | Checking for blocking 'time.sleep'...")
        code = """
import time

async def fetch_data():
    print("Start")
    time.sleep(5)
    return "Done"
"""
        result = map_async_execution(code)
        
        violations = result["violations"]
        logger.info(f"Output: Found {len(violations)} violations.")
        if violations:
            v = violations[0]
            logger.info(f"Violation: {v['blocking_call']} in {v['function']} (Line {v['line']})")

        self.assertTrue(len(violations) > 0)
        self.assertEqual(violations[0]["function"], "fetch_data")
        self.assertEqual(violations[0]["blocking_call"], "time.sleep")
        self.assertIn("await asyncio.sleep", violations[0]["suggestion"])

    def test_async_safe_code(self):
        """Test that correct async code triggers no violations."""
        logger.info("TEST: async_safe_code | Verifying safe code passes...")
        code = """
import asyncio
async def safe_fetch():
    await asyncio.sleep(1)
"""
        result = map_async_execution(code)
        logger.info(f"Output: Found {len(result['violations'])} violations (Expect 0).")
        self.assertEqual(len(result["violations"]), 0)


    # --- Tool 4: Resource Trace (Memory/CPU) ---

    def test_trace_unbounded_read(self):
        """Test detection of .read() without arguments."""
        logger.info("TEST: trace_unbounded_read | Checking for dangerous file reads...")
        code = """
def read_file(path):
    with open(path) as f:
        content = f.read()
"""
        result = trace_data_flow(code)
        
        hotspots = result["resource_hotspots"]
        logger.info(f"Output: Found {len(hotspots)} hotspots.")
        if hotspots:
            logger.info(f"Hotspot: {hotspots[0]['type']} -> {hotspots[0]['description']}")

        self.assertTrue(len(hotspots) > 0)
        self.assertEqual(hotspots[0]["type"], "Unbounded Read")
        self.assertIn(".read()", hotspots[0]["pattern"])

    def test_trace_infinite_loop(self):
        """Test detection of while True without break."""
        logger.info("TEST: trace_infinite_loop | Checking for infinite loops...")
        code = """
def run_forever():
    while True:
        print("Still running...")
"""
        result = trace_data_flow(code)
        hotspots = result["resource_hotspots"]
        
        logger.info(f"Output: Found {len(hotspots)} hotspots.")
        if hotspots:
             logger.info(f"Hotspot: {hotspots[0]['type']}")

        self.assertTrue(len(hotspots) > 0)
        self.assertEqual(hotspots[0]["type"], "Infinite Loop Risk")

    def test_trace_safe_loop(self):
        """Test that while True WITH break is ignored."""
        logger.info("TEST: trace_safe_loop | Verifying safe loops are ignored...")
        code = """
def run_worker():
    while True:
        msg = get_message()
        if not msg:
            break
"""
        result = trace_data_flow(code)
        logger.info(f"Output: Found {len(result['resource_hotspots'])} hotspots (Expect 0).")
        self.assertEqual(len(result["resource_hotspots"]), 0)

    # --- Robustness ---

    def test_syntax_error_handling(self):
        """Ensure tools don't crash on bad syntax."""
        logger.info("TEST: syntax_error_handling | Checking crash resistance...")
        bad_code = "def broken_func(:"
        
        res1 = analyze_code_structure(bad_code)
        res2 = inspect_loop_mechanics(bad_code)
        
        logger.info("Output: Handled SyntaxError gracefully without crashing.")
        self.assertEqual(res1["summary"]["total_functions"], 0)
        self.assertEqual(res2["loops_analyzed"], 0)

if __name__ == "__main__":
    unittest.main()