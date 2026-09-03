//! mdBook's `SUMMARY.md`: reading a repository's book table of contents and writing chapter lines.
//!
//! The grammar followed is the one the mdBook documentation gives (`format/summary.html`): a chapter is
//! `[Title](path.md)` at column 0 (prefix or suffix chapter) or `- [Title](path.md)` nested by indentation
//! (numbered chapter), `- [Title]()` is a draft chapter, `# Title` is a part title and `---` a separator.
//! Anything else is ignored, as mdBook ignores it.

use std::path::{Path, PathBuf};

use toml::{Table, Value};

/// One chapter line of a `SUMMARY.md`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Entry {
    /// Nesting depth: 0 for a top-level chapter.
    pub depth: usize,
    /// The chapter title.
    pub title: String,
    /// The chapter file, relative to the book's source directory; `None` for a draft chapter.
    pub path: Option<String>,
    /// The 1-based line of the `SUMMARY.md` the entry came from.
    pub line: usize,
}

/// Parses the chapter lines of a `SUMMARY.md`. Part titles are dropped: mdBook allows no part inside a
/// chapter, and every entry here ends up nested under the repository's chapter.
pub fn parse(text: &str) -> Vec<Entry> {
    let mut entries = Vec::new();
    let mut indents: Vec<usize> = vec![0];
    for (index, raw) in text.lines().enumerate() {
        let line = index + 1;
        let expanded = raw.replace('\t', "    ");
        let indent = expanded.len() - expanded.trim_start().len();
        let content = expanded.trim();
        let Some(link) = content
            .strip_prefix("- ")
            .or_else(|| content.strip_prefix("* "))
            .map(str::trim_start)
        else {
            if indent == 0
                && let Some((title, path)) = split_link(content)
            {
                indents.truncate(1);
                entries.push(Entry {
                    depth: 0,
                    title,
                    path,
                    line,
                });
            }
            continue;
        };
        let Some((title, path)) = split_link(link) else {
            continue;
        };
        while indents.last().is_some_and(|top| *top > indent) {
            indents.pop();
        }
        if indents.last().is_some_and(|top| *top < indent) {
            indents.push(indent);
        }
        entries.push(Entry {
            depth: indents.len() - 1,
            title,
            path,
            line,
        });
    }
    entries
}

/// `[Title](path)` → (title, Some(path)); `[Title]()` → (title, None); anything else → `None`.
fn split_link(text: &str) -> Option<(String, Option<String>)> {
    let inner = text.strip_prefix('[')?.strip_suffix(')')?;
    let (title, path) = inner.rsplit_once("](")?;
    let path = path.trim();
    Some((
        title.trim().to_owned(),
        (!path.is_empty()).then(|| path.to_owned()),
    ))
}

/// Renders `entries` as numbered chapters, each nested `depth` levels deeper than written and with
/// `path_prefix` in front of every chapter file.
pub fn render(entries: &[Entry], depth: usize, path_prefix: &str) -> String {
    entries
        .iter()
        .map(|e| {
            let indent = "  ".repeat(depth + e.depth);
            match &e.path {
                Some(path) => format!("{indent}- [{}]({path_prefix}{path})\n", e.title),
                None => format!("{indent}- [{}]()\n", e.title),
            }
        })
        .collect()
}

/// The source directory of the book under `docs`, when there is one: `docs/book.toml` names it
/// (`[book].src`, `src` by default); without a `book.toml`, `docs/src/SUMMARY.md` makes `docs/src` the book.
pub fn locate_book(docs: &Path) -> Result<Option<PathBuf>, String> {
    let config = docs.join("book.toml");
    let src = if config.is_file() {
        let text =
            std::fs::read_to_string(&config).map_err(|e| format!("{}: {e}", config.display()))?;
        let table: Table = text
            .parse()
            .map_err(|e| format!("{}: not TOML: {e}", config.display()))?;
        let src = table
            .get("book")
            .and_then(Value::as_table)
            .and_then(|b| b.get("src"))
            .and_then(Value::as_str)
            .unwrap_or("src");
        docs.join(src)
    } else {
        docs.join("src")
    };
    Ok(src.join("SUMMARY.md").is_file().then_some(src))
}

#[cfg(test)]
mod tests {
    use super::*;

    const SUMMARY: &str = "# Summary\n\n[Prefix](prefix.md)\n\n# Part one\n\n- [One](one.md)\n  - [One A](one/a.md)\n    - [One A i](one/a/i.md)\n  - [Draft]()\n* not a link\n- [Two](two.md)\n\n---\n\n[Suffix](suffix.md)\n";

    #[test]
    fn chapters_keep_their_order_depth_and_line() {
        let entries = parse(SUMMARY);
        let seen: Vec<(usize, &str, Option<&str>, usize)> = entries
            .iter()
            .map(|e| (e.depth, e.title.as_str(), e.path.as_deref(), e.line))
            .collect();
        assert_eq!(
            seen,
            [
                (0, "Prefix", Some("prefix.md"), 3),
                (0, "One", Some("one.md"), 7),
                (1, "One A", Some("one/a.md"), 8),
                (2, "One A i", Some("one/a/i.md"), 9),
                (1, "Draft", None, 10),
                (0, "Two", Some("two.md"), 12),
                (0, "Suffix", Some("suffix.md"), 16),
            ]
        );
    }

    #[test]
    fn four_space_and_tab_indentation_nest_the_same_way() {
        let entries = parse("- [A](a.md)\n    - [B](b.md)\n\t\t- [C](c.md)\n- [D](d.md)\n");
        let depths: Vec<usize> = entries.iter().map(|e| e.depth).collect();
        assert_eq!(depths, [0, 1, 2, 0]);
    }

    #[test]
    fn rendering_nests_and_prefixes() {
        let entries = parse("[Intro](intro.md)\n- [One](one.md)\n  - [Draft]()\n");
        assert_eq!(
            render(&entries, 1, "repos/x/book/"),
            "  - [Intro](repos/x/book/intro.md)\n  - [One](repos/x/book/one.md)\n    - [Draft]()\n"
        );
    }

    #[test]
    fn a_book_is_found_through_book_toml_or_the_default_src() {
        let dir =
            std::env::temp_dir().join(format!("pub-docs-aggregate-locate-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(dir.join("docs/pages")).unwrap();
        assert_eq!(locate_book(&dir.join("docs")).unwrap(), None);
        std::fs::write(dir.join("docs/pages/SUMMARY.md"), "").unwrap();
        assert_eq!(
            locate_book(&dir.join("docs")).unwrap(),
            None,
            "pages/ is not the default src"
        );
        std::fs::write(dir.join("docs/book.toml"), "[book]\nsrc = \"pages\"\n").unwrap();
        assert_eq!(
            locate_book(&dir.join("docs")).unwrap(),
            Some(dir.join("docs/pages"))
        );
        std::fs::remove_dir_all(&dir).unwrap();
    }
}
