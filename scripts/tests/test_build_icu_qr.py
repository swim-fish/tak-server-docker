"""Check ICU profile values against the installed 7.5.1 preference format."""

import sys
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_icu_qr import build_profile


class BuildIcuQrTests(unittest.TestCase):
    def test_default_profile_sets_indoor_streaming_and_metric_altitude(self) -> None:
        root = ET.fromstring(build_profile("takbox.local", 8322, "live/alpha/1/", "icu-alpha"))
        entries = {entry.get("key"): entry for entry in root.findall("./preference/entry")}
        expected = {
            "disableLocalBroadcast": ("class java.lang.Boolean", "true"),
            "stream_resolution": ("class java.lang.String", "3"),
            "stream_frame_rate": ("class java.lang.String", "15"),
            "stream_bit_rate": ("class java.lang.String", "900"),
            "display_coord_alt": ("class java.lang.String", "0"),
        }
        for key, (kind, value) in expected.items():
            with self.subTest(key=key):
                self.assertEqual((entries[key].get("class"), entries[key].text), (kind, value))
        self.assertNotIn("display_coord_sys", entries)

    def test_profile_accepts_supported_quality_and_altitude_values(self) -> None:
        root = ET.fromstring(build_profile("takbox.local", 8322, "live/", "publisher",
                                         stream_resolution="2", stream_frame_rate="30",
                                         stream_bit_rate="2000", altitude_display="1",
                                         disable_local_broadcast=False))
        values = {entry.get("key"): entry.text for entry in root.findall("./preference/entry")}
        self.assertEqual(values["disableLocalBroadcast"], "false")
        self.assertEqual(values["stream_resolution"], "2")
        self.assertEqual(values["stream_frame_rate"], "30")
        self.assertEqual(values["stream_bit_rate"], "2000")
        self.assertEqual(values["display_coord_alt"], "1")


if __name__ == "__main__":
    unittest.main()
