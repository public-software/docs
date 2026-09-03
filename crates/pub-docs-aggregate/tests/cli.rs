//! The binary as a user runs it: on the fixture catalog, checkouts and handbook under `tests/fixtures`.

use std::path::{Path, PathBuf};
use std::process::{Command, Output};

fn command() -> Command {
    Command::new(env!("CARGO_BIN_EXE_docs-aggregate"))
}

fn fixture(relative: &str) -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures")
        .join(relative)
}

/// A fresh output directory per test, removed before the run so a stale tree cannot pass a test.
fn out_dir(test: &str) -> PathBuf {
    let dir =
        std::env::temp_dir().join(format!("pub-docs-aggregate-{test}-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    dir
}

fn aggregate(catalog: &str, out: &Path) -> Output {
    command()
        .arg("--catalog")
        .arg(fixture(catalog))
        .arg("--repos")
        .arg(fixture("repos"))
        .arg("--handbook")
        .arg(fixture("handbook"))
        .arg("--out")
        .arg(out)
        .output()
        .expect("the binary runs")
}

fn read(path: &Path) -> String {
    std::fs::read_to_string(path).unwrap_or_else(|e| panic!("{}: {e}", path.display()))
}

/// The SUMMARY.md the fixtures produce: the handbook's own chapters, then a Repositories part in
/// ring order (alpha is spine, beta platform, delta domain) inserted before the handbook's suffix chapter.
const EXPECTED_SUMMARY: &str = "# Summary

[Introduction](introduction.md)

- [The suite](suite.md)
- [How we work](how-we-work.md)

# Repositories

- [alpha](repos/alpha/index.md)
  - [Architecture decisions]()
    - [ADR-0001: Use TOML for the catalog](repos/alpha/adr/0001-use-toml.md)
- [beta](repos/beta/index.md)
  - [Overview](repos/beta/book/overview.md)
  - [Getting started](repos/beta/book/start.md)
    - [Details](repos/beta/book/deeper/details.md)
  - [Draft chapter]()
  - [Reference](repos/beta/book/reference.md)
  - [Architecture decisions]()
    - [ADR-0001: One book per repository](repos/beta/adr/0001-one-book.md)
- [delta](repos/delta/index.md)

[Colophon](colophon.md)
";

#[test]
fn version_exits_zero_and_names_the_command() {
    let out = command()
        .arg("--version")
        .output()
        .expect("the binary runs");
    assert!(out.status.success(), "{out:?}");
    assert!(String::from_utf8_lossy(&out.stdout).starts_with("docs-aggregate "));
}

#[test]
fn an_unknown_argument_exits_one_and_explains_on_stderr() {
    let out = command().arg("--bogus").output().expect("the binary runs");
    assert_eq!(out.status.code(), Some(1), "{out:?}");
    assert!(String::from_utf8_lossy(&out.stderr).contains("unknown argument"));
}

#[test]
fn a_missing_flag_exits_one_and_prints_the_usage() {
    let out = command()
        .arg("--catalog")
        .arg("x.toml")
        .output()
        .expect("the binary runs");
    assert_eq!(out.status.code(), Some(1), "{out:?}");
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(stderr.contains("--repos"), "{stderr}");
    assert!(stderr.contains("--handbook"), "{stderr}");
    assert!(stderr.contains("--out"), "{stderr}");
}

#[test]
fn two_repositories_become_one_site_tree_with_a_summary() {
    let out_dir = out_dir("site");
    let out = aggregate("catalog.toml", &out_dir);
    assert!(out.status.success(), "{out:?}");
    let src = out_dir.join("src");

    // The handbook is copied whole.
    assert!(out_dir.join("book.toml").is_file());
    assert!(out_dir.join("brand.css").is_file());
    assert_eq!(
        read(&src.join("introduction.md")),
        read(&fixture("handbook/src/introduction.md"))
    );

    // alpha: the generated index page and its ADRs, without the template.
    let alpha = read(&src.join("repos/alpha/index.md"));
    assert!(alpha.starts_with("# alpha\n"), "{alpha}");
    assert!(
        alpha.contains("The alpha purpose: decisions only."),
        "{alpha}"
    );
    assert!(alpha.contains("spine"), "{alpha}");
    assert!(
        alpha.contains("https://github.com/public-software/alpha"),
        "{alpha}"
    );
    assert!(src.join("repos/alpha/adr/0001-use-toml.md").is_file());
    assert!(!src.join("repos/alpha/adr/0000-template.md").exists());

    // beta: the book's source tree, non-Markdown files included, and its ADR.
    assert!(src.join("repos/beta/book/deeper/details.md").is_file());
    assert!(src.join("repos/beta/book/deeper/diagram.svg").is_file());
    assert!(src.join("repos/beta/adr/0001-one-book.md").is_file());

    // delta: not checked out, so only the index page.
    let delta = read(&src.join("repos/delta/index.md"));
    assert!(
        delta.contains("The delta purpose: not checked out."),
        "{delta}"
    );
    assert!(delta.contains("L16 L12"), "{delta}");

    assert_eq!(read(&src.join("SUMMARY.md")), EXPECTED_SUMMARY);
    let stdout = String::from_utf8_lossy(&out.stdout);
    assert!(stdout.contains("3 repositories"), "{stdout}");
}

#[test]
fn a_dangling_link_and_a_missing_chapter_fail_the_run_and_are_named() {
    let out_dir = out_dir("dangling");
    let out = aggregate("catalog-with-gamma.toml", &out_dir);
    assert_eq!(out.status.code(), Some(1), "{out:?}");
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(
        stderr.contains("repos/gamma/adr/0001-broken.md:5: dangling link to ../spec/missing.md"),
        "{stderr}"
    );
    assert!(
        stderr.contains("repos/gamma/book/SUMMARY.md:4: dangling link to missing.md"),
        "{stderr}"
    );
    assert!(!stderr.contains("present.md"), "{stderr}");
    assert!(!stderr.contains("alpha"), "{stderr}");
    // The tree is written before the verdict, so the offending page can be inspected.
    assert!(out_dir.join("src/repos/gamma/adr/0001-broken.md").is_file());
}
