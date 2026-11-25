# Xarvis

**Xarvis** is a workspace for managing multiple projects of **RISC-V eXpress (RVX)** side by side. Each project is its own git repository, cloned into this directory; Xarvis holds the clones of RVX modules that several projects can share.

[https://riscvexpress.github.io](https://riscvexpress.github.io)

## Layout

```
xarvis/
├── clone_rvx_module.py     # clones a module shared by the projects here
├── rvx_util/os_util.py     # common utilities (from rvx_util)
├── <project>/              # a project: its own git repository
└── <module>-<commit>/      # a shared module clone (e.g. rvx_binary-c88fd52)
```

The project directories and shared module clones are not part of this repository.

## Shared modules

`clone_rvx_module.py` clones an RVX module (e.g. `rvx_binary`, `rvx_synthesizer`) once into `<module>-<commit>/`, so the projects that use the same commit share one copy. It prints the directory of the module.

```sh
python3 clone_rvx_module.py -name rvx_binary -commit c88fd52 -url <module url> -user_path <project>
python3 clone_rvx_module.py -name rvx_binary -commit c88fd52 -path_only   # print the directory only
```

| Option | Meaning |
|---|---|
| `-name` | module name |
| `-commit` | commit hash, or a branch (a branch is updated with `git fetch` and a fast-forward merge on every run) |
| `-url` | repository url (required unless `-path_only`) |
| `-source` | a clone of the module elsewhere to copy from, when none is here yet |
| `-user_path` | top directory of the project that uses the module |
| `-user_url` | git url of that project, for the record |
| `-path_only` | print the directory without cloning |

- A new clone is copied from another clone of the same module here (or from `-source`) when there is one, then fetched and checked out at the requested commit; otherwise it is cloned from the url.
- The users of each clone are recorded in `clone_rvx_module.json`. When a project switches to another commit, the clone that no project uses any more is removed.
