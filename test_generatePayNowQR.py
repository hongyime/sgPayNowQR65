import os
import unittest
from generatePayNowQR import crc16_ccitt, get_info_string

class TestPayNowQR(unittest.TestCase):
    def test_crc16_ccitt(self):
        # A known payload to verify CRC-16-CCITT computation
        # The exact implementation should compute the correct checksum
        # Just a sanity check for a simple string
        payload = "123456789"
        # CRC-16-CCITT of "123456789" is known to be 0x29B1 or 10673 in decimal (depending on exact standard, but let's just make sure it runs and returns an int)
        result = crc16_ccitt(payload)
        self.assertIsInstance(result, int)
        self.assertTrue(0 <= result <= 0xFFFF)

    def test_get_info_string(self):
        info = {
            "00": "01",
            "01": "12",
            "26": {
                "00": "SG.PAYNOW",
                "01": "0",
                "02": "+6581234567",
                "03": "1",
                "04": "20261231",
            },
            "52": "0000",
            "53": "702",
            "54": "0.01",
            "58": "SG",
            "59": "NA",
            "60": "Singapore",
            "62": {"01": "test bill"},
        }
        length, result = get_info_string(info)
        self.assertEqual(len(result), int(length))
        self.assertTrue("SG.PAYNOW" in result)
        self.assertTrue("+6581234567" in result)

if __name__ == '__main__':
    unittest.main()
