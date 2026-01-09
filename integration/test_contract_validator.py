"""Test cases for Runtime Contract Validator"""

import unittest
from integration.runtime_contract_validator import RuntimeContractValidator, ValidationResult

class TestRuntimeContractValidator(unittest.TestCase):
    
    def setUp(self):
        self.validator = RuntimeContractValidator()
    
    def test_valid_state_passes(self):
        """Test that valid state payload passes validation"""
        valid_payload = {
            "app": "sample-backend",
            "env": "stage", 
            "state": "healthy",
            "latency_ms": 340,
            "workers": 2,
            "errors_last_min": 3
        }
        
        is_valid, result, message = self.validator.validate_state(valid_payload)
        self.assertTrue(is_valid)
        self.assertEqual(result, ValidationResult.VALID)
    
    def test_missing_required_fields_fails(self):
        """Test that missing required fields trigger NOOP"""
        incomplete_payload = {
            "app": "sample-backend",
            "latency_ms": 340
            # Missing 'env' and 'state'
        }
        
        is_valid, result, message = self.validator.validate_state(incomplete_payload)
        self.assertFalse(is_valid)
        self.assertEqual(result, ValidationResult.INCOMPLETE_DATA)
        self.assertIn("Missing required fields", message)
    
    def test_invalid_environment_fails(self):
        """Test that invalid environment triggers rejection"""
        invalid_env_payload = {
            "app": "sample-backend",
            "env": "invalid-env",
            "state": "healthy"
        }
        
        is_valid, result, message = self.validator.validate_state(invalid_env_payload)
        self.assertFalse(is_valid)
        self.assertEqual(result, ValidationResult.INVALID_ENV)
    
    def test_invalid_state_fails(self):
        """Test that invalid state triggers rejection"""
        invalid_state_payload = {
            "app": "sample-backend", 
            "env": "stage",
            "state": "unknown-state"
        }
        
        is_valid, result, message = self.validator.validate_state(invalid_state_payload)
        self.assertFalse(is_valid)
        self.assertEqual(result, ValidationResult.UNKNOWN_STATE)
    
    def test_empty_app_name_fails(self):
        """Test that empty app name triggers rejection"""
        empty_app_payload = {
            "app": "",
            "env": "stage",
            "state": "healthy"
        }
        
        is_valid, result, message = self.validator.validate_state(empty_app_payload)
        self.assertFalse(is_valid)
        self.assertEqual(result, ValidationResult.INVALID_APP)
    
    def test_noop_response_format(self):
        """Test NOOP response contains required safety fields"""
        noop = self.validator.get_noop_response("Test failure")
        
        self.assertEqual(noop["action"], "NOOP")
        self.assertEqual(noop["reason"], "Test failure")
        self.assertTrue(noop["safe_fallback"])
        self.assertIn("timestamp", noop)

if __name__ == "__main__":
    unittest.main()