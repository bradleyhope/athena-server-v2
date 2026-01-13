# COGOS Project Reference

This ATHENA server is part of the COGOS (Cognitive Operating System) project management framework.

## COGOS Location

- **Repository:** https://github.com/bradleyhope/cogos-system
- **Branch:** master
- **Project File:** `projects/labs/athena.yaml`

## COGOS Documentation

The COGOS system contains additional ATHENA documentation:

| File | Purpose |
|------|---------|
| `projects/labs/athena.yaml` | Complete project specification |
| `docs/athena/README.md` | Overview and quick reference |
| `docs/athena/architecture.md` | Three-tier thinking model |
| `docs/athena/notion-integration.md` | All Notion databases and pages |

## How to Initialize

When starting a new Manus session, say:

```
init cogos athena
```

This loads the ATHENA project context including:
- All Notion database IDs
- API endpoint documentation
- Architecture overview
- Session types and naming conventions

## Cross-References

| This Repository | COGOS System |
|-----------------|--------------|
| `docs/` | `docs/athena/` |
| `config.py` | `projects/labs/athena.yaml` |
| `jobs/*.py` | Session type definitions |
| `db/brain/` | Brain architecture docs |

---

*Last updated: January 13, 2026*
