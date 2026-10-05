import argparse
from pathlib import Path
import unittest

from hrc_pilot.backend_options import add_backend_options, backend_provenance, configure_backend


class BackendOptionTests(unittest.TestCase):
    def parser(self):
        parser = argparse.ArgumentParser()
        add_backend_options(parser)
        return parser

    def test_important_tier_requires_genesis(self):
        args = self.parser().parse_args(["--important"])
        with self.assertRaises(SystemExit):
            configure_backend(args, self.parser(), Path("/tmp/hrc-test-output"))

    def test_important_genesis_provenance_declares_video_contract(self):
        args = self.parser().parse_args(["--backend", "genesis", "--important"])
        provenance = backend_provenance(args)
        self.assertEqual(provenance["experiment_tier"], "important")
        self.assertTrue(provenance["sim_video_required"])
        self.assertEqual(provenance["sim_video_contract"]["artifact"], "demo.mp4")

    def test_exploratory_reference_does_not_require_video(self):
        args = self.parser().parse_args([])
        provenance = backend_provenance(args)
        self.assertEqual(provenance["experiment_tier"], "exploratory")
        self.assertFalse(provenance["sim_video_required"])


if __name__ == "__main__":
    unittest.main()
