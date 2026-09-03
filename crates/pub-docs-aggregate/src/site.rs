//! Assembling the site tree: the handbook copied whole, one chapter per catalog repository added under
//! `src/repos/<name>/`, and the handbook's `SUMMARY.md` rewritten with a Repositories part.

use std::path::{Path, PathBuf};

use crate::catalog::{Catalog, Repository};
use crate::links::{self, Dangling};
use crate::summary;

/// The ADR template every repository carries; it is not a decision.
const ADR_TEMPLATE: &str = "0000-template.md";

/// What one run produced.
#[derive(Debug, Default, PartialEq, Eq)]
pub struct Report {
    /// Catalog repositories given a chapter (every one of them, checked out or not).
    pub repositories: usize,
    /// Repositories whose `docs/` book was folded in.
    pub books: usize,
    /// Architecture decision records folded in, over every repository.
    pub decisions: usize,
    /// Every link in the written tree whose target is not there, sorted by page then line.
    pub dangling: Vec<Dangling>,
}

/// The chapter lines and counts one repository contributes.
#[derive(Debug, Default)]
struct Chapter {
    lines: String,
    book: bool,
    decisions: usize,
    dangling: Vec<Dangling>,
}

/// Writes the site tree for `catalog` into `out`: `handbook` copied, then `src/repos/<name>/` for every
/// repository (its checkout looked up under `repos`), then `src/SUMMARY.md`. Existing files in `out` are
/// overwritten; the tree is written in full before the links are checked, so a dangling link can be inspected.
pub fn build(
    catalog: &Catalog,
    repos: &Path,
    handbook: &Path,
    out: &Path,
) -> Result<Report, String> {
    copy_tree(handbook, out, &[])?;
    let src = out.join("src");
    let summary_path = src.join("SUMMARY.md");
    let handbook_summary = std::fs::read_to_string(&summary_path)
        .map_err(|e| format!("{}: {e}", summary_path.display()))?;

    let mut report = Report::default();
    let mut part = String::from("# Repositories\n\n");
    for repository in &catalog.repositories {
        let chapter = assemble(
            repository,
            &catalog.org,
            &repos.join(&repository.name),
            &src,
        )?;
        part.push_str(&chapter.lines);
        report.repositories += 1;
        report.books += usize::from(chapter.book);
        report.decisions += chapter.decisions;
        report.dangling.extend(chapter.dangling);
    }
    write(&summary_path, &insert_part(&handbook_summary, &part))?;

    report.dangling.extend(links::check_tree(&src)?);
    report.dangling.sort();
    Ok(report)
}

/// One repository's chapter: the generated index page, its book's chapters, its decision records.
fn assemble(
    repository: &Repository,
    org: &str,
    checkout: &Path,
    src: &Path,
) -> Result<Chapter, String> {
    let name = &repository.name;
    let dir = src.join("repos").join(name);
    std::fs::create_dir_all(&dir).map_err(|e| format!("{}: {e}", dir.display()))?;
    let mut chapter = Chapter {
        lines: format!("- [{name}](repos/{name}/index.md)\n"),
        ..Chapter::default()
    };
    let docs = checkout.join("docs");

    if let Some(book_src) = summary::locate_book(&docs)? {
        let summary_file = book_src.join("SUMMARY.md");
        let text = std::fs::read_to_string(&summary_file)
            .map_err(|e| format!("{}: {e}", summary_file.display()))?;
        let entries = summary::parse(&text);
        let book_dir = dir.join("book");
        copy_tree(&book_src, &book_dir, &["SUMMARY.md"])?;
        let prefix = format!("repos/{name}/book/");
        chapter
            .lines
            .push_str(&summary::render(&entries, 1, &prefix));
        for entry in entries {
            if let Some(path) = entry.path
                && !book_dir.join(&path).is_file()
            {
                chapter.dangling.push(Dangling {
                    page: format!("{prefix}SUMMARY.md"),
                    line: entry.line,
                    dest: path,
                });
            }
        }
        chapter.book = true;
    }

    let decisions = decision_records(&docs.join("adr"))?;
    if !decisions.is_empty() {
        let adr_dir = dir.join("adr");
        copy_tree(&docs.join("adr"), &adr_dir, &[ADR_TEMPLATE])?;
        chapter.lines.push_str("  - [Architecture decisions]()\n");
        for (file, title) in &decisions {
            chapter
                .lines
                .push_str(&format!("    - [{title}](repos/{name}/adr/{file})\n"));
        }
        chapter.decisions = decisions.len();
    }

    write(
        &dir.join("index.md"),
        &index_page(repository, org, chapter.book || chapter.decisions > 0),
    )?;
    Ok(chapter)
}

/// The `.md` files of an ADR directory (the template excluded), sorted, each with its title: the first
/// `# ` heading, or the file stem when there is none. An absent directory is no decision at all.
fn decision_records(adr: &Path) -> Result<Vec<(String, String)>, String> {
    if !adr.is_dir() {
        return Ok(Vec::new());
    }
    let mut files: Vec<PathBuf> = std::fs::read_dir(adr)
        .map_err(|e| format!("{}: {e}", adr.display()))?
        .map(|entry| {
            entry
                .map(|e| e.path())
                .map_err(|e| format!("{}: {e}", adr.display()))
        })
        .collect::<Result<_, _>>()?;
    files.sort();
    let mut records = Vec::new();
    for file in files {
        let Some(file_name) = file.file_name().map(|f| f.to_string_lossy().into_owned()) else {
            continue;
        };
        if !file.is_file()
            || file_name == ADR_TEMPLATE
            || file.extension().is_none_or(|e| e != "md")
        {
            continue;
        }
        let text =
            std::fs::read_to_string(&file).map_err(|e| format!("{}: {e}", file.display()))?;
        let title = text
            .lines()
            .find_map(|l| l.strip_prefix("# "))
            .map(str::trim)
            .filter(|t| !t.is_empty())
            .map(str::to_owned)
            .unwrap_or_else(|| file_name.trim_end_matches(".md").to_owned());
        records.push((file_name, title));
    }
    Ok(records)
}

/// The generated index page of a repository's chapter.
fn index_page(repository: &Repository, org: &str, has_documentation: bool) -> String {
    let Repository {
        name,
        ring,
        wave,
        layers,
        purpose,
    } = repository;
    let mut page = format!(
        "# {name}\n\n{purpose}\n\n- Ring: {ring}\n- Wave: {wave}\n- Layers: {}\n- Repository: <https://github.com/{org}/{name}>\n",
        layers.join(" ")
    );
    if !has_documentation {
        page.push_str("\nThis repository has no documentation of its own yet.\n");
    }
    page
}

/// The handbook's `SUMMARY.md` with `part` inserted before its first suffix chapter, or at its end when it
/// has none: a suffix chapter is a column-0 `[Title](path)` line after the numbered chapters.
fn insert_part(summary: &str, part: &str) -> String {
    let lines: Vec<&str> = summary.lines().collect();
    let mut numbered_seen = false;
    let mut suffix_at = None;
    for (i, line) in lines.iter().enumerate() {
        let trimmed = line.trim_start();
        if trimmed.starts_with("- [") || trimmed.starts_with("* [") {
            numbered_seen = true;
        } else if numbered_seen && line.starts_with('[') {
            suffix_at = Some(i);
            break;
        }
    }
    let (head, tail) = match suffix_at {
        Some(i) => (lines[..i].join("\n"), Some(lines[i..].join("\n"))),
        None => (lines.join("\n"), None),
    };
    match tail {
        Some(tail) => format!("{}\n\n{part}\n{}\n", head.trim_end(), tail.trim_end()),
        None => format!("{}\n\n{part}", head.trim_end()),
    }
}

/// Copies the directory `from` into `to` (created as needed), skipping the top-level names in `skip`.
fn copy_tree(from: &Path, to: &Path, skip: &[&str]) -> Result<(), String> {
    std::fs::create_dir_all(to).map_err(|e| format!("{}: {e}", to.display()))?;
    let entries = std::fs::read_dir(from).map_err(|e| format!("{}: {e}", from.display()))?;
    for entry in entries {
        let entry = entry.map_err(|e| format!("{}: {e}", from.display()))?;
        let name = entry.file_name();
        if skip.iter().any(|s| name == *s) {
            continue;
        }
        let (source, target) = (entry.path(), to.join(&name));
        if source.is_dir() {
            copy_tree(&source, &target, &[])?;
        } else {
            std::fs::copy(&source, &target)
                .map_err(|e| format!("{} -> {}: {e}", source.display(), target.display()))?;
        }
    }
    Ok(())
}

fn write(path: &Path, text: &str) -> Result<(), String> {
    std::fs::write(path, text).map_err(|e| format!("{}: {e}", path.display()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_part_goes_before_the_first_suffix_chapter() {
        let summary =
            "# Summary\n\n[Intro](intro.md)\n\n- [One](one.md)\n\n\n[Suffix](suffix.md)\n";
        assert_eq!(
            insert_part(summary, "# Repositories\n\n- [a](repos/a/index.md)\n"),
            "# Summary\n\n[Intro](intro.md)\n\n- [One](one.md)\n\n# Repositories\n\n- [a](repos/a/index.md)\n\n[Suffix](suffix.md)\n"
        );
    }

    #[test]
    fn without_a_suffix_chapter_the_part_goes_last() {
        assert_eq!(
            insert_part("[Intro](intro.md)\n- [One](one.md)\n", "# Repositories\n"),
            "[Intro](intro.md)\n- [One](one.md)\n\n# Repositories\n"
        );
    }

    #[test]
    fn a_prefix_chapter_is_not_a_suffix_chapter() {
        let summary = "[Intro](intro.md)\n[More](more.md)\n";
        assert_eq!(
            insert_part(summary, "# R\n"),
            "[Intro](intro.md)\n[More](more.md)\n\n# R\n"
        );
    }

    #[test]
    fn the_index_page_says_when_there_is_nothing_else() {
        let repository = Repository {
            name: "x".into(),
            ring: "spine".into(),
            wave: 1,
            layers: vec!["L2".into(), "L4".into()],
            purpose: "Purpose.".into(),
        };
        let page = index_page(&repository, "org", false);
        assert!(page.starts_with("# x\n\nPurpose.\n\n- Ring: spine\n- Wave: 1\n- Layers: L2 L4\n- Repository: <https://github.com/org/x>\n"), "{page}");
        assert!(page.contains("no documentation of its own yet"));
        assert!(!index_page(&repository, "org", true).contains("no documentation"));
    }

    #[test]
    fn decision_records_skip_the_template_and_title_from_the_heading() {
        let adr =
            std::env::temp_dir().join(format!("pub-docs-aggregate-adr-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&adr);
        std::fs::create_dir_all(&adr).unwrap();
        std::fs::write(adr.join(ADR_TEMPLATE), "# ADR-0000: Title\n").unwrap();
        std::fs::write(
            adr.join("0002-second.md"),
            "- Status: accepted\n\n# ADR-0002: Second\n",
        )
        .unwrap();
        std::fs::write(adr.join("0001-first.md"), "no heading here\n").unwrap();
        std::fs::write(adr.join("sketch.png"), "").unwrap();
        assert_eq!(
            decision_records(&adr).unwrap(),
            [
                ("0001-first.md".to_owned(), "0001-first".to_owned()),
                ("0002-second.md".to_owned(), "ADR-0002: Second".to_owned())
            ]
        );
        assert!(decision_records(&adr.join("absent")).unwrap().is_empty());
        std::fs::remove_dir_all(&adr).unwrap();
    }
}
