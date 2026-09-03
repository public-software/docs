//! `pub-docs-aggregate` — the `docs-aggregate` command of [`docs`](https://github.com/public-software/docs):
//! folds every repository's `docs/` (its mdBook, its architecture decision records) into the one handbook
//! site tree, and fails when a cross-link in that tree points nowhere.
//!
//! `main` does the I/O; [`run`] does the work and is what the unit tests call.

#![forbid(unsafe_code)]

mod catalog;
mod links;
mod site;
mod summary;

use std::path::PathBuf;
use std::process::ExitCode;

/// What `--version` prints.
const VERSION_LINE: &str = concat!("docs-aggregate ", env!("CARGO_PKG_VERSION"));

/// What a wrong invocation prints.
const USAGE: &str = "usage: docs-aggregate --catalog <catalog.toml> --repos <checkouts> --handbook <site/handbook> --out <dir>
       docs-aggregate --version";

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match run(&args) {
        Ok(out) => {
            print!("{out}");
            ExitCode::SUCCESS
        }
        Err(problem) => {
            eprintln!("docs-aggregate: {problem}");
            ExitCode::FAILURE
        }
    }
}

/// The four paths a run needs.
#[derive(Debug, PartialEq, Eq)]
struct Paths {
    /// The catalog (`catalog/catalog.toml` of the catalog repository).
    catalog: PathBuf,
    /// The directory holding one checkout per repository, named as in the catalog.
    repos: PathBuf,
    /// The handbook's mdBook root (`site/handbook`): `book.toml` and `src/`.
    handbook: PathBuf,
    /// Where the site tree is written.
    out: PathBuf,
}

/// Runs the command on `args` and returns what it prints; free of I/O so tests call it directly.
fn run(args: &[String]) -> Result<String, String> {
    let args: Vec<&str> = args.iter().map(String::as_str).collect();
    match args.as_slice() {
        [] | ["--version"] => Ok(format!("{VERSION_LINE}\n")),
        _ => aggregate(&parse_flags(&args)?),
    }
}

/// Reads the four `--flag <value>` pairs, in any order.
fn parse_flags(args: &[&str]) -> Result<Paths, String> {
    let (mut catalog, mut repos, mut handbook, mut out) = (None, None, None, None);
    let mut rest = args;
    while let [flag, tail @ ..] = rest {
        let slot = match *flag {
            "--catalog" => &mut catalog,
            "--repos" => &mut repos,
            "--handbook" => &mut handbook,
            "--out" => &mut out,
            other => {
                return Err(format!(
                    "unknown argument `{other}`; try --version\n{USAGE}"
                ));
            }
        };
        let [value, tail @ ..] = tail else {
            return Err(format!("{flag} needs a value\n{USAGE}"));
        };
        *slot = Some(PathBuf::from(value));
        rest = tail;
    }
    let required = |name: &str, value: Option<PathBuf>| {
        value.ok_or_else(|| format!("missing {name}\n{USAGE}"))
    };
    Ok(Paths {
        catalog: required("--catalog", catalog)?,
        repos: required("--repos", repos)?,
        handbook: required("--handbook", handbook)?,
        out: required("--out", out)?,
    })
}

/// Builds the site tree and reports it; a dangling link is an error naming every one of them.
fn aggregate(paths: &Paths) -> Result<String, String> {
    let catalog = catalog::Catalog::load(&paths.catalog)?;
    let report = site::build(&catalog, &paths.repos, &paths.handbook, &paths.out)?;
    if !report.dangling.is_empty() {
        let list: Vec<String> = report.dangling.iter().map(ToString::to_string).collect();
        return Err(format!(
            "{} in {}:\n{}",
            plural(report.dangling.len(), "dangling link", "dangling links"),
            paths.out.display(),
            list.join("\n")
        ));
    }
    Ok(format!(
        "docs-aggregate: {}, {}, {} written to {}\n",
        plural(report.repositories, "repository", "repositories"),
        plural(report.books, "book", "books"),
        plural(report.decisions, "decision record", "decision records"),
        paths.out.display()
    ))
}

fn plural(count: usize, one: &str, many: &str) -> String {
    format!("{count} {}", if count == 1 { one } else { many })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn args(list: &[&str]) -> Vec<String> {
        list.iter().map(|a| (*a).to_owned()).collect()
    }

    #[test]
    fn no_arguments_prints_the_version_line() {
        assert_eq!(run(&args(&[])).unwrap(), format!("{VERSION_LINE}\n"));
    }

    #[test]
    fn version_names_the_command() {
        assert!(
            run(&args(&["--version"]))
                .unwrap()
                .starts_with("docs-aggregate ")
        );
    }

    #[test]
    fn an_unknown_argument_is_an_error_naming_it() {
        let problem = run(&args(&["--bogus"])).unwrap_err();
        assert!(problem.contains("--bogus"), "{problem}");
    }

    #[test]
    fn the_flags_come_in_any_order() {
        let paths = parse_flags(&[
            "--out",
            "o",
            "--handbook",
            "h",
            "--repos",
            "r",
            "--catalog",
            "c",
        ])
        .unwrap();
        assert_eq!(
            paths,
            Paths {
                catalog: "c".into(),
                repos: "r".into(),
                handbook: "h".into(),
                out: "o".into()
            }
        );
    }

    #[test]
    fn a_missing_flag_or_value_is_named_with_the_usage() {
        let problem =
            parse_flags(&["--catalog", "c", "--repos", "r", "--handbook", "h"]).unwrap_err();
        assert!(problem.starts_with("missing --out\nusage:"), "{problem}");
        let problem = parse_flags(&["--catalog"]).unwrap_err();
        assert!(problem.starts_with("--catalog needs a value"), "{problem}");
    }

    #[test]
    fn a_catalog_that_does_not_exist_is_the_error() {
        let problem = run(&args(&[
            "--catalog",
            "/nonexistent/catalog.toml",
            "--repos",
            ".",
            "--handbook",
            ".",
            "--out",
            ".",
        ]))
        .unwrap_err();
        assert!(problem.contains("/nonexistent/catalog.toml"), "{problem}");
    }

    #[test]
    fn counts_read_as_english() {
        assert_eq!(plural(1, "book", "books"), "1 book");
        assert_eq!(plural(0, "book", "books"), "0 books");
    }
}
