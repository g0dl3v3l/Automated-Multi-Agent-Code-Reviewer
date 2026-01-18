"""
Unit Tests for Security Tools.
Verifies the deterministic logic of CVE lookup, Secret Scanning, AST Analysis, and Route Auditing.
"""
import unittest
from unittest.mock import patch, MagicMock
from src.agents.security.tools import (
    cve_lookup,
    scan_secrets,
    analyze_ast_patterns,
    audit_route_permissions
)

class TestSecurityTools(unittest.TestCase):

    # --- TEST 1: CVE LOOKUP (Mocked) ---
    @patch('src.agents.security.tools.requests.post')
    def test_cve_lookup_vulnerable(self, mock_post):
        """Test that the tool correctly identifies a vulnerable package."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "vulns": [
                        {
                            "id": "CVE-TEST-001",
                            "summary": "Critical Flaw in Lodash"
                        }
                    ]
                }
            ]
        }
        mock_post.return_value = mock_response

        result = cve_lookup("lodash==4.17.15", ecosystem="npm")

        self.assertEqual(result['status'], "VULNERABLE")
        self.assertEqual(result['packages'][0]['name'], "lodash")
        self.assertEqual(result['packages'][0]['cves'][0]['id'], "CVE-TEST-001")

    @patch('src.agents.security.tools.requests.post')
    def test_cve_lookup_safe(self, mock_post):
        """Test that the tool returns SAFE when no vulns are found."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{}]} 
        mock_post.return_value = mock_response

        result = cve_lookup("requests==2.31.0")
        self.assertEqual(result['status'], "SAFE")

    # --- TEST 2: SECRET SCANNING ---
    def test_scan_secrets_regex(self):
        """Test detection of AWS keys via Regex."""
        unsafe_code = "aws_key = 'AKIAIOSFODNN7EXAMPLE'" 
        result = scan_secrets(unsafe_code)
        
        self.assertTrue(result['found_secrets'])
        self.assertEqual(result['matches'][0]['type'], "AWS_Access_Key")

    def test_scan_secrets_entropy(self):
        """Test detection of high-entropy strings using a REALISTIC example."""
        # FIX: This is a fake AWS Secret Key (40 chars, Base64).
        # It is exactly what a real secret looks like. 
        # Entropy Calculation: 40 chars, random distribution = ~5.2 entropy score.
        # Threshold: 4.5
        real_looking_secret = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        unsafe_code = f"aws_secret = '{real_looking_secret}'"
        
        result = scan_secrets(unsafe_code)
        
        if not result['found_secrets']:
            print(f"\nDEBUG: Failed on realistic key: {real_looking_secret}")

        self.assertTrue(result['found_secrets'])
        self.assertEqual(result['matches'][0]['method'], "HIGH_ENTROPY")
    def test_scan_secrets_safe(self):
        """Test that normal code doesn't trigger false positives."""
        safe_code = "print('Hello World')"
        result = scan_secrets(safe_code)
        self.assertFalse(result['found_secrets'])

    # --- TEST 3: AST / SAST ANALYSIS ---
    def test_ast_command_injection(self):
        """Test detection of subprocess.call with variables."""
        unsafe_code = """
import subprocess
user_input = input()
subprocess.call(user_input) # Dangerous Sink
"""
        result = analyze_ast_patterns(unsafe_code)
        self.assertTrue(result['risk_found'])
        self.assertEqual(result['patterns'][0]['risk'], "Command_Injection")

    def test_ast_safe_call(self):
        """Test that literal arguments are considered safe."""
        safe_code = "subprocess.call('ls -l')" 
        result = analyze_ast_patterns(safe_code)
        self.assertFalse(result['risk_found'])

    def test_ast_eval(self):
        """Test detection of eval()."""
        unsafe_code = "eval('2 + 2')"
        result = analyze_ast_patterns(unsafe_code)
        self.assertTrue(result['risk_found'])
        self.assertEqual(result['patterns'][0]['function'], "eval")

    # --- TEST 4: ROUTE AUDITING ---
    def test_audit_routes_missing_auth(self):
        """Test detection of unauthenticated routes."""
        unsafe_code = """
@app.route('/admin')
def admin_panel():
    pass
"""
        result = audit_route_permissions(unsafe_code)
        route = result['routes_found'][0]
        self.assertEqual(route['path'], "unknown") 
        self.assertFalse(route['standard_auth_found'])

    def test_audit_routes_with_auth(self):
        """Test detection of authenticated routes."""
        safe_code = """
@app.route('/dashboard')
@login_required
def dashboard():
    pass
"""
        result = audit_route_permissions(safe_code)
        route = result['routes_found'][0]
        self.assertTrue(route['standard_auth_found'])

if __name__ == '__main__':
    unittest.main()