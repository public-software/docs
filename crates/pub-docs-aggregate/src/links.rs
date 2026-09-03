//! The cross-link check: every relative link and image in the site's Markdown must point at a file in the tree.

use std::path::{Component, Path, PathBuf};

use pulldown_cmark::{Event, Parser, Tag};

/// A link whose target is not in the site tree.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct Dangling {
    /// The page the link is on, relative to the site's `src/`.
    pub page: String,
    /// The 1-based line the link starts on.
    pub line: usize,
    /// The destination as written.
    pub dest: String,
}

impl std::fmt::Display for Dangling {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "{}:{}: dangling link to {}",
            self.page, self.line, self.dest
        )
    }
}

/// Every link and image destination in the Markdown `text` that names a file relative to the page, with the
/// line it starts on. Absolute paths, URLs with a scheme, `mailto:` and fragment-only links are not files.
pub fn relative_links(text: &str) -> Vec<(String, usize)> {
    Parser::new(text)
        .into_offset_iter()
        .filter_map(|(event, range)| match event {
            Event::Start(Tag::Link { dest_url, .. } | Tag::Image { dest_url, .. })
                if is_relative(&dest_url) =>
            {
                Some((
                    dest_url.into_string(),
                    text[..range.start].matches('\n').count() + 1,
                ))
            }
            _ => None,
        })
        .collect()
}

/// Whether `dest` is a path relative to the page (as opposed to a URL, an absolute path or a fragment).
fn is_relative(dest: &str) -> bool {
    if dest.is_empty() || dest.starts_with('#') || dest.starts_with('/') {
        return false;
    }
    let scheme_end = dest.find(':').unwrap_or(0);
    let scheme = &dest[..scheme_end];
    !(scheme_end > 0
        && scheme.starts_with(|c: char| c.is_ascii_alphabetic())
        && scheme
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || "+.-".contains(c)))
}

/// Where a relative `dest` written on the page at `page` (relative to the root) points, normalized
/// lexically; `None` when it climbs out of the root.
fn resolve(page: &Path, dest: &str) -> Option<PathBuf> {
    let target = dest.split(['#', '?']).next().unwrap_or("");
    let mut parts: Vec<String> = Vec::new();
    for component in page
        .parent()
        .unwrap_or(Path::new(""))
        .join(target)
        .components()
    {
        match component {
            Component::Normal(part) => parts.push(part.to_string_lossy().into_owned()),
            Component::ParentDir => {
                parts.pop()?;
            }
            Component::CurDir => {}
            Component::RootDir | Component::Prefix(_) => return None,
        }
    }
    Some(parts.iter().collect())
}

/// Checks every `.md` page under `root`; the dangling links come back sorted by page then line.
pub fn check_tree(root: &Path) -> Result<Vec<Dangling>, String> {
    let mut pages = Vec::new();
    collect_pages(root, root, &mut pages)?;
    let mut dangling = Vec::new();
    for page in pages {
        let text = std::fs::read_to_string(root.join(&page))
            .map_err(|e| format!("{}: {e}", page.display()))?;
        for (dest, line) in relative_links(&text) {
            if !exists(root, &page, &dest) {
                dangling.push(Dangling {
                    page: page.to_string_lossy().replace('\\', "/"),
                    line,
                    dest,
                });
            }
        }
    }
    dangling.sort();
    Ok(dangling)
}

/// Whether `dest`, written on `page`, names a file of the tree. mdBook renders `x.md` as `x.html`, so a link
/// to `x.html` is satisfied by `x.md` too.
fn exists(root: &Path, page: &Path, dest: &str) -> bool {
    let Some(target) = resolve(page, dest) else {
        return false;
    };
    if root.join(&target).exists() {
        return true;
    }
    target.extension().is_some_and(|e| e == "html")
        && root.join(target.with_extension("md")).is_file()
}

fn collect_pages(root: &Path, dir: &Path, pages: &mut Vec<PathBuf>) -> Result<(), String> {
    let mut children: Vec<PathBuf> = std::fs::read_dir(dir)
        .map_err(|e| format!("{}: {e}", dir.display()))?
        .map(|entry| {
            entry
                .map(|e| e.path())
                .map_err(|e| format!("{}: {e}", dir.display()))
        })
        .collect::<Result<_, _>>()?;
    children.sort();
    for child in children {
        if child.is_dir() {
            collect_pages(root, &child, pages)?;
        } else if child.extension().is_some_and(|e| e == "md") {
            let relative = child
                .strip_prefix(root)
                .map_err(|e| format!("{}: {e}", child.display()))?;
            pages.push(relative.to_path_buf());
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn only_relative_file_destinations_are_links_to_check() {
        let text = "Line one.\n\n[a](a.md) and [b](../b/c.md#x) and ![i](img.png)\n\n[u](https://x.test/) [m](mailto:a@b) [f](#frag) [abs](/root.md) <https://auto.test/>\n\n[r][ref]\n\n[ref]: deeper/ref.md\n";
        assert_eq!(
            relative_links(text),
            [
                ("a.md".to_owned(), 3),
                ("../b/c.md#x".to_owned(), 3),
                ("img.png".to_owned(), 3),
                ("deeper/ref.md".to_owned(), 7)
            ]
        );
    }

    #[test]
    fn links_inside_code_are_not_links() {
        assert!(relative_links("`[a](a.md)`\n\n```\n[b](b.md)\n```\n").is_empty());
    }

    #[test]
    fn a_windows_drive_is_not_a_scheme_but_a_colon_in_a_file_name_is_not_either() {
        assert!(
            !is_relative("c:/x.md"),
            "a one-letter scheme is a scheme, as mdBook treats it"
        );
        assert!(
            !is_relative("notes:today.md"),
            "a scheme-shaped prefix is a scheme"
        );
        assert!(is_relative("a b.md"));
        assert!(is_relative("./a.md"));
    }

    #[test]
    fn resolution_is_lexical_and_stays_under_the_root() {
        assert_eq!(
            resolve(Path::new("repos/x/adr/0001.md"), "../index.md#top"),
            Some(PathBuf::from("repos/x/index.md"))
        );
        assert_eq!(
            resolve(Path::new("a/b.md"), "./c.md?x=1"),
            Some(PathBuf::from("a/c.md"))
        );
        assert_eq!(resolve(Path::new("a.md"), "../escape.md"), None);
    }

    #[test]
    fn a_tree_reports_what_is_missing_with_page_and_line() {
        let root =
            std::env::temp_dir().join(format!("pub-docs-aggregate-links-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&root);
        std::fs::create_dir_all(root.join("sub")).unwrap();
        std::fs::write(
            root.join("index.md"),
            "# I\n\n[ok](sub/page.md) [html](sub/page.html) [gone](sub/gone.md)\n",
        )
        .unwrap();
        std::fs::write(
            root.join("sub/page.md"),
            "[up](../index.md)\n\n[out](../../x.md)\n",
        )
        .unwrap();
        let found = check_tree(&root).unwrap();
        let shown: Vec<String> = found.iter().map(ToString::to_string).collect();
        assert_eq!(
            shown,
            [
                "index.md:3: dangling link to sub/gone.md",
                "sub/page.md:3: dangling link to ../../x.md"
            ]
        );
        std::fs::remove_dir_all(&root).unwrap();
    }
}
