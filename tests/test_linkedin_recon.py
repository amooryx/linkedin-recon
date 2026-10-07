import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import linkedin_recon


class SearchPlanTests(unittest.TestCase):
    def test_profile_query_is_scoped_and_url_encoded(self):
        plan = linkedin_recon.build_search_plan(
            'Acme "Research" & Co', "Security Engineer", "bing"
        )
        search = plan["searches"][0]

        self.assertEqual(search["type"], "employee_profiles")
        self.assertEqual(search["engine"], "bing")
        self.assertIn("site:linkedin.com/in", search["query"])
        self.assertEqual(
            parse_qs(urlparse(search["url"]).query)["q"], [search["query"]]
        )
        self.assertEqual(urlparse(search["url"]).netloc, "www.bing.com")
        self.assertIn(r'"Acme \"Research\" & Co"', search["query"])

    def test_tech_search_is_labeled_as_job_posting_signal(self):
        plan = linkedin_recon.build_search_plan(
            "Acme", include_tech=True
        )

        self.assertEqual(
            [search["type"] for search in plan["searches"]],
            ["employee_profiles", "job_posting_technology_signals"],
        )
        self.assertIn("jobs engineering", plan["searches"][1]["query"])
        self.assertIn("Kubernetes", plan["searches"][1]["query"])

    def test_scope_validation_rejects_empty_oversized_and_control_values(self):
        for company, expected in (
            ("  ", "must not be empty"),
            ("x" * 121, "no more than 120"),
            ("Acme\nsite:example.com", "control characters"),
        ):
            with self.subTest(company=company[:20]):
                with self.assertRaisesRegex(ValueError, expected):
                    linkedin_recon.build_search_plan(company)

        with self.assertRaisesRegex(ValueError, "Title"):
            linkedin_recon.build_search_plan("Acme", "\t")

    def test_unknown_engine_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported search engine"):
            linkedin_recon.build_search_plan("Acme", engine="unknown")


class CommandLineTests(unittest.TestCase):
    def test_text_output_says_no_pages_were_fetched(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = linkedin_recon.main(["Acme"])

        self.assertEqual(result, 0)
        self.assertIn("No pages were fetched", output.getvalue())
        self.assertIn("https://www.google.com/search?", output.getvalue())

    def test_json_output_has_stable_machine_readable_shape(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = linkedin_recon.main(["Acme", "--tech", "--format", "json"])

        plan = json.loads(output.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(plan["tool"], "linkedin-recon")
        self.assertEqual(plan["schema_version"], 1)
        self.assertEqual(len(plan["searches"]), 2)
        self.assertNotIn("profiles", plan)
        self.assertNotIn("email_guesses", plan)

    def test_file_output_is_written_and_announced_on_stderr(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            output = io.StringIO()
            errors = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                result = linkedin_recon.main(
                    ["Acme", "--format", "json", "--out", str(path)]
                )

            self.assertEqual(result, 0)
            self.assertEqual(output.getvalue(), "")
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["scope"]["company"], "Acme")
            self.assertIn("Search plan written", errors.getvalue())

    def test_missing_output_directory_fails_explicitly(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing" / "plan.json"
            errors = io.StringIO()
            with contextlib.redirect_stderr(errors):
                result = linkedin_recon.main(["Acme", "--out", str(path)])

        self.assertEqual(result, 2)
        self.assertIn("Output directory does not exist", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
