# Findings

- The adapter previously stored one chart subscription and replaced it on every selection.
- Lightstreamer chart item names already contain exact EPIC and interval identity.
- No Qt/runtime caller is changed in this lot; existing selected-chart behavior remains intact.
