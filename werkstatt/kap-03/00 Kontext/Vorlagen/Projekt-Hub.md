---
tags: [projekt]
typ: projekt-hub
layer: curated
status: aktiv                 # beim Anlegen aktiv; aendert nur der Eigner
phase: konzeption
meeting_key: {{KUERZEL}}
erstellt: {{DATUM}}
start: {{DATUM}}
ende: offen
source: {{SOURCE}}
governance: "[[{{PFAD}}/Projekt-Governance]]"
kontakte: []
---

# {{NAME}}

> Ein Satz: Was ist das Projekt, und warum machen wir es?

## Projektziel

## Status

## Entscheide
```dataview
TABLE status, erstellt FROM "{{PFAD}}/Decisions" SORT erstellt DESC
```

## Meetings
```dataview
LIST FROM "{{PFAD}}/Meetings" SORT file.name DESC LIMIT 10
```
