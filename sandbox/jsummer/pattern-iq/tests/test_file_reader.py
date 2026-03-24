import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".cortex", "skills", "pattern-extract", "stages", "distiller", "scripts"))
from file_reader import load_manifest, passes_threshold, process_domain, read_file_content


class TestPassesThreshold:
    def test_high_only(self):
        assert passes_threshold("high", "high") is True
        assert passes_threshold("medium", "high") is False
        assert passes_threshold("low", "high") is False

    def test_medium_includes_high(self):
        assert passes_threshold("high", "medium") is True
        assert passes_threshold("medium", "medium") is True
        assert passes_threshold("low", "medium") is False

    def test_all_includes_everything(self):
        assert passes_threshold("high", "all") is True
        assert passes_threshold("medium", "all") is True
        assert passes_threshold("low", "all") is True


class TestReadFileContent:
    def test_reads_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("hello world")
            f.flush()
            content = read_file_content(os.path.dirname(f.name), os.path.basename(f.name))
        os.unlink(f.name)
        assert content == "hello world"

    def test_missing_file(self):
        assert read_file_content("/tmp", "nonexistent_file_abc123.py") is None


class TestProcessDomain:
    def test_basic_processing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "main.py"), "w") as f:
                f.write("def main(): pass\n")
            domain = {
                "name": "test-domain",
                "files": [{"path": "main.py", "utility_score": "high", "line_count": 1}],
            }
            result = process_domain(domain, tmpdir, "high")
            assert result["name"] == "test-domain"
            assert len(result["files"]) == 1
            assert result["files"][0]["content"] is not None
            assert result["truncated_count"] == 0

    def test_filters_by_threshold(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "a.py"), "w") as f:
                f.write("x = 1\n")
            with open(os.path.join(tmpdir, "b.py"), "w") as f:
                f.write("y = 2\n")
            domain = {
                "name": "mixed",
                "files": [
                    {"path": "a.py", "utility_score": "high", "line_count": 1},
                    {"path": "b.py", "utility_score": "low", "line_count": 1},
                ],
            }
            result = process_domain(domain, tmpdir, "high")
            assert len(result["files"]) == 1
            assert result["files"][0]["path"] == "a.py"

    def test_context_budget_truncation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "big.py"), "w") as f:
                f.write("x" * 70000)
            with open(os.path.join(tmpdir, "small.py"), "w") as f:
                f.write("y = 1\n")
            domain = {
                "name": "overflow",
                "files": [
                    {"path": "big.py", "utility_score": "high", "line_count": 1},
                    {"path": "small.py", "utility_score": "high", "line_count": 1},
                ],
            }
            result = process_domain(domain, tmpdir, "high")
            assert result["truncated_count"] == 1
            big_file = [f for f in result["files"] if f["path"] == "big.py"][0]
            assert big_file["truncated"] is False
            assert len(big_file["content"]) == 60000
            small_file = [f for f in result["files"] if f["path"] == "small.py"][0]
            assert small_file["truncated"] is True
            assert small_file["content"] is None

    def test_sorts_by_utility(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "low.py"), "w") as f:
                f.write("low\n")
            with open(os.path.join(tmpdir, "high.py"), "w") as f:
                f.write("high\n")
            domain = {
                "name": "sorted",
                "files": [
                    {"path": "low.py", "utility_score": "medium", "line_count": 1},
                    {"path": "high.py", "utility_score": "high", "line_count": 1},
                ],
            }
            result = process_domain(domain, tmpdir, "medium")
            assert result["files"][0]["path"] == "high.py"
            assert result["files"][1]["path"] == "low.py"

    def test_empty_domain(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            domain = {"name": "empty", "files": []}
            result = process_domain(domain, tmpdir, "high")
            assert result["files"] == []
            assert result["truncated_count"] == 0


class TestCLI:
    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "app.py"), "w") as f:
                f.write("def main(): pass\n")

            manifest = {
                "repo_name": "test",
                "repo_url": "",
                "domains": [
                    {
                        "name": "api-service",
                        "files": [{"path": "app.py", "utility_score": "high", "line_count": 1}],
                    }
                ],
            }
            manifest_path = os.path.join(tmpdir, "manifest.json")
            with open(manifest_path, "w") as f:
                json.dump(manifest, f)

            outfile = os.path.join(tmpdir, "output.json")
            import subprocess
            reader_path = os.path.join(
                os.path.dirname(__file__), "..", ".cortex", "skills",
                "pattern-extract", "stages", "distiller", "scripts", "file_reader.py",
            )
            result = subprocess.run(
                [sys.executable, reader_path, "--manifest", manifest_path,
                 "--repo-root", tmpdir, "--threshold", "high", "--output", outfile],
                capture_output=True, text=True,
            )
            assert result.returncode == 0
            with open(outfile) as fh:
                data = json.load(fh)
            assert len(data["domains"]) == 1
            assert data["domains"][0]["files"][0]["content"] is not None
