import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".cortex", "skills", "pattern-extract", "stages", "architect", "scripts"))
from tree_scanner import (
    collect_dependencies,
    count_lines,
    extract_head,
    parse_package_json,
    parse_pyproject_toml,
    parse_requirements_txt,
    read_readme,
    scan_tree,
    summarize,
)


class TestCountLines:
    def test_counts_lines(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("line1\nline2\nline3\n")
            f.flush()
            assert count_lines(f.name) == 3
        os.unlink(f.name)

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("")
            f.flush()
            assert count_lines(f.name) == 0
        os.unlink(f.name)

    def test_missing_file(self):
        assert count_lines("/nonexistent/path.py") == 0


class TestExtractHead:
    def test_python_gets_10_lines(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            for i in range(20):
                f.write(f"line {i}\n")
            f.flush()
            head = extract_head(f.name, ".py")
        os.unlink(f.name)
        assert "line 9" in head
        assert "line 10" not in head

    def test_other_gets_5_lines(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            for i in range(20):
                f.write(f"line {i}\n")
            f.flush()
            head = extract_head(f.name, ".sql")
        os.unlink(f.name)
        assert "line 4" in head
        assert "line 5" not in head


class TestParseRequirementsTxt:
    def test_basic(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("requests>=2.0\nflask\npyyaml==6.0\n")
            f.flush()
            deps = parse_requirements_txt(f.name)
        os.unlink(f.name)
        assert "requests" in deps
        assert "flask" in deps
        assert "pyyaml" in deps

    def test_skips_comments(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("# comment\nrequests\n")
            f.flush()
            deps = parse_requirements_txt(f.name)
        os.unlink(f.name)
        assert "requests" in deps
        assert len(deps) == 1


class TestParsePyprojectToml:
    def test_basic(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('[project]\ndependencies = [\n    "pyyaml>=6.0",\n    "snowflake-connector-python>=3.0",\n]\n')
            f.flush()
            deps = parse_pyproject_toml(f.name)
        os.unlink(f.name)
        assert "pyyaml" in deps
        assert "snowflake-connector-python" in deps


class TestParsePackageJson:
    def test_basic(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"dependencies": {"react": "^18.0"}, "devDependencies": {"jest": "^29.0"}}, f)
            f.flush()
            deps = parse_package_json(f.name)
        os.unlink(f.name)
        assert "react" in deps
        assert "jest" in deps

    def test_no_deps(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"name": "test"}, f)
            f.flush()
            deps = parse_package_json(f.name)
        os.unlink(f.name)
        assert deps == []


class TestReadReadme:
    def test_reads_readme(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "README.md"), "w") as f:
                f.write("# My Project\nThis is a test.\n")
            result = read_readme(tmpdir)
            assert "My Project" in result

    def test_truncates_at_500(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "README.md"), "w") as f:
                f.write("x" * 1000)
            result = read_readme(tmpdir)
            assert len(result) == 500

    def test_no_readme(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            assert read_readme(tmpdir) == ""


class TestCollectDependencies:
    def test_combines_sources(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "requirements.txt"), "w") as f:
                f.write("requests\n")
            with open(os.path.join(tmpdir, "pyproject.toml"), "w") as f:
                f.write('[project]\ndependencies = ["flask"]\n')
            deps = collect_dependencies(tmpdir)
            assert "requests" in deps
            assert "flask" in deps

    def test_deduplicates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "requirements.txt"), "w") as f:
                f.write("requests\n")
            with open(os.path.join(tmpdir, "pyproject.toml"), "w") as f:
                f.write('[project]\ndependencies = ["requests>=2.0"]\n')
            deps = collect_dependencies(tmpdir)
            assert deps.count("requests") == 1


class TestScanTree:
    def test_scans_python_and_sql(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "app.py"), "w") as f:
                f.write("def main():\n    pass\n")
            with open(os.path.join(tmpdir, "setup.sql"), "w") as f:
                f.write("CREATE TABLE t (id INT);\n")
            result = scan_tree(tmpdir)
            exts = {f["ext"] for f in result["files"]}
            assert ".py" in exts
            assert ".sql" in exts

    def test_skips_venv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = os.path.join(tmpdir, ".venv", "lib")
            os.makedirs(venv_dir)
            with open(os.path.join(venv_dir, "hidden.py"), "w") as f:
                f.write("x = 1\n")
            with open(os.path.join(tmpdir, "visible.py"), "w") as f:
                f.write("x = 1\n")
            result = scan_tree(tmpdir)
            paths = [f["path"] for f in result["files"]]
            assert "visible.py" in paths
            assert not any(".venv" in p for p in paths)

    def test_skips_git(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            git_dir = os.path.join(tmpdir, ".git", "objects")
            os.makedirs(git_dir)
            with open(os.path.join(git_dir, "data.py"), "w") as f:
                f.write("x = 1\n")
            result = scan_tree(tmpdir)
            assert not any(".git" in f["path"] for f in result["files"])

    def test_relative_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sub = os.path.join(tmpdir, "src")
            os.makedirs(sub)
            with open(os.path.join(sub, "main.py"), "w") as f:
                f.write("x = 1\n")
            result = scan_tree(tmpdir)
            assert result["files"][0]["path"] == os.path.join("src", "main.py")

    def test_project_root_prefixes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sub = os.path.join(tmpdir, "service")
            os.makedirs(sub)
            with open(os.path.join(sub, "app.py"), "w") as f:
                f.write("x = 1\n")
            result = scan_tree(sub, project_root=tmpdir)
            assert result["files"][0]["path"] == os.path.join("service", "app.py")

    def test_empty_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = scan_tree(tmpdir)
            assert result["files"] == []

    def test_includes_head(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "app.py"), "w") as f:
                f.write('"""Module docstring."""\nimport os\n')
            result = scan_tree(tmpdir)
            assert "docstring" in result["files"][0]["head"]

    def test_ignores_unsupported_extensions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "data.csv"), "w") as f:
                f.write("a,b\n1,2\n")
            with open(os.path.join(tmpdir, "image.png"), "wb") as f:
                f.write(b"\x89PNG")
            result = scan_tree(tmpdir)
            assert result["files"] == []

    def test_collects_dependencies(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "requirements.txt"), "w") as f:
                f.write("flask\nrequests\n")
            with open(os.path.join(tmpdir, "app.py"), "w") as f:
                f.write("x = 1\n")
            result = scan_tree(tmpdir)
            assert "flask" in result["dependencies"]

    def test_collects_readme(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "README.md"), "w") as f:
                f.write("# Hello World\n")
            with open(os.path.join(tmpdir, "app.py"), "w") as f:
                f.write("x = 1\n")
            result = scan_tree(tmpdir)
            assert "Hello World" in result["readme"]


class TestSummarize:
    def test_removes_head(self):
        result = {
            "files": [{"path": "a.py", "ext": ".py", "line_count": 10, "head": "import os"}],
            "dependencies": ["flask"],
            "readme": "Hello",
        }
        summary = summarize(result)
        assert "head" not in summary["files"][0]
        assert summary["files"][0]["path"] == "a.py"
        assert summary["dependencies"] == ["flask"]


class TestCLIFlags:
    def test_output_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "app.py"), "w") as f:
                f.write("x = 1\n")
            outfile = os.path.join(tmpdir, "result.json")
            import subprocess
            scanner_path = os.path.join(
                os.path.dirname(__file__), "..", ".cortex", "skills",
                "pattern-extract", "stages", "architect", "scripts", "tree_scanner.py",
            )
            result = subprocess.run(
                [sys.executable, scanner_path, tmpdir, "--output", outfile],
                capture_output=True, text=True,
            )
            assert result.returncode == 0
            with open(outfile) as fh:
                data = json.load(fh)
            assert "files" in data
            assert "head" in data["files"][0]

    def test_summary_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "app.py"), "w") as f:
                f.write("x = 1\n")
            import subprocess
            scanner_path = os.path.join(
                os.path.dirname(__file__), "..", ".cortex", "skills",
                "pattern-extract", "stages", "architect", "scripts", "tree_scanner.py",
            )
            result = subprocess.run(
                [sys.executable, scanner_path, tmpdir, "--summary"],
                capture_output=True, text=True,
            )
            assert result.returncode == 0
            data = json.loads(result.stdout)
            assert "head" not in data["files"][0]
