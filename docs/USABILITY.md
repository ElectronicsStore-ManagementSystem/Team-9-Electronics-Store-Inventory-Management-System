# New Staff Usability Check

This checklist verifies requirement EIMS-NF-003 for a staff member using the
application for the first time without formal training.

## Search a component

1. Sign in and read the **Quick start** instructions.
2. Type a component name, SKU, or category in **Search inventory**.
3. Select a component name in the results table to view its details.

The search updates shortly after typing, and pressing **Enter** runs the search
immediately. An empty result explains that filters can be changed or cleared.

## Add a component

Users with `ADMIN` or `MANAGER` permissions:

1. Select **Add component**.
2. Complete the labeled fields using the helper text below each field.
3. Select **Save component** and confirm the success message and generated SKU.

The form focuses the component name field when opened, trims text input, marks
blank required fields, and displays server validation errors without losing the
entered values.

Users with `STAFF` permissions can search and review inventory. The Quick start
guide explains that a manager must add new stock, matching the application's
role permissions.

## Acceptance timing

For a release check, record the time from the user's first screen view to:

- finding and opening the requested component; and
- completing the add flow, when the user has `ADMIN` or `MANAGER` permissions.

Each task passes when completed within five minutes without formal training.
