//! The catalog: which repositories exist, in which ring, with what purpose.
//!
//! Only the fields the site needs are read; the catalog's own schema is validated by `pub catalog validate`.

use std::path::Path;

use toml::{Table, Value};

/// The rings, inward first: the order the Repositories part lists them in.
pub const RINGS: [&str; 5] = ["spine", "platform", "system", "domain", "standards"];

/// One `[[repo]]` entry of the catalog.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Repository {
    /// The repository name, also its directory under the checkouts and its GitHub name.
    pub name: String,
    /// The dependency ring (`spine`, `platform`, `system`, `domain`, `standards`).
    pub ring: String,
    /// The wave the repository's first crate becomes buildable in.
    pub wave: u64,
    /// The layers of the stack the repository serves (`L0`..`L18`, or `all`).
    pub layers: Vec<String>,
    /// The one-line purpose.
    pub purpose: String,
}

/// The catalog: the organization and its repositories, in ring order then by name.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Catalog {
    /// The GitHub organization (`[catalog].org`).
    pub org: String,
    /// Every `[[repo]]` entry, sorted by ring (inward first) then by name.
    pub repositories: Vec<Repository>,
}

impl Catalog {
    /// Reads and parses the catalog at `path`.
    pub fn load(path: &Path) -> Result<Catalog, String> {
        let text = std::fs::read_to_string(path).map_err(|e| format!("{}: {e}", path.display()))?;
        Catalog::parse(&text).map_err(|e| format!("{}: {e}", path.display()))
    }

    /// Parses the catalog text; the repositories come back in ring order then by name.
    pub fn parse(text: &str) -> Result<Catalog, String> {
        let table: Table = text.parse().map_err(|e| format!("not TOML: {e}"))?;
        let org = table
            .get("catalog")
            .and_then(Value::as_table)
            .and_then(|c| c.get("org"))
            .and_then(Value::as_str)
            .ok_or("no [catalog].org")?
            .to_owned();
        let entries = match table.get("repo") {
            None => &[][..],
            Some(Value::Array(entries)) => entries.as_slice(),
            Some(_) => return Err("`repo` is not an array of tables".to_owned()),
        };
        let mut repositories = entries
            .iter()
            .enumerate()
            .map(|(i, entry)| {
                Repository::from_value(entry).map_err(|e| format!("[[repo]] entry {}: {e}", i + 1))
            })
            .collect::<Result<Vec<_>, _>>()?;
        repositories
            .sort_by(|a, b| (ring_rank(&a.ring), &a.name).cmp(&(ring_rank(&b.ring), &b.name)));
        Ok(Catalog { org, repositories })
    }
}

impl Repository {
    fn from_value(value: &Value) -> Result<Repository, String> {
        let table = value.as_table().ok_or("not a table")?;
        let string = |key: &str| -> Result<String, String> {
            table
                .get(key)
                .and_then(Value::as_str)
                .map(str::to_owned)
                .ok_or(format!("no string `{key}`"))
        };
        let wave = table
            .get("wave")
            .and_then(Value::as_integer)
            .and_then(|w| u64::try_from(w).ok())
            .ok_or("no integer `wave`")?;
        let layers = table
            .get("layers")
            .and_then(Value::as_array)
            .ok_or("no array `layers`")?
            .iter()
            .map(|l| {
                l.as_str()
                    .map(str::to_owned)
                    .ok_or("a layer is not a string".to_owned())
            })
            .collect::<Result<Vec<_>, _>>()?;
        Ok(Repository {
            name: string("name")?,
            ring: string("ring")?,
            wave,
            layers,
            purpose: string("purpose")?,
        })
    }
}

/// Where a ring sorts: the catalog's rings in order, anything unknown after them.
fn ring_rank(ring: &str) -> usize {
    RINGS.iter().position(|r| *r == ring).unwrap_or(RINGS.len())
}

#[cfg(test)]
mod tests {
    use super::*;

    const CATALOG: &str = r#"
[catalog]
version = 1
org = "example-org"

[[repo]]
name = "zeta"
ring = "domain"
wave = 2
layers = ["L16"]
purpose = "Last."

[[repo]]
name = "beta"
ring = "spine"
wave = 1
layers = ["all"]
purpose = "Second."

[[repo]]
name = "alpha"
ring = "spine"
wave = 1
layers = ["L2", "L4"]
purpose = "First."
"#;

    #[test]
    fn repositories_come_back_in_ring_order_then_by_name() {
        let catalog = Catalog::parse(CATALOG).unwrap();
        assert_eq!(catalog.org, "example-org");
        let names: Vec<&str> = catalog
            .repositories
            .iter()
            .map(|r| r.name.as_str())
            .collect();
        assert_eq!(names, ["alpha", "beta", "zeta"]);
        assert_eq!(catalog.repositories[0].layers, ["L2", "L4"]);
        assert_eq!(catalog.repositories[2].wave, 2);
    }

    #[test]
    fn an_unknown_ring_sorts_after_the_known_ones() {
        assert!(ring_rank("elsewhere") > ring_rank("standards"));
        assert!(ring_rank("spine") < ring_rank("platform"));
    }

    #[test]
    fn a_missing_field_names_the_entry_and_the_field() {
        let text = "[catalog]\norg = \"o\"\n\n[[repo]]\nname = \"x\"\nring = \"spine\"\nwave = 1\nlayers = []\n";
        let problem = Catalog::parse(text).unwrap_err();
        assert!(
            problem.contains("entry 1") && problem.contains("`purpose`"),
            "{problem}"
        );
    }

    #[test]
    fn a_catalog_without_an_org_is_refused() {
        assert!(
            Catalog::parse("[[repo]]\nname = \"x\"\n")
                .unwrap_err()
                .contains("org")
        );
    }
}
