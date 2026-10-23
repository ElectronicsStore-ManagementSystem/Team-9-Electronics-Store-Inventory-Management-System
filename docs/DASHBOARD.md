# Dashboard summary widgets

The authenticated dashboard presents four inventory summaries:

- **Total components**: count of active inventory records.
- **Stock value**: sum of quantity multiplied by unit price.
- **Low stock items**: count of active components at or below their reorder
  level, excluding components with zero quantity.
- **Recently added**: up to five active components ordered by creation time,
  newest first.

Each recently added item is clickable and opens the same component details
view as the inventory table. The dashboard and inventory list are refreshed
together after an inventory change so the widgets remain current.

The dashboard also renders two charts:

- **Stock by category**: a bar chart of current units grouped by category.
- **Stock added over time**: a bar chart grouped by the date components were
  added. This uses the available creation history; a separate stock-movement
  history is not stored by the current data model.
